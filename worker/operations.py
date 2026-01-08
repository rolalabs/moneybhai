from datetime import datetime
import re
import json
from dateutil import parser
import requests
from sqlalchemy.orm import Session
from googleapiclient.discovery import Resource
from packages.models import Transaction
from worker.connectors import ENV_SETTINGS, GEN_AI_CLIENT
from worker.log import setup_logger
from worker.models import EmailMessage

logger = setup_logger(__name__)

class EmailManager:
    '''
    This class is supposed to do the following actions:
    1. Fetch emails from Gmail API
    2. Process emails through llm
    3. Store processed emails in the database
    '''
    def __init__(self, gmail_service: Resource, email: str, user_id: str):
        self.gmail_service: Resource = gmail_service
        self.email = email
        self.user_id = user_id

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
                'date_time': date_time.isoformat() if date_time else None,
                'emailSender': emailSender,
                'emailId': emailId
            }
            return mail_data
        except Exception as e:
            print(f"Error fetching message {msg_id}: {e}")
            return None


    def fetch_emails_messages_list(self, query, next_page_token=None, max_results=1) -> tuple:
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

    def fetch_messages_details_list(self, email_messages: list[dict]) -> list[EmailMessage]:
        messages_to_insert = []
        for msg in email_messages:
            result = self.fetch_message_details(msg, msg['id'])
            if result:
                email: EmailMessage = EmailMessage(**result)
                messages_to_insert.append(email)
        
        return messages_to_insert

    def sync_database(self, processed_messages: list[EmailMessage]):
        '''
        Send the list of emails to mb-backend api to insert into db
        Send in batch of 50
        '''
        batch = [email.model_dump_json() for email in processed_messages]
        response = requests.post(
            ENV_SETTINGS.MB_BACKEND_API_URL + 'v1/emails/insert-bulk',
            headers={'Content-Type': 'application/json'},
            json={
                'emails': batch,
                'userId': self.user_id,
                'emailId': self.email,
            }
        )
        if response.status_code != 200:
            logger.error(f"Failed to insert batch starting at index : {response.text}")
        else:
            logger.info("Successfully inserted batch starting at index")
        
        return response.status_code


class AIManager:
    '''
    This class is supposed to do the following actions:
    1. Process emails through llm
    '''
    def __init__(self, email: str, user_id: str):
        self.email = email
        self.user_id = user_id

    def generate_transactions_list_from_emails(self, message_to_parse_list: list[str]) -> list:
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
        
        # Add retry logic for timeout errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = GEN_AI_CLIENT.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=final_prompt,
                    # config={
                    #     'temperature': 0.1,
                    #     'max_output_tokens': 8192,
                    # }
                )
                return response.text
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All retry attempts failed for generate_content: {str(e)}")
                    raise

    def extract_json_from_response(self, response: str) -> dict | None:
        """Extract JSON content from LLM response, handling code blocks."""
        try:
            cleaned = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", response)
            return json.loads(cleaned)
        except Exception as e:
            # logger.error("Failed to extract JSON from LLM response: %s", e)
            print(f"Failed to extract JSON from LLM response: {e}")
            return None
    
    def mark_email_as_gemini_parsed(self, email_id: str):
        pass

    def process_emails(self, emails_list: list[EmailMessage]) -> list[dict]:

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

        model_response = self.generate_transactions_list_from_emails(message_to_parse_list) 
        transactions_json_list = self.extract_json_from_response(model_response)

        if not transactions_json_list:
            print("No valid transactions found.")
            for msg in emails_list:
                self.mark_email_as_gemini_parsed(msg.id)
            return

        transactions_list = []
        for transaction in transactions_json_list:
            try:
                txn: Transaction = Transaction(**transaction)
                email_details: EmailMessage = message_dict_list.get(txn.id, None)

                if email_details is None:
                    raise Exception(f"Email details not found for transaction ID: {txn.id}")

                txn.emailId = email_details.emailId if email_details else None
                txn.emailSender = email_details.emailSender if email_details else None
                txn.date_time = email_details.date_time if email_details else None

                transactions_list.append(txn.model_dump_json())
            except Exception as e:
                logger.exception(e)
            finally:
                # Mark the email as a transaction
                self.mark_email_as_gemini_parsed(transaction.get('id'))
        
        return transactions_list

    def syncDatabase(self, transactions_list: list[dict]):
        '''
        Send the list of transactions to mb-backend api to insert into db
        Send in batch of 50
        '''
        response = requests.post(
            ENV_SETTINGS.MB_BACKEND_API_URL + 'v1/transactions/bulk-insert',
            headers={'Content-Type': 'application/json'},
            json={
                'emails': transactions_list,
                'userId': self.user_id,
                'emailId': self.email,
            }
        )
        if response.status_code != 200:
            logger.error(f"Failed to insert batch starting at index : {response.text}")
        else:
            logger.info("Successfully inserted batch starting at index")
        
        return response.status_code


        