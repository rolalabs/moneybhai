from pydantic import BaseModel
import sqlalchemy
from sqlalchemy import Column, String, Float, DateTime
from src.core.database import DB_BASE

class Transaction(BaseModel):
    id: str = None
    amount: float = None
    transaction_type: str = None
    source_identifier: str = None
    source_type: str = None
    destination: str = None
    mode: str = None
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
