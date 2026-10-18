import re
import uuid
from pathlib import Path
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from src.core.config import ALLOWED_EXTS, ALLOWED_IMAGE_EXTS, ALLOWED_VIDEO_EXTS

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes user-provided filenames to prevent Directory Traversal & Command Injection.
    Strips directory separators, restricts to safe ASCII characters, and appends a UUID.
    """
    if not filename:
        return f"file_{uuid.uuid4().hex}"
    
    # Extract only the base name (no directory paths)
    base = Path(filename).name
    # Keep only safe alphanumeric characters, dashes, underscores, and dots
    safe_name = re.sub(r'[^a-zA-Z0-9_\.-]', '_', base)
    # Strip leading/trailing dots to prevent hidden files or extension tricks
    safe_name = safe_name.strip('.')
    
    suffix = Path(safe_name).suffix.lower()
    stem = Path(safe_name).stem[:40] # cap stem length
    
    unique_name = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    return unique_name

def safe_resolve_path(base_dir: Path, filename: str) -> Path:
    """
    Ensures the target file strictly resides within base_dir.
    Prevents path traversal attacks (e.g. ../../Windows/System32).
    """
    clean_name = Path(filename).name  # strictly enforce basename only
    target_path = (base_dir / clean_name).resolve()
    base_resolved = base_dir.resolve()
    
    try:
        # Python 3.9+ is_relative_to
        if not target_path.is_relative_to(base_resolved):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security violation: Path traversal detected."
            )
    except AttributeError:
        # Fallback for older python
        if not str(target_path).startswith(str(base_resolved)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security violation: Path traversal detected."
            )
            
    return target_path

def validate_media_type(filename: str) -> str:
    """
    Validates file extension against strict whitelists and returns 'video' or 'image'.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTS))}"
        )
    return "video" if ext in ALLOWED_VIDEO_EXTS else "image"

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Enforces industry-standard HTTP security headers.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "media-src 'self' data: blob:;"
        )
        return response
