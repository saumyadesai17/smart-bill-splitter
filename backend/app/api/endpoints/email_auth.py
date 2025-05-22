from typing import Any, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session as DbSession
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.user import UserCreate
from app.schemas.token import Token

# Update imports to use the new modular services
from app.services.auth_service import authenticate_user
from app.services.user import create_user

router = APIRouter()

class EmailSignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

@router.post("/signup", response_model=Token)
def signup_with_email(
    signup_data: EmailSignupRequest,
    db: DbSession = Depends(get_db)
) -> Any:
    """Register a new user with email/password authentication"""
    user_create = UserCreate(
        username=signup_data.username,
        email=signup_data.email,
        password=signup_data.password,
        full_name=signup_data.full_name
    )
    
    user = create_user(db, user_create)
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id, "auth_provider": "email"},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/login", response_model=Token)
def login_with_email(
    db: DbSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """Login with email/username and password"""
    user = authenticate_user(db, form_data.username, form_data.password, provider="email")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
        )
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id, "auth_provider": "email"},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}