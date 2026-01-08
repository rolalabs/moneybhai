from pydantic import BaseModel

class Transaction(BaseModel):
    id: str = None
    amount: float = None
    transaction_type: str = None
    source_identifier: str = None
    source_type: str = None
    destination: str = None
    mode: str = None
    reference_number: str = None
    emailSender: str = None
    emailId: str = None
    date_time: str = None

class TransactionBulkInsertPayload(BaseModel):
    transactions: list[Transaction]
    userId: str
    emailId: str