from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from fastapi import Depends
from src.modules.accounts.schema import AccountsORM
from src.modules.accounts.operations import getAccountById
from src.modules.users.operations import fetchUserById
from src.modules.emails.model import EmailBulkInsertPayload, EmailMessageORM
from src.core.database import get_db
from src.utils.log import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MoneyBhai Email Processor API", "status": "running"}


# add an endpoint that will insert 100 emails at once into the database. the payload will have list of emails
@router.post("/insert-bulk")
async def insert_bulk_emails(payload: EmailBulkInsertPayload, db: Session = Depends(get_db)):
    """Route to insert bulk emails into the database"""
    try:
        # validate user
        user = fetchUserById(payload.userId, db)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        account: AccountsORM = getAccountById(payload.accountId, db)
        if not account:
            return JSONResponse(
                status_code=404,
                content={"message": "Account not found"}
            )
        

        logger.info(f"Inserting {len(payload.emails)} emails into the database for email: {payload.emailId}")

        # Create ORM objects for type safety
        email_orm_list = []
        for email in payload.emails:
            email_orm = EmailMessageORM(
                thread_id=email.threadId,
                id=email.id,
                snippet=email.snippet,
                date_time=email.receivedAt,
                emailSender=email.emailSender,
                emailId=email.emailId,
                accountId=payload.accountId,
            )
            email_orm_list.append(email_orm)
        
        # Convert ORM objects to dictionaries for bulk insert
        email_data = []
        for orm_obj in email_orm_list:
            obj_dict = {}
            for col in EmailMessageORM.__table__.columns:
                obj_dict[col.name] = getattr(orm_obj, col.name)
            email_data.append(obj_dict)
        
        # Use PostgreSQL's ON CONFLICT DO NOTHING to skip duplicates
        stmt = insert(EmailMessageORM).values(email_data)
        stmt = stmt.on_conflict_do_nothing(index_elements=['id'])
        
        result = db.execute(stmt)
        db.commit()
        
        inserted_count = result.rowcount
        skipped_count = len(payload.emails) - inserted_count

        logger.info(f"Inserted {inserted_count} emails, skipped {skipped_count} duplicates.")
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Inserted {inserted_count} emails successfully, skipped {skipped_count} duplicates",
                "status": "completed",
                "inserted": inserted_count,
                "skipped": skipped_count,
                "total": len(payload.emails)
            }
        )
    except Exception as e:
        logger.exception(f"Error inserting bulk emails: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to insert bulk emails", "error": str(e)}
        )