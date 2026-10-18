from typing import Optional
from pydantic import BaseModel, Field

class TestFrameRequest(BaseModel):
    media_type: str = Field(default="video", pattern="^(video|image)$")
    filename: Optional[str] = None
    timestamp: float = Field(default=0.0, ge=0.0)
    x: float = Field(default=75.0, ge=0.0, le=100.0)
    y: float = Field(default=80.0, ge=0.0, le=100.0)
    w: float = Field(default=18.0, ge=0.5, le=100.0)
    h: float = Field(default=12.0, ge=0.5, le=100.0)
    model: str = Field(default="AI LaMa", pattern="^(AI LaMa|OpenCV Telea)$")
    radius: int = Field(default=5, ge=1, le=25)
    feather: int = Field(default=3, ge=0, le=15)
    padding: int = Field(default=2, ge=0, le=20)

class ProcessMediaRequest(BaseModel):
    media_type: str = Field(default="video", pattern="^(video|image)$")
    filename: Optional[str] = None
    x: float = Field(default=75.0, ge=0.0, le=100.0)
    y: float = Field(default=80.0, ge=0.0, le=100.0)
    w: float = Field(default=18.0, ge=0.5, le=100.0)
    h: float = Field(default=12.0, ge=0.5, le=100.0)
    model: str = Field(default="AI LaMa", pattern="^(AI LaMa|OpenCV Telea)$")
    radius: int = Field(default=5, ge=1, le=25)
    feather: int = Field(default=3, ge=0, le=15)
    padding: int = Field(default=2, ge=0, le=20)
    crf: int = Field(default=18, ge=12, le=32)

class UploadResponse(BaseModel):
    status: str
    media_type: str
    filename: str
    file_url: str
    width: int
    height: int
    duration: float
    fps: float
    total_frames: int

class TaskProgressResponse(BaseModel):
    status: str
    progress: float = 0.0
    current_frame: int = 0
    total_frames: int = 0
    message: Optional[str] = None
    file_url: Optional[str] = None
    download_url: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None
