import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column
from src.core.database import DB_BASE


class UsersORM(DB_BASE):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    createdAt = Column(DateTime, default=datetime.now, nullable=False)
    gmailRefreshToken = Column(String, nullable=True)
    gmailRefreshTokenCreatedAt = Column(DateTime, nullable=True)

# create table on startup
# DB_BASE.metadata.create_all(bind=DB_BASE.metadata.bind, checkfirst=True)
# DB_BASE.metadata.create_all(DB_ENGINE)