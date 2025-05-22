from typing import Optional, List
from pydantic import BaseModel
from app.schemas.user import User

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User  # Include user data in response

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[int] = None
    auth_provider: Optional[str] = None
    exp: Optional[int] = None