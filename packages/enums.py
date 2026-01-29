from enum import Enum


class BudgetType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]
