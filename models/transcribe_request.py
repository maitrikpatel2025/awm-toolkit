from typing import Dict, Any, Optional
from pydantic import BaseModel, HttpUrl
from enum import Enum

# Pydantic base models
class OutputType(str, Enum):
    transcript = "transcript"
    srt = "srt"
    vtt = "vtt"
    ass = "ass"

class TranscribeRequest(BaseModel):
    media_url: HttpUrl
    output: Optional[OutputType] = OutputType.transcript
    webhook_url: Optional[HttpUrl] = None
    max_chars: Optional[int] = 56
    id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "media_url": "https://example.com/media.mp4",
                "output": "transcript",
                "webhook_url": "https://example.com/webhook",
                "max_chars": 56,
                "id": "123"
            }
        }