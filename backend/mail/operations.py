'''
This part of the code is responsible for ensuring the data is intact.
1. Populate all emailId fields
    1.1 Find all emails where emailId is empty
    1.2 Ensure emailSender is not empty
    1.3 Ensure emailSender has valid email format
    1.4 For each email, if emailId is empty, populate it with the emailSender
'''
import re
from backend.utils.connectors import DB_SESSION
from backend.mail.model import EmailMessageORM
from sqlalchemy import update
from backend.utils.log import log

def fetch_emails_with_empty_id():
    """
    Fetch all emails where emailId is empty.
    """
    return DB_SESSION.query(EmailMessageORM).filter(EmailMessageORM.emailId.is_(None)).all()

def is_valid_email(email):
    """
    Check if the email is in a valid format.
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def update_email_id(email: EmailMessageORM) -> bool:
    """
    Update the emailId field with the emailSender if emailId is empty.
    """
    email.emailId = email.emailSender
    return True

def populate_email_ids():
    """
    Populate emailId fields for all emails where it is empty.
    """
    emails = fetch_emails_with_empty_id()
    update_count = 0
    for email in emails:
        if email.emailSender and is_valid_email(email.emailSender):
            email.emailId = email.emailSender.lower()
            update_count += 1
            log.info(f"Updating emailId for emailSender: {email.emailSender} in email ID: {email.id}")

            # Update the email in the database
            stmt = update(EmailMessageORM).where(EmailMessageORM.id == email.id).values(emailId=email.emailId)
            DB_SESSION.execute(stmt)
            # Commit the changes to the database
            DB_SESSION.commit()
        else:
            log.error(f"Invalid email format for emailSender: {email.emailSender} in email ID: {email.id}")
    
def mark_email_as_transaction(thread_id: str):
    """
    Update the isTransaction field for emails based on their content.
    """
    email = DB_SESSION.query(EmailMessageORM).filter(EmailMessageORM.thread_id == thread_id).first()
    if email:
        email.isTransaction = True
        DB_SESSION.commit()
        log.info(f"Marked email as transaction for thread_id: {thread_id}")
    else:
        log.error(f"Email not found for thread_id: {thread_id}")

def mark_email_as_gemini_parsed(thread_id: str):
    """
    Update the isGeminiParsed field for emails based on their content.
    """
    email = DB_SESSION.query(EmailMessageORM).filter(EmailMessageORM.thread_id == thread_id).first()
    if email:
        email.isGeminiParsed = True
        DB_SESSION.commit()
        log.info(f"Marked email as gemini parsed for thread_id: {thread_id}")
    else:
        log.error(f"Email not found for thread_id: {thread_id}")