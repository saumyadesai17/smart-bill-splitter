from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

def get_user_by_any_identifier(db: Session, identifier: str) -> Optional[User]:
    """Get a user by any identifier (username, email, or phone)"""
    return db.query(User).filter(
        or_(
            User.username == identifier,
            User.email == identifier,
            User.phone_number == identifier
        )
    ).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    return db.query(User).filter(User.phone_number == phone).first()

def get_user(db: Session, user_id: int) -> User:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Retrieve a list of users with pagination."""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user_create: UserCreate) -> User:
    """Create a new user with basic validation"""
    from app.services.auth_provider import validate_auth_providers
    
    # Check for existing username
    existing_username = get_user_by_username(db, user_create.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Check for existing email if provided
    if user_create.email:
        existing_email = get_user_by_email(db, user_create.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Validate authentication providers and get prepared user data
    user_data = validate_auth_providers(db, user_create)
    
    # Create user
    try:
        db_user = User(**user_data)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        if "unique constraint" in str(e).lower():
            # Additional fallback for any other unique constraints
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user: {str(e)}"
        )

def update_user(db: Session, user_id: int, user_update_schema: UserUpdate) -> User:
    from app.core.security import hash_password
    
    db_user = get_user(db, user_id) # get_user will raise 404 if not found

    update_data = user_update_schema.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != db_user.email:
        existing_user_with_email = get_user_by_email(db, email=update_data["email"])
        if existing_user_with_email and existing_user_with_email.id != db_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    
    if "username" in update_data and update_data["username"] != db_user.username:
        existing_user_with_username = get_user_by_username(db, username=update_data["username"])
        if existing_user_with_username and existing_user_with_username.id != db_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    if "password" in update_data:
        password = update_data.pop("password")
        if password: # Only hash and update if a non-empty password is provided
            update_data["hashed_password"] = hash_password(password)

    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> User:
    db_user = get_user(db, user_id) # get_user will raise 404 if not found
    db.delete(db_user)
    db.commit()
    return db_user