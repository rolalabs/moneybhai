from datetime import datetime
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from src.modules.accounts.operations import updateAccountById
from packages.enums import GMAIL_SCOPES
from src.modules.users.schema import UsersORM
from src.core.environment import ENV_SETTINGS
from src.utils.log import setup_logger

logger = setup_logger(__name__)

def fetchUserById(user_id: str, db: Session):
    user = db.query(UsersORM).filter(UsersORM.id == user_id).first()
    if not user:
        logger.error(f"User with ID {user_id} not found.") 
    return user

def fetchUserByEmail(email: str, db: Session) -> UsersORM | None:
    user = db.query(UsersORM).filter(UsersORM.email == email).first()
    if not user:
        logger.error(f"User with email {email} not found.") 
    return user

def updateUserById(userId: str, update_data: dict, db: Session):
    user = db.query(UsersORM).filter(UsersORM.id == userId).first()
    if not user:
        logger.error(f"User with ID {userId} not found for update.")
        return None
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    logger.info(f"Updated user with ID {userId}.")
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


def generateGmailAccessUrl(accountId: str) -> str:
    flow = generateOAuthFlow(accountId)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="false",
        state=accountId,
    )
    return auth_url

def generateOAuthFlow() -> Flow:

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": ENV_SETTINGS.GMAIL_WEB_CLIENT_ID,
                "client_secret": ENV_SETTINGS.GMAIL_WEB_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=GMAIL_SCOPES
    )

    flow.redirect_uri = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/users/auth/callback"
    return flow

def gmailExchangeCodeForToken(accountId: str, code: str, db: Session) -> dict:

    flow = generateOAuthFlow()
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        logger.info("Exchanged code for Gmail access token successfully.")

        updatePayload = {
            "gmailRefreshToken": credentials.refresh_token,
            "gmailRefreshTokenCreatedAt": datetime.now()
        }
        udpatedAccount = updateAccountById(accountId, updatePayload, db)
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
    except Exception as e:
        logger.error(f"Failed to exchange code for token: {e}")
        raise