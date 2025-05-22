import pytest
from unittest.mock import patch
from fastapi import status

def test_phone_auth_new_user(client, db):
    # Directly patch the function in the module where it's used
    with patch('app.api.endpoints.phone_auth.verify_firebase_token') as mock_verify:
        # Configure mock to return expected data
        mock_verify.return_value = {
            "phone_number": "+1234567890",
            "uid": "firebase-uid-123"
        }
        
        auth_data = {
            "id_token": "mock-firebase-token",
            "register_if_not_exists": True,
            "username": "phoneuser"
        }
        
        response = client.post("/api/phone-auth/verify", json=auth_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["user_exists"] is True
        assert data["phone_number"] == "+1234567890"
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify user was created
        assert data["user"]["username"] == "phoneuser"
        assert data["user"]["phone_number"] == "+1234567890"

def test_phone_auth_existing_user(client, db):
    # Patch the function in the same way for consistency
    with patch('app.api.endpoints.phone_auth.verify_firebase_token') as mock_verify:
        # Configure mock to return expected data
        mock_verify.return_value = {
            "phone_number": "+1234567890",
            "uid": "firebase-uid-123"
        }
        
        # First create a user
        auth_data = {
            "id_token": "mock-firebase-token",
            "register_if_not_exists": True,
            "username": "phoneuser"
        }
        
        client.post("/api/phone-auth/verify", json=auth_data)
        
        # Now try to authenticate again
        auth_data = {
            "id_token": "mock-firebase-token",
            "register_if_not_exists": False
        }
        
        response = client.post("/api/phone-auth/verify", json=auth_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["user_exists"] is True
        assert "access_token" in data