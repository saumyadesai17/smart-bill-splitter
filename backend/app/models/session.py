from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from app.db.base import Base

def generate_session_id():
    return str(uuid.uuid4())

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=generate_session_id)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    # Relationship with User model
    user = relationship("User", back_populates="sessions")

    @property
    def is_expired(self):
        # Ensure self.expires_at is not None before trying to call .replace()
        if self.expires_at is None:
            # Or handle as appropriate, e.g., return True or raise an error
            return True 

        # If self.expires_at is already aware, use it directly.
        # Otherwise, assume it's naive UTC and make it aware.
        if self.expires_at.tzinfo is None:
            aware_expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            aware_expires_at = self.expires_at
            
        return datetime.now(timezone.utc) > aware_expires_at