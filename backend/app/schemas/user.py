from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr
    
    @field_validator('username')
    @classmethod
    def username_must_not_be_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Username must not be empty")
        return v

class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    @classmethod
    def password_must_be_strong(cls, v):
        if not v: # Added check for empty string before length check
            raise ValueError("Password must not be empty")
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('password')
    @classmethod
    def password_update_must_be_strong_if_provided(cls, v: Optional[str]):
        if v is not None: # Only validate if password is provided
            if not v: # Check for empty string
                 raise ValueError("Password must not be empty if provided for update")
            if len(v) < 6:
                raise ValueError("Password must be at least 6 characters long if provided for update")
        return v
    
    @field_validator('username')
    @classmethod
    def username_update_must_not_be_empty_if_provided(cls, v: Optional[str]):
        if v is not None and (not v or v.strip() == ""):
            raise ValueError("Username must not be empty if provided for update")
        return v


class User(UserBase):
    id: int
    full_name: Optional[str] = None
    is_active: bool = True
    
    model_config = ConfigDict(from_attributes=True)

class UserInDB(User):
    hashed_password: str