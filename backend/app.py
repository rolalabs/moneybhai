import time
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse

from backend.mail.auth import authenticate_gmail
from backend.mail.fetch import fetch_emails, fetch_emails_from_database
from backend.transactions.operations import process_emails
from backend.mail.model import EmailMessage
from backend.mail.operations import populate_email_ids
from backend.utils.log import log

app = FastAPI(title="MoneyBhai Email Processor", version="1.0.0")

def run_email_watcher(poll_every_sec=5):
    log.info("Starting Gmail polling service...")

    last_checked = datetime.utcnow()
    gmail_service = authenticate_gmail()

    try:
        fetch_emails(gmail_service)
    except Exception as e:
        log.exception(f"Error in watcher loop: {e}")


# run_email_watcher()


# populate_email_ids()

def fetch_and_process_emails():
    while True:
        start_time = time.time()
        log.info("Fetching and processing emails...")

        emails_list: list[EmailMessage] = fetch_emails_from_database()

        if not emails_list:
            log.info("No new emails found.")
            break
        process_emails(emails_list)

        log.info(f"Processed {len(emails_list)} emails in {time.time() - start_time:.2f} seconds.")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MoneyBhai Email Processor API", "status": "running"}

@app.post("/process-emails")
async def fetch_and_process_emails_route(background_tasks: BackgroundTasks):
    """Route to fetch and process emails"""
    try:
        background_tasks.add_task(fetch_and_process_emails)
        log.info("Email fetch and process task started in background")
        return JSONResponse(
            status_code=200,
            content={"message": "Email fetch and process task started successfully", "status": "started"}
        )
    except Exception as e:
        log.exception(f"Error starting email fetch and process task: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to start email fetch and process task", "error": str(e)}
        )

@app.post("/fetch-emails")
async def run_email_watcher_route(background_tasks: BackgroundTasks, poll_every_sec: int = 5):
    """Route to start the email watcher service"""
    try:
        background_tasks.add_task(run_email_watcher, poll_every_sec)
        log.info(f"Email watcher started in background with polling interval: {poll_every_sec}s")
        return JSONResponse(
            status_code=200,
            content={"message": "Email watcher started successfully", "status": "started", "poll_interval": poll_every_sec}
        )
    except Exception as e:
        log.exception(f"Error starting email watcher: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to start email watcher", "error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# fetch_and_process_emails()