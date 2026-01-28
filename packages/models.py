from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class Transaction(BaseModel):
    id: Optional[str] = None
    amount: Optional[float] = None
    transaction_type: Optional[str] = None
    source_identifier: Optional[str] = None
    destination: Optional[str] = None
    mode: Optional[str] = None
    reference_number: Optional[str] = None
    emailSender: Optional[str] = None
    emailId: Optional[str] = None
    date_time: Optional[str] = None

class TransactionBulkInsertPayload(BaseModel):
    transactions: list[Transaction]
    userId: str
    accountId: str
    emailId: str


class TaskQueuePayload(BaseModel):
    email: str
    accountId: str
    userId: str
    token: str


class OrderItemsIntentModel(BaseModel):
    model_config = ConfigDict(extra='ignore')

    name: Optional[str] = Field(None, description="Name of the item")
    itemType: Optional[str] = Field(None, description="Type of expense the item like 'product' | 'tax' | 'fee' | 'shipping' | 'discount' | 'tip' | 'misc' | null")
    quantity: Optional[float] = Field(None, description="Quantity of the item in numeric like 1, 2, 3.5 etc.")
    unitType: Optional[str] = Field(None, description="Unit of the item quantity like pcs, kg, gms, liters, etc.")
    unitPrice: Optional[float] = Field(None, description="Unit price of the item or how much for each item")
    total: Optional[float] = Field(None, description="Total price of the item as per the receipt")

class OrdersIntentModel(BaseModel):
    model_config = ConfigDict(extra='ignore')

    orderId: str = Field(..., description="Unique identifier for the order")
    messageId: str = Field(..., description="Gmail message ID from which the order was extracted")
    vendor: Optional[str] = Field(None, description="Name of the vendor like Swiggy, Zomato, Amazon, Flipkart, Zepto, etc.")
    orderDate: Optional[str] = Field(None, description="Date and time when the order was placed in ISO 8601 format")
    currency: Optional[str] = Field(None, description="Currency code in format of USD, INR, EUR, etc.")
    subTotal: Optional[float] = Field(None, description="Subtotal amount before taxes and discounts")
    total: Optional[float] = Field(None, description="Total amount after taxes and discounts")
    items: list[OrderItemsIntentModel] = []

class OrdersListIntentModel(BaseModel):
    orders: list[OrdersIntentModel] = Field(..., description="List of orders extracted from emails")

class EmailSanitized(BaseModel):
    id: str
    threadId: str
    emailSender: str
    emailId: str
    subject: str
    snippet: str
    body: str
    receivedAt: datetime
