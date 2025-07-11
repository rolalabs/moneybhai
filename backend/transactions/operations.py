import re
import json
from dateutil import parser
from backend.mail.model import EmailMessage
from backend.mail.operations import mark_email_as_gemini_parsed, mark_email_as_transaction
from backend.transactions.models import Transaction, TransactionORM
from backend.utils.connectors import DB_SESSION, MODEL
from backend.utils.log import log

def get_last_transaction():
    last_record = DB_SESSION.query(TransactionORM).order_by(TransactionORM.id.desc()).first()
    DB_SESSION.close()
    return last_record


def process_emails(emails_list: list[EmailMessage]):

    message_dict_list = {msg.id: msg for msg in emails_list}
    message_to_parse_list = []

    # Prepare messages for parsing
    for msg in emails_list:
        id = msg.id
        snippet = msg.snippet

        if not snippet:
            continue

        snippet = f"Thread-ID {id}:\n{snippet}"
        message_to_parse_list.append(snippet)
        mark_email_as_gemini_parsed(msg.thread_id)

    model_response = MODEL(str(message_to_parse_list), list[Transaction])
    transactions_json = json.loads(model_response)

    count = 0
    for transaction in transactions_json:
        t: Transaction = Transaction(**transaction)
        email_details: EmailMessage = message_dict_list.get(t.thread_id, None)
        txn = TransactionORM(
            id=t.thread_id, 
            amount=t.amount,
            transaction_type=t.transaction_type,
            source_identifier=t.source_identifier,
            source_type=t.source_type,
            destination=t.destination,
            mode=t.mode,
            reference_number=t.reference_number,
            emailSender=email_details.emailSender,
            emailId=email_details.emailId,
            date_time=email_details.date_time,
        )
        # wrap around try catch to handle failures
        try:
            DB_SESSION.add(txn)
            DB_SESSION.commit()
            count += 1
        except Exception as e:
            DB_SESSION.rollback()
            print(f"Error inserting transactions: {e}")
        finally:
            # Mark the email as a transaction
            mark_email_as_transaction(email_details.thread_id)
    
    log.info(f"Processed {count} transactions from {len(emails_list)} emails.")
    DB_SESSION.close()