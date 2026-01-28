# worker/main.py
from fastapi import Depends, FastAPI, Request, HTTPException
import json
import logging
import base64
import requests

from packages.models import EmailSanitized, TaskQueuePayload
from worker.connectors import ENV_SETTINGS
from worker.operations import AIManager, EmailManager
from worker.gmailAuth import authenticateGmail

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def release_sync_lock(account_id: str) -> None:
    """Release sync lock for a user after task completion or error."""
    try:
        unlock_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/accounts/{account_id}/unlock"
        unlock_response = requests.post(unlock_url)
        logger.info(f"Sync lock released for user with {account_id}, status: {unlock_response.status_code}")
    except Exception as unlock_error:
        logger.error(f"Failed to release sync lock for user with {account_id}: {unlock_error}")

def fetch_user_details(user_id: str) -> dict:
    """Fetch user details from backend API."""
    try:
        user_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/users/{user_id}"
        response = requests.get(user_url)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to fetch user details, status: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching user details for user {user_id}: {e}")
        return None

def fetch_account_details(account_id: str) -> dict:
    """Fetch account details from backend API."""
    try:
        account_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/accounts/{account_id}"
        response = requests.get(account_url)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to fetch account details, status: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching account details for account {account_id}: {e}")
        return None
    
def update_last_synced_at(accountId: str, last_synced_at: str) -> None:
    """Update lastSyncedAt for a account."""
    try:
        update_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/accounts/{accountId}"
        response = requests.put(
            update_url,
            headers={'Content-Type': 'application/json'},
            json={'lastSyncedAt': last_synced_at}
        )
        logger.info(f"Updated lastSyncedAt for account {accountId}, status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to update lastSyncedAt for account {accountId}: {e}")
    
def fetch_transactions(user_id: str) -> list:
    """Fetch transactions for a user from backend API."""
    try:
        transactions_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/users/{user_id}/transactions"
        response = requests.get(transactions_url)
        if response.status_code == 200:
            return response.json().get("transactions", [])
        logger.error(f"Failed to fetch transactions, status: {response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Error fetching transactions for user {user_id}: {e}")
        return []

def fetch_orders(user_id: str) -> list:
    """Fetch orders for a user from backend API."""
    try:
        orders_url = f"{ENV_SETTINGS.MB_BACKEND_API_URL}api/v1/users/{user_id}/orders"
        response = requests.get(orders_url)
        if response.status_code == 200:
            return response.json().get("orders", [])
        logger.error(f"Failed to fetch orders, status: {response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Error fetching orders for user {user_id}: {e}")
        return []

@app.post("/tasks/process")
async def processTask(request: Request):
    '''
    1. take the user id given in input
    2. fetch the user details via user id
    3. use the stored token to authenticate gmail
    4. fetch unread emails
    5. process emails
    6. store results in db
    7. return status    
    '''
    accountId = None
    try:
        logger.info("Received task processing request")
        payload = await request.body()
        payload = base64.b64decode(payload).decode("utf-8")
        payload = json.loads(payload)  # Parse the JSON string to dictionary
        logger.info(f"Received task payload: {payload}")
        accountId = payload.get("accountId")

        tasksPayload: TaskQueuePayload = TaskQueuePayload(**payload)  # Validate payload structure

        # Fetch account details to get lastSyncedAt
        accountDetails = fetch_account_details(tasksPayload.accountId)
        if not accountDetails:
            raise Exception("Failed to fetch account details")
        
        # Fetch user details to get lastSyncedAt
        userDetails = fetch_user_details(tasksPayload.userId)
        if not userDetails:
            raise Exception("Failed to fetch user details")
        
        last_synced_at = accountDetails.get('lastSyncedAt')
        logger.info(f"Account lastSyncedAt: {last_synced_at}")

        # Authenticate Gmail
        gmailService = authenticateGmail(tasksPayload.token)

        # Fetch emails and process it
        emailManager = EmailManager(
            gmail_service=gmailService,
            email=tasksPayload.email,
            userId=accountDetails.get('userId'),
            accountId=tasksPayload.accountId,
        )

        # Build query based on lastSyncedAt
        query = emailManager.build_gmail_query(last_synced_at)
        logger.info(f"Gmail query: {query}")

        next_page_token = None
        latest_email_time = None
        while True:
            # Fetch emails in batches
            messages, next_page_token = emailManager.fetch_emails_messages_list(query, next_page_token, max_results=10)
            logger.info(f"Fetched {len(messages)} emails for accountId: {tasksPayload.accountId}")
            if len(messages) == 0:
                break
            processed_messages: list[EmailSanitized] = emailManager.fetch_messages_details_list(messages)
            logger.info(f"Processed {len(processed_messages)} emails for accountId: {tasksPayload.accountId}")
            
            # send emails to mb-backend for inserting into db
            # TODO: if userDetails.get("has_allowed_analytics", False) is True:
            statusCode: int = emailManager.sync_database(processed_messages)
            logger.info(f"Database sync status code: {statusCode}")

            # Process LLM through Gemini and update the database
            aiManager: AIManager = AIManager(
                email=tasksPayload.email, 
                userId=tasksPayload.userId, 
                accountId=tasksPayload.accountId,
            )
            transactions_list: list[dict] = aiManager.extract_transactions_from_emails(processed_messages)

            # Send processed transactions to mb-backend for inserting into db
            if transactions_list:            
                logger.info(f"Processed and extracted {len(transactions_list)} transactions from emails for email: {tasksPayload.email}")
                status = aiManager.saveTransactions(transactions_list)
                logger.info(f"AI Manager database sync status: {status}")
            else:
                logger.info("No transactions extracted from emails, skipping database sync")


            # Process Orders from emails
            llm_orders_response = aiManager.extract_order_from_emails(processed_messages)
            orders_list = aiManager.extract_json_from_response(llm_orders_response.get("raw_model_output"))
            if orders_list:
                logger.info(f"Processed and extracted {len(orders_list)} orders from emails for email: {tasksPayload.email}")
                status = aiManager.saveOrders(orders_list)
                logger.info(f"AI Manager orders database sync status: {status}")

            # Update lastSyncedAt to the latest email timestamp
            if processed_messages:
                if not latest_email_time:
                    latest_email_time = processed_messages[0].receivedAt
                for msg in processed_messages:
                    if msg.receivedAt:
                        latest_email_time = max(msg.receivedAt, latest_email_time)
            if not next_page_token:
                break
        # while loop ends

        if latest_email_time:
            update_last_synced_at(tasksPayload.accountId, latest_email_time.isoformat())
            logger.info(f"Updated lastSyncedAt to {latest_email_time.isoformat()}")

        return {"status": "done"}
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.exception(e)
        logger.error(f"Invalid JSON or base64 payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload format")
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error processing job: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        # TODO: figure out way to unlock user if user id is not present
        if accountId:
            release_sync_lock(account_id=accountId)

@app.post("/tasks/co-relate-orders")
async def processOrders(request: Request):
    '''
    This API will be used to figure out the orders placed by user from different platforms
    It will take input of the orders and transactions already stored in the db
    And then it will try to figure out a co-relation between them. The respective orders and transactions
    will be updated with the co-relation info.
    1. take the user id given in input
    2. fetch the orders and transactions from the db via api calls
    3. use co-relation logic to find matches
    4. update the orders and transactions in the db via api calls
    5. return status

    '''
    try:
        logger.info("Received order processing request")
        payload = await request.body()
        payload = base64.b64decode(payload).decode("utf-8")
        payload = json.loads(payload)
        logger.info(f"Received order payload: {payload}")

        # Fetch orders from backend API
        orders_list = fetch_orders(payload.get("userId"))
        logger.info(f"Fetched {len(orders_list)} orders for userId: {payload.get('userId')}")
        # Fetch transactions from backend API
        transactions_list = fetch_transactions(payload.get("userId"))
        logger.info(f"Fetched {len(transactions_list)} transactions for userId: {payload.get('userId')}")

        if not orders_list or not transactions_list:
            logger.info("No orders or transactions found, skipping co-relation")
            return {"status": "no data to process"}
        
        # Implement co-relation logic



    except (json.JSONDecodeError, ValueError) as e:
        logger.exception(e)
        logger.error(f"Invalid JSON or base64 payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload format")
    except Exception as e:
        logger.exception(e)
        logger.error(f"Error processing orders job: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Add health check api
@app.get("/health")
async def health_check():
    return {"status": "worker is healthy"}