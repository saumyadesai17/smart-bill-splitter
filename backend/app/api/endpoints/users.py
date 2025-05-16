from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DbSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate
from app.services.user import create_user, delete_user, get_user, get_users, update_user

router = APIRouter()

@router.get("/me", response_model=UserSchema)
def read_user_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=UserSchema)
def update_user_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
) -> Any:
    """
    Update current user.
    """
    user = update_user(db, current_user.id, user_in)
    return user

@router.get("/{user_id}", response_model=UserSchema)
def read_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
) -> Any:
    """
    Get a specific user by id.
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist",
        )
    return user

@router.get("/", response_model=List[UserSchema])
def read_users(
    db: DbSession = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve users.
    """
    users = get_users(db, skip=skip, limit=limit)
    return users