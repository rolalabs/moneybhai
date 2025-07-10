import base64
from datetime import datetime, timedelta
import psycopg2
from sqlalchemy.exc import IntegrityError
from backend.utils.log import log
from dateutil import parser
import re
from googleapiclient.discovery import Resource
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.mail.model import EmailMessage, EmailMessageORM
from backend.utils.connectors import DB_SESSION

def extract_email_body(payload):
    # Recursive function to handle multipart emails
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif part['mimeType'] == 'text/html':
                data = part['body'].get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            else:
                # recursively check sub-parts
                return extract_email_body(part)
    else:
        data = payload['body'].get('data')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return "(No body found)"


def fetch_email_threads_list(service: Resource, next_page_token=None, max_results=100):
    """
    Fetches a list of email threads from the Gmail API.
    
    Args:
        next_page_token (str): Token for pagination.
        max_results (int): Maximum number of results to return.
    
    Returns:
        list: List of email threads.
    """
    response = service.users().threads().list(
        userId='me',
        pageToken=next_page_token,
        maxResults=max_results
    ).execute()

    threads = response.get('threads', [])
    next_page_token = response.get('nextPageToken')

    return threads, next_page_token

def fetch_message_details(service, msg_id):
    try:
        msg_data = service.users().messages().get(userId='me', id=msg_id).execute()
        emailSender: str = ''
        emailId: str = ''
        date_time: datetime = None

        for header in msg_data.get('payload', {}).get('headers', []):
            if header.get('name') == 'From':
                from_header = header.get('value', '')
                match = re.match(r'^(.*?)(?:\s*<([^>]+)>)?$', from_header)
                if match:
                    emailSender = match.group(1).strip()
                    emailId = match.group(2) if match.group(2) else None

            if header.get('name') == 'Date':
                date_time = parser.parse(header.get('value', ''))


        mail_data = EmailMessageORM(
            thread_id=msg_data.get('threadId', ''),
            id=msg_data.get('id', ''),
            snippet=msg_data.get('snippet', ''),
            date_time=date_time,
            emailSender=emailSender,
            emailId=emailId
        )
        return mail_data
    except Exception as e:
        print(f"Error fetching message {msg_id}: {e}")
        return None

def process_mails_and_insert_to_db(service: Resource, message_list = []):
    """
    Processes a list of email messages and inserts them into the database.
    
    Args:
        message_list (list): List of email messages to process.
    """
    messages_to_insert = []

    with ThreadPoolExecutor() as executor:
            
            # Prepare futures for fetching message details
            futures = [
                executor.submit(fetch_message_details, service, msg['id'])
                for msg in message_list
            ]

            # Collect results as they complete
            log.info("Processing emails in parallel...")
            log.info(f"Total emails to process: {len(futures)}")
            for future in as_completed(futures):
                result = future.result()
                if result:
                    messages_to_insert.append(result)

            # Insert messages into the database
            log.info(f"Inserting {len(messages_to_insert)} emails into the database...")
            try:
                DB_SESSION.add_all(messages_to_insert)
                DB_SESSION.commit()
            except IntegrityError as e:
                DB_SESSION.rollback()
                if isinstance(e.orig, psycopg2.errors.UniqueViolation):
                    log.error("❌ Duplicate entry for a unique field!")
                    # You can raise custom error or skip
                else:
                    raise  # re-raise if it's another type of IntegrityError

def fetch_emails(service: Resource):
    messages = []
    after_date = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    query = f"after:{after_date}"
    next_page_token = None

    while True:
        start_time = datetime.now()
        threads, next_page_token = fetch_email_threads_list(service, next_page_token, 100)
        log.info(f"✅ Found {len(threads)} emails \n")

        process_mails_and_insert_to_db(service, threads)


        log.info("Processing time: %s seconds", (datetime.now() - start_time).total_seconds())

        if not next_page_token:
            break


    log.info(f"✅ Processed {len(messages)} emails in total.")
    

