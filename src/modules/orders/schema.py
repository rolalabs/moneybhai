import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import DB_BASE


class OrdersORM(DB_BASE):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(String, nullable=False)
    message_id = Column(String, nullable=True)
    vendor = Column(String, nullable=True)
    order_date = Column(DateTime, nullable=True)
    currency = Column(String, nullable=True)
    sub_total = Column(Float, nullable=True)
    total = Column(Float, nullable=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class OrderItemsORM(DB_BASE):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
    name = Column(String, nullable=True)
    item_type = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    unit_type = Column(String, nullable=True)
    unit_price = Column(Float, nullable=True)
    total = Column(Float, nullable=True) 