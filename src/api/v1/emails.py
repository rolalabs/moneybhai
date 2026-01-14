from fastapi import APIRouter
import time
from datetime import datetime
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert
from fastapi import Depends
from src.modules.users.operations import fetchUserById
from src.modules.emails.model import EmailBulkInsertPayload, EmailBulkInsertResponse, EmailMessage, EmailMessageORM
from src.core.database import get_db
from src.utils.log import setup_logger
from src.utils.common import enqueue_worker_task

router = APIRouter()
logger = setup_logger(__name__)

# def fetch_and_process_emails():
#     while True:
#         start_time = time.time()
#         logger.info("Fetching and processing emails...")

#         emails_list: list[EmailMessage] = fetch_emails_from_database()

#         if not emails_list:
#             logger.info("No new emails found.")
#             break
#         process_emails(emails_list)

#         logger.info(f"Processed {len(emails_list)} emails in {time.time() - start_time:.2f} seconds.")

@router.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MoneyBhai Email Processor API", "status": "running"}

# @router.post("/process-emails")
# async def fetch_and_process_emails_route(background_tasks: BackgroundTasks):
#     """Route to fetch and process emails"""
#     try:
#         background_tasks.add_task(fetch_and_process_emails)
#         logger.info("Email fetch and process task started in background")
#         return JSONResponse(
#             status_code=200,
#             content={"message": "Email fetch and process task started successfully", "status": "started"}
#         )
#     except Exception as e:
#         logger.exception(f"Error starting email fetch and process task: {e}")
#         return JSONResponse(
#             status_code=500,
#             content={"message": "Failed to start email fetch and process task", "error": str(e)}
#         )

# @router.post("/fetch-emails")
# async def run_email_watcher_route(background_tasks: BackgroundTasks, poll_every_sec: int = 5):
#     """Route to start the email watcher service"""
#     try:
#         background_tasks.add_task(run_email_watcher, poll_every_sec)
#         logger.info(f"Email watcher started in background with polling interval: {poll_every_sec}s")
#         return JSONResponse(
#             status_code=200,
#             content={"message": "Email watcher started successfully", "status": "started", "poll_interval": poll_every_sec}
#         )
#     except Exception as e:
#         logger.exception(f"Error starting email watcher: {e}")
#         return JSONResponse(
#             status_code=500,
#             content={"message": "Failed to start email watcher", "error": str(e)}
#         )


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

        logger.info(f"Inserting {len(payload.emails)} emails into the database for email: {payload.emailId}")

        # Create ORM objects for type safety
        email_orm_list = []
        for email in payload.emails:
            email_orm = EmailMessageORM(
                thread_id=email.thread_id,
                id=email.id,
                snippet=email.snippet,
                date_time=email.date_time,
                emailSender=email.emailSender,
                emailId=email.emailId,
                source=email.source,
                isTransaction=email.isTransaction,
                isGeminiParsed=email.isGeminiParsed
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