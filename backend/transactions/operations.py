import re
import json
from dateutil import parser
from backend.mail.model import EmailMessage
from backend.mail.operations import mark_email_as_gemini_parsed, mark_email_as_transaction
from backend.transactions.models import Transaction, TransactionORM
from backend.utils.connectors import DB_SESSION, GEN_AI_CLIENT
from backend.utils.log import log

def get_last_transaction():
    last_record = DB_SESSION.query(TransactionORM).order_by(TransactionORM.id.desc()).first()
    DB_SESSION.close()
    return last_record

def generate_transactions_list_from_emails(message_to_parse_list: list[str]) -> list:
    BASE_PROMPT = """You are an expert data extraction assistant specialized in financial transaction alert messages from banks, credit cards, or UPI platforms.

    **Your Goal:** Extract the specified data fields from the provided message(s) and return **ONLY** a valid JSON list. Each item in the list must be a JSON object representing one transaction.

    **Strict Output Requirements:**
    * **Absolutely no conversational text, explanations, or markdown formatting (e.g., ```json) outside the JSON list itself.**
    * The response must begin with `[` and end with `]`.

    **Extracted Fields and Constraints:**
    * `id` (string): Unique identifier for the message. This maps to the "ID" in the message.
    * `amount` (number): Numeric value of the transaction. Do not include currency symbols.
    * `transaction_type` (string): **Strictly** one of: "debit" or "credit".
    * `source_identifier` (string): Account number, card number, or UPI ID from which money was deducted or into which money was received.
    * `destination` (string): Name, UPI ID, merchant, or platform that is the recipient or sender.
    * `reference_number` (string): UPI or bank transaction reference number. Can be an empty string if not found.
    * `mode` (string): **Strictly** one of: "UPI", "Credit Card", "Bank Transfer", "ATM", "POS", or "Unknown".
    * `reason` (string): Description or reason for the transaction. Can be an empty string if not found.
    * `date` (string): The transaction date in 'YYYY-MM-DD' format. If the year is not explicitly mentioned, assume the current year (2025). If the date is not found, return `null`.

    Rules:
    1. Exclude any emails that is for OTPs, promotional offers, or non-transactional alerts.

    **Example Message and Expected Output:**

    Message: "Dear Customer, Rs.65.00 has been debited from account 1531 to VPA Q285361434@ybl MADHU SUDHAN S on 04-07-25. Your UPI transaction reference number is 254342617978. Thread-ID: 1234567890abcdef"

    Expected Output:
    ```json
    [
    {
        "id": "1234567890abcdef",
        "amount": 65.00,
        "transaction_type": "debit",
        "source_identifier": "1531",
        "destination": "Q285361434@ybl MADHU SUDHAN S",
        "reference_number": "254342617978",
        "mode": "UPI",
        "reason": "Payment to VPA Q285361434@ybl MADHU SUDHAN S",
        "date": "2025-07-04"
    }
    ]"""
    final_prompt = BASE_PROMPT + "\n\n" + "\n\n".join(message_to_parse_list)
    response = GEN_AI_CLIENT.models.generate_content(
        model='gemini-2.5-pro', contents=final_prompt
    )
    return response.text

def extract_json_from_response(response: str) -> dict | None:
    """Extract JSON content from LLM response, handling code blocks."""
    try:
        cleaned = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", response)
        return json.loads(cleaned)
    except Exception as e:
        # logger.error("Failed to extract JSON from LLM response: %s", e)
        print(f"Failed to extract JSON from LLM response: {e}")
        return None
def process_emails(emails_list: list[EmailMessage]):

    message_dict_list = {msg.id: msg for msg in emails_list}
    message_to_parse_list = []

    # Prepare messages for parsing
    for msg in emails_list:
        id = msg.id
        snippet = msg.snippet

        if not snippet:
            continue

        snippet = f"ID {id}:\n{snippet}"
        message_to_parse_list.append(snippet)
        # mark_email_as_gemini_parsed(msg.thread_id)

    model_response = generate_transactions_list_from_emails(message_to_parse_list) 
    transactions_json = extract_json_from_response(model_response)

    if not transactions_json:
        print("No valid transactions found.")
        return

    count = 0
    for transaction in transactions_json:
        t: Transaction = Transaction(**transaction)
        email_details: EmailMessage = message_dict_list.get(t.id, None)
        txn = TransactionORM(
            id=t.id, 
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
            mark_email_as_transaction(email_details.id)
            mark_email_as_gemini_parsed(msg.id)
    
    log.info(f"Processed {count} transactions from {len(emails_list)} emails.")
    DB_SESSION.close()