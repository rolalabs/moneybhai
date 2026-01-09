
import sqlalchemy
from sqlalchemy import Column, String, Float, DateTime
from src.core.database import DB_BASE
from sqlalchemy.dialects.postgresql import UUID


class TransactionORM(DB_BASE):
    __tablename__ = 'transactions'
    id = sqlalchemy.Column(String, primary_key=True)
    amount = Column(Float)
    transaction_type = Column(String(128))
    source_identifier = Column(String(128))
    source_type = Column(String(128))
    destination = Column(String(128))
    mode = Column(String(128))
    date_time = Column(DateTime)
    emailSender = Column(String(128))
    emailId = Column(String(128))
    reference_number = Column(String(128))
    userId = Column(UUID(as_uuid=True), nullable=False)
