import pytest
from fastapi import status # For status codes, though direct integers are also used
from app.core.config import settings
from datetime import datetime, timedelta
from freezegun import freeze_time

# Note: Ensure 'client', 'test_user', and 'db' fixtures are available 
# (e.g., from your conftest.py)

def test_login_with_username(client, test_user):
    """Test login using username."""
    login_data = {
        "username": "testuser",  # test_user's username
        "password": "password123" # test_user's password
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    assert "status" in response.json()
    assert response.json()["status"] == "success"
    assert settings.SESSION_COOKIE_NAME in response.cookies

def test_login_with_email_address(client, test_user):
    """Test login using email address."""
    login_data = {
        "username": "test@example.com",  # test_user's email
        "password": "password123"     # test_user's password
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    assert "status" in response.json()
    assert response.json()["status"] == "success"
    assert settings.SESSION_COOKIE_NAME in response.cookies

def test_invalid_login_credentials(client, test_user):
    """Test login with correct username but invalid password."""
    login_data = {
        "username": "testuser",
        "password": "wrongpassword"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()
    assert "Incorrect email/username or password" in response.json()["detail"]

def test_session_should_expire(client, test_user, db):
    """Test that an expired session is rejected."""
    # Login to establish a session
    login_data = {
        "username": "testuser",
        "password": "password123"
    }
    login_response = client.post("/api/auth/login", data=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    assert settings.SESSION_COOKIE_NAME in login_response.cookies

    # Advance time beyond session expiry
    # Ensure settings.SESSION_EXPIRY_DAYS is correctly configured
    future_time = datetime.now() + timedelta(days=settings.SESSION_EXPIRY_DAYS + 1)
    with freeze_time(future_time):
        # Attempt to access a protected route
        protected_response = client.get("/api/users/me")
        assert protected_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in protected_response.json()
        assert "Not authenticated" in protected_response.json()["detail"]

def test_logout_when_not_authenticated(client):
    """Test logout attempt without an active session."""
    response = client.post("/api/auth/logout")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()
    assert "Not authenticated" in response.json()["detail"]

def test_signup_with_existing_username(client, test_user):
    """Test signup with a username that is already taken."""
    # test_user fixture (username="testuser") already exists
    signup_data = {
        "username": "testuser",  # Duplicate username
        "email": "new_unique_email@example.com",
        "password": "a_new_password"
    }
    response = client.post("/api/auth/signup", json=signup_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()
    assert "Username already taken" in response.json()["detail"]

def test_signup_with_existing_email(client, test_user):
    """Test signup with an email that is already registered."""
    # test_user fixture (email="test@example.com") already exists
    signup_data = {
        "username": "new_unique_user",
        "email": "test@example.com",  # Duplicate email
        "password": "a_new_password"
    }
    response = client.post("/api/auth/signup", json=signup_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()
    assert "Email already registered" in response.json()["detail"]

def test_signup_short_password(client):
    """Test signup with a password that is too short."""
    signup_data = {
        "username": "shortpassuser",
        "email": "shortpass@example.com",
        "password": "123"  # Invalid short password
    }
    response = client.post("/api/auth/signup", json=signup_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY  # Pydantic validation error
    assert "detail" in response.json()
    # Check for the specific Pydantic validation error message if needed
    # Example: assert any("Password must be at least 6 characters long" in err["msg"] for err in response.json()["detail"])

def test_signup_empty_username(client):
    """Test signup with an empty username."""
    signup_data = {
        "username": "",  # Empty username
        "email": "emptyuser@example.com",
        "password": "password123"
    }
    response = client.post("/api/auth/signup", json=signup_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY # Pydantic validation error
    assert "detail" in response.json()
    # Example: assert any("Username must not be empty" in err["msg"] for err in response.json()["detail"])

def test_signup_invalid_email_format(client):
    """Test signup with an invalid email format."""
    signup_data = {
        "username": "invalidemailuser",
        "email": "not-an-email",  # Invalid email format
        "password": "password123"
    }
    response = client.post("/api/auth/signup", json=signup_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY # Pydantic validation error
    assert "detail" in response.json()
    # Example: assert any("value is not a valid email address" in err["msg"] for err in response.json()["detail"])


def test_successful_logout(client, test_user, db):
    """Test successful logout and subsequent access denial."""
    # Login to establish a session
    login_data = {
        "username": "testuser",
        "password": "password123"
    }
    login_response = client.post("/api/auth/login", data=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    assert settings.SESSION_COOKIE_NAME in login_response.cookies

    # Logout
    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == status.HTTP_200_OK
    assert logout_response.json()["status"] == "success"
    assert settings.SESSION_COOKIE_NAME not in logout_response.cookies # Check if cookie is cleared

    # Attempt to access a protected route after logout
    protected_response = client.get("/api/users/me")
    assert protected_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in protected_response.json()
    assert "Not authenticated" in protected_response.json()["detail"]

def test_update_user_me_username(client, test_user, db):
    """Test updating the current user's username."""
    # Login
    login_data = {"username": "testuser", "password": "password123"}
    client.post("/api/auth/login", data=login_data)

    new_username = "updatedtestuser"
    update_data = {"username": new_username}
    response = client.put("/api/users/me", json=update_data)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == new_username
    assert response.json()["email"] == test_user.email # Email should remain unchanged

    # Verify in DB (optional, but good for thoroughness)
    from app.services.user import get_user_by_username
    updated_db_user = get_user_by_username(db, new_username)
    assert updated_db_user is not None
    assert updated_db_user.id == test_user.id

def test_update_user_me_password(client, test_user, db):
    """Test updating the current user's password."""
    # Login
    login_data = {"username": "testuser", "password": "password123"}
    client.post("/api/auth/login", data=login_data)

    new_password = "newpassword123"
    update_data = {"password": new_password}
    response = client.put("/api/users/me", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    # Logout
    client.post("/api/auth/logout")

    # Try to login with the new password
    login_data_new_pass = {"username": "testuser", "password": new_password}
    response_new_login = client.post("/api/auth/login", data=login_data_new_pass)
    assert response_new_login.status_code == status.HTTP_200_OK
    assert response_new_login.json()["status"] == "success"

def test_update_user_me_email_and_username(client, test_user, db):
    """Test updating the current user's email and username."""
    # Login
    login_data = {"username": "testuser", "password": "password123"}
    client.post("/api/auth/login", data=login_data)

    new_username = "new_username_for_email_update"
    new_email = "new_email@example.com"
    update_data = {"username": new_username, "email": new_email}
    response = client.put("/api/users/me", json=update_data)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == new_username
    assert response.json()["email"] == new_email

    # Verify in DB
    from app.services.user import get_user_by_email
    updated_db_user = get_user_by_email(db, new_email)
    assert updated_db_user is not None
    assert updated_db_user.username == new_username
    assert updated_db_user.id == test_user.id

def test_login_with_nonexistent_user(client):
    """Test login with a username that does not exist."""
    login_data = {
        "username": "nonexistentuser",
        "password": "password123"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()
    assert "Incorrect email/username or password" in response.json()["detail"]

def test_successful_signup_and_user_data_returned(client, db):
    """Test successful user signup and verify returned data."""
    # Ensure this user does not exist before the test
    from app.services.user import get_user_by_username, get_user_by_email
    from app.models.user import User # Assuming your User model
    
    new_username = "newsignupuser"
    new_email = "newsignup@example.com"
    new_password = "password123"

    # Clean up if user exists from a previous failed run (optional, depends on test setup)
    # existing_user = get_user_by_username(db, new_username)
    # if existing_user:
    #     db.delete(existing_user)
    #     db.commit()

    signup_data = {
        "username": new_username,
        "email": new_email,
        "password": new_password
    }
    response = client.post("/api/auth/signup", json=signup_data)
    assert response.status_code == status.HTTP_200_OK # Or 201 if your API returns that
    
    response_data = response.json()
    assert response_data["username"] == new_username
    assert response_data["email"] == new_email
    assert "id" in response_data
    # assert "hashed_password" not in response_data # Ensure password is not returned

    # Verify user in DB
    db_user = get_user_by_username(db, new_username)
    assert db_user is not None
    assert db_user.email == new_email

def test_get_user_me_success(client, test_user):
    """Test successful retrieval of current user's data."""
    # Login
    login_data = {"username": test_user.username, "password": "password123"}
    login_response = client.post("/api/auth/login", data=login_data)
    assert login_response.status_code == status.HTTP_200_OK

    response = client.get("/api/users/me")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id

def test_update_user_me_to_existing_email_of_another_user(client, test_user, db):
    """Test updating current user's email to one already taken by another user."""
    # Create another user
    other_user_data = {
        "username": "otheruser",
        "email": "other@example.com",
        "password": "password123"
    }
    # Assuming you have a direct way to create a user for setup, or use signup
    # For simplicity, let's assume a direct creation or that signup is robustly tested
    client.post("/api/auth/signup", json=other_user_data) # Create the other user

    # Login as test_user
    login_data = {"username": test_user.username, "password": "password123"}
    client.post("/api/auth/login", data=login_data)

    update_data = {"email": "other@example.com"} # Attempt to use other_user's email
    response = client.put("/api/users/me", json=update_data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()
    assert "Email already registered" in response.json()["detail"] # Or similar message

def test_signup_missing_password_field(client):
    """Test signup with missing password field."""
    signup_data = {
        "username": "missingpassuser",
        "email": "missingpass@example.com",
        # "password": "password123" // Password field is missing
    }
    response = client.post("/api/auth/signup", json=signup_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "detail" in response.json()
    # You might want to assert the specific error message for the missing field
    # e.g., assert any(err["loc"] == ["body", "password"] and err["type"] == "missing" for err in response.json()["detail"])