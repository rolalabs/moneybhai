from fastapi.responses import JSONResponse
from packages.models import Transaction, TransactionBulkInsertPayload
from src.modules.transactions.schema import TransactionORM
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic

from src.core.database import get_db
from sqlalchemy.orm import Session

from src.utils.log import setup_logger

router = APIRouter(prefix="/transactions", tags=["transactions"])
security = HTTPBasic()

logger = setup_logger(__name__)


@router.get("/{id}")
async def get_transaction(id: str, db: Session = Depends(get_db)):
    """Get a transaction by ID."""
    # Placeholder implementation
    return {"transaction_id": id, "status": "not implemented"}

# create an endpoint to insert bulk transactions
@router.post("/bulk-insert")
async def bulk_insert_transactions(transactionsPayload: TransactionBulkInsertPayload, db: Session = Depends(get_db)):
    """Bulk insert transactions into the database."""
    try:
        txn_orm_list = []
        failed_transactions = []
        
        for idx, transaction in enumerate(transactionsPayload.transactions):
            try:
                txn = TransactionORM(
                    id=transaction.id, 
                    amount=transaction.amount,
                    transaction_type=transaction.transaction_type,
                    source_identifier=transaction.source_identifier,
                    source_type=transaction.source_type,
                    destination=transaction.destination,
                    mode=transaction.mode,
                    reference_number=transaction.reference_number,
                    emailSender=transaction.emailSender,
                    emailId=transaction.emailId,
                    date_time=transaction.date_time,
                )
                txn_orm_list.append(txn)
            except Exception as e:
                failed_transactions.append({"index": idx, "error": str(e), "transaction_id": transaction.get("id", "unknown")})
                logger.warning(f"Failed to process transaction at index {idx}: {e}")
        
        if txn_orm_list:
            db.bulk_save_objects(txn_orm_list)
            db.commit()
        
        inserted_count = len(txn_orm_list)
        failed_count = len(failed_transactions)
        
        logger.info(f"Inserted {inserted_count} transactions. Failed: {failed_count}")
        
        return JSONResponse(
            status_code=200 if failed_count == 0 else 207,  # 207 = Multi-Status (partial success)
            content={
                "message": f"Inserted {inserted_count} transactions, {failed_count} failed",
                "status": "success" if failed_count == 0 else "partial_success",
                "inserted": inserted_count,
                "failed": failed_count,
                "failed_transactions": failed_transactions if failed_transactions else None
            }
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"Error inserting bulk transactions: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to insert bulk transactions", "error": str(e)}
        )