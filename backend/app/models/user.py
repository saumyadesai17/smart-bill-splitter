import json
from sqlalchemy import Boolean, Column, Integer, String, DateTime, TypeDecorator, JSON
from sqlalchemy.sql import func
from app.db.base import Base

# For SQLite compatibility with arrays
class ArrayOfStrings(TypeDecorator):
    impl = JSON
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return json.loads(value)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    
    # Core identity fields - all can be nullable initially
    username = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    
    # Authentication method identifiers
    hashed_password = Column(String, nullable=True)  # For email/password auth
    firebase_uid = Column(String, unique=True, index=True, nullable=True)  # For phone auth
    google_id = Column(String, unique=True, index=True, nullable=True)  # For Google auth
    
    # Profile information
    full_name = Column(String, index=True, nullable=True)
    avatar_url = Column(String, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    profile_completed = Column(Boolean, default=False)
    
    # Authentication methods
    auth_providers = Column(ArrayOfStrings, default=list)  # List of auth methods used ['email', 'phone', 'google']
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())