from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session as DbSession

from app.db.session import get_db
from app.models.user import User
from app.services.session import get_valid_session
from app.core.config import settings

def get_current_user(
    request: Request,
    db: DbSession = Depends(get_db)
) -> User:
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    session = get_valid_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )
    
    return session.user

def set_session_cookie(response: Response, session_id: str):
    """Set a session cookie on the response."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_EXPIRY_DAYS * 24 * 60 * 60,  # in seconds
    )

def delete_session_cookie(response: Response):
    """Delete the session cookie from the response."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )