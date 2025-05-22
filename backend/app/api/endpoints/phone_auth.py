from typing import Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession
from pydantic import BaseModel

from app.db.session import get_db
from app.schemas.user import User as UserSchema
from app.services.phone_auth import (
    verify_phone_token,
    find_or_create_user,
    generate_auth_response
)

router = APIRouter()

class PhoneAuthRequest(BaseModel):
    id_token: str
    register_if_not_exists: bool = True
    username: Optional[str] = None  # Required only for new users

class PhoneVerifyResponse(BaseModel):
    user_exists: bool
    phone_number: str
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    user: Optional[UserSchema] = None

@router.post("/verify", response_model=PhoneVerifyResponse)
def verify_phone_otp(
    auth_request: PhoneAuthRequest,
    db: DbSession = Depends(get_db)
) -> Any:
    """Verify Firebase phone OTP token and get or create a user"""
    
    # Step 1: Verify the Firebase token
    token_data = verify_phone_token(auth_request.id_token, db)
    phone_number = token_data["phone_number"]
    firebase_uid = token_data["firebase_uid"]
    
    # Step 2: Find or create the user
    user, user_existed = find_or_create_user(
        db=db,
        phone_number=phone_number,
        firebase_uid=firebase_uid,
        register_if_not_exists=auth_request.register_if_not_exists,
        username=auth_request.username
    )
    
    # If user was not found and not to be created
    if not user:
        return {
            "user_exists": False,
            "phone_number": phone_number
        }
    
    # Step 3: Generate the authentication response
    return generate_auth_response(
        user=user,
        user_existed=user_existed,
        phone_number=phone_number
    )