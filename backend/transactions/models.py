from pydantic import BaseModel
import sqlalchemy
from sqlalchemy import Column, String, Float, DateTime
from backend.utils.connectors import DB_BASE, DB_SESSION

class Transaction(BaseModel):
    thread_id: str
    amount: float
    transaction_type: str
    source_identifier: str
    source_type: str
    destination: str
    mode: str
    reference_number: str = None

class TransactionORM(DB_BASE):
    __tablename__ = 'transactions'
    __table_args__ = {'extend_existing': True}  
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

DB_BASE.metadata.create_all(DB_SESSION.bind)  # Create tables if they don't exist