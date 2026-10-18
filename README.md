# Local Video Cleanup Studio v2

## Update your existing Antigravity workspace
Replace your existing `app.py` and `requirements.txt` with these files, then in the project terminal run:

PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

If PowerShell activation is blocked, use CMD:
```bat
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:7860. Stop an old instance with Ctrl+C first if port 7860 is already in use.

## Connect AI LaMa
In the same activated `.venv` used to run the app:
```powershell
python -m pip install simple-lama-inpainting
```
Restart `python app.py`, choose **AI LaMa**, then click Repair and export. The first use may download pretrained weights; after that inference runs locally. The package API accepts a PIL RGB image and a grayscale mask whose white (255) pixels indicate what should be filled. See https://pypi.org/project/simple-lama-inpainting/.

The package can use CUDA when a compatible PyTorch/CUDA installation is available, otherwise it runs on CPU. CPU video processing may be slow. For GPU-specific PyTorch setup, consult https://pytorch.org/get-started/locally/.

## Modern SaaS UI & Features

### 🎬 Interactive On-Canvas Bounding Box
- **Direct Visual Drag & Resize**: Directly click and drag the bounding box on the video or image canvas.
- **8 Resize Handles**: Corner and edge handles (`nw, n, ne, e, se, s, sw, w`) allow pixel-perfect sizing.
- **3x3 Rule-of-Thirds Grid**: Clean dashed alignment guidelines inside the box.
- **Click & Drag Anywhere to Create**: Drawing outside the active box instantly creates a new selection area.

### ⚡ Timeline Scrubber & 1-Frame Fast Test
- **Video Scrubber**: Scrub through any point in the video timeline to position the watermark area accurately.
- **⚡ Quick Test on Current Frame**: Inpaint just the active preview frame in ~1 second to verify AI LaMa or OpenCV Telea results before running full video export.

### 🚀 High-Fidelity Processing
- **Edge Feathering (Blend)**: Gaussian soft-alpha blending along edges prevents visible seams with the untouched original content.
- **Mask Padding**: Dilates the mask boundary to catch translucent watermark drop-shadows.
- **Audio Preservation & CRF Control**: Muxes original AAC audio and re-encodes with H.264 CRF control. Output files are saved in `outputs/`.

## Limitations
- One fixed rectangle is applied to all video frames; it does not track a moving logo.
- OpenCV Telea is basic and can smear complex scenery.
- LaMa is an image inpainting model applied independently to frames, not a temporal video model, so flicker may occur.
- Video dimensions and nominal FPS are preserved but video is re-encoded. Audio is retained when supported by FFmpeg.
- This edits visible pixels only, not invisible provenance signals.
- The app is bound to localhost; do not expose it publicly.
