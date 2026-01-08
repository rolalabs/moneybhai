from datetime import datetime
import re
import psycopg2
from dateutil import parser
from sqlalchemy.orm import Session
from googleapiclient.discovery import Resource
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from worker.models import EmailMessageORM
from worker.log import setup_logger

logger = setup_logger(__name__)

class EmailManager:
    '''
    This class is supposed to do the following actions:
    1. Fetch emails from Gmail API
    2. Process emails through llm
    3. Store processed emails in the database
    '''
    def __init__(self, gmail_service: Resource, db_session: Session):
        self.gmail_service: Resource = gmail_service
        self.db_session: Session = db_session
        self.email_messages = []

    def fetch_message_details(self, msg_data, msg_id) -> dict:
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


    def fetch_emails_messages_list(self, query, next_page_token=None, max_results=10) -> tuple:
        results = self.gmail_service.users().messages().list(
            userId='me', 
            maxResults=max_results, 
            q=query,
            pageToken=next_page_token,
        ).execute()
        messages = results.get('messages', [])
        message_list = []
        for msg in messages:
            msg_data = self.gmail_service.users().messages().get(userId='me', id=msg['id']).execute()
            message_list.append(msg_data)
        return message_list, results.get('nextPageToken')

    def process_emails(self, email_messages: list[dict]) -> list[dict]:
        messages_to_insert = []
        for msg in email_messages:
            result = self.fetch_message_details(msg, msg['id'])
            if result:
                messages_to_insert.append(result)
        
        return messages_to_insert

    def sync_database(self, processed_emails: list[dict]):
        try:

            insert_statement = insert(EmailMessageORM).values(processed_emails)
            on_conflict_statement = insert_statement.on_conflict_do_nothing(
                index_elements=[EmailMessageORM.id] # Or other unique columns
            )
            self.db_session.execute(on_conflict_statement)
            self.db_session.commit()
        except IntegrityError as e:
            self.db_session.rollback()
            if isinstance(e.orig, psycopg2.errors.UniqueViolation):
                logger.error("❌ Duplicate entry for a unique field!")
                # You can raise custom error or skip
            else:
                raise  # re-raise if it's another type of IntegrityError
        except Exception as e:
            # self.db_session.rollback()
            logger.error(f"Error syncing database: {str(e)}")
            raise
    
    def fetch_latest_message_from_db(self) -> EmailMessageORM:
        message = self.db_session.query(EmailMessageORM).order_by(EmailMessageORM.date_time.desc()).first()
        return message
    

    def execute(self, query: str):
        next_page_token = None
        messages, next_page_token = self.fetch_emails_messages_list(query, next_page_token)
        processed_messages = self.process_emails(messages)
        # self.sync_database(processed_messages)
        return processed_messages
