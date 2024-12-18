from typing import Optional
from pydantic import BaseModel


class KeyGenRequest(BaseModel):
    description: Optional[str] = None
    expires_in_days: Optional[int] = 365
    rate_limit: Optional[int] = 100


class KeyInfoResponse(BaseModel):
    created_at: str
    expires_at: Optional[str]
    description: Optional[str]
    is_active: bool
    rate_limit: int
    today_usage: int


class KeyResponse(BaseModel):
    message: str
    api_key: Optional[str] = None