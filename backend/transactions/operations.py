import re
from dateutil import parser
from backend.transactions.models import TransactionORM
from backend.utils.connectors import DB_SESSION

def get_last_transaction():
    last_record = DB_SESSION.query(TransactionORM).order_by(TransactionORM.id.desc()).first()
    DB_SESSION.close()
    return last_record

def insert_emails(transaction_list: list):


    for t in transaction_list:
        
        txn = TransactionORM(
            id=t.thread_id, 
            amount=t.amount,
            transaction_type=t.transaction_type,
            source_identifier=t.source_identifier,
            source_type=t.source_type,
            destination=t.destination,
            mode=t.mode,
            reference_number=t.reference_number
        )

        mail_data = message_dict_list.get(t.thread_id, {})

        for header in mail_data.get('payload', {}).get('headers', []):
            if header.get('name') == 'From':
                from_header = header.get('value', '')
                match = re.match(r'^(.*?)(?:\s*<([^>]+)>)?$', from_header)
                if match:
                    txn.emailSender = match.group(1).strip()
                    txn.emailId = match.group(2) if match.group(2) else None

            if header.get('name') == 'Date':
                txn.date_time = parser.parse(header.get('value', ''))

        session.add(txn)

    session.commit()
    session.close()

def process_emails(message_list: list):

    message_dict_list = {msg['id']: msg for msg in message_list}
    message_to_parse_list = []

    for msg in message_list[10:20]:
        id = msg.get('id', '')
        snippet = msg.get('snippet', '')
        headers = msg.get('payload', {}).get('headers', [])
        additional_data = ""
        if snippet:
            # snippet = f"{from_details}\n{date_details}\n{snippet}"
            snippet = f"Thread-ID {id}:\n{snippet}"
            message_to_parse_list.append(snippet)

    import json

    model_response = model(str(message_to_parse_list), list[Transaction])
    transactions_json = json.loads(model_response)

    transaction_list: list[Transaction] = []
    for transaction in transactions_json:
        transaction_list.append(Transaction(**transaction))
    transaction_list