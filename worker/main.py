# worker/main.py
from fastapi import FastAPI, Request, HTTPException
import json
import asyncio
import logging
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/tasks/process")
async def process_task(request: Request):
    try:
        # Get the raw body (which is base64 encoded)
        body = await request.body()
        
        # Decode the base64 payload
        decoded_body = base64.b64decode(body).decode("utf-8")
        
        # Parse the JSON
        payload = json.loads(decoded_body)
        
        # Validate payload
        job_id = payload.get("job_id")
        if not job_id:
            raise HTTPException(status_code=400, detail="Missing job_id in payload")

        logger.info(f"Processing job {job_id}")

        # simulate long work (using async sleep instead of blocking sleep)
        await asyncio.sleep(5)

        # TODO: update DB here
        # Example: await update_job_status(job_id, "completed")

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
    return {"status": "ok"}