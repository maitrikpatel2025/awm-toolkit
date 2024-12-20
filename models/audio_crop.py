from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import time

class AudioCropRequest(BaseModel):
    media_url: HttpUrl = Field(..., description="URL of the input audio file")
    start_time: str = Field(..., description="Start time in format HH:MM:SS or MM:SS")
    end_time: str = Field(..., description="End time in format HH:MM:SS or MM:SS")
    webhook_url: Optional[HttpUrl] = None
    id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "media_url": "https://example.com/audio.mp3",
                "start_time": "00:01:30",
                "end_time": "00:02:45",
                "webhook_url": "https://example.com/webhook",
                "id": "1234567890"
            }
        } 