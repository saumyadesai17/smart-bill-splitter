from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy.orm.attributes import flag_modified

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.services.user import get_user, get_user_by_email, get_user_by_phone

def get_user_by_auth_id(db: Session, provider: str, auth_id: str) -> User:
    """Get a user by an authentication provider ID"""
    if provider == "google":
        return db.query(User).filter(User.google_id == auth_id).first()
    elif provider == "firebase":
        return db.query(User).filter(User.firebase_uid == auth_id).first()
    return None

def validate_auth_providers(db: Session, user_create: UserCreate) -> Dict[str, Any]:
    """Validate authentication providers and prepare user data"""
    # Determine which auth methods are being used
    has_email_password = user_create.password is not None and (user_create.email is not None or user_create.username is not None)
    has_phone = user_create.firebase_uid is not None
    has_google = user_create.google_id is not None
    
    if not any([has_email_password, has_phone, has_google]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one authentication method must be provided"
        )
    
    # Check for existing identifiers
    auth_providers = []
    user_data = {}
    
    # Check email if provided
    if user_create.email:
        existing_email = get_user_by_email(db, email=user_create.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user_data["email"] = user_create.email
        if has_email_password:
            auth_providers.append("email")
    
    # Check username if provided
    if user_create.username:
        user_data["username"] = user_create.username
    
    # Check phone auth
    if user_create.firebase_uid:
        existing_firebase = db.query(User).filter(User.firebase_uid == user_create.firebase_uid).first()
        if existing_firebase:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already linked to another account"
            )
        user_data["firebase_uid"] = user_create.firebase_uid
        auth_providers.append("phone")
        
        # If phone number is provided, add it
        if user_create.phone_number:
            existing_phone = get_user_by_phone(db, phone=user_create.phone_number)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered"
                )
            user_data["phone_number"] = user_create.phone_number
    
    # Check Google auth
    if user_create.google_id:
        existing_google = db.query(User).filter(User.google_id == user_create.google_id).first()
        if existing_google:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account already linked to another account"
            )
        user_data["google_id"] = user_create.google_id
        auth_providers.append("google")
    
    # Add other fields
    if user_create.full_name:
        user_data["full_name"] = user_create.full_name
    
    # Hash password if provided
    if user_create.password:
        user_data["hashed_password"] = hash_password(user_create.password)
    
    # Set verification status (phone and Google auth are considered pre-verified)
    user_data["is_verified"] = bool(has_phone or has_google)
    
    # Set auth providers
    user_data["auth_providers"] = auth_providers
    
    # Determine if profile is complete based on having username and full_name
    user_data["profile_completed"] = bool(user_create.username and user_create.full_name)
    
    return user_data

def link_auth_method(db: Session, user_id: int, provider: str, auth_data: dict) -> User:
    """Link a new authentication method to an existing user"""
    user = get_user(db, user_id)
    
    # Always start with a fresh list to avoid reference issues
    current_providers = user.auth_providers.copy() if user.auth_providers else []
    
    if provider == "email":
        # Linking email + password
        if "email" in current_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email authentication already linked"
            )
        
        # Validate email
        email = auth_data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        existing_email = get_user_by_email(db, email=email)
        if existing_email and existing_email.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered to another account"
            )
        
        # Validate password
        password = auth_data.get("password")
        if not password or len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        # Update user
        user.email = email
        user.hashed_password = hash_password(password)
        if "email" not in current_providers:
            current_providers.append("email")
    
    elif provider == "phone":
        # Linking phone number via Firebase
        if "phone" in current_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone authentication already linked"
            )
        
        # Validate Firebase UID
        firebase_uid = auth_data.get("firebase_uid")
        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Firebase UID is required"
            )
        
        existing_firebase = db.query(User).filter(User.firebase_uid == firebase_uid).first()
        if existing_firebase and existing_firebase.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone already linked to another account"
            )
        
        # Validate phone number
        phone_number = auth_data.get("phone_number")
        if phone_number:
            existing_phone = get_user_by_phone(db, phone=phone_number)
            if existing_phone and existing_phone.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered to another account"
                )
            user.phone_number = phone_number
        
        # Update user
        user.firebase_uid = firebase_uid
        if "phone" not in current_providers:
            current_providers.append("phone")
    
    elif provider == "google":
        # Linking Google OAuth
        if "google" in current_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google authentication already linked"
            )
        
        # Validate Google ID
        google_id = auth_data.get("google_id")
        if not google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google ID is required"
            )
        
        existing_google = db.query(User).filter(User.google_id == google_id).first()
        if existing_google and existing_google.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account already linked to another account"
            )
        
        # Update email if provided and not already set
        email = auth_data.get("email")
        if email and not user.email:
            existing_email = get_user_by_email(db, email=email)
            if existing_email and existing_email.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered to another account"
                )
            user.email = email
        
        # Update user
        user.google_id = google_id
        if "google" not in current_providers:
            current_providers.append("google")
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported authentication provider: {provider}"
        )
    
    # Explicitly overwrite the entire array to trigger SQLAlchemy change detection
    user.auth_providers = current_providers
    
    # Force SQLAlchemy to detect changes to this column
    flag_modified(user, "auth_providers")
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

def unlink_auth_method(db: Session, user_id: int, provider: str) -> User:
    """Unlink an authentication method from a user"""
    user = get_user(db, user_id)
    auth_providers = user.auth_providers or []
    
    # Prevent unlinking the only authentication method
    if len(auth_providers) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink the only authentication method"
        )
    
    if provider == "email":
        if "email" not in auth_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email authentication not linked"
            )
        user.hashed_password = None
        auth_providers = [p for p in auth_providers if p != "email"]  # Use list comprehension to create new list
    
    elif provider == "phone":
        if "phone" not in auth_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone authentication not linked"
            )
        user.firebase_uid = None
        # Don't remove phone_number as it's part of the user's identity
        auth_providers = [p for p in auth_providers if p != "phone"]
    
    elif provider == "google":
        if "google" not in auth_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google authentication not linked"
            )
        user.google_id = None
        auth_providers = [p for p in auth_providers if p != "google"]
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported authentication provider: {provider}"
        )
    
    # Update auth providers
    user.auth_providers = auth_providers
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user