from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DEBUG: bool = False
    MB_BACKEND_API_URL: str | None = None
    GMAIL_WEB_CLIENT_ID: str | None = None
    GMAIL_WEB_CLIENT_SECRET: str | None = None
    WORKER_CLOUD_RUN_URL: str | None = None
    API_TOKEN_GITHUB: str | None = None
    GCP_CREDENTIALS: str | None = None
    DATABASE_URL: str | None = None
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str = "MoneyBhai"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

ENV_SETTINGS = Settings()