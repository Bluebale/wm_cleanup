import sys
import webbrowser
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from src.core.config import (
    STATIC_DIR,
    TEMPLATES_DIR,
    UPLOADS_DIR,
    OUTPUTS_DIR,
    DEFAULT_HOST,
    DEFAULT_PORT
)
from src.core.security import SecurityHeadersMiddleware
from src.api.routes import router

app = FastAPI(
    title="Local Video & Image Cleanup Studio",
    description="Enterprise-grade local watermark, logo, and object removal powered by AI LaMa and OpenCV.",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None
)

# Enforce Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# Mount Static Assets & User Content Directories
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# Register API Router
app.include_router(router)

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

if __name__ == "__main__":
    url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"
    print(f"\n=======================================================")
    print(f"  Local Video Cleanup Studio v2.0 (Industry Standard)  ")
    print(f"  Access URL: {url}                                    ")
    print(f"  API Docs:   {url}/api/docs                           ")
    print(f"=======================================================\n")
    webbrowser.open(url)
    uvicorn.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT, log_level="info")
