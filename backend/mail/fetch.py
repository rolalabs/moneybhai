import base64
from datetime import datetime, timedelta
import time
import psycopg2
from sqlalchemy.exc import IntegrityError
from backend.utils.log import log
from dateutil import parser
import re
from googleapiclient.discovery import Resource
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.mail.model import EmailMessage, EmailMessageORM
from backend.utils.connectors import DB_SESSION
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime



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

def fetch_emails_messages_list(service: Resource, query, next_page_token=None, max_results=100) -> tuple:
    results = service.users().messages().list(
        userId='me', 
        maxResults=max_results, 
        q=query,
        pageToken=next_page_token,
    ).execute()
    messages = results.get('messages', [])
    message_list = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        message_list.append(msg_data)
    return message_list, results.get('nextPageToken')

def fetch_email_threads_list(service: Resource, next_page_token=None, max_results=100, query=None) -> tuple:
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
        maxResults=max_results,
        q=query
    ).execute()

    threads = response.get('threads', [])
    next_page_token = response.get('nextPageToken')

    return threads, next_page_token

def fetch_message_details(msg_data, msg_id) -> dict:
    try:
        # msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        # if not msg_data:
        #     log.error(f"Message with ID {msg_id} not found.")
        #     return None
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

        mail_data = {
            'thread_id': msg_data.get('threadId', ''),
            'id': msg_data.get('id', ''),
            'snippet': msg_data.get('snippet', ''),
            'date_time': date_time,
            'emailSender': emailSender,
            'emailId': emailId
        }
        return mail_data
    except Exception as e:
        print(f"Error fetching message {msg_id}: {e}")
        return None

def process_mails_and_insert_to_db(message_list = []):
    """
    Processes a list of email messages and inserts them into the database.
    
    Args:
        message_list (list): List of email messages to process.
    """
    messages_to_insert = []
    for msg in message_list:
        result = fetch_message_details(msg, msg['id'])
        if result:
            messages_to_insert.append(result)

    try:

        insert_statement = insert(EmailMessageORM).values(messages_to_insert)

        # For PostgreSQL/SQLite, specify the unique constraint column(s)
        # Replace 'id' with your actual unique column or (col1, col2) for composite unique constraints
        on_conflict_statement = insert_statement.on_conflict_do_nothing(
            index_elements=[EmailMessageORM.id] # Or other unique columns
        )
        DB_SESSION.execute(on_conflict_statement)
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

    next_page_token = None

    # read the last processed email ID from the database
    last_processed_email = DB_SESSION.query(EmailMessageORM).order_by(EmailMessageORM.date_time.desc()).first()
    if last_processed_email:
        # get its time
        last_processed_time = last_processed_email.date_time - timedelta(days=3)
        last_processed_time = last_processed_time.strftime('%Y/%m/%d')
        # filter from that time onwards
        query = f"after:{last_processed_time}"

    while True:
        start_time = datetime.now()
        # threads, next_page_token = fetch_email_threads_list(service, next_page_token, 100, query=query)
        messages, next_page_token = fetch_emails_messages_list(
            service=service, 
            next_page_token=next_page_token, 
            max_results=100, 
            query=query
        )
        log.info(f"✅ Found {len(messages)} emails \n")

        if messages is None or len(messages) == 0:
            log.info("No more emails to process.")
            break
        process_mails_and_insert_to_db(messages)


        log.info("Processing time: %s seconds", (datetime.now() - start_time).total_seconds())
        log.info(next_page_token)

        if not next_page_token:
            break


    log.info(f"✅ Processed {len(messages)} emails in total.")

def fetch_emails_from_database() -> list[EmailMessage]:
    """
    Fetches all email messages from the database.
    
    Returns:
        list: List of EmailMessage objects.
    """
    emails_serialized_list = []
    # fetch 10 emails from the database where isGeminiParsed is False
    now = datetime.now()
    year = now.year
    threshold = datetime(year, 10, 31)

    emails_list = DB_SESSION.query(EmailMessageORM) \
        .filter(EmailMessageORM.isGeminiParsed.is_(False)) \
        .filter(EmailMessageORM.date_time > threshold) \
        .order_by(EmailMessageORM.date_time.desc()) \
        .limit(10) \
        .all()
    if not emails_list:
        log.info("No emails found in the database.")
        return []
    
    try:
        for email in emails_list:
            # Convert ORM object to Pydantic model
            emailId = email.emailId
            if emailId is None:
                emailId = email.emailSender
            email_serialized = EmailMessage(
                thread_id=email.thread_id,
                id=email.id,
                snippet=email.snippet,
                date_time=email.date_time,
                emailSender=email.emailSender,
                emailId=emailId
            )
            emails_serialized_list.append(email_serialized)
        return emails_serialized_list
    except Exception as e:
        log.error(f"Error fetching emails from database: {e}")
        return []
