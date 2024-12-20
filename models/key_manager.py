from typing import Optional, List
from pydantic import BaseModel

class KeyGenRequest(BaseModel):
    key_name: str
    description: Optional[str] = None
    expires_in_days: Optional[int] = 365

    class Config:
        json_schema_extra = {
            "example": {
                "key_name": "Production API Key",
                "description": "API key for accessing the transcription service",
                "expires_in_days": 30
            }
        }

class KeyInfo(BaseModel):
    key: str
    key_id: str
    key_name: str
    created_at: str
    expires_at: Optional[str] = None
    description: Optional[str] = None
    is_active: bool

    class Config:
        json_schema_extra = {
            "example": {
                "key": "abcd1234efgh5678",
                "key_name": "Production API Key",
                "created_at": "2024-12-18T12:00:00Z",
                "expires_at": "2025-12-18T12:00:00Z",
                "description": "Key for accessing transcription API",
                "is_active": True
            }
        }

class KeyResponse(BaseModel):
    message: str
    key_name: str
    key_id: str
    api_key: Optional[str] = None

class KeyListResponse(BaseModel):
    keys: List[KeyInfo]
