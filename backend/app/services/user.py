from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate # Ensure UserUpdate is imported
from app.core.security import hash_password, verify_password

def create_user(db: Session, user_create_schema: UserCreate) -> User:
    # Check if user with the email already exists
    existing_user_by_email = get_user_by_email(db, email=user_create_schema.email)
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if user with the username already exists
    existing_user_by_username = get_user_by_username(db, username=user_create_schema.username)
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = hash_password(user_create_schema.password)
    db_user = User(
        username=user_create_schema.username,
        email=user_create_schema.email,
        hashed_password=hashed_password,
        is_active=True # Default to active, can be changed via update if needed
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email_or_username: str, password: str) -> Optional[User]:
    # First try to find user by email
    user = get_user_by_email(db, email=email_or_username)
    if not user:
        # If not found by email, try username
        user = get_user_by_username(db, username=email_or_username)
        if not user:
            return None # User not found by either email or username
    
    if not verify_password(password, user.hashed_password):
        return None # Password does not match
    return user

def get_user(db: Session, user_id: int) -> User:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 10) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()

def update_user(db: Session, user_id: int, user_update_schema: UserUpdate) -> User:
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
            # Assuming UserUpdate schema now has password validation (e.g., min length)
            # If not, you might add a len(password) < N check here too.
            update_data["hashed_password"] = hash_password(password)
        # If password in update_data is None or empty, it's effectively ignored here
        # unless UserUpdate schema validation catches it.

    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> User: # Or -> None if you prefer not to return the user
    db_user = get_user(db, user_id) # get_user will raise 404 if not found
    
    # Cascading delete for sessions should be handled by SQLAlchemy if configured in the model
    db.delete(db_user)
    db.commit()
    # return db_user # Returning the deleted user object can be useful
    # Or, if you prefer a confirmation or no return:
    # return None 
    # For now, let's keep returning the user object as it was, but now it's guaranteed to exist.
    return db_user