from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from packages.enums import BudgetType


class BudgetCreate(BaseModel):
    budgetType: BudgetType = Field(..., description="Budget type: 'daily', 'weekly', or 'monthly'")
    limitAmount: float = Field(..., description="Budget limit amount", gt=0)
    activeFrom: datetime = Field(..., description="Budget active from date")


class BudgetUpdate(BaseModel):
    limitAmount: Optional[float] = Field(None, description="Updated budget limit amount", gt=0)
    activeTo: Optional[datetime] = Field(None, description="Budget active to date")


class BudgetResponse(BaseModel):
    id: str
    userId: str
    budgetType: str
    limitAmount: float
    spentAmount: float
    remainingAmount: float
    usagePercent: float
    exceeded: bool
    activeFrom: datetime
    activeTo: Optional[datetime]
    createdAt: datetime
    updatedAt: datetime


class BudgetListResponse(BaseModel):
    budgets: list[BudgetResponse]
