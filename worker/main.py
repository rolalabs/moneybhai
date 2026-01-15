# worker/main.py
from fastapi import Depends, FastAPI, Request, HTTPException
import json
import logging
import base64
import requests

from sqlalchemy.orm import Session
from packages.models import TaskQueuePayload
from worker.connectors import get_db, ENV_SETTINGS
from worker.operations import AIManager, EmailManager
from worker.gmailAuth import authenticateGmail
from worker.models import EmailMessage, TaskModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def release_sync_lock(user_id: str) -> None:
    """Release sync lock for a user after task completion or error."""
    try:
        unlock_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/users/{user_id}/unlock"
        unlock_response = requests.post(unlock_url)
        logger.info(f"Sync lock released for user {user_id}, status: {unlock_response.status_code}")
    except Exception as unlock_error:
        logger.error(f"Failed to release sync lock for user {user_id}: {unlock_error}")

def fetch_user_details(user_id: str) -> dict:
    """Fetch user details from backend API."""
    try:
        user_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/users/{user_id}"
        response = requests.get(user_url)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to fetch user details, status: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching user details for user {user_id}: {e}")
        return None

def update_last_synced_at(user_id: str, last_synced_at: str) -> None:
    """Update lastSyncedAt for a user."""
    try:
        update_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/users/{user_id}"
        response = requests.put(
            update_url,
            headers={'Content-Type': 'application/json'},
            json={'lastSyncedAt': last_synced_at}
        )
        logger.info(f"Updated lastSyncedAt for user {user_id}, status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to update lastSyncedAt for user {user_id}: {e}")

@app.post("/tasks/process")
async def processTask(request: Request, db: Session = Depends(get_db)):
    '''
    1. take the user id given in input
    2. fetch the user details via user id
    3. use the stored token to authenticate gmail
    4. fetch unread emails
    5. process emails
    6. store results in db
    7. return status    
    '''
    user_id = None
    try:
        logger.info("Received task processing request")
        payload = await request.body()
        payload = base64.b64decode(payload).decode("utf-8")
        payload = json.loads(payload)  # Parse the JSON string to dictionary
        logger.info(f"Received task payload: {payload}")
        user_id = payload.get("userId")

        tasksPayload: TaskQueuePayload = TaskQueuePayload(**payload)  # Validate payload structure

        # Fetch user details to get lastSyncedAt
        user_details = fetch_user_details(tasksPayload.userId)
        if not user_details:
            raise Exception("Failed to fetch user details")
        
        last_synced_at = user_details.get('lastSyncedAt')
        logger.info(f"User lastSyncedAt: {last_synced_at}")

        # Authenticate Gmail
        gmailService = authenticateGmail(tasksPayload.token)

        # Fetch emails and process it
        emailManager = EmailManager(gmailService, tasksPayload.email, tasksPayload.userId)

        # Build query based on lastSyncedAt
        query = emailManager.build_gmail_query(last_synced_at)
        logger.info(f"Gmail query: {query}")
        
        next_page_token = None
        messages, next_page_token = emailManager.fetch_emails_messages_list(query, next_page_token, max_results=100)
        logger.info(f"Fetched {len(messages)} emails for userId: {tasksPayload.userId}")
        processed_messages: list[EmailMessage] = emailManager.fetch_messages_details_list(messages)
        logger.info(f"Processed {len(processed_messages)} emails for userId: {tasksPayload.userId}")
        
        # send emails to mb-backend for inserting into db
        statusCode: int = emailManager.sync_database(processed_messages)
        logger.info(f"Database sync status code: {statusCode}")

        # Process LLM through Gemini and update the database
        aiManager: AIManager = AIManager(email=tasksPayload.email, user_id=tasksPayload.userId)
        transactions_list: list[dict] = aiManager.process_emails(processed_messages)

        # Send processed transactions to mb-backend for inserting into db
        if transactions_list is None:
            logger.info("No transactions extracted from emails, skipping database sync")
            return {"status": "done"}
        
        logger.info(f"Processed and extracted {len(transactions_list)} transactions from emails for email: {tasksPayload.email}")
        status = aiManager.syncDatabase(transactions_list)
        logger.info(f"AI Manager database sync status: {status}")

        # Update lastSyncedAt to the latest email timestamp
        if processed_messages:
            latest_email_time = max(msg.date_time for msg in processed_messages if msg.date_time)
            if latest_email_time:
                update_last_synced_at(tasksPayload.userId, latest_email_time.isoformat())
                logger.info(f"Updated lastSyncedAt to {latest_email_time.isoformat()}")

        return {"status": "done"}
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.exception(e)
        logger.error(f"Invalid JSON or base64 payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload format")
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error processing job: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        # TODO: figure out way to unlock user if user id is not present
        if user_id:
            release_sync_lock(user_id)

# Add health check api
@app.get("/health")
async def health_check():
    return {"status": "worker is healthy"}