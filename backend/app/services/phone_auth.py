from typing import Dict, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import secrets

from app.models.user import User
from app.schemas.user import UserCreate, User as UserSchema
from app.services.firebase_auth import verify_firebase_token
from app.services.user import create_user
from app.core.security import create_access_token
from datetime import timedelta
from app.core.config import settings

def verify_phone_token(
    id_token: str, 
    db: Session
) -> Dict:
    """Verify Firebase phone auth token and extract user data"""
    decoded_token = verify_firebase_token(id_token)
    
    phone_number = decoded_token.get("phone_number")
    firebase_uid = decoded_token.get("uid")
    
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number not found in token"
        )
    
    return {
        "phone_number": phone_number,
        "firebase_uid": firebase_uid
    }

def find_or_create_user(
    db: Session,
    phone_number: str, 
    firebase_uid: str,
    register_if_not_exists: bool = True,
    username: Optional[str] = None
) -> Tuple[User, bool]:
    """
    Find a user by phone number or create one if not exists
    Returns: (user, user_existed)
    """
    # Check if user exists
    db_user = db.query(User).filter(
        (User.phone_number == phone_number) | (User.firebase_uid == firebase_uid)
    ).first()
    
    user_existed = bool(db_user)
    
    # If user does not exist
    if not db_user:
        if not register_if_not_exists:
            return None, False
        
        # Validate required fields for new user registration
        if not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is required for new user registration"
            )
            
        # Create a new user
        random_password = secrets.token_urlsafe(16)
        
        user_create = UserCreate(
            username=username,
            email=f"{username}_{firebase_uid[:8]}@phone.auth",
            password=random_password,
            phone_number=phone_number
        )
        
        try:
            db_user = create_user(db, user_create)
            # Update firebase_uid
            db_user.firebase_uid = firebase_uid
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        except Exception as e:
            db.rollback()
            if "UniqueViolation" in str(e) or "unique constraint" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username or email already exists"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create user: {str(e)}"
            )
    else:
        # Update user if needed
        needs_update = False
        
        # Update phone number if it changed
        if db_user.phone_number != phone_number:
            db_user.phone_number = phone_number
            needs_update = True
            
        # Update firebase_uid if it's missing or changed
        if not db_user.firebase_uid or db_user.firebase_uid != firebase_uid:
            db_user.firebase_uid = firebase_uid
            needs_update = True
            
        if needs_update:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
    
    return db_user, user_existed

def generate_auth_response(user: User, user_existed: bool, phone_number: str) -> Dict:
    """Generate authentication response with tokens"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email or user.username,
            "user_id": user.id,
            "phone_verified": True
        },
        expires_delta=access_token_expires
    )
    
    return {
        "user_exists": user_existed,
        "phone_number": phone_number,
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }