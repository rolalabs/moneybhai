from fastapi.responses import JSONResponse
from packages.models import TransactionBulkInsertPayload
from src.modules.transactions.schema import TransactionORM
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic

from src.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

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
        logger.info(f"Processing {len(transactionsPayload.transactions)} transactions for bulk insert")
        
        # Create ORM objects for type safety
        txn_orm_list = []
        failed_count = 0
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
                    userId=transactionsPayload.userId,
                    accountId=transactionsPayload.accountId,
                )
                txn_orm_list.append(txn)
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to process transaction at index {idx}: {e}. Failed transaction ID: {transaction.id}")
        
        inserted_count = 0
        skipped_count = 0
        
        if txn_orm_list:
            # Convert ORM objects to dictionaries for bulk insert
            txn_data = []
            for orm_obj in txn_orm_list:
                obj_dict = {}
                for col in TransactionORM.__table__.columns:
                    obj_dict[col.name] = getattr(orm_obj, col.name)
                txn_data.append(obj_dict)
            
            # Use PostgreSQL's ON CONFLICT DO NOTHING to skip duplicates
            stmt = insert(TransactionORM).values(txn_data)
            stmt = stmt.on_conflict_do_nothing(index_elements=['id'])
            
            result = db.execute(stmt)
            db.commit()
            
            inserted_count = result.rowcount
            skipped_count = len(txn_orm_list) - inserted_count
        
        logger.info(f"Inserted {inserted_count} transactions, skipped {skipped_count} duplicates, failed {failed_count}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Inserted {inserted_count} transactions, skipped {skipped_count} duplicates, {failed_count} failed",
                "status": "completed",
                "inserted": inserted_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "total": len(transactionsPayload.transactions)
            }
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"Error inserting bulk transactions: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to insert bulk transactions", "error": str(e)}
        )