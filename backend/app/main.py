from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from app.api.endpoints.router import router as api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, get_db
from app.services.session import clear_expired_sessions
from sqlalchemy.orm import Session as DbSession

# Create all tables in the database
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    db = next(get_db())
    clear_expired_sessions(db)
    logging.info("Cleared expired sessions")
    yield
    # Shutdown code (if needed)
    pass

app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Configure CORS with credentials support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update with your frontend domain
    allow_credentials=True,  # Important for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI backend!"}