import time
from datetime import datetime

from backend.mail.auth import authenticate_gmail
from backend.mail.fetch import fetch_emails, fetch_emails_from_database
from backend.transactions.operations import process_emails
from backend.mail.model import EmailMessage
from backend.mail.reconcile import populate_email_ids
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


# populate_email_ids()

def fetch_and_process_emails():
    log.info("Fetching and processing emails...")

    emails_list: list[EmailMessage] = fetch_emails_from_database()

    if not emails_list:
        log.info("No new emails found.")
        return
    emails_list = emails_list[:10]
    process_emails(emails_list)

    log.info(f"Processed {len(emails_list)} emails.")