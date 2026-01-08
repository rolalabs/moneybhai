from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON
from pydantic import BaseModel
from worker.connectors import DB_BASE

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


class TaskModel(BaseModel):
    id: str
    token: str
    email: str

