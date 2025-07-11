import re
import json
from dateutil import parser
from backend.mail.model import EmailMessage
from backend.transactions.models import Transaction, TransactionORM
from backend.utils.connectors import DB_SESSION, MODEL

def get_last_transaction():
    last_record = DB_SESSION.query(TransactionORM).order_by(TransactionORM.id.desc()).first()
    DB_SESSION.close()
    return last_record

def insert_emails(transaction_list: list[Transaction], message_dict_list: dict):


    for t in transaction_list:
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
        DB_SESSION.add(txn)

    DB_SESSION.commit()
    DB_SESSION.close()

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

    model_response = MODEL(str(message_to_parse_list), list[Transaction])
    transactions_json = json.loads(model_response)

    transaction_list: list[Transaction] = []
    for transaction in transactions_json:
        transaction_list.append(Transaction(**transaction))
    
    insert_emails(transaction_list, message_dict_list)