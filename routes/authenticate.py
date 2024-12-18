from fastapi import APIRouter, Depends, HTTPException
from services.key_management import KeyManager
from models.key_manager import KeyGenRequest, KeyResponse, KeyInfoResponse
from app_utils import verify_api_key

router = APIRouter()
key_manager = KeyManager()

@router.get("/authenticate",
    summary="Verify API key",
    description="Endpoint to verify if the provided API key is valid",
    tags=["Authentication"])
async def authenticate_endpoint(api_key: str = Depends(verify_api_key)):
    return {"message": "Authorized", "endpoint": "/authenticate", "code": 200}

@router.post("/generate-key",
    summary="Generate API key",
    description="Generate a new API key for authentication",
    response_model=KeyResponse,
    tags=["Authentication"])
async def generate_key(request: KeyGenRequest):
    try:
        api_key = key_manager.generate_key(
            description=request.description,
            expires_in_days=request.expires_in_days,
            rate_limit=request.rate_limit
        )
        return KeyResponse(
            message="API key generated successfully",
            api_key=api_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/revoke-key/{api_key}",
    summary="Revoke API key",
    description="Revoke an existing API key",
    response_model=KeyResponse,
    tags=["Authentication"])
async def revoke_key(api_key: str):
    if key_manager.revoke_key(api_key):
        return KeyResponse(message="API key revoked successfully")
    raise HTTPException(status_code=404, detail="API key not found")

@router.get("/key-info/{api_key}",
    summary="Get API key information",
    description="Get detailed information about an API key",
    response_model=KeyInfoResponse,
    tags=["Authentication"])
async def get_key_info(api_key: str):
    try:
        return key_manager.get_key_info(api_key)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
