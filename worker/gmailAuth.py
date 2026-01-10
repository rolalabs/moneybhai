from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from worker.connectors import ENV_SETTINGS

from packages.enums import GMAIL_SCOPES

def authenticateGmail(refresh_token: str):
    """
    Authenticates and returns a Gmail API service instance using OAuth 2.0.
    This function checks for existing user credentials stored in 'token.json'.
    If valid credentials are found, they are used to authenticate the user.
    If credentials are missing, expired, or invalid, the function initiates the OAuth 2.0 flow
    using the client secrets from 'credentials.json' and saves the new credentials to 'token.json'.
    Returns:
        googleapiclient.discovery.Resource: An authorized Gmail API service instance.
    Raises:
        FileNotFoundError: If 'credentials.json' is not found when initiating the OAuth flow.
        google.auth.exceptions.RefreshError: If the credentials cannot be refreshed.
    """


    creds = Credentials(
        token=None,  # will be filled after refresh
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=ENV_SETTINGS.GMAIL_WEB_CLIENT_ID,
        client_secret=ENV_SETTINGS.GMAIL_WEB_CLIENT_SECRET,
        scopes=GMAIL_SCOPES
    )

    creds.refresh(Request())

    return build('gmail', 'v1', credentials=creds)
