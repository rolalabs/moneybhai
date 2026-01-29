from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid

from src.core.database import get_db
from src.modules.budgets.models import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetListResponse
from packages.enums import BudgetType
from src.modules.budgets.operations import (
    create_budget,
    get_active_budget,
    get_all_active_budgets,
    update_budget,
    deactivate_budget,
    get_budget_with_calculations
)
from src.modules.budgets.schema import BudgetORM
from src.modules.users.operations import fetchUserById
from src.utils.log import setup_logger

router = APIRouter(prefix="/users/{user_id}/budgets", tags=["budgets"])
logger = setup_logger(__name__)


@router.post("/", response_model=BudgetResponse)
async def create_budget_route(user_id: str, payload: BudgetCreate, db: Session = Depends(get_db)):
    """
    Create a new budget for a user.
    Automatically deactivates any existing active budget of the same type.
    
    Args:
        user_id: User's ID
        payload: Budget creation payload
        db: Database session
    
    Returns:
        Created budget with calculations
    """
    try:
        # Verify user exists
        user = fetchUserById(user_id, db)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        # Validate budget type (Pydantic already validates enum, but keeping for explicit error message)
        valid_types = [e.value for e in BudgetType]
        if payload.budgetType.value not in valid_types:
            return JSONResponse(
                status_code=400,
                content={"message": f"Invalid budget type. Must be one of {valid_types}"}
            )
        
        # Create budget
        budget = create_budget(
            user_id=uuid.UUID(user_id),
            budget_type=payload.budgetType.value,
            limit_amount=payload.limitAmount,
            active_from=payload.activeFrom,
            db=db
        )
        
        # Return budget with calculations
        budget_response = get_budget_with_calculations(budget, db)
        return budget_response
    
    except ValueError as e:
        logger.error(f"Validation error creating budget: {e}")
        return JSONResponse(
            status_code=400,
            content={"message": str(e)}
        )
    except Exception as e:
        logger.exception(f"Error creating budget for user {user_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to create budget", "error": str(e)}
        )


@router.get("", response_model=BudgetListResponse)
async def get_all_budgets_route(user_id: str, db: Session = Depends(get_db)):
    """
    Get all active budgets for a user.
    Returns budgets with calculated spent, remaining, and usage percentage.
    
    Args:
        user_id: User's ID
        db: Database session
    
    Returns:
        List of active budgets with calculations
    """
    try:
        # Verify user exists
        user = fetchUserById(user_id, db)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        # Get all active budgets
        budgets = get_all_active_budgets(uuid.UUID(user_id), db)
        
        # Calculate spent for each budget
        budget_responses = [get_budget_with_calculations(budget, db) for budget in budgets]
        
        return BudgetListResponse(budgets=budget_responses)
    
    except Exception as e:
        logger.exception(f"Error fetching budgets for user {user_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to fetch budgets", "error": str(e)}
        )


@router.get("/{budget_type}", response_model=BudgetResponse)
async def get_budget_by_type_route(user_id: str, budget_type: str, db: Session = Depends(get_db)):
    """
    Get active budget for a user by budget type.
    Returns budget with calculated spent, remaining, and usage percentage.
    
    Args:
        user_id: User's ID
        budget_type: Budget type ('daily', 'weekly', or 'monthly')
        db: Database session
    
    Returns:
        Active budget with calculations
    """
    try:
        # Verify user exists
        user = fetchUserById(user_id, db)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        # Validate budget type
        valid_types = [e.value for e in BudgetType]
        if budget_type not in valid_types:
            return JSONResponse(
                status_code=400,
                content={"message": f"Invalid budget type. Must be one of {valid_types}"}
            )
        
        # Get active budget
        budget = get_active_budget(uuid.UUID(user_id), budget_type, db)
        
        if not budget:
            return JSONResponse(
                status_code=404,
                content={"message": f"No active {budget_type} budget found for user"}
            )
        
        # Return budget with calculations
        budget_response = get_budget_with_calculations(budget, db)
        return budget_response
    
    except Exception as e:
        logger.exception(f"Error fetching {budget_type} budget for user {user_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to fetch budget", "error": str(e)}
        )


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget_route(user_id: str, budget_id: str, payload: BudgetUpdate, db: Session = Depends(get_db)):
    """
    Update a budget.
    Can update limit amount or deactivate budget by setting activeTo.
    
    Args:
        user_id: User's ID
        budget_id: Budget ID
        payload: Budget update payload
        db: Database session
    
    Returns:
        Updated budget with calculations
    """
    try:
        # Verify user exists
        user = fetchUserById(user_id, db)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        # Verify budget exists and belongs to user
        budget = db.query(BudgetORM).filter(BudgetORM.id == uuid.UUID(budget_id)).first()
        if not budget:
            return JSONResponse(
                status_code=404,
                content={"message": "Budget not found"}
            )
        
        if str(budget.user_id) != user_id:
            return JSONResponse(
                status_code=403,
                content={"message": "Budget does not belong to user"}
            )
        
        # Update budget
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return JSONResponse(
                status_code=400,
                content={"message": "No fields to update"}
            )
        
        updated_budget = update_budget(
            budget_id=uuid.UUID(budget_id),
            limit_amount=update_data.get('limitAmount'),
            active_to=update_data.get('activeTo'),
            db=db
        )
        
        if not updated_budget:
            return JSONResponse(
                status_code=404,
                content={"message": "Budget not found"}
            )
        
        # Return budget with calculations
        budget_response = get_budget_with_calculations(updated_budget, db)
        return budget_response
    
    except Exception as e:
        logger.exception(f"Error updating budget {budget_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to update budget", "error": str(e)}
        )


@router.delete("/{budget_id}")
async def deactivate_budget_route(user_id: str, budget_id: str, db: Session = Depends(get_db)):
    """
    Deactivate a budget.
    Sets the budget's activeTo to current timestamp.
    
    Args:
        user_id: User's ID
        budget_id: Budget ID
        db: Database session
    
    Returns:
        Success message
    """
    try:
        # Verify user exists
        user = fetchUserById(user_id, db)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        # Verify budget exists and belongs to user
        budget = db.query(BudgetORM).filter(BudgetORM.id == uuid.UUID(budget_id)).first()
        if not budget:
            return JSONResponse(
                status_code=404,
                content={"message": "Budget not found"}
            )
        
        if str(budget.user_id) != user_id:
            return JSONResponse(
                status_code=403,
                content={"message": "Budget does not belong to user"}
            )
        
        # Deactivate budget
        success = deactivate_budget(uuid.UUID(budget_id), db)
        
        if not success:
            return JSONResponse(
                status_code=404,
                content={"message": "Budget not found"}
            )
        
        return JSONResponse(
            status_code=200,
            content={"message": "Budget deactivated successfully"}
        )
    
    except Exception as e:
        logger.exception(f"Error deactivating budget {budget_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to deactivate budget", "error": str(e)}
        )
