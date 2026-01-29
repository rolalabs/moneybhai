import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import DB_BASE


class BudgetORM(DB_BASE):
    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    budget_type = Column(String(16), nullable=False)  # 'daily', 'weekly', 'monthly'
    limit_amount = Column(Float, nullable=False)
    active_from = Column(DateTime, nullable=False)
    active_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
