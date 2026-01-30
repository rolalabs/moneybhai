from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from packages.utils import convert_iso_to_datetime
from src.core.database import get_db
from sqlalchemy.orm import Session
from src.modules.orders.schema import OrdersORM, OrderItemsORM
from src.modules.orders.models import OrdersBulkInsertPayload
from src.modules.accounts.schema import AccountsORM
from src.utils.log import setup_logger

router = APIRouter(prefix="/users/{user_id}/orders", tags=["orders"])
logger = setup_logger(__name__)


# create an endpoint to insert bulk transactions
@router.post("/bulk-insert")
async def bulk_insert_transactions(user_id: str, orderPayloadList: OrdersBulkInsertPayload, db: Session = Depends(get_db)):
    """Insert orders one by one into the database."""
    logger.info(
        f"Processing {len(orderPayloadList.orders)} orders for insertion",
        extra={
            "total_count": len(orderPayloadList.orders),
            "account_id": orderPayloadList.accountId,
            "user_id": orderPayloadList.userId
        }
    )
    
    inserted_count = 0
    skipped_count = 0
    failed_count = 0
    updated_count = 0
    
    for idx, order in enumerate(orderPayloadList.orders):
        try:
            # Check if order already exists
            existing_order = db.query(OrdersORM).filter(OrdersORM.order_id == order.orderId).first()
            
            if existing_order:
                # Update existing order with any new non-None values
                if order.vendor is not None:
                    existing_order.vendor = order.vendor
                if order.orderDate is not None:
                    existing_order.order_date = convert_iso_to_datetime(order.orderDate)
                if order.currency is not None:
                    existing_order.currency = order.currency
                if order.subTotal is not None:
                    existing_order.sub_total = order.subTotal
                if order.total is not None:
                    existing_order.total = order.total
                if order.messageId is not None:
                    existing_order.message_id = order.messageId
                
                db.commit()
                updated_count += 1
                logger.debug(f"Updated existing order at index {idx}: {order.orderId}")
                ord = existing_order
            else:
                # Create new order
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
                db.add(ord)
                db.commit()
                db.refresh(ord)
                inserted_count += 1

            # Insert order items (append new items)
            for item in order.items:
                order_item = OrderItemsORM(
                    order_id=ord.id,
                    account_id=orderPayloadList.accountId,
                    name=item.name,
                    item_type=item.itemType,
                    quantity=item.quantity,
                    unit_price=item.unitPrice,
                    category=item.category,
                    unit_type=item.unitType,
                    total=item.total,
                )
                db.add(order_item)
            db.commit()
                
        except Exception as e:
            db.rollback()
            failed_count += 1
            logger.warning(f"Failed to process order at index {idx}: {e}. Order ID: {order.orderId}")
            continue
    
    logger.info(
        f"Insert completed: {inserted_count} inserted, {skipped_count} skipped, {failed_count} failed",
        extra={
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "total_count": len(orderPayloadList.orders),
            "account_id": orderPayloadList.accountId
        }
    )
    return {
        "inserted": inserted_count,
        "skipped": skipped_count,
        "updated": updated_count,
        "failed": failed_count
    }


@router.get("/")
async def get_orders_by_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all orders for a specific user.
    
    Args:
        user_id: User ID
        db: Database session
    
    Returns:
        List of orders with their items
    """
    try:
        # Get all account IDs for this user
        account_ids = db.query(AccountsORM.id).filter(
            AccountsORM.userId == user_id
        ).all()
        
        if not account_ids:
            return JSONResponse(
                status_code=404,
                content={"message": "No accounts found for user"}
            )
        
        account_id_list = [acc.id for acc in account_ids]
        
        # Query orders and items in a single JOIN query
        results = db.query(OrdersORM, OrderItemsORM).outerjoin(
            OrderItemsORM, OrdersORM.id == OrderItemsORM.order_id
        ).filter(
            OrdersORM.account_id.in_(account_id_list)
        ).order_by(OrdersORM.order_date.desc()).all()
        
        # Group items by order
        orders_map = {}
        order: OrdersORM
        item: OrderItemsORM
        for order, item in results:
            order_id = order.order_id
            if order_id not in orders_map:
                orders_map[order_id] = {
                    "orderId": order.order_id,
                    "messageId": order.message_id,
                    "vendor": order.vendor,
                    "orderDate": order.order_date.isoformat() if order.order_date else None,
                    "currency": order.currency,
                    "subTotal": order.sub_total,
                    "total": order.total,
                    "accountId": str(order.account_id),
                    "createdAt": order.created_at.isoformat() if order.created_at else None,
                    "items": []
                }
            
            if item:
                orders_map[order_id]["items"].append({
                    "id": str(item.id),
                    "name": item.name,
                    "category": item.category,
                    "itemType": item.item_type,
                    "quantity": item.quantity,
                    "unitType": item.unit_type,
                    "unitPrice": item.unit_price,
                    "total": item.total
                })
        
        orders_data = list(orders_map.values())
        
        return JSONResponse(
            status_code=200,
            content={
                "userId": user_id,
                "totalOrders": len(orders_data),
                "orders": orders_data
            }
        )
        
    except Exception as e:
        logger.exception(f"Error fetching orders for userId {user_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to fetch orders", "error": str(e)}
        )