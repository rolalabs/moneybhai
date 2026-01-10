from pydantic import BaseModel, ConfigDict
from typing import Optional

class Transaction(BaseModel):
    id: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[str] = None
    source_identifier: Optional[str] = None
    source_type: str | None = None
    destination: Optional[str] = None
    mode: Optional[str] = None
    reference_number: Optional[str] = None
    emailSender: Optional[str] = None
    emailId: Optional[str] = None
    date_time: Optional[str] = None

class TransactionBulkInsertPayload(BaseModel):
    transactions: list[Transaction]
    userId: str
    emailId: str


class TaskQueuePayload(BaseModel):
    email: str
    userId: str
    token: str