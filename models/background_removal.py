from typing import Optional
from pydantic import BaseModel, HttpUrl
from enum import Enum

class ImageFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"

class BackgroundRemovalRequest(BaseModel):
    media_url: HttpUrl
    output_format: Optional[ImageFormat] = ImageFormat.PNG
    webhook_url: Optional[str] = None
    id: Optional[str] = None



    class Config:
        json_schema_extra = {
            "example": {
                "media_url": "https://example.com/media.png",
                "output_format": "png",
                "webhook_url": "https://example.com/webhook",
                "id": "123"
            }
        }