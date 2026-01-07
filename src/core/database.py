
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from src.core.environment import ENV_SETTINGS

DB_BASE = declarative_base()

DB_ENGINE = create_engine(
    ENV_SETTINGS.DATABASE_URL,
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
