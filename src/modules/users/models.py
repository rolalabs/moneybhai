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

class UserAuthPayload(BaseModel):
    token: str

class GmailAuthVerificationResponse(BaseModel):
    email: str
    email_verified: bool
    name: str
    picture: str
    given_name: str
    family_name: str
    iat: int
    exp: int
    sub: str
    aud: str
    azp: str
    iss: str


    
