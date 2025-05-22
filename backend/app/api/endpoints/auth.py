from typing import Any, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session as DbSession
from pydantic import BaseModel, EmailStr

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, User as UserSchema, ProfileComplete
from app.schemas.token import Token
from app.services.user import (
    authenticate_user, create_user, complete_profile,
    link_auth_method, unlink_auth_method
)

router = APIRouter()

class EmailSignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

@router.post("/signup/email", response_model=Token)
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

@router.post("/login/email", response_model=Token)
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

class PhoneVerifyRequest(BaseModel):
    id_token: str
    register_if_not_exists: bool = True
    username: Optional[str] = None

@router.post("/login/phone", response_model=Token)
def login_with_phone(
    auth_data: PhoneVerifyRequest,
    db: DbSession = Depends(get_db)
) -> Any:
    """Login or register with phone number via Firebase"""
    from app.services.firebase_auth import verify_firebase_token
    
    # Verify Firebase token
    decoded_token = verify_firebase_token(auth_data.id_token)
    
    # Extract phone number and Firebase UID
    phone_number = decoded_token.get("phone_number")
    firebase_uid = decoded_token.get("uid")
    
    if not phone_number or not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Firebase token: missing phone number or UID"
        )
    
    # Try to find user by Firebase UID
    user = authenticate_user(db, "", provider="phone", auth_id=firebase_uid)
    
    # If user doesn't exist and registration is allowed
    if not user and auth_data.register_if_not_exists:
        if not auth_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is required for new registration"
            )
        
        # Create a new user with phone auth
        user_create = UserCreate(
            username=auth_data.username,
            phone_number=phone_number,
            firebase_uid=firebase_uid
        )
        
        user = create_user(db, user_create)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found and registration not allowed"
        )
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id, "auth_provider": "phone"},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

class GoogleAuthRequest(BaseModel):
    token: str
    register_if_not_exists: bool = True
    username: Optional[str] = None

@router.post("/login/google", response_model=Token)
def login_with_google(
    auth_data: GoogleAuthRequest,
    db: DbSession = Depends(get_db)
) -> Any:
    """Login or register with Google OAuth"""
    from app.services.google_auth import verify_google_token
    
    # Verify Google token
    user_info = verify_google_token(auth_data.token)
    
    # Extract Google ID and email
    google_id = user_info.get("sub")
    email = user_info.get("email")
    
    if not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google token: missing user ID"
        )
    
    # Try to find user by Google ID
    user = authenticate_user(db, "", provider="google", auth_id=google_id)
    
    # If user doesn't exist and registration is allowed
    if not user and auth_data.register_if_not_exists:
        # For Google auth, we might create a username from email if not provided
        username = auth_data.username or email.split("@")[0] if email else None
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is required for new registration"
            )
        
        # Get name from Google profile if available
        full_name = user_info.get("name")
        
        # Create a new user with Google auth
        user_create = UserCreate(
            username=username,
            email=email,
            google_id=google_id,
            full_name=full_name
        )
        
        user = create_user(db, user_create)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found and registration not allowed"
        )
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id, "auth_provider": "google"},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@router.post("/profile/complete", response_model=UserSchema)
def complete_user_profile(
    profile_data: ProfileComplete,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db)
) -> Any:
    """Complete user profile after initial registration"""
    updated_user = complete_profile(db, current_user.id, profile_data)
    return updated_user

class AuthMethodLink(BaseModel):
    provider: str
    auth_data: dict

@router.post("/link", response_model=UserSchema)
def link_authentication_method(
    link_data: AuthMethodLink,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db)
) -> Any:
    """Link a new authentication method to the current user"""
    updated_user = link_auth_method(db, current_user.id, link_data.provider, link_data.auth_data)
    return updated_user

@router.post("/unlink/{provider}", response_model=UserSchema)
def unlink_authentication_method(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db)
) -> Any:
    """Unlink an authentication method from the current user"""
    updated_user = unlink_auth_method(db, current_user.id, provider)
    return updated_user

@router.post("/logout")
def logout():
    """
    With JWT tokens, logout is handled client-side by removing the token.
    This endpoint exists for consistency and future extension.
    """
    return {"status": "success", "message": "Logout successful"}