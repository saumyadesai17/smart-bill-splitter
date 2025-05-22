import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException, status
import os
from app.core.config import settings  # Assuming this loads .env automatically

# Load and validate Firebase environment variables
project_id = settings.FIREBASE_PROJECT_ID
client_email = settings.FIREBASE_CLIENT_EMAIL
private_key = settings.FIREBASE_PRIVATE_KEY

if not project_id or not client_email or not private_key:
    raise RuntimeError("Missing one or more Firebase environment variables.")

# Fix escaped newlines in private key
private_key = private_key.replace('\\n', '\n')

# Construct credentials dictionary
cred_dict = {
    "type": "service_account",
    "project_id": project_id,
    "private_key": private_key,
    "client_email": client_email,
    "token_uri": "https://oauth2.googleapis.com/token"
}

# Initialize Firebase Admin SDK safely
try:
    cred = credentials.Certificate(cred_dict)
    firebase_app = firebase_admin.initialize_app(cred)
except ValueError as e:
    # Handle "app already exists" error
    if "already exists" in str(e):
        firebase_app = firebase_admin.get_app()
    else:
        raise RuntimeError(f"Error initializing Firebase: {e}")

def verify_firebase_token(id_token: str):
    """
    Verify Firebase ID token and return the decoded token
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {str(e)}"
        )

def get_user_by_phone(phone_number: str):
    """
    Get Firebase user by phone number
    """
    try:
        user = auth.get_user_by_phone_number(phone_number)
        return user
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firebase error: {str(e)}"
        )