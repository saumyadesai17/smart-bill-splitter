from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import ProfileComplete
from app.services.user import get_user, get_user_by_email, get_user_by_username

def complete_profile(db: Session, user_id: int, profile_data: ProfileComplete) -> User:
    """Complete a user profile after initial authentication"""
    user = get_user(db, user_id)
    
    # Check username if provided
    if profile_data.username and profile_data.username != user.username:
        existing_username = get_user_by_username(db, username=profile_data.username)
        if existing_username and existing_username.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        user.username = profile_data.username
    
    # Check email if provided
    if profile_data.email and profile_data.email != user.email:
        existing_email = get_user_by_email(db, email=profile_data.email)
        if existing_email and existing_email.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = profile_data.email
    
    # Set full name if provided
    if profile_data.full_name:
        user.full_name = profile_data.full_name
    
    # Determine if profile is now complete
    if user.username and user.full_name:
        user.profile_completed = True
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user