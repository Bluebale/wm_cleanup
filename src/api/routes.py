import time
import uuid
import threading
from pathlib import Path
from typing import Dict, Any

import cv2
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

from src.core.config import UPLOADS_DIR, OUTPUTS_DIR, MAX_UPLOAD_SIZE_BYTES, TASK_TTL_SECONDS
from src.core.security import sanitize_filename, safe_resolve_path, validate_media_type
from src.models.schemas import TestFrameRequest, ProcessMediaRequest, UploadResponse
from src.services.media_service import (
    get_video_metadata,
    extract_frame_at_timestamp,
    create_box_mask,
    repair_frame_with_blend,
    process_video_pipeline,
    process_image_pipeline
)

router = APIRouter(prefix="/api", tags=["Media Processing"])

# Thread-safe in-memory task registry
TASKS: Dict[str, Dict[str, Any]] = {}
TASKS_LOCK = threading.Lock()
ACTIVE_SESSION: Dict[str, Path] = {}

def prune_expired_tasks():
    """Removes tasks older than TASK_TTL_SECONDS to avoid memory leaks."""
    now = time.time()
    with TASKS_LOCK:
        expired = [tid for tid, t in TASKS.items() if now - t.get("created_at", now) > TASK_TTL_SECONDS]
        for tid in expired:
            del TASKS[tid]

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Local Watermark Studio", "timestamp": time.time()}

@router.post("/upload", response_model=UploadResponse)
async def upload_media(file: UploadFile = File(...)):
    """
    Secure file upload with filename sanitization, extension validation, and size capping.
    """
    prune_expired_tasks()

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")

    media_type = validate_media_type(file.filename)
    safe_name = sanitize_filename(file.filename)
    save_path = safe_resolve_path(UPLOADS_DIR, safe_name)

    # Stream file to disk with strict size check
    total_bytes = 0
    chunk_size = 1024 * 1024 # 1MB chunks
    with open(save_path, "wb") as out_f:
        while chunk := await file.read(chunk_size):
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                out_f.close()
                save_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Uploaded file exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
                )
            out_f.write(chunk)

    ACTIVE_SESSION["current_file"] = save_path

    # Extract media metadata
    width, height, duration, fps, frames = 0, 0, 0.0, 30.0, 0
    if media_type == "video":
        try:
            meta = get_video_metadata(save_path)
            width = meta["width"]
            height = meta["height"]
            duration = meta["duration"]
            fps = meta["fps"]
            frames = meta["total_frames"]
        except Exception as e:
            save_path.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Corrupt video file: {e}")
    else:
        try:
            with Image.open(save_path) as im:
                width, height = im.size
        except Exception as e:
            save_path.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Corrupt image file: {e}")

    return UploadResponse(
        status="ok",
        media_type=media_type,
        filename=safe_name,
        file_url=f"/uploads/{safe_name}",
        width=width,
        height=height,
        duration=duration,
        fps=fps,
        total_frames=frames
    )

@router.post("/test-frame")
async def test_frame(req: TestFrameRequest):
    """
    Renders inpainting on a single frame in ~1 second for fast user verification.
    """
    target_file = ACTIVE_SESSION.get("current_file")
    if req.filename:
        target_file = safe_resolve_path(UPLOADS_DIR, req.filename)
        
    if not target_file or not target_file.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active media file found. Please upload first.")

    t0 = time.time()
    if req.media_type == "video":
        frame_bgr, target_frame, _ = extract_frame_at_timestamp(target_file, req.timestamp)
    else:
        with Image.open(target_file) as im:
            rgb = np.array(im.convert("RGB"))
            frame_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    h, w = frame_bgr.shape[:2]
    mask = create_box_mask(w, h, req.x, req.y, req.w, req.h, padding_px=req.padding)
    repaired_bgr = repair_frame_with_blend(frame_bgr, mask, method=req.model, radius=req.radius, feather_px=req.feather)

    out_name = f"test_frame_{uuid.uuid4().hex[:8]}.png"
    out_path = safe_resolve_path(OUTPUTS_DIR, out_name)
    cv2.imwrite(str(out_path), repaired_bgr)
    elapsed = time.time() - t0

    return {
        "status": "ok",
        "file_url": f"/outputs/{out_name}",
        "elapsed": elapsed
    }

def _bg_video_worker(task_id: str, file_path: Path, p: ProcessMediaRequest):
    def update_progress(prog, curr, total, fps, eta):
        with TASKS_LOCK:
            if task_id in TASKS:
                TASKS[task_id]["progress"] = prog
                TASKS[task_id]["current_frame"] = curr
                TASKS[task_id]["total_frames"] = total
                TASKS[task_id]["message"] = f"Frame {curr}/{total} ({fps:.1f} fps, ETA {eta:.0f}s)"

    out_name = f"{file_path.stem}_cleaned_{uuid.uuid4().hex[:6]}.mp4"
    try:
        t0 = time.time()
        final_path = process_video_pipeline(
            source_path=file_path,
            output_filename=out_name,
            x=p.x, y=p.y, w=p.w, h=p.h,
            model=p.model,
            radius=p.radius,
            feather=p.feather,
            padding=p.padding,
            crf=p.crf,
            progress_callback=update_progress
        )
        total_time = time.time() - t0
        with TASKS_LOCK:
            TASKS[task_id] = {
                "status": "complete",
                "progress": 1.0,
                "filename": out_name,
                "file_url": f"/outputs/{out_name}",
                "download_url": f"/api/download/{out_name}",
                "message": f"Successfully cleaned video in {total_time:.1f}s. Audio retained."
            }
    except Exception as e:
        with TASKS_LOCK:
            TASKS[task_id] = {
                "status": "error",
                "error": str(e)
            }

def _bg_image_worker(task_id: str, file_path: Path, p: ProcessMediaRequest):
    out_name = f"{file_path.stem}_cleaned_{uuid.uuid4().hex[:6]}.png"
    try:
        t0 = time.time()
        final_path = process_image_pipeline(
            source_path=file_path,
            output_filename=out_name,
            x=p.x, y=p.y, w=p.w, h=p.h,
            model=p.model,
            radius=p.radius,
            feather=p.feather,
            padding=p.padding
        )
        total_time = time.time() - t0
        with TASKS_LOCK:
            TASKS[task_id] = {
                "status": "complete",
                "progress": 1.0,
                "filename": out_name,
                "file_url": f"/outputs/{out_name}",
                "download_url": f"/api/download/{out_name}",
                "message": f"Image cleaned in {total_time:.2f}s using {p.model}."
            }
    except Exception as e:
        with TASKS_LOCK:
            TASKS[task_id] = {
                "status": "error",
                "error": str(e)
            }

@router.post("/process")
async def process_media(req: ProcessMediaRequest):
    """
    Initiates asynchronous media inpainting in background thread.
    """
    prune_expired_tasks()
    target_file = ACTIVE_SESSION.get("current_file")
    if req.filename:
        target_file = safe_resolve_path(UPLOADS_DIR, req.filename)

    if not target_file or not target_file.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active media file found.")

    task_id = uuid.uuid4().hex
    with TASKS_LOCK:
        TASKS[task_id] = {
            "status": "processing",
            "progress": 0.02,
            "current_frame": 0,
            "total_frames": 1,
            "message": "Initializing inpainting engine...",
            "created_at": time.time()
        }

    if req.media_type == "video":
        t = threading.Thread(target=_bg_video_worker, args=(task_id, target_file, req), daemon=True)
    else:
        t = threading.Thread(target=_bg_image_worker, args=(task_id, target_file, req), daemon=True)
    
    t.start()
    return {"status": "started", "task_id": task_id}

@router.get("/progress/{task_id}")
async def get_task_progress(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task ID not found.")
    return task

@router.get("/download/{filename}")
async def download_output_file(filename: str):
    """
    Protected download endpoint with traversal defense.
    """
    safe_path = safe_resolve_path(OUTPUTS_DIR, filename)
    if not safe_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requested file does not exist.")
    
    return FileResponse(
        path=str(safe_path),
        filename=safe_path.name,
        media_type="application/octet-stream"
    )
