import time
from datetime import datetime

from backend.mail.auth import authenticate_gmail
from backend.mail.fetch import fetch_emails
from backend.utils.log import log

def run_email_watcher(poll_every_sec=5):
    log.info("Starting Gmail polling service...")

    last_checked = datetime.utcnow()
    gmail_service = authenticate_gmail()

    try:
        fetch_emails(gmail_service)
    except Exception as e:
        log.exception(f"Error in watcher loop: {e}")


run_email_watcher()