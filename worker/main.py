# worker/main.py
from fastapi import Depends, FastAPI, Request, HTTPException
import json
import logging
import base64

from sqlalchemy.orm import Session
from worker.connectors import get_db
from worker.email import EmailManager
from worker.gmailAuth import authenticateGmail
from worker.models import TaskModel

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
        logger.info(request)
        payload = await request.body()
        logger.info(f"Raw payload: {payload}")
        payload = base64.b64decode(payload).decode("utf-8")
        logger.info(f"Received task payload: {payload}")
        gmailService = authenticateGmail(payload["token"])

        # simulate long work (using async sleep instead of blocking sleep)
        emailManager = EmailManager(gmailService, db)
        messages = emailManager.execute("is:unread")
        for message in messages:
            logger.info(f"Processing message ID: {message['id']}")
        return {"status": "done"}
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid JSON or base64 payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload format")
    except Exception as e:
        logger.error(f"Error processing job: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Add health check api
@app.get("/health")
async def health_check():
    return {"status": "worker is healthy"}