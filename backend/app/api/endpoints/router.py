from fastapi import APIRouter
from app.api.endpoints import (
    email_auth,
    phone_auth,
    social_auth,
    profile, 
    session,
    users
)
from app.core.config import settings

router = APIRouter()

# Authentication endpoints grouped under /auth
router.include_router(
    email_auth.router, 
    prefix="/auth/email", 
    tags=["authentication"]
)

# Include phone auth router if enabled
if settings.PHONE_AUTH_ENABLED:
    router.include_router(
        phone_auth.router, 
        prefix="/auth/phone", 
        tags=["authentication"]
    )

# Social authentication
router.include_router(
    social_auth.router, 
    prefix="/auth/social", 
    tags=["authentication"]
)

# Session management (logout, refresh tokens, etc.)
router.include_router(
    session.router, 
    prefix="/auth/session", 
    tags=["authentication"]
)

# Profile management - moved to user context
router.include_router(
    profile.router, 
    prefix="/users/profile", 
    tags=["user-management"]
)

# User management
router.include_router(
    users.router, 
    prefix="/users", 
    tags=["user-management"]
)

@router.get("/")
async def read_root():
    return {"message": "Welcome to the FastAPI backend!"}

# Additional endpoints can be added here as needed.