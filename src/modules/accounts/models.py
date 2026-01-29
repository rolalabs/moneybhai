from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AccountUpdatePayload(BaseModel):
    lastSyncedAt: Optional[datetime] = None
    isSyncing: Optional[bool] = None
    gmailRefreshToken: Optional[str] = None
    gmailRefreshTokenCreatedAt: Optional[datetime] = None
