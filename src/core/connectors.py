from google import genai
from google.genai.types import HttpOptions
from src.core.environment import ENV_SETTINGS
from google.oauth2 import service_account
import json


credentials = service_account.Credentials.from_service_account_info(
    json.loads(ENV_SETTINGS.GCP_CREDENTIALS)
)
credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])

VERTEXT_CLIENT = genai.Client(
    http_options=HttpOptions(api_version="v1"),
    vertexai=True,
    project="rola-labs",
    location="asia-south1",
    credentials=credentials,
)