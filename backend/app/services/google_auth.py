from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def verify_google_token(token: str) -> dict:
    """
    Verify a Google ID token and return user information using Google Auth Library.
    
    This is the recommended approach for production environments.
    """
    try:
        # Create a request adapter for Google Auth
        request = requests.Request()
        
        # Verify the token - the library verifies that the token is properly signed by Google
        id_info = id_token.verify_oauth2_token(token, request)
        
        # Verify issuer
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Invalid issuer')
            
        # If GOOGLE_AUTH_ENABLED and we have a client ID, verify audience manually
        if settings.GOOGLE_AUTH_ENABLED and settings.GOOGLE_CLIENT_ID:
            if id_info.get('aud') != settings.GOOGLE_CLIENT_ID:
                raise ValueError(f'Invalid audience. Expected {settings.GOOGLE_CLIENT_ID}, got {id_info.get("aud")}')
        
        # Return the verified user info
        return id_info
        
    except ValueError as e:
        # This includes token expired, invalid signature, wrong audience, etc.
        logger.warning(f"Google token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during Google token verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying Google token: {str(e)}"
        )