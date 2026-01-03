from fastapi import APIRouter
import time
from datetime import datetime
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from src.utils.log import setup_logger
from src.utils.common import enqueue_worker_task

router = APIRouter()
logger = setup_logger(__name__)


import os.path
import base64
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def fetch_and_process_emails():
    while True:
        start_time = time.time()
        logger.info("Fetching and processing emails...")

        emails_list: list[EmailMessage] = fetch_emails_from_database()

        if not emails_list:
            logger.info("No new emails found.")
            break
        process_emails(emails_list)

        logger.info(f"Processed {len(emails_list)} emails in {time.time() - start_time:.2f} seconds.")

@router.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MoneyBhai Email Processor API", "status": "running"}

@router.post("/process-emails")
async def fetch_and_process_emails_route(background_tasks: BackgroundTasks):
    """Route to fetch and process emails"""
    try:
        background_tasks.add_task(fetch_and_process_emails)
        logger.info("Email fetch and process task started in background")
        return JSONResponse(
            status_code=200,
            content={"message": "Email fetch and process task started successfully", "status": "started"}
        )
    except Exception as e:
        logger.exception(f"Error starting email fetch and process task: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to start email fetch and process task", "error": str(e)}
        )

@router.post("/fetch-emails")
async def run_email_watcher_route(background_tasks: BackgroundTasks, poll_every_sec: int = 5):
    """Route to start the email watcher service"""
    try:
        background_tasks.add_task(run_email_watcher, poll_every_sec)
        logger.info(f"Email watcher started in background with polling interval: {poll_every_sec}s")
        return JSONResponse(
            status_code=200,
            content={"message": "Email watcher started successfully", "status": "started", "poll_interval": poll_every_sec}
        )
    except Exception as e:
        logger.exception(f"Error starting email watcher: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to start email watcher", "error": str(e)}
        )
    
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
@router.post("/synchronize")
async def scrape_emails_route(background_tasks: BackgroundTasks):
    """Route to scrape emails immediately"""
    try:     
        # background_tasks.add_task(run_email_watcher)
        # creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # gmail_service = build('gmail', 'v1', credentials=creds)

        enqueue_worker_task({
            "user_id": "user_id",
            "expense_id": "expense_id"
        })


        return JSONResponse(
            status_code=200,
            content={"message": "Email scraping completed successfully", "status": "completed"}
        )
    except Exception as e:
        logger.exception(f"Error during email scraping: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to scrape emails", "error": str(e)}
        )