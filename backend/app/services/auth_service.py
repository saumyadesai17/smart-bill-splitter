from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.core.security import verify_password
from app.services.user import get_user_by_any_identifier

def authenticate_user(db: Session, identifier: str, password: str = None, provider: str = None, auth_id: str = None) -> Optional[User]:
    """
    Flexible authentication supporting multiple methods:
    - Email/username + password
    - Phone number (via Firebase)
    - Google (via OAuth)
    """
    user = None
    
    if provider == "email" or (provider is None and password is not None):
        # Traditional email/username + password auth
        user = get_user_by_any_identifier(db, identifier)
        if not user or not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
    
    elif provider == "phone":
        # Phone auth via Firebase
        if not auth_id:
            return None
        user = db.query(User).filter(User.firebase_uid == auth_id).first()
    
    elif provider == "google":
        # Google OAuth
        if not auth_id:
            return None
        user = db.query(User).filter(User.google_id == auth_id).first()
    
    # Check if user is active
    if user and not user.is_active:
        return None
    
    return user