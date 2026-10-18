import time
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any, Callable, Optional

import cv2
import numpy as np
from PIL import Image

from src.core.config import OUTPUTS_DIR
from src.services.lama_service import inpaint_with_lama

def get_ffmpeg_binary() -> str:
    """Finds available FFmpeg executable."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'

def get_video_metadata(video_path: Path) -> Dict[str, Any]:
    """Extracts FPS, dimensions, total frame count, and duration from video."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to decode video at {video_path.name}. Unsupported or corrupt format.")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = (total_frames / fps) if fps > 0 and total_frames > 0 else 0.0
    cap.release()
    
    return {
        "fps": fps,
        "width": w,
        "height": h,
        "total_frames": total_frames,
        "duration": duration
    }

def extract_frame_at_timestamp(video_path: Path, timestamp_sec: float) -> Tuple[np.ndarray, int, int]:
    """Reads a single BGR frame at the requested timestamp in seconds."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Failed to open video stream.")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    target_frame = min(max(0, int(timestamp_sec * fps)), max(0, total_frames - 1))
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ok, frame = cap.read()
    cap.release()
    
    if not ok or frame is None:
        raise ValueError(f"Could not read frame at {timestamp_sec:.2f}s.")
        
    return frame, target_frame, total_frames

def create_box_mask(w: int, h: int, x_pct: float, y_pct: float, w_pct: float, h_pct: float, padding_px: int = 0) -> np.ndarray:
    """
    Computes a binary uint8 mask (255 inside box, 0 outside) from percentage coordinates.
    Optional padding expands the mask outward to catch faint watermark drop-shadows.
    """
    xx = min(max(0, int(w * (x_pct / 100.0))), w - 1)
    yy = min(max(0, int(h * (y_pct / 100.0))), h - 1)
    ww = min(max(1, int(w * (w_pct / 100.0))), w - xx)
    hh = min(max(1, int(h * (h_pct / 100.0))), h - yy)

    mask = np.zeros((h, w), dtype=np.uint8)
    mask[yy:yy + hh, xx:xx + ww] = 255

    if padding_px > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * padding_px + 1, 2 * padding_px + 1))
        mask = cv2.dilate(mask, kernel, iterations=1)

    return mask

def repair_frame_with_blend(frame_bgr: np.ndarray, mask: np.ndarray, method: str = 'AI LaMa', radius: int = 5, feather_px: int = 3) -> np.ndarray:
    """
    Inpaints frame using AI LaMa or OpenCV Telea.
    Applies Gaussian soft-alpha blending along borders to prevent visible seams.
    """
    if method == 'AI LaMa':
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        repaired_rgb = inpaint_with_lama(rgb, mask)
        repaired_bgr = cv2.cvtColor(repaired_rgb, cv2.COLOR_RGB2BGR)

        if feather_px > 0:
            k = 2 * feather_px + 1
            soft_mask = cv2.GaussianBlur(mask, (k, k), 0).astype(np.float32) / 255.0
            soft_mask = np.expand_dims(soft_mask, axis=-1)
            blended = (repaired_bgr.astype(np.float32) * soft_mask + 
                       frame_bgr.astype(np.float32) * (1.0 - soft_mask))
            return np.clip(blended, 0, 255).astype(np.uint8)
        return repaired_bgr
    else:
        # OpenCV Telea
        bin_mask = (mask > 127).astype(np.uint8) * 255
        return cv2.inpaint(frame_bgr, bin_mask, float(radius), cv2.INPAINT_TELEA)

def process_video_pipeline(
    source_path: Path,
    output_filename: str,
    x: float, y: float, w: float, h: float,
    model: str,
    radius: int,
    feather: int,
    padding: int,
    crf: int,
    progress_callback: Optional[Callable[[float, int, int, float, float], None]] = None
) -> Path:
    """
    Frame-by-frame video inpainting with FFmpeg audio muxing and fallback.
    """
    meta = get_video_metadata(source_path)
    fps = meta["fps"]
    width = meta["width"]
    height = meta["height"]
    total_frames = meta["total_frames"]

    mask = create_box_mask(width, height, x, y, w, h, padding_px=padding)

    temp_dir = Path(tempfile.mkdtemp(prefix='wm_render_'))
    silent_temp = temp_dir / 'rendered_silent.mp4'
    out_path = OUTPUTS_DIR / output_filename

    writer = cv2.VideoWriter(str(silent_temp), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Failed to initialize OpenCV VideoWriter encoder.")

    cap = cv2.VideoCapture(str(source_path))
    count = 0
    t_start = time.time()

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            clean_frame = repair_frame_with_blend(frame, mask, method=model, radius=radius, feather_px=feather)
            writer.write(clean_frame)
            count += 1

            if progress_callback and total_frames > 0 and (count % 2 == 0 or count == total_frames):
                elapsed = time.time() - t_start
                fps_proc = count / elapsed if elapsed > 0 else 0
                eta_sec = (total_frames - count) / fps_proc if fps_proc > 0 else 0
                prog = min(count / total_frames, 0.99)
                progress_callback(prog, count, total_frames, fps_proc, eta_sec)
    finally:
        cap.release()
        writer.release()

    # Audio Muxing via FFmpeg
    ffmpeg = get_ffmpeg_binary()
    cmd = [
        ffmpeg, '-y',
        '-i', str(silent_temp),
        '-i', str(source_path),
        '-map', '0:v:0',
        '-map', '1:a:0?',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', str(int(crf)),
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        '-movflags', '+faststart',
        str(out_path)
    ]

    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=7200)
    if p.returncode or not out_path.exists():
        # Fallback without audio
        fallback_cmd = [
            ffmpeg, '-y',
            '-i', str(silent_temp),
            '-an',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', str(int(crf)),
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            str(out_path)
        ]
        p2 = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=7200)
        if p2.returncode or not out_path.exists():
            raise RuntimeError(f"FFmpeg encoding failed: {(p.stderr or p2.stderr)[-1000:]}")

    return out_path

def process_image_pipeline(
    source_path: Path,
    output_filename: str,
    x: float, y: float, w: float, h: float,
    model: str,
    radius: int,
    feather: int,
    padding: int
) -> Path:
    """Performs inpainting on a static image and saves output."""
    with Image.open(source_path) as im:
        rgb = np.array(im.convert("RGB"))
        frame_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    height, width = frame_bgr.shape[:2]
    mask = create_box_mask(width, height, x, y, w, h, padding_px=padding)
    repaired_bgr = repair_frame_with_blend(frame_bgr, mask, method=model, radius=radius, feather_px=feather)

    out_path = OUTPUTS_DIR / output_filename
    cv2.imwrite(str(out_path), repaired_bgr)
    return out_path
