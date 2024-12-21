from fastapi import APIRouter, Depends, HTTPException, Header, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta
import jwt
from jwt import PyJWTError

from models.user_model import UserCreate, UserUpdate, UserResponse, LoginData, TokenResponse, Role
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

def check_user_role(current_user: dict, required_roles: list[Role]):
    """Check if user has required role"""
    if current_user.get("role") not in required_roles:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to perform this action"
        )

async def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify Bearer token and return user"""
    try:
        token = credentials.credentials
        
        # Check if token is blacklisted
        if user_service.is_token_blacklisted(token):
            raise HTTPException(status_code=401, detail="Token has been invalidated")
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        user = user_service.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
            
        # Add role to user dict if not present
        if "role" not in user:
            user["role"] = Role.USER
            
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
            description="Register a new user (always creates with USER role)",
            response_description="User registered successfully",
            tags=["users"])
async def register_user(user_data: UserCreate):
    """Register a new user"""

    # Check if user already exists
    existing_user = user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")  
    
    # Create user with USER role only
    user = user_service.create_user(    
        email=user_data.email,
        username=user_data.username,
        password=user_data.password
        # role parameter removed as it's handled in service
    )
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
    # Check if user is updating their own info
    is_self_update = current_user["id"] == user_id
    current_user_role = Role(current_user["role"])
    
    # If not self-update, require admin privileges
    if not is_self_update and current_user_role not in [Role.ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update other users"
        )
    
    # Handle role updates
    if user_data.role is not None:
        # Only super_admin can change roles
        if current_user_role != Role.SUPER_ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only super admins can change user roles"
            )
        
        # Prevent assigning super_admin role
        if user_data.role == Role.SUPER_ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Cannot assign super_admin role"
            )
    
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
    # Allow self-deletion or admin deletion
    if current_user["id"] != user_id and Role(current_user["role"]) not in [Role.ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to delete this user"
        )
    
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

@router.get("/users",
            summary="Get all users (Admin only)",
            description="Get all users in the system",
            response_description="List of users",
            tags=["users"])
async def get_all_users(
    current_user: dict = Depends(get_current_user_from_token)
):
    """Get all users (Admin only)"""
    if Role(current_user["role"]) not in [Role.ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Only admins can view all users"
        )
    return user_service.get_all_users()

@router.post("/users/create-super-admin",
            summary="Create a super admin user",
            description="Create a new super admin user (Only accessible by existing super admins)",
            response_description="Super admin user created successfully",
            tags=["users"])
async def create_super_admin(
    user_data: UserCreate
):
    """Create a super admin user"""
    super_admin_user = user_service.get_user_by_email(user_data.email)
    if super_admin_user:
        raise HTTPException(status_code=400, detail="Super admin user already exists")  
    # Create user with SUPER_ADMIN role
    user = user_service.create_user(
        email=user_data.email,
        username=user_data.username,        
        password=user_data.password,
        role=Role.SUPER_ADMIN.value
    )
    
    await email_service.send_welcome_email(user_data.email, user_data.username)
    return user

@router.post("/users/create-admin",
            summary="Create an admin user",
            description="Create a new admin user (Only accessible by super admins)",
            response_description="Admin user created successfully",
            tags=["users"])
async def create_admin(
    user_data: UserCreate,
):
    """Create an admin user"""
    # Check if the current user is a super admin
    admin_user = user_service.get_user_by_email(user_data.email)
    if admin_user:
        raise HTTPException(status_code=400, detail="Super admin user already exists")
    
    # Create user with ADMIN role
    user = user_service.create_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        role=Role.ADMIN.value
    )
    
    await email_service.send_welcome_email(user_data.email, user_data.username)
    return user

@router.post("/users/logout",
            summary="Logout user",
            description="Invalidate the current access token",
            response_description="Logout successful",
            tags=["users"])
async def logout(
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Logout user by blacklisting their current token"""
    token = credentials.credentials
    
    try:
        # Decode token to get expiry
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_expiry = datetime.fromtimestamp(payload["exp"])
        
        # Add token to blacklist
        if user_service.blacklist_token(token, token_expiry):
            return {"message": "Successfully logged out"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Error logging out"
            )
    except PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )