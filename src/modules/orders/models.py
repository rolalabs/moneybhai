from pydantic import BaseModel
from typing import List

from packages.models import OrdersIntentModel

class OrdersBulkInsertPayload(BaseModel):
    userId: str
    accountId: str
    orders: List[OrdersIntentModel]

 