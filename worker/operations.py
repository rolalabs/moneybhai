from datetime import datetime, timedelta, timezone
import re
import base64
from email.utils import parseaddr
from email.header import decode_header
import json
from langsmith import traceable
import requests
from langsmith.run_helpers import get_current_run_tree
from googleapiclient.discovery import Resource
from packages.models import EmailSanitized, OrdersListIntentModel, Transaction
from worker.connectors import ENV_SETTINGS, VERTEXT_CLIENT
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
    def __init__(self, gmail_service: Resource, email: str, userId: str, accountId: str):
        self.gmail_service: Resource = gmail_service
        self.email = email
        self.userId = userId
        self.accountId = accountId

    def build_gmail_query(self, last_synced_at: str = None) -> str:
        """Build Gmail search query based on lastSyncedAt."""
        
        if last_synced_at:
            # Convert ISO format to unix timestamp
            try:
                dt = datetime.fromisoformat(last_synced_at.replace('Z', '+00:00'))
                timestamp = int(dt.timestamp())
                return f"after:{timestamp}"
            except Exception as e:
                logger.error(f"Error parsing lastSyncedAt: {e}")
    
        # If no lastSyncedAt, use today - 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        timestamp = int(seven_days_ago.timestamp())
        return f"after:{timestamp}"

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
                    emailSender, emailId = parseaddr(from_header)

            if emailId is None or emailId == '':
                logger.error(f"Email ID not found in 'From' header for message {msg_id}. Skipping.")

            internal_date_ms = int(msg_data.get("internalDate"))
            date_time = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc)
            mail_data = {
                'thread_id': msg_data.get('threadId', ''),
                'id': msg_data.get('id', ''),
                'snippet': msg_data.get('snippet', ''),
                'date_time': date_time,
                'emailSender': emailSender,
                'emailId': emailId.lower(),
            }
            return mail_data
        except Exception as e:
            print(f"Error fetching message {msg_id}: {e}")
            return None

    def get_initial_history_id(service):
        profile = service.users().getProfile(userId="me").execute()
        return profile["historyId"]

    def fetch_emails_messages_list(self, query, next_page_token=None, max_results=1) -> tuple:
        results = self.gmail_service.users().messages().list(
            userId='me', 
            maxResults=max_results, 
            q=query,
            pageToken=next_page_token,
            includeSpamTrash=False,
        ).execute()
        messages = results.get('messages', [])
        message_list = []
        for msg in messages:
            msg_data = self.gmail_service.users().messages().get(userId='me', id=msg['id']).execute()
            message_list.append(msg_data)
        return message_list, results.get('nextPageToken')

    def sync_database(self, processed_messages: list[EmailMessage]):
        '''
        Send the list of emails to mb-backend api to insert into db
        Send in batch of 50
        '''
        formatted_email_list = []
        for email in processed_messages:
            formatted_email_list.append(json.loads(email.model_dump_json()))

        response = requests.post(
            ENV_SETTINGS.MB_BACKEND_API_URL + 'api/v1/emails/insert-bulk',
            headers={'Content-Type': 'application/json'},
            json={
                'emails': formatted_email_list,
                'userId': self.userId,
                'emailId': self.email,
                'accountId': self.accountId,
            }
        )
        if response.status_code != 200:
            logger.error(f"Failed to insert batch starting at index : {response.text}")
        else:
            logger.info("Successfully inserted batch starting at index")
        
        return response.status_code


    def parse_received_at(self, msg: dict):
        internal_date_ms = msg.get("internalDate")
        if not internal_date_ms:
            return None

        return datetime.fromtimestamp(
            int(internal_date_ms) / 1000,
            tz=timezone.utc
        )
    def decode_base64url(self, data: str) -> str:
        if not data:
            return ""
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


    def decode_sender_name(self, raw_name: str) -> str | None:
        if not raw_name:
            return None

        parts = decode_header(raw_name)
        decoded = ""

        for part, encoding in parts:
            if isinstance(part, bytes):
                decoded += part.decode(encoding or "utf-8", errors="replace")
            else:
                decoded += part

        return decoded.strip() or None


    def decode_subject(self, raw_subject: str) -> str | None:
        if not raw_subject:
            return None

        parts = decode_header(raw_subject)
        decoded = ""

        for part, encoding in parts:
            if isinstance(part, bytes):
                decoded += part.decode(encoding or "utf-8", errors="replace")
            else:
                decoded += part

        return decoded.strip() or None

    def extract_headers(self, headers: list[dict]) -> dict:
        from_header = ""
        subject_header = ""

        for h in headers:
            name = h.get("name", "").lower()
            value = h.get("value", "")

            if name == "from":
                from_header = value
            elif name == "subject":
                subject_header = value

        raw_name, email_id = parseaddr(from_header)

        return {
            "sender_name": self.decode_sender_name(raw_name),
            "sender_email": email_id or None,
            "subject": self.decode_subject(subject_header)
        }

    def extract_body_from_payload(self, payload: dict) -> dict:
        """
        Recursively walk MIME tree.
        Returns dict with keys: text, html
        """
        result = {"text": None, "html": None}

        mime_type = payload.get("mimeType", "")
        body = payload.get("body", {})
        data = body.get("data")

        # Direct body
        if mime_type == "text/plain" and data:
            result["text"] = self.decode_base64url(data)
            return result

        if mime_type == "text/html" and data:
            result["html"] = self.decode_base64url(data)
            return result

        # Multipart
        for part in payload.get("parts", []):
            sub = self.extract_body_from_payload(part)

            if sub["text"] and not result["text"]:
                result["text"] = sub["text"]

            if sub["html"] and not result["html"]:
                result["html"] = sub["html"]

            if result["text"]:
                break

        return result


    def html_to_text(self, html: str) -> str:
        text = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.S)
        text = re.sub(r"<style.*?>.*?</style>", " ", html, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


    def extract_email_body(self, msg: dict) -> str:
        payload = msg.get("payload", {})
        bodies = self.extract_body_from_payload(payload)

        if bodies["text"]:
            return bodies["text"].strip()

        if bodies["html"]:
            return self.html_to_text(bodies["html"])

        return ""

    def process_gmail_message(self, msg: dict) -> EmailSanitized:
        headers = msg.get("payload", {}).get("headers", [])
        header_data = self.extract_headers(headers)

        receivedAt = self.parse_received_at(msg)

        body = self.extract_email_body(msg)
        sender_email = header_data.get("sender_email")
        sender_name = header_data.get("sender_name", sender_email)
        if not sender_name:
            sender_name = sender_email

        return EmailSanitized(
            id=msg.get("id"),
            threadId=msg.get("threadId"),
            emailSender=sender_name,
            emailId=sender_email,
            subject=header_data.get("subject"),
            snippet=msg.get("snippet"),
            body=body,
            receivedAt=receivedAt,
        )

    def fetch_messages_details_list(self, email_messages: list[dict]) -> list[EmailSanitized]:
        messages_to_insert: list[EmailSanitized] = []
        for msg in email_messages:
            result = self.process_gmail_message(msg)
            if result:
                messages_to_insert.append(result)
        
        return messages_to_insert

class AIManager:
    '''
    This class is supposed to do the following actions:
    1. Process emails through llm
    '''
    def __init__(self, email: str, userId: str, accountId: str):
        self.email = email
        self.userId = userId
        self.accountId = accountId

    @traceable(
        name="generate_transactions",
        run_type="llm",
        metadata={"ls_provider": "Gemini", "ls_model_name": "gemini-2.5-flash"}
    )
    def generate_transactions_list_from_emails(self, message_to_parse_list: list[str]) -> list:

        run = get_current_run_tree()
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
                response = VERTEXT_CLIENT.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=final_prompt,
                )

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    token_usage = {
                        "input_tokens": response.usage_metadata.prompt_token_count,
                        "output_tokens": response.usage_metadata.candidates_token_count,
                        "total_tokens": response.usage_metadata.total_token_count,
                        "input_token_details": {
                            "cache_read": response.usage_metadata.cached_content_token_count,
                        },
                    }
                    run.set(usage_metadata=token_usage)
                
                run.metadata["user_id"] = self.userId
                run.metadata["email"] = self.email
                run.metadata["account_id"] = self.accountId
                return {
                    "input_messages": message_to_parse_list,
                    "raw_model_output": response.text
                }
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All retry attempts failed for generate_content: {str(e)}")
                    raise
    @traceable(
        name="generate_orders",
        run_type="llm",
        metadata={"ls_provider": "Gemini", "ls_model_name": "gemini-2.5-flash"}
    )
    def extract_order_from_emails(self, sanitized_emails: list[EmailSanitized]) -> list[dict]:

        message_to_parse_list = []
        for email in sanitized_emails:
            body = email.body
            if not body:
                continue
            body = f"ID {email.id}:\n{body}"
            message_to_parse_list.append(body)
        
        run = get_current_run_tree()
        BASE_PROMPT = f"""
        You are an expert data extraction assistant specialized in order confirmation emails from e-commerce platforms.


        You will be given MULTIPLE emails.

        For EACH email:
        - `messageId` (string): Unique identifier for the message. This maps to the "ID" in the message.
        - Extract AT MOST ONE order
        - If the email is not a purchase receipt, then skip it
        - Do NOT merge information across emails
        - Do NOT infer missing data from other emails
        - Maintain the SAME ORDER as input

        **Strict Output Requirements:**
        * **Absolutely no conversational text, explanations, or markdown formatting (e.g., ```json) outside the JSON list itself.**
        * The response must begin with `[` and end with `]`.

        Rules:
        - Output ONLY valid JSON
        - Do NOT include explanations or markdown
        - Do NOT guess missing values (use null)
        - Represent ALL monetary components as lineItems
        - Discounts must have NEGATIVE totals
        - Do not invent items or prices

        OutputSchema:
        {OrdersListIntentModel.model_json_schema()}
        
        """
        final_prompt = BASE_PROMPT + "\n\n" + "\n\n".join(message_to_parse_list)
        
        # Add retry logic for timeout errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = VERTEXT_CLIENT.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=final_prompt,
                )

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    token_usage = {
                        "input_tokens": response.usage_metadata.prompt_token_count,
                        "output_tokens": response.usage_metadata.candidates_token_count,
                        "total_tokens": response.usage_metadata.total_token_count,
                        "input_token_details": {
                            "cache_read": response.usage_metadata.cached_content_token_count,
                        },
                    }
                    run.set(usage_metadata=token_usage)
                
                run.metadata["user_id"] = self.userId
                run.metadata["email"] = self.email
                run.metadata["account_id"] = self.accountId
                return {
                    "input_messages": message_to_parse_list,
                    "raw_model_output": response.text
                }
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

    def extract_transactions_from_emails(self, emails_list: list[EmailMessage]) -> list[dict]:

        message_dict_list = {msg.id: msg for msg in emails_list}
        message_to_parse_list = []

        # Prepare messages for parsing
        for msg in emails_list:
            id = msg.id
            snippet = msg.snippet

            if not snippet:
                continue
            logger.info(f"Preparing email ID {id} for parsing. Snippet: {snippet}")
            snippet = f"ID {id}:\n{snippet}"
            message_to_parse_list.append(snippet)
            # mark_email_as_gemini_parsed(msg.thread_id)

        model_response = self.generate_transactions_list_from_emails(message_to_parse_list).get("raw_model_output", "")
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
                txn.date_time = email_details.date_time.isoformat() if email_details else None

                transactions_list.append(json.loads(txn.model_dump_json(exclude_none=True)))
            except Exception as e:
                logger.exception(e)
            finally:
                # Mark the email as a transaction
                self.mark_email_as_gemini_parsed(transaction.get('id'))
        
        return transactions_list

    def saveTransactions(self, transactions_list: list[dict]):
        '''
        Send the list of transactions to mb-backend api to insert into db
        Send in batch of 50
        '''
        response = requests.post(
            ENV_SETTINGS.MB_BACKEND_API_URL + 'api/v1/transactions/bulk-insert',
            headers={'Content-Type': 'application/json'},
            json={
                'transactions': transactions_list,
                'userId': self.userId,
                'emailId': self.email,
                'accountId': self.accountId,
            }
        )
        if response.status_code != 200:
            logger.error(f"Failed to insert batch starting at index : {response.text}")
        else:
            logger.info("Successfully inserted batch starting at index")
        
        return response.status_code

    def saveOrders(self, orders_list: list[dict]):
        '''
        Send the list of orders to mb-backend api to insert into db
        Send in batch of 50
        '''
        response = requests.post(
            ENV_SETTINGS.MB_BACKEND_API_URL + 'api/v1/orders/bulk-insert',
            headers={'Content-Type': 'application/json'},
            json={
                'orders': orders_list,
                'userId': self.userId,
                'accountId': self.accountId,
            }
        )
        if response.status_code != 200:
            logger.error(f"Failed to insert orders batch starting at index : {response.text}")
        else:
            logger.info("Successfully inserted orders batch starting at index")
        
        return response.status_code

class CoRelationManager:
    '''
    This class is supposed to do the following actions:
    The logic to co-relate will be as follows, 
    1. For each order, find transactions whose amount matches the order total (with a tolerance of +/- 2%)
    2. For each order, find transaction which is closest in time to the order date/time (within a window of 7 days)
    3. For each order, check the vendor name against transaction description for a match (case insensitive substring match)
    4. Assign a confidence score based on amount match, time proximity, and vendor name for each transaction candidate
    5. Select the transaction with the highest confidence score above a certain threshold (e.g. 90%) as the match for the order
    6. Weightage of each factor can be adjusted to improve accuracy based on observed data
    '''
    def __init__(self, email: str, userId: str, accountId: str, orders_list: list[dict], transactions_list: list[dict]):
        self.email = email
        self.userId = userId
        self.accountId = accountId
        self.orders_list = orders_list
        self.transactions_list = transactions_list
