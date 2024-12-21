from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID, uuid4
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    SUPER_ADMIN = "super_admin"

class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    role: Role = Role.USER
    
class UserCreate(UserBase):
    password: str
    role: Optional[Role] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "username": "johndoe",
                "password": "securepassword123",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+1234567890",
                "bio": "Software developer with 5 years of experience",
                "profile_picture_url": "https://example.com/profile.jpg"
            }
        }

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    role: Optional[Role] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+1234567890",
                "bio": "Updated bio information",
                "profile_picture_url": "https://example.com/new-profile.jpg",
                "role": "user"
            }
        }

class User(UserBase):
    id: UUID = Field(default_factory=uuid4)
    hashed_password: str
    reset_token: Optional[str] = None
    reset_token_expires: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]
    bio: Optional[str]
    profile_picture_url: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "john.doe@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "+1234567890",
                "bio": "Software developer with 5 years of experience",
                "profile_picture_url": "https://example.com/profile.jpg",
                "is_active": True,
                "is_verified": True,
                "created_at": "2024-03-18T12:00:00Z",
                "updated_at": "2024-03-18T12:00:00Z"
            }
        }

class LoginData(BaseModel):
    email: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "userpassword"
            }
        }
        
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
