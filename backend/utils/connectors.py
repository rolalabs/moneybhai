import outlines
from google import genai
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

GEN_AI_CLIENT = genai.Client(api_key=os.getenv('GENAI_API_KEY'))

# Initialize the Gemini model
# MODEL = outlines.from_gemini(GEN_AI_CLIENT, "gemini-2.5-flash")


def get_db():
    CLOUD_SQL_USER = 'reverie'
    CLOUD_SQL_PASSWORD = 'postgres'
    CLOUD_SQL_HOST = 'localhost:5432'  
    CLOUD_SQL_DB = 'postgres'

    DATABASE_URL = f"postgresql+psycopg2://{CLOUD_SQL_USER}:{CLOUD_SQL_PASSWORD}@{CLOUD_SQL_HOST}/{CLOUD_SQL_DB}"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

DB_SESSION = get_db()
DB_BASE = declarative_base()