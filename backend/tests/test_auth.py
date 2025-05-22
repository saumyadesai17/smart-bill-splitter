import pytest
from fastapi import status
from datetime import datetime, timedelta
from freezegun import freeze_time
from app.core.config import settings

# ===================== Email Authentication Tests =====================

class TestEmailAuth:
    def test_signup_with_email(self, client, db):
        """Test successful user signup via email"""
        signup_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User"
        }
        response = client.post("/api/auth/email/signup", json=signup_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == signup_data["username"]
        assert data["user"]["email"] == signup_data["email"]
        assert data["user"]["full_name"] == signup_data["full_name"]
        assert "auth_providers" in data["user"]
        assert "email" in data["user"]["auth_providers"]

    def test_signup_with_existing_email(self, client, test_user):
        """Test signup with an email that is already registered"""
        signup_data = {
            "username": "different_user",
            "email": "test@example.com",  # Same as test_user
            "password": "password123"
        }
        response = client.post("/api/auth/email/signup", json=signup_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]

    def test_signup_with_existing_username(self, client, test_user):
        """Test signup with a username that is already taken"""
        signup_data = {
            "username": "testuser",  # Same as test_user
            "email": "different@example.com",
            "password": "password123"
        }
        response = client.post("/api/auth/email/signup", json=signup_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username already taken" in response.json()["detail"]

    def test_login_with_username(self, client, test_user):
        """Test login using username"""
        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        response = client.post("/api/auth/email/login", data=login_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["id"] == test_user.id

    def test_login_with_email(self, client, test_user):
        """Test login using email address"""
        login_data = {
            "username": "test@example.com",  # Using email as username
            "password": "password123"
        }
        response = client.post("/api/auth/email/login", data=login_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["id"] == test_user.id

    def test_login_with_incorrect_password(self, client, test_user):
        """Test login with correct username but wrong password"""
        login_data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        response = client.post("/api/auth/email/login", data=login_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email/username or password" in response.json()["detail"]

    def test_login_with_nonexistent_user(self, client):
        """Test login with username that doesn't exist"""
        login_data = {
            "username": "nonexistentuser",
            "password": "password123"
        }
        response = client.post("/api/auth/email/login", data=login_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email/username or password" in response.json()["detail"]

# ===================== Phone Authentication Tests =====================

class TestPhoneAuth:
    def test_verify_phone_signup_success(self, client, mock_firebase_verify, db):
        """Test successful user registration via phone verification"""
        verify_data = {
            "id_token": "mock-firebase-token",
            "register_if_not_exists": True,
            "username": "phoneuser"
        }
        
        response = client.post("/api/auth/phone/verify", json=verify_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["user_exists"] is False  # New user
        assert data["phone_number"] == "+1234567890"
        assert "access_token" in data
        assert data["user"]["username"] == "phoneuser"
        assert "phone" in data["user"]["auth_providers"]

    def test_verify_phone_login_success(self, client, mock_firebase_verify, db):
        """Test successful user login via phone verification"""
        # First create a user with phone auth
        verify_data = {
            "id_token": "mock-firebase-token",
            "register_if_not_exists": True,
            "username": "phoneuser"
        }
        client.post("/api/auth/phone/verify", json=verify_data)
        
        # Now try to login with the same phone
        login_data = {
            "id_token": "mock-firebase-token",
            "register_if_not_exists": False
        }
        
        response = client.post("/api/auth/phone/verify", json=login_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["user_exists"] is True  # Existing user
        assert data["phone_number"] == "+1234567890"
        assert "access_token" in data
        assert data["user"]["username"] == "phoneuser"

    def test_verify_phone_user_not_found(self, client, mock_firebase_verify):
        """Test phone verification with no matching user"""
        verify_data = {
            "id_token": "mock-firebase-token",
            "register_if_not_exists": False  # Don't create if not exists
        }
        
        response = client.post("/api/auth/phone/verify", json=verify_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["user_exists"] is False
        assert data["phone_number"] == "+1234567890"
        assert "access_token" not in data
        assert "user" not in data

    def test_verify_phone_missing_username(self, client, mock_firebase_verify):
        """Test phone signup with missing username"""
        verify_data = {
            "id_token": "mock-firebase-token",
            "register_if_not_exists": True
            # Missing username for new registration
        }
        
        response = client.post("/api/auth/phone/verify", json=verify_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username is required" in response.json()["detail"]

# ===================== Social (Google) Authentication Tests =====================

class TestSocialAuth:
    def test_google_login_success(self, client, db, mock_google_verify):
        """Test successful login/signup via Google"""
        # No need to define mock again - use the fixture
        auth_data = {
            "token": "mock-google-token",
            "register_if_not_exists": True,
            "username": "googleuser"
        }
        
        response = client.post("/api/auth/social/google", json=auth_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "googleuser"
        assert data["user"]["email"] == "google_user@example.com"
        assert "google" in data["user"]["auth_providers"]

    def test_google_login_existing_user(self, client, db, monkeypatch):
        """Test login with existing Google user"""
        # First create a Google user
        def mock_verify_google_token(token):
            return {
                "sub": "google-123456",
                "email": "google_user@example.com",
                "name": "Google User",
                "email_verified": True
            }
        
        from app.services import google_auth
        monkeypatch.setattr(google_auth, "verify_google_token", mock_verify_google_token)
        
        # Register first
        auth_data = {
            "token": "mock-google-token",
            "register_if_not_exists": True,
            "username": "googleuser"
        }
        client.post("/api/auth/social/google", json=auth_data)
        
        # Now try to login
        login_data = {
            "token": "mock-google-token",
            "register_if_not_exists": False
        }
        
        response = client.post("/api/auth/social/google", json=login_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["username"] == "googleuser"

    def test_google_login_no_registration(self, client, db, monkeypatch):
        """Test Google login with no matching user and registration disabled"""
        def mock_verify_google_token(token):
            return {
                "sub": "google-999999",  # Different Google ID
                "email": "another_google@example.com",
                "name": "Another Google User"
            }
        
        from app.services import google_auth
        monkeypatch.setattr(google_auth, "verify_google_token", mock_verify_google_token)
        
        auth_data = {
            "token": "mock-google-token",
            "register_if_not_exists": False  # Don't create new user
        }
        
        response = client.post("/api/auth/social/google", json=auth_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found and registration not allowed" in response.json()["detail"]

# ===================== Profile Management Tests =====================

class TestProfileManagement:
    def test_complete_profile(self, authenticated_client, test_user, db):
        """Test completing a user profile"""
        profile_data = {
            "full_name": "Test User Complete", 
            "username": "testuser_complete"
        }
        
        response = authenticated_client.post("/api/users/profile/complete", json=profile_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["full_name"] == profile_data["full_name"]
        assert data["username"] == profile_data["username"]
        assert data["profile_completed"] is True

    def test_get_profile_status(self, authenticated_client, test_user):
        """Test getting profile status"""
        response = authenticated_client.get("/api/users/me/profile-status")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "is_complete" in data
        assert "auth_providers" in data
        assert "has_email" in data
        assert "username" in data
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

# ===================== Authentication Provider Linking Tests =====================

class TestAuthProviderLink:
    def test_link_phone_to_email_user(self, authenticated_client, test_user, db, mock_firebase_verify):
        """Test linking phone auth to an email user"""
        link_data = {
            "provider": "phone",
            "auth_data": {
                "firebase_uid": "firebase-uid-123",
                "phone_number": "+1234567890"
            }
        }
        
        response = authenticated_client.post("/api/users/profile/link", json=link_data)
        assert response.status_code == status.HTTP_200_OK
        
        # Debug - directly query the database
        raw_user = db.execute(f"SELECT id, auth_providers FROM users WHERE id = {test_user.id}").fetchone()
        print(f"Direct SQL query result: {raw_user}")
        
        # Update the test_user object from the database to get fresh data
        db.refresh(test_user)
        print(f"After db.refresh(): user.auth_providers = {test_user.auth_providers}")
        
        data = response.json()
        print(f"Response JSON: {data}")
        assert "phone" in data["auth_providers"]

    def test_unlink_auth_method(self, client, db):
        """Test unlinking an auth method from user with multiple methods"""
        # Create a user with both email and phone
        from app.services.user import create_user
        from app.schemas.user import UserCreate
        
        user_create = UserCreate(
            username="multiauth",
            email="multiauth@example.com",
            password="password123",
            phone_number="+9876543210",
            firebase_uid="firebase-uid-multi",
            auth_providers=["email", "phone"]  # Make sure to explicitly set this
        )
        
        multi_user = create_user(db, user_create)
        
        # Verify the user was created with both auth methods
        assert "email" in multi_user.auth_providers
        assert "phone" in multi_user.auth_providers
        
        # Login with that user
        login_data = {
            "username": "multiauth",
            "password": "password123"
        }
        
        login_response = client.post("/api/auth/email/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Try to unlink email
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/users/profile/unlink/email", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "email" not in data["auth_providers"]
        assert "phone" in data["auth_providers"]

    def test_unlink_only_auth_method(self, authenticated_client, test_user):
        """Test trying to unlink the only auth method (should fail)"""
        response = authenticated_client.post("/api/users/profile/unlink/email")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot unlink the only authentication method" in response.json()["detail"]

# ===================== Session Management Tests =====================

class TestSessionManagement:
    def test_token_access(self, client, test_user):
        """Test accessing protected route with valid token"""
        # Login to get token
        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        login_response = client.post("/api/auth/email/login", data=login_data)
        token = login_response.json()["access_token"]
        
        # Access protected route
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/users/me", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == test_user.id

    def test_access_protected_route_without_token(self, client):
        """Test accessing protected route without token"""
        response = client.get("/api/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(reason="Requires token expiration setup")
    def test_expired_token(self, client, test_user, db):
        """Test that an expired token is rejected"""
        # This test requires setting token expiration to a small value
        # and using freeze_time or similar to advance time
        pass

    def test_logout(self, client):
        """Test logout endpoint (client-side session management)"""
        response = client.post("/api/auth/session/logout")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "success"