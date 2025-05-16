from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session as DbSession

from app.core.auth import set_session_cookie, delete_session_cookie, get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.schemas.user import UserCreate, User
from app.services.user import authenticate_user, create_user
from app.services.session import create_session, delete_session

router = APIRouter()

@router.post("/signup", response_model=User)
def signup(user_in: UserCreate, db: DbSession = Depends(get_db)) -> Any:
    """
    Create new user.
    """
    user = create_user(db, user_in)
    return user

@router.post("/login")
def login(
    response: Response,
    db: DbSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Session-based login, sets a session cookie for future requests.
    Note: The 'username' field should contain the user's email address or username.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
        )
    
    # Create a new session for the user
    session = create_session(db, user)
    
    # Set the session cookie
    set_session_cookie(response, session.id)
    
    return {"status": "success", "message": "Login successful"}

@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Logout by clearing the session cookie and removing the session from the database.
    """
    # Get the session ID from the cookie
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_id:
        # Delete the session from the database
        delete_session(db, session_id)
    
    # Delete the session cookie
    delete_session_cookie(response)
    
    return {"status": "success", "message": "Logout successful"}