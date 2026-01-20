from fastapi.responses import JSONResponse
from modules.users.operations import generateGmailAccessUrl
from src.modules.accounts.models import AccountUpdatePayload
from src.modules.accounts.operations import releaseSyncLock, updateAccountById
from src.modules.accounts.schema import AccountsORM
from fastapi import APIRouter, Depends
from src.core.database import get_db
from sqlalchemy.orm import Session
from src.utils.log import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/{id}")
async def get_account(id: str, db: Session = Depends(get_db)):
    """Get an account by ID."""
    account = db.query(AccountsORM).filter(AccountsORM.id == id).first()
    if not account:
        return JSONResponse(
            status_code=404,
            content={"message": "Account not found"}
        )
    return account

@router.put("/{id}")
async def update_account(id: str, payload: AccountUpdatePayload, db: Session = Depends(get_db)):
    """Update account by ID."""
    try:
        account = db.query(AccountsORM).filter(AccountsORM.id == id).first()
        if not account:
            return JSONResponse(
                status_code=404,
                content={"message": "Account not found"}
            )
        
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return JSONResponse(
                status_code=400,
                content={"message": "No fields to update"}
            )
        
        updated_account = updateAccountById(id, update_data, db)
        return JSONResponse(
            status_code=200,
            content={"message": "Account updated successfully", "account": {"id": str(updated_account.id)}}
        )
    except Exception as e:
        logger.exception(f"Error updating account {id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to update account", "error": str(e)}
        )

@router.post("/{id}/unlock")
async def unlock_sync_route(id: str, db: Session = Depends(get_db)):
    """Release sync lock for account - to be called by worker after completion"""
    try:
        account = db.query(AccountsORM).filter(AccountsORM.id == id).first()
        if not account:
            return JSONResponse(
                status_code=404,
                content={"message": "Account not found"}
            )
        
        releaseSyncLock(id, db)
        return JSONResponse(
            status_code=200,
            content={"message": "Sync lock released successfully"}
        )
    except Exception as e:
        logger.exception(f"Error releasing sync lock: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to release sync lock", "error": str(e)}
        )

@router.get("/{id}/gmail-access-url", response_model=dict)
async def get_refresh_token_route(id: str, db: Session = Depends(get_db)):
    """Get the Gmail refresh token for the account."""
    account = db.query(AccountsORM).filter(AccountsORM.id == id).first()
    if not account:
        return JSONResponse(
            status_code=404,
            content={"message": "Account not found"}
        )
    gmail_access_url = generateGmailAccessUrl(str(account.id))

    return {
        "gmailAccessUrl": gmail_access_url
    }