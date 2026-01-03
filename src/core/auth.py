import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.core.connectors import ENV_SETTINGS
from src.utils.log import setup_logger
import json

logger = setup_logger(__name__)

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials from environment variable"""
    try:
        if not firebase_admin._apps:
            # Parse the JSON string from environment variable
            service_account_info = json.loads(ENV_SETTINGS.GCP_CREDENTIALS)
            cred = credentials.Certificate(service_account_info)
            default_app = firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK initialized successfully - Project: {default_app.project_id}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GOOGLE_APPLICATION_CREDENTIALS JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        raise

# Initialize Firebase on module import
# initialize_firebase()

# Security scheme for Bearer token
security = HTTPBearer()

class FirebaseAuthDependency:
    def __init__(self):
        self.security = HTTPBearer()
    
    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """
        Verify Firebase ID token and return the decoded token.
        
        Args:
            credentials: HTTPAuthorizationCredentials containing the Bearer token
            
        Returns:
            dict: Decoded Firebase token containing user information
            
        Raises:
            HTTPException: If token is invalid or verification fails
        """
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Authorization header is required"
            )
        
        token = credentials.credentials
        
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(token)
            logger.info(f"Successfully verified token for user: {decoded_token.get('uid')}")
            return decoded_token
        
        except auth.InvalidIdTokenError as e:
            logger.error(f"Invalid ID token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )
        except auth.ExpiredIdTokenError as e:
            logger.error(f"Expired ID token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Authentication token has expired"
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Authentication failed"
            )

# Create a dependency instance
verify_firebase_token = FirebaseAuthDependency()

def get_current_user_uid(token_data: dict = Depends(verify_firebase_token)) -> str:
    """
    Extract the user UID from the verified Firebase token.
    
    Args:
        token_data: Decoded Firebase token from verify_firebase_token
        
    Returns:
        str: Firebase user UID
    """
    return token_data.get("uid")

def get_current_user_email(token_data: dict = Depends(verify_firebase_token)) -> str:
    """
    Extract the user email from the verified Firebase token.
    
    Args:
        token_data: Decoded Firebase token from verify_firebase_token
        
    Returns:
        str: User email address
    """
    return token_data.get("email")

def get_current_user_info(token_data: dict = Depends(verify_firebase_token)) -> dict:
    """
    Extract user information from the verified Firebase token.
    
    Args:
        token_data: Decoded Firebase token from verify_firebase_token
        
    Returns:
        dict: User information including uid, email, name, etc.
    """
    return {
        "uid": token_data.get("uid"),
        "email": token_data.get("email"),
        "name": token_data.get("name"),
        "picture": token_data.get("picture"),
        "email_verified": token_data.get("email_verified", False)
    }
