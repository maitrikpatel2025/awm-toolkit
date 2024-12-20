from typing import Dict, Any, Optional, List
from pydantic import BaseModel, HttpUrl, AnyUrl

# ... existing OutputType enum ...

class AudioUrl(BaseModel):
    audio_url: HttpUrl

class CombineAudioRequest(BaseModel):
    audio_urls: Optional[List[AudioUrl]] = None
    webhook_url: Optional[HttpUrl] = None
    id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "audio_urls": [
                    {"audio_url": "https://drive.google.com/uc?id=1iba3btMZepCrfLrxY3tESafHOx_g3dRQ"},
                    {"audio_url": "https://drive.google.com/uc?id=1iba3btMZepCrfLrxY3tESafHOx_g3dRQ"}
                ],
                "webhook_url": "https://example.com/webhook",
                "id": "2323"
            }
        }