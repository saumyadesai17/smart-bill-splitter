from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session as DbSession

from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from app.services.user import get_user

# Update the tokenUrl to match your new email authentication login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/email/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: DbSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: Optional[int] = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    try:
        user = get_user(db, user_id)
    except HTTPException:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
        
    return user