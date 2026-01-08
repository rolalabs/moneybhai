from pydantic import BaseModel
import uuid

class CreateUser(BaseModel):
    email: str
    full_name: str
    is_active: bool = True

class UserDBModel(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool


class UserSyncModel(BaseModel):
    token: dict
    userId: str
