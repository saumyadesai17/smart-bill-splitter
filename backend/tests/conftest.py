import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.services.user import create_user
from app.schemas.user import UserCreate

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Add event listener to handle timezone-aware datetime objects in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Add adapter for datetime objects with timezone info
def adapt_datetime_with_timezone(value):
    """Convert timezone-aware datetime to naive for SQLite storage"""
    if hasattr(value, 'tzinfo') and value.tzinfo is not None:
        return value.replace(tzinfo=None)  # Convert to naive datetime
    return value

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, params, context, executemany):
    if params:
        if isinstance(params, dict):
            for key, value in list(params.items()):
                if isinstance(value, datetime):
                    params[key] = adapt_datetime_with_timezone(value)
        elif isinstance(params, (list, tuple)):
            params = list(params)
            for i, value in enumerate(params):
                if isinstance(value, datetime):
                    params[i] = adapt_datetime_with_timezone(value)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a new session for each test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after the test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    # Override the get_db dependency to use our test database
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db):
    # Create a test user
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="password123"
    )
    return create_user(db, user_data)

@pytest.fixture(scope="function")
def authenticated_client(client, test_user):
    # Login with the test user
    login_data = {
        "username": "testuser",
        "password": "password123"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200
    return client