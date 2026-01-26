from fastapi import APIRouter, Depends
from packages.utils import convert_iso_to_datetime
from src.core.database import get_db
from sqlalchemy.orm import Session
from src.modules.orders.schema import OrdersORM, OrderItemsORM
from src.modules.orders.models import OrdersBulkInsertPayload
from src.utils.log import setup_logger

router = APIRouter(prefix="/orders", tags=["orders"])
logger = setup_logger(__name__)


# create an endpoint to insert bulk transactions
@router.post("/bulk-insert")
async def bulk_insert_transactions(orderPayloadList: OrdersBulkInsertPayload, db: Session = Depends(get_db)):
    """Insert orders one by one into the database."""
    logger.info(f"Processing {len(orderPayloadList.orders)} orders for insertion")
    
    inserted_count = 0
    skipped_count = 0
    failed_count = 0
    
    for idx, order in enumerate(orderPayloadList.orders):
        try:
            # Create ORM object
            ord = OrdersORM(
                order_id=order.orderId, 
                vendor=order.vendor,
                order_date=convert_iso_to_datetime(order.orderDate),
                currency=order.currency,
                sub_total=order.subTotal,
                total=order.total,
                account_id=orderPayloadList.accountId,
                message_id=order.messageId
            )
            
            # Try to insert the order
            db.add(ord)
            db.commit()
            inserted_count += 1
                
        except Exception as e:
            db.rollback()
            # Check if it's a duplicate key error
            if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                skipped_count += 1
                logger.debug(f"Skipped duplicate order at index {idx}: {order.orderId}")
            else:
                failed_count += 1
                logger.warning(f"Failed to insert order at index {idx}: {e}. Order ID: {order.orderId}")
            continue
    
    logger.info(f"Insert completed: {inserted_count} inserted, {skipped_count} skipped, {failed_count} failed")
    return {
        "inserted": inserted_count,
        "skipped": skipped_count,
        "failed": failed_count
    }