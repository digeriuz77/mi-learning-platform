"""
Authentication models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    display_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """User profile with stats"""
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserProfileWithStats(BaseModel):
    """User profile with statistics"""
    id: str
    user_id: str
    display_name: Optional[str] = None
    total_points: int = 0
    level: int = 1
    modules_completed: int = 0
    change_talk_evoked: int = 0
    reflections_offered: int = 0
    technique_mastery: dict = {}
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime] = None

    class Config:
        from_attributes = True
