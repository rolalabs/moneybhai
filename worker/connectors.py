import json
from google import genai
from pydantic_settings import BaseSettings, SettingsConfigDict
from google.oauth2 import service_account
from google.genai.types import HttpOptions

class Settings(BaseSettings):
    DEBUG: bool = False
    WORKER_CLOUD_RUN_URL: str
    MB_BACKEND_API_URL: str = "http://0.0.0.0:8080/api/"
    API_TOKEN_GITHUB: str = None
    GCP_CREDENTIALS: str = None
    GMAIL_WEB_CLIENT_ID: str = None
    GMAIL_WEB_CLIENT_SECRET: str = None
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str = "MoneyBhai"


    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

ENV_SETTINGS = Settings()

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

# credentials = service_account.Credentials.from_service_account_info(
#     json.loads(ENV_SETTINGS.GOOGLE_APPLICATION_CREDENTIALS)
# )
# credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
