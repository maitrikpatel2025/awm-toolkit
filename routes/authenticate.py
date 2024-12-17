from fastapi import APIRouter, Depends
from services.authentication import authenticate

router = APIRouter()

@router.get("/authenticate",
    summary="Verify API key",
    description="Endpoint to verify if the provided API key is valid",
    tags=["Authentication"])
async def authenticate_endpoint(api_key: str = Depends(authenticate)):
    return {"message": "Authorized", "endpoint": "/authenticate", "code": 200}
