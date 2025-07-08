import os.path
import base64
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
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

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)
