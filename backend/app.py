from logging import log
import time
from datetime import datetime

from backend.mail.auth import authenticate_gmail
from backend.mail.fetch import fetch_emails

def run_email_watcher(poll_every_sec=60):
    log("Starting Gmail polling service...")

    last_checked = datetime.utcnow()
    gmail_service = authenticate_gmail()

    while True:
        try:
            emails = get_new_emails(since=last_checked)
            message_list = fetch_emails(gmail_service, max_results=100)
            log(f"Found {len(message_list)} new emails")
            if message_list:
                structured = extract_transactions(message_list)
                insert_transactions(structured)
                last_checked = datetime.utcnow()
        except Exception as e:
            log(f"Error in watcher loop: {e}")

        time.sleep(poll_every_sec)
