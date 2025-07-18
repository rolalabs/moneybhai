from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON
from pydantic import BaseModel
from backend.utils.connectors import DB_BASE, DB_SESSION

class EmailMessage(BaseModel):
    thread_id: str
    id: str
    snippet: str
    date_time: datetime
    emailSender: str
    emailId: str
    source: str = "ss.saswatsahoo@gmail"
    isTransaction: bool = False
    isGeminiParsed: bool = False  


class EmailMessageORM(DB_BASE):
    __tablename__ = "emails"

    thread_id = Column(String, primary_key=True)
    id = Column(String)
    snippet = Column(Text)
    date_time = Column(DateTime)
    emailSender = Column(String(128))
    emailId = Column(String(128))
    source = Column(String(128), default="ss.saswatsahoo@gmail")
    isTransaction = Column(Boolean, default=False)
    isGeminiParsed = Column(Boolean, default=False)


# DB_BASE.metadata.create_all(DB_SESSION.bind)  # Create tables if they don't exist