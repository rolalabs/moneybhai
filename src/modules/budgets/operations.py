from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid

from src.modules.budgets.schema import BudgetORM
from src.modules.transactions.schema import TransactionORM
from src.modules.budgets.models import BudgetResponse
from src.utils.log import setup_logger
from packages.enums import BudgetType

logger = setup_logger(__name__)


def get_date_range_for_budget(budget_type: str, reference_date: datetime, user_timezone: str = 'UTC') -> tuple[datetime, datetime]:
    """
    Calculate the date range for a given budget type and reference date.
    Returns (start_date, end_date) in UTC.
    
    Args:
        budget_type: 'daily', 'weekly', or 'monthly'
        reference_date: The reference date for calculation (should be timezone-aware)
        user_timezone: User's timezone (default: 'UTC')
    """
    # Ensure reference_date is timezone-aware
    if reference_date.tzinfo is None:
        reference_date = reference_date.replace(tzinfo=timezone.utc)
    
    if budget_type == BudgetType.DAILY:
        start_date = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    
    elif budget_type == BudgetType.WEEKLY:
        # Calendar week: Monday (0) to Sunday (6)
        days_since_monday = reference_date.weekday()
        start_date = (reference_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
    
    elif budget_type == BudgetType.MONTHLY:
        # First day of the month
        start_date = reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # First day of next month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
    
    else:
        raise ValueError(f"Invalid budget_type: {budget_type}. Must be one of {[e.value for e in BudgetType]}")
    
    return start_date, end_date


def calculate_spent_amount(user_id: uuid.UUID, start_date: datetime, end_date: datetime, db: Session) -> float:
    """
    Calculate the total spent amount for a user within a date range.
    Only includes debit transactions (transaction_type = 'debit').
    Excludes credits, refunds, and reversals.
    
    Args:
        user_id: User's UUID
        start_date: Start of the date range (inclusive)
        end_date: End of the date range (exclusive)
        db: Database session
    
    Returns:
        Total spent amount
    """
    result = db.query(func.sum(TransactionORM.amount)).filter(
        and_(
            TransactionORM.user_id == user_id,
            TransactionORM.transaction_type == 'debit',
            TransactionORM.date_time >= start_date,
            TransactionORM.date_time < end_date
        )
    ).scalar()
    
    return result if result is not None else 0.0


def create_budget(user_id: uuid.UUID, budget_type: str, limit_amount: float, active_from: datetime, db: Session) -> BudgetORM:
    """
    Create a new budget for a user.
    Deactivates any existing active budget of the same type.
    
    Args:
        user_id: User's UUID
        budget_type: 'daily', 'weekly', or 'monthly'
        limit_amount: Budget limit amount
        active_from: Budget active from date
        db: Database session
    
    Returns:
        Created budget ORM object
    """
    # Validate budget type
    if budget_type not in [e.value for e in BudgetType]:
        raise ValueError(f"Invalid budget_type: {budget_type}. Must be one of {[e.value for e in BudgetType]}")
    
    # Deactivate existing active budgets of the same type
    existing_budgets = db.query(BudgetORM).filter(
        and_(
            BudgetORM.user_id == user_id,
            BudgetORM.budget_type == budget_type,
            BudgetORM.active_to.is_(None)
        )
    ).all()
    
    for budget in existing_budgets:
        budget.active_to = datetime.now(timezone.utc)
        logger.info(f"Deactivated existing budget {budget.id} for user {user_id}")
    
    # Create new budget
    new_budget = BudgetORM(
        user_id=user_id,
        budget_type=budget_type,
        limit_amount=limit_amount,
        active_from=active_from,
        active_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    
    logger.info(f"Created budget {new_budget.id} for user {user_id}")
    return new_budget


def get_active_budget(user_id: uuid.UUID, budget_type: str, db: Session) -> Optional[BudgetORM]:
    """
    Get the active budget for a user and budget type.
    
    Args:
        user_id: User's UUID
        budget_type: 'daily', 'weekly', or 'monthly'
        db: Database session
    
    Returns:
        Active budget ORM object or None
    """
    budget = db.query(BudgetORM).filter(
        and_(
            BudgetORM.user_id == user_id,
            BudgetORM.budget_type == budget_type,
            BudgetORM.active_to.is_(None)
        )
    ).first()
    
    return budget


def get_all_active_budgets(user_id: uuid.UUID, db: Session) -> list[BudgetORM]:
    """
    Get all active budgets for a user.
    
    Args:
        user_id: User's UUID
        db: Database session
    
    Returns:
        List of active budget ORM objects
    """
    budgets = db.query(BudgetORM).filter(
        and_(
            BudgetORM.user_id == user_id,
            BudgetORM.active_to.is_(None)
        )
    ).all()
    
    return budgets


def update_budget(budget_id: uuid.UUID, limit_amount: Optional[float], active_to: Optional[datetime], db: Session) -> Optional[BudgetORM]:
    """
    Update a budget.
    
    Args:
        budget_id: Budget UUID
        limit_amount: New limit amount (optional)
        active_to: New active_to date (optional)
        db: Database session
    
    Returns:
        Updated budget ORM object or None if not found
    """
    budget = db.query(BudgetORM).filter(BudgetORM.id == budget_id).first()
    
    if not budget:
        logger.error(f"Budget {budget_id} not found")
        return None
    
    if limit_amount is not None:
        budget.limit_amount = limit_amount
    
    if active_to is not None:
        budget.active_to = active_to
    
    budget.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(budget)
    
    logger.info(f"Updated budget {budget_id}")
    return budget


def deactivate_budget(budget_id: uuid.UUID, db: Session) -> bool:
    """
    Deactivate a budget by setting active_to to current timestamp.
    
    Args:
        budget_id: Budget UUID
        db: Database session
    
    Returns:
        True if deactivated, False if not found
    """
    budget = db.query(BudgetORM).filter(BudgetORM.id == budget_id).first()
    
    if not budget:
        logger.error(f"Budget {budget_id} not found")
        return False
    
    budget.active_to = datetime.now(timezone.utc)
    budget.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    logger.info(f"Deactivated budget {budget_id}")
    return True


def get_budget_with_calculations(budget: BudgetORM, db: Session, user_timezone: str = 'UTC') -> BudgetResponse:
    """
    Get budget with calculated spent, remaining, and usage percentage.
    
    Args:
        budget: Budget ORM object
        db: Database session
        user_timezone: User's timezone (default: 'UTC')
    
    Returns:
        BudgetResponse with all calculated fields
    """
    # Get current date range for this budget type
    current_time = datetime.now(timezone.utc)
    start_date, end_date = get_date_range_for_budget(budget.budget_type, current_time, user_timezone)
    
    # Calculate spent amount
    spent_amount = calculate_spent_amount(budget.user_id, start_date, end_date, db)
    
    # Calculate remaining and usage
    remaining_amount = budget.limit_amount - spent_amount
    usage_percent = (spent_amount / budget.limit_amount * 100) if budget.limit_amount > 0 else 0
    exceeded = spent_amount > budget.limit_amount
    
    return BudgetResponse(
        id=str(budget.id),
        userId=str(budget.user_id),
        budgetType=budget.budget_type,
        limitAmount=budget.limit_amount,
        spentAmount=spent_amount,
        remainingAmount=remaining_amount,
        usagePercent=round(usage_percent, 2),
        exceeded=exceeded,
        activeFrom=budget.active_from,
        activeTo=budget.active_to,
        createdAt=budget.created_at,
        updatedAt=budget.updated_at
    )
