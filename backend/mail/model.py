from sqlalchemy import Column, String, Text, Integer, DateTime
from typing import List, Optional
from pydantic import BaseModel
from backend.utils.connectors import DB_BASE, DB_SESSION

class Header(BaseModel):
    name: str
    value: str


class Body(BaseModel):
    size: int
    data: Optional[str] = None


class Part(BaseModel):
    partId: str
    mimeType: str
    filename: str
    headers: Optional[List[Header]] = None
    body: Body


class Payload(BaseModel):
    partId: str
    mimeType: str
    filename: str
    headers: List[Header]
    body: Body
    parts: Optional[List[Part]] = None


class EmailMessage(BaseModel):
    id: str
    threadId: str
    labelIds: List[str]
    snippet: str
    payload: Payload
    sizeEstimate: int
    historyId: str
    internalDate: str


class EmailMessageORM(DB_BASE):
    __tablename__ = "emails"

    thread_id = Column(String, primary_key=True)
    id = Column(String)
    snippet = Column(Text)
    date_time = Column(DateTime)
    emailSender = Column(String(128))
    emailId = Column(String(128))


DB_BASE.metadata.create_all(DB_SESSION.bind)  # Create tables if they don't exist