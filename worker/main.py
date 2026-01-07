# worker/main.py
from fastapi import Depends, FastAPI, Request, HTTPException
import json
import logging

from sqlalchemy.orm import Session
from worker.connectors import get_db
from worker.email import EmailManager
from worker.gmailAuth import authenticateGmail

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/tasks/process")
async def processTask(request: Request, db: Session = Depends(get_db)):
    try:
        # Get the raw body (which is base64 encoded)
        body = await request.json()
        
        # Decode the base64 payload
        # decodedBody = base64.b64decode(body).decode("utf-8")
        
        # Parse the JSON
        payload = json.loads(body)
        
        # Validate payload
        job_id = payload.get("job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="Missing job_id in payload")

        logger.info(f"Processing job {job_id}")

        gmailService = authenticateGmail(payload.get("token"))

        # simulate long work (using async sleep instead of blocking sleep)
        emailManager = EmailManager(gmailService, db)
        messages = emailManager.execute("is:unread")

        logger.info(f"Completed job {job_id}")
        return {"status": "done", "job_id": job_id}
    
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