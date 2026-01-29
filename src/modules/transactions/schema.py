
import sqlalchemy
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from src.core.database import DB_BASE
from sqlalchemy.dialects.postgresql import UUID


class TransactionORM(DB_BASE):
    __tablename__ = 'transactions'
    id = sqlalchemy.Column(String, primary_key=True)
    amount = Column(Float)
    transaction_type = Column(String(128))
    source_identifier = Column(String(128))
    is_include_analytics = Column(sqlalchemy.Boolean, default=True, server_default=sqlalchemy.sql.expression.true())
    destination = Column(String(128))
    mode = Column(String(128))
    date_time = Column(DateTime)
    email_sender = Column(String(128))
    email_id = Column(String(128))
    reference_number = Column(String(128))
    userId = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    accountId = Column(UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
