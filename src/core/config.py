from pathlib import Path
from typing import Set

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"

UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# Security Limits
MAX_UPLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB limit
ALLOWED_IMAGE_EXTS: Set[str] = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'}
ALLOWED_VIDEO_EXTS: Set[str] = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v'}
ALLOWED_EXTS: Set[str] = ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS

# Server Settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7860
TASK_TTL_SECONDS = 3600  # Prune task records older than 1 hour
