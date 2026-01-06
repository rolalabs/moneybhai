from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DEBUG: bool = False
    GEMINI_API_KEY: str
    WORKER_CLOUD_RUN_URL: str
    DATABASE_URL: str
    API_TOKEN_GITHUB: str = None
    GCP_CREDENTIALS: str = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

ENV_SETTINGS = Settings()