import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "FastAPI Backend"
    admin_email: str = "admin@example.com"
    items_per_page: int = 10
    
    # JWT Settings (keeping for reference)
    SECRET_KEY: str 
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Session Settings
    SESSION_EXPIRY_DAYS: int
    SESSION_COOKIE_NAME: str
    SESSION_COOKIE_SECURE: bool
    SESSION_COOKIE_HTTPONLY: bool
    SESSION_COOKIE_SAMESITE: str
    
    # Database Settings - match the env variable names exactly
    user: str
    password: str
    host: str
    port: str
    dbname: str
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",  # Allow extra fields
    }

settings = Settings()