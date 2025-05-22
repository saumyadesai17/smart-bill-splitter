import pytest
from fastapi import HTTPException
from app.services.google_auth import verify_google_token

# Patch the actual Google function from the oauth2 lib
from google.oauth2 import id_token as google_id_token

# Your app setting for GOOGLE_CLIENT_ID if you're checking 'aud'
class DummySettings:
    GOOGLE_AUTH_ENABLED = True
    GOOGLE_CLIENT_ID = "test-client-id"

# Patch settings
@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    monkeypatch.setattr("app.services.google_auth.settings", DummySettings)

# ✅ Test: Successful verification
def test_verify_valid_token(mocker):
    mock_id_info = {
        "iss": "accounts.google.com",
        "aud": "test-client-id",
        "email": "test@example.com",
        "sub": "1234567890"
    }

    mocker.patch.object(google_id_token, "verify_oauth2_token", return_value=mock_id_info)

    result = verify_google_token("valid-token")
    assert result["email"] == "test@example.com"

# ❌ Test: Invalid issuer
def test_verify_token_invalid_issuer(mocker):
    mock_id_info = {
        "iss": "malicious.com",
        "aud": "test-client-id"
    }

    mocker.patch.object(google_id_token, "verify_oauth2_token", return_value=mock_id_info)

    with pytest.raises(HTTPException) as exc_info:
        verify_google_token("token-with-bad-issuer")

    assert exc_info.value.status_code == 401
    assert "Invalid issuer" in exc_info.value.detail

# ❌ Test: Invalid audience
def test_verify_token_invalid_audience(mocker):
    mock_id_info = {
        "iss": "accounts.google.com",
        "aud": "wrong-client-id"
    }

    mocker.patch.object(google_id_token, "verify_oauth2_token", return_value=mock_id_info)

    with pytest.raises(HTTPException) as exc_info:
        verify_google_token("token-with-bad-audience")

    assert exc_info.value.status_code == 401
    assert "Invalid audience" in exc_info.value.detail

# ❌ Test: Token verification fails (e.g. expired or tampered)
def test_verify_token_verification_failure(mocker):
    mocker.patch.object(google_id_token, "verify_oauth2_token", side_effect=ValueError("Token expired"))

    with pytest.raises(HTTPException) as exc_info:
        verify_google_token("expired-token")

    assert exc_info.value.status_code == 401
    assert "Token expired" in exc_info.value.detail
