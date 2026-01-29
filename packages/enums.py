from enum import Enum


class BudgetType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TransactionCategory(str, Enum):
    GROCERY = "GROCERY"
    FOOD_AND_DINING = "FOOD_AND_DINING"
    HEALTH = "HEALTH"
    PHARMACY = "PHARMACY"
    ELECTRICITY = "ELECTRICITY"
    WATER = "WATER"
    GAS = "GAS"
    INTERNET = "INTERNET"
    MOBILE = "MOBILE"
    RENT = "RENT"
    EDUCATION = "EDUCATION"
    TRANSPORT = "TRANSPORT"
    TRAVEL = "TRAVEL"
    FUEL = "FUEL"
    SHOPPING = "SHOPPING"
    ENTERTAINMENT = "ENTERTAINMENT"
    SUBSCRIPTION = "SUBSCRIPTION"
    INSURANCE = "INSURANCE"
    CREDIT_CARD_BILL = "CREDIT_CARD_BILL"
    LOAN_REPAYMENT = "LOAN_REPAYMENT"
    TAX = "TAX"
    FEES_AND_CHARGES = "FEES_AND_CHARGES"
    SALARY = "SALARY"
    INVESTMENT = "INVESTMENT"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]
