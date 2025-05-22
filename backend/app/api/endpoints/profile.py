from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import User as UserSchema, ProfileComplete
from app.services.profile_service import complete_profile
from app.services.auth_provider import link_auth_method, unlink_auth_method

router = APIRouter()

@router.post("/complete", response_model=UserSchema)
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
    # Debug logging
    print(f"Linking provider: {link_data.provider} with data: {link_data.auth_data}")
    
    updated_user = link_auth_method(
        db, 
        current_user.id, 
        link_data.provider, 
        link_data.auth_data
    )
    
    # Debug logging
    print(f"Updated user auth_providers: {updated_user.auth_providers}")
    
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