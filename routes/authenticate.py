from fastapi import APIRouter, Depends, HTTPException
from services.key_management import KeyManager
from models.key_manager import KeyGenRequest, KeyResponse, KeyListResponse, KeyInfo
from app_utils import verify_api_key
from routes.user_routes import get_current_user_from_token

router = APIRouter()
key_manager = KeyManager()

async def current_user_id(api_key: str):
    user_id = key_manager.get_key_user_id(api_key)
    return user_id

@router.get("/authenticate",
    summary="Verify API key",
    description="Endpoint to verify if the provided API key is valid",
    tags=["Authentication"])
async def authenticate_endpoint(api_key: str = Depends(verify_api_key)):
    return {"message": "Authorized", "endpoint": "/authenticate", "code": 200}

@router.post("/generate-key",
    summary="Generate API key",
    response_model=KeyResponse,
    tags=["Authentication"])
async def generate_key(
    request: KeyGenRequest,
    current_user: dict = Depends(get_current_user_from_token)
):
    try:
        result = key_manager.generate_key(
            user_id=current_user["id"],
            key_name=request.key_name,
            description=request.description,
            expires_in_days=request.expires_in_days
        )
        return KeyResponse(
            message="API key generated successfully",
            key_name=result["key_name"],
            key_id=result["key_id"],
            api_key=result["api_key"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list-keys",
    summary="List user's API keys",
    response_model=KeyListResponse,
    tags=["Authentication"])
async def list_keys(current_user: dict = Depends(get_current_user_from_token)):
    """List all API keys for the current user"""
    try:
        keys = key_manager.get_user_keys(current_user["id"])
        return KeyListResponse(keys=keys)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/revoke-key/{key_id}",
    summary="Revoke API key",
    response_model=KeyResponse,
    tags=["Authentication"])
async def revoke_key(
    key_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Revoke an API key by its ID"""
    try:
        if key_manager.revoke_key(key_id, current_user["id"]):
            return KeyResponse(
                message="API key revoked successfully",
                key_id=key_id,
                key_name=""  # Key name is optional in response
            )
        raise HTTPException(status_code=404, detail="API key not found")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/key-info/{key_id}",
    summary="Get API key information",
    response_model=KeyInfo,
    tags=["Authentication"])
async def get_key_info(
    key_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get detailed information about an API key by its ID"""
    try:
        return key_manager.get_key_info(key_id, current_user["id"])
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
