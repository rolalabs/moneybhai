from pydantic import BaseModel
from sqlalchemy import Column, String, Float
class Transaction(BaseModel):
    thread_id: str
    amount: float
    transaction_type: str
    source_identifier: str
    source_type: str
    destination: str
    mode: str
    reference_number: str = None
