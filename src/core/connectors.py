from google import genai
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator
from google import genai
from google.genai.types import HttpOptions
from google.oauth2 import service_account

class Settings(BaseSettings):
    DEBUG: bool = False
    CLOUD_SQL_USER: str
    CLOUD_SQL_PASSWORD: str
    CLOUD_SQL_HOST: str
    CLOUD_SQL_DB: str
    API_TOKEN_GITHUB: str = None
    GOOGLE_APPLICATION_CREDENTIALS: str = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

ENV_SETTINGS = Settings()


GEN_AI_CLIENT = genai.Client(api_key=ENV_SETTINGS.GEMINI_API_KEY, http_options=HttpOptions(timeout=60))

# Initialize the Gemini model
# MODEL = outlines.from_gemini(GEN_AI_CLIENT, "gemini-2.5-flash")

DB_BASE = declarative_base(metadata=MetaData(schema="moneybhai"))
DATABASE_URL = f"postgresql+psycopg2://{ENV_SETTINGS.CLOUD_SQL_USER}:{ENV_SETTINGS.CLOUD_SQL_PASSWORD}@{ENV_SETTINGS.CLOUD_SQL_HOST}/{ENV_SETTINGS.CLOUD_SQL_DB}"

DB_ENGINE = create_engine(
    DATABASE_URL,
    echo=False,  # optional, logs SQL queries
    future=True
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=DB_ENGINE
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db  # provides the session to route
    finally:
        db.close()  # ensures session is closed after request

credentials = service_account.Credentials.from_service_account_info(
    json.loads(ENV_SETTINGS.GOOGLE_APPLICATION_CREDENTIALS)
)
credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
