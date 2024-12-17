from fastapi import Header, HTTPException
import os

async def authenticate(x_api_key: str = Header(..., description="API Key for authentication")):
    """FastAPI dependency for authentication"""
    if x_api_key != os.environ.get('API_KEY'):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_api_key
