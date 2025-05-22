import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Helper: Fake user object class
class FakeUser:
    def __init__(self, id=1, username="testuser", email="test@example.com", google_id="google-id-123", full_name="Test User"):
        self.id = id
        self.username = username
        self.email = email
        self.google_id = google_id
        self.full_name = full_name
        self.auth_providers = ["google"]  # Add auth_providers for serialization

# ✅ Test: New user registration
def test_google_auth_registers_new_user(monkeypatch):
    mock_token_data = {
        "sub": "google-id-123",
        "email": "test@example.com",
        "name": "Test User"
    }

    # This is the module path actually used in your application
    monkeypatch.setattr("app.api.endpoints.social_auth.verify_google_token", lambda token: mock_token_data)
    monkeypatch.setattr("app.api.endpoints.social_auth.authenticate_user", lambda db, _, provider, auth_id: None)
    monkeypatch.setattr("app.api.endpoints.social_auth.create_user", lambda db, user_create: FakeUser())
    monkeypatch.setattr("app.api.endpoints.social_auth.create_access_token", lambda data, expires_delta: "fake-token")

    response = client.post("/api/auth/social/google", json={
        "token": "valid-token",
        "register_if_not_exists": True,
        "username": "testuser"
    })

    assert response.status_code == 200
    json = response.json()
    assert json["access_token"] == "fake-token"
    assert json["user"]["username"] == "testuser"

# ✅ Test: Existing user logs in
def test_google_auth_existing_user(monkeypatch):
    mock_token_data = {
        "sub": "google-id-123",
        "email": "test@example.com",
        "name": "Test User"
    }

    monkeypatch.setattr("app.api.endpoints.social_auth.verify_google_token", lambda token: mock_token_data)
    monkeypatch.setattr("app.api.endpoints.social_auth.authenticate_user", lambda db, _, provider, auth_id: FakeUser())
    monkeypatch.setattr("app.api.endpoints.social_auth.create_access_token", lambda data, expires_delta: "existing-token")

    response = client.post("/api/auth/social/google", json={
        "token": "valid-token",
        "register_if_not_exists": True  # Shouldn't matter
    })

    assert response.status_code == 200
    assert response.json()["access_token"] == "existing-token"

# ❌ Test: Missing Google ID
def test_google_auth_missing_google_id(monkeypatch):
    mock_token_data = {
        "email": "test@example.com"
        # No "sub" field
    }

    monkeypatch.setattr("app.api.endpoints.social_auth.verify_google_token", lambda token: mock_token_data)

    response = client.post("/api/auth/social/google", json={
        "token": "token-without-sub"
    })

    assert response.status_code == 400
    assert "missing user ID" in response.json()["detail"]

# ❌ Test: Registration not allowed and user doesn't exist
def test_google_auth_registration_disabled(monkeypatch):
    mock_token_data = {
        "sub": "google-id-123",
        "email": "test@example.com",
        "name": "Test User"
    }

    monkeypatch.setattr("app.api.endpoints.social_auth.verify_google_token", lambda token: mock_token_data)
    monkeypatch.setattr("app.api.endpoints.social_auth.authenticate_user", lambda db, _, provider, auth_id: None)

    response = client.post("/api/auth/social/google", json={
        "token": "valid-token",
        "register_if_not_exists": False
    })

    assert response.status_code == 401
    assert "registration not allowed" in response.json()["detail"]

# ❌ Test: Missing username during registration
def test_google_auth_missing_username(monkeypatch):
    mock_token_data = {
        "sub": "google-id-123",
        "email": None
    }

    monkeypatch.setattr("app.api.endpoints.social_auth.verify_google_token", lambda token: mock_token_data)
    monkeypatch.setattr("app.api.endpoints.social_auth.authenticate_user", lambda db, _, provider, auth_id: None)

    response = client.post("/api/auth/social/google", json={
        "token": "valid-token",
        "register_if_not_exists": True
        # No username provided
    })

    assert response.status_code == 400
    assert "Username is required" in response.json()["detail"]