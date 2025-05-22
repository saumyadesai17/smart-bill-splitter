from typing import Any, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.user import UserCreate
from app.schemas.token import Token
from app.services.user import create_user
from app.services.auth_service import authenticate_user
from app.services.google_auth import verify_google_token

router = APIRouter()

class GoogleAuthRequest(BaseModel):
    token: str
    register_if_not_exists: bool = True
    username: Optional[str] = None

@router.post("/google", response_model=Token)
def login_with_google(
    auth_data: GoogleAuthRequest,
    db: DbSession = Depends(get_db)
) -> Any:
    """Login or register with Google OAuth"""
    
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