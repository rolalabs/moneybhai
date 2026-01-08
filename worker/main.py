# worker/main.py
from fastapi import Depends, FastAPI, Request, HTTPException
import json
import logging
import base64

from sqlalchemy.orm import Session
from worker.connectors import get_db
from worker.operations import AIManager, EmailManager
from worker.gmailAuth import authenticateGmail
from worker.models import EmailMessage, TaskModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

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
    try:
        logger.info("Received task processing request")
        payload = await request.body()
        payload = base64.b64decode(payload).decode("utf-8")
        payload = json.loads(payload)  # Parse the JSON string to dictionary
        logger.info(f"Received task payload: {payload}")

        # Authenticate Gmail
        gmailService = authenticateGmail(payload.get("token"))

        # Fetch emails and process it
        emailManager = EmailManager(gmailService, payload.get("email"), payload.get("userId"))

        next_page_token = None
        messages, next_page_token = emailManager.fetch_emails_messages_list("is:unread", next_page_token)
        logger.info(f"Fetched {len(messages)} unread emails for userId: {payload.get('userId')}")

        processed_messages: list[EmailMessage] = emailManager.fetch_messages_details_list(messages)
        logger.info(f"Fetched {len(processed_messages)} unread emails for userId: {payload.get('userId')}")
        
        # send emails to mb-backend for inserting into db
        statusCode: int = emailManager.sync_database(processed_messages)
        logger.info(f"Database sync status code: {statusCode}")

        # Process LLM through Gemini and update the database
        aiManager: AIManager = AIManager(email=payload.get("email"), user_id=payload.get("userId"))
        transactions_list: list[dict] = aiManager.process_emails(processed_messages)
        logger.info(f"Processed and extracted {len(transactions_list)} transactions from emails for email: {payload.get('emailId')}")

        # Send processed transactions to mb-backend for inserting into db
        if len(transactions_list) == 0:
            logger.info("No transactions extracted from emails, skipping database sync")
            return {"status": "done"}
        status = aiManager.syncDatabase(transactions_list)
        logger.info(f"AI Manager database sync status: {status}")

        return {"status": "done"}
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.exception(e)
        logger.error(f"Invalid JSON or base64 payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload format")
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error processing job: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Add health check api
@app.get("/health")
async def health_check():
    return {"status": "worker is healthy"}