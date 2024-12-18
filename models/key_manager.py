from typing import Optional
from pydantic import BaseModel

class KeyGenRequest(BaseModel):
    description: Optional[str] = None
    expires_in_days: Optional[int] = 365
    rate_limit: Optional[int] = 100

    class Config:
        json_schema_extra = {
            "example": {
                "description": "API key for accessing the transcription service",
                "expires_in_days": 30,
                "rate_limit": 500
            }
        }

class KeyInfoResponse(BaseModel):
    created_at: str
    expires_at: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    rate_limit: int
    today_usage: int

    class Config:
        json_schema_extra = {
            "example": {
                "created_at": "2024-12-18T12:00:00Z",
                "expires_at": "2025-12-18T12:00:00Z",
                "description": "Key for accessing transcription API",
                "is_active": True,
                "rate_limit": 1000,
                "today_usage": 150
            }
        }

class KeyResponse(BaseModel):
    message: str
    api_key: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "API key generated successfully",
                "api_key": "abcd1234efgh5678"
            }
        }
