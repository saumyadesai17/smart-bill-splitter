from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session as DbSession
from app.models.session import Session
from app.models.user import User
from app.core.config import settings

def create_session(db: DbSession, user: User) -> Session:
    """Create a new session for a user."""
    # Delete any existing sessions for this user (optional, depending on your requirements)
    delete_user_sessions(db, user.id)
    
    # Create a new session with explicit timezone information
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.SESSION_EXPIRY_DAYS)
    db_session = Session(
        user_id=user.id,
        expires_at=expires_at
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    # Ensure timezone info is preserved after DB retrieval
    if db_session.expires_at.tzinfo is None:
        db_session.expires_at = db_session.expires_at.replace(tzinfo=timezone.utc)
    
    return db_session

def get_session(db: DbSession, session_id: str) -> Optional[Session]:
    """Get a session by its ID."""
    return db.query(Session).filter(Session.id == session_id).first()

def get_valid_session(db: DbSession, session_id: str) -> Optional[Session]:
    """Get a session that is not expired."""
    session = get_session(db, session_id)
    if session and not session.is_expired:
        return session
    return None

def delete_session(db: DbSession, session_id: str) -> None:
    """Delete a session."""
    session = get_session(db, session_id)
    if session:
        db.delete(session)
        db.commit()

def delete_user_sessions(db: DbSession, user_id: int) -> None:
    """Delete all sessions for a specific user."""
    db.query(Session).filter(Session.user_id == user_id).delete()
    db.commit()

def clear_expired_sessions(db: DbSession) -> None:
    """Delete all expired sessions."""
    db.query(Session).filter(Session.expires_at < datetime.now(timezone.utc)).delete()
    db.commit()