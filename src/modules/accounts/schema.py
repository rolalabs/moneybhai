import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column
from src.core.database import DB_BASE


class AccountsORM(DB_BASE):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    userId = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    createdAt = Column(DateTime, default=datetime.now, nullable=False)
    gmailRefreshToken = Column(String, nullable=True)
    gmailRefreshTokenCreatedAt = Column(DateTime, nullable=True)
    isSyncing = Column(Boolean, default=False, nullable=False)
    lastSyncedAt = Column(DateTime, nullable=True)