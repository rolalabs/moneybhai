from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from worker.connectors import DB_BASE

class EmailMessage(BaseModel):
    thread_id: Optional[str] = None
    id: Optional[str] = None
    snippet: Optional[str] = None
    date_time: Optional[datetime] = None
    emailSender: Optional[str] = None
    emailId: Optional[str] = None
    source: Optional[str] = "ss.saswatsahoo@gmail"
    isTransaction: Optional[bool] = False
    isGeminiParsed: bool = False  


class TaskModel(BaseModel):
    id: str
    token: str
    email: str

