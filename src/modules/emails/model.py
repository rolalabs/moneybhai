from sqlalchemy import UUID, Column, ForeignKey, String, Text, DateTime
from pydantic import BaseModel
from packages.models import EmailSanitized
from src.core.database import DB_BASE

class EmailBulkInsertPayload(BaseModel):
    emails: list[EmailSanitized]
    userId: str
    accountId: str
    emailId: str

class EmailBulkInsertResponse(BaseModel):
    message: str
    status: str

class EmailMessageORM(DB_BASE):
    __tablename__ = "emails"

    id = Column(String, primary_key=True)
    thread_id = Column(String)
    snippet = Column(Text)
    date_time = Column(DateTime)
    emailSender = Column(String(128))
    emailId = Column(String(128))
    accountId = Column(UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)