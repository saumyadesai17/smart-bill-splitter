import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "FastAPI Backend"
    admin_email: str = "admin@example.com"
    items_per_page: int = 10
    
    # JWT Settings
    SECRET_KEY: str 
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Database Settings
    user: str
    password: str
    host: str
    port: str
    dbname: str
    
    # Firebase Settings
    FIREBASE_PROJECT_ID: str
    FIREBASE_CLIENT_EMAIL: str
    FIREBASE_PRIVATE_KEY: str

    PHONE_AUTH_ENABLED: bool = True
    
    # Google OAuth Settings
    GOOGLE_AUTH_ENABLED: bool = True
    GOOGLE_CLIENT_ID: str
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",
    }

settings = Settings()