from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from src.core.database import get_db
from src.modules.transactions.schema import TransactionORM
from src.modules.users.schema import UsersORM
from src.utils.log import setup_logger

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = setup_logger(__name__)


@router.get("/{userId}/daily-expenditure")
async def get_daily_expenditure(
    userId: str,
    days: int = Query(default=7, ge=1, le=365, description="Number of days to fetch (1-365)"),
    db: Session = Depends(get_db)
):
    """
    Get daily expenditure for a user over a specified number of days.
    
    Args:
        userId: User ID
        days: Number of days to include (default: 7, max: 365)
        db: Database session
    
    Returns:
        Daily expenditure data with totals for each day
    """
    try:
        user = db.query(UsersORM).filter(UsersORM.id == userId).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)
        
        results = db.query(
            func.date(TransactionORM.date_time).label('date'),
            func.sum(TransactionORM.amount).label('total')
        ).filter(
            TransactionORM.userId == userId,
            TransactionORM.transaction_type == 'debit',
            func.date(TransactionORM.date_time) >= start_date,
            func.date(TransactionORM.date_time) <= end_date
        ).group_by(
            func.date(TransactionORM.date_time)
        ).order_by(
            func.date(TransactionORM.date_time)
        ).all()
        
        expenditure_map = {str(row.date): float(row.total) for row in results}
        
        data = []
        current_date = start_date
        while current_date <= end_date:
            date_str = str(current_date)
            data.append({
                "date": date_str,
                "total": expenditure_map.get(date_str, 0.00)
            })
            current_date += timedelta(days=1)
        
        return JSONResponse(
            status_code=200,
            content={
                "metric": "daily_expenditure",
                "currency": "INR",
                "range": {
                    "start": str(start_date),
                    "end": str(end_date)
                },
                "data": data
            }
        )
    
    except Exception as e:
        logger.exception(f"Error fetching daily expenditure for userId {userId}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to fetch daily expenditure", "error": str(e)}
        )


@router.get("/{userId}/average-expenditure")
async def get_average_expenditure(
    userId: str,
    days: int = Query(default=7, ge=1, le=365, description="Number of days for average calculation (1-365)"),
    db: Session = Depends(get_db)
):
    """
    Get average daily expenditure for a user over a specified number of days.
    
    Args:
        userId: User ID
        days: Number of days to calculate average over (default: 7, max: 365)
        db: Database session
    
    Returns:
        Average daily expenditure data
    """
    try:
        user = db.query(UsersORM).filter(UsersORM.id == userId).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)
        
        result = db.query(
            func.sum(TransactionORM.amount).label('total')
        ).filter(
            TransactionORM.userId == userId,
            TransactionORM.transaction_type == 'debit',
            func.date(TransactionORM.date_time) >= start_date,
            func.date(TransactionORM.date_time) <= end_date
        ).first()
        
        total_expenditure = float(result.total) if result.total else 0.0
        average_expenditure = round(total_expenditure / days, 2)
        
        return JSONResponse(
            status_code=200,
            content={
                "metric": "average_expenditure",
                "currency": "INR",
                "range": {
                    "start": str(start_date),
                    "end": str(end_date),
                    "days": days
                },
                "total_expenditure": total_expenditure,
                "average_per_day": average_expenditure
            }
        )
    
    except Exception as e:
        logger.exception(f"Error fetching average expenditure for userId {userId}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to fetch average expenditure", "error": str(e)}
        )
