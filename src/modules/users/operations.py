from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from src.modules.users.schema import UsersORM
from src.core.environment import ENV_SETTINGS
from src.utils.log import setup_logger

logger = setup_logger(__name__)

def fetchUserById(user_id: str, db: Session):
    user = db.query(UsersORM).filter(UsersORM.id == user_id).first()
    if not user:
        logger.error(f"User with ID {user_id} not found.") 
    return user

def fetchUserByEmail(email: str, db: Session):
    user = db.query(UsersORM).filter(UsersORM.email == email).first()
    if not user:
        logger.error(f"User with email {email} not found.") 
    return user

def createUser(email: str, name: str, db: Session):
    new_user = UsersORM(email=email, name=name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"Created new user with email: {email}")
    return new_user

def verifyGmailToken(token: str) -> dict:
    try:
        verification_response: dict = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            ENV_SETTINGS.GMAIL_WEB_CLIENT_ID
        )
        logger.info("Gmail token verified successfully.")
        return verification_response
    except ValueError as e:
        logger.error(f"Token verification failed: {e}")
        raise


def generateGmailAccessUrl() -> str:

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": ENV_SETTINGS.GMAIL_WEB_CLIENT_ID,
                "client_secret": ENV_SETTINGS.GMAIL_WEB_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES
    )

    flow.redirect_uri = f"{ENV_SETTINGS.MB_BACKEND_API_URL}/api/v1/users/auth/callback"

    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    return auth_url
