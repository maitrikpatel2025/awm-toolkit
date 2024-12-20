from fastapi import APIRouter, Depends, HTTPException, Header, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta
import jwt
from jwt import PyJWTError

from models.user_model import UserCreate, UserUpdate, UserResponse, LoginData, TokenResponse
from services.user_service import UserService
from services.email_service import EmailService
from pydantic import EmailStr

router = APIRouter()
user_service = UserService()
email_service = EmailService()

# JWT Configuration
SECRET_KEY = "your-secret-key"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

async def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify Bearer token and return user"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        user = user_service.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
            
        return user
            
    except PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_access_token(data: dict):
    """Create JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/users/register",
            summary="Register a new user",
            description="Register a new user",
            response_description="User registered successfully",
            tags=["users"])
async def register_user(user_data: UserCreate):
    """Register a new user"""
    user = user_service.create_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password
    )
    # Send welcome email
    await email_service.send_welcome_email(user_data.email, user_data.username)
    return user

@router.post("/users/login",
            summary="Login user and return access token",
            description="Login user and return access token",
            response_description="Access token",
            tags=["users"])
async def login(login_data: LoginData):
    """Login user and return access token"""
    user = user_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": user["id"]})
    return TokenResponse(access_token=access_token)

@router.get("/users/me",
            summary="Get current authenticated user information",
            description="Get current authenticated user information",
            response_description="User information",
            tags=["users"])
async def get_current_user_info(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get current authenticated user information"""
    return current_user

@router.put("/users/{user_id}",
            summary="Update user information",
            description="Update user information",
            response_description="User information updated successfully",
            tags=["users"])
async def update_user_info(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Update user information"""
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
    return user_service.update_user(user_id, user_data.dict(exclude_unset=True))

@router.delete("/users/{user_id}",
            summary="Delete user",
            description="Delete user",
            response_description="User deleted successfully",
            tags=["users"])
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user_from_token)
):
    """Delete user"""
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")
    
    if user_service.delete_user(user_id):
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found") 

@router.post("/users/forgot-password",
            summary="Request password reset",
            description="Request password reset",
            response_description="Password reset email sent",
            tags=["users"])
async def forgot_password(email: EmailStr):
    """Request password reset"""
    reset_token = user_service.create_password_reset_token(email)
    if reset_token:
        await email_service.send_password_reset_email(email, reset_token)
        return {"message": "Password reset email sent"}
    raise HTTPException(status_code=404, detail="User not found")

@router.post("/users/reset-password/{token}",
            summary="Reset password using token",
            description="Reset password using token",
            response_description="Password reset successful",
            tags=["users"])
async def reset_password(token: str, new_password: str):
    """Reset password using token"""
    if user_service.reset_password(token, new_password):
        return {"message": "Password reset successful"}
    raise HTTPException(status_code=400, detail="Invalid or expired reset token") 