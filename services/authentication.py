from fastapi import Header, HTTPException, Request
from .key_management import KeyManager

key_manager = KeyManager()

async def authenticate(
    request: Request,
    x_api_key: str = Header(..., description="API Key for authentication")
):
    """FastAPI dependency for authentication"""
    if not key_manager.is_key_valid(x_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if not key_manager.check_rate_limit(x_api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
    # Log the API usage
    key_manager.log_usage(x_api_key, str(request.url))
    return x_api_key
