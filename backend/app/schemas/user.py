from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

class UserBase(BaseModel):
    """Base user schema with optional fields to support different auth flows"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    full_name: Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def username_must_not_be_empty_if_provided(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Username must not be empty if provided")
        return v

class UserCreate(UserBase):
    """User creation schema supporting multiple auth methods"""
    password: Optional[str] = None
    firebase_uid: Optional[str] = None  # For phone auth
    google_id: Optional[str] = None     # For Google auth
    
    @field_validator('password')
    @classmethod
    def password_must_be_strong_if_provided(cls, v):
        if v is not None:
            if not v:
                raise ValueError("Password must not be empty if provided")
            if len(v) < 6:
                raise ValueError("Password must be at least 6 characters long")
        return v
    
    # At least one authentication method must be provided
    # This validation will be handled in the service layer

class ProfileComplete(BaseModel):
    """Schema for completing a profile after initial auth"""
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    
    @field_validator('username')
    @classmethod
    def username_must_not_be_empty_if_provided(cls, v):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Username must not be empty if provided")
        return v

class UserUpdate(BaseModel):
    """Schema for updating a user"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    
    @field_validator('password')
    @classmethod
    def password_update_must_be_strong_if_provided(cls, v: Optional[str]):
        if v is not None:
            if not v:
                raise ValueError("Password must not be empty if provided for update")
            if len(v) < 6:
                raise ValueError("Password must be at least 6 characters long")
        return v
    
    @field_validator('username')
    @classmethod
    def username_update_must_not_be_empty_if_provided(cls, v: Optional[str]):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Username must not be empty if provided for update")
        return v

class User(BaseModel):
    """Response schema for a user"""
    id: int
    username: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    profile_completed: bool = False
    auth_providers: List[str] = []
    created_at: datetime = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserInDB(User):
    """Internal schema with sensitive fields"""
    hashed_password: Optional[str] = None
    firebase_uid: Optional[str] = None
    google_id: Optional[str] = None