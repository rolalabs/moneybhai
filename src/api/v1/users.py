from fastapi.responses import JSONResponse
from src.modules.accounts.operations import createAccount, getAccountByEmailId, getAccountsByUserId, setSyncLock, releaseSyncLock
from src.modules.accounts.schema import AccountsORM
from src.modules.transactions.schema import TransactionORM
from packages.models import TaskQueuePayload
from src.modules.users.models import UserAuthPayload, GmailAuthVerificationResponse, UserUpdatePayload
from src.modules.users.schema import UsersORM
from src.modules.users.operations import createUser, fetchUserById, gmailExchangeCodeForToken, verifyGmailToken, fetchUserByEmail, updateUserById

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic

from src.core.database import get_db
from sqlalchemy.orm import Session

from src.utils.common import enqueue_worker_task
from src.utils.log import setup_logger

router = APIRouter()
security = HTTPBasic()

logger = setup_logger(__name__)

# create an endpoint to create account for a user by taking UserAuthPayload
@router.post("/{user_id}/accounts", response_model=dict)
async def create_account_for_user(user_id: str, payload: UserAuthPayload, db: Session = Depends(get_db)):
    """Create an account for a user using the provided email from the auth payload."""
    user = fetchUserById(user_id, db)
    if not user:
        return JSONResponse(
            status_code=404,
            content={"message": "User not found"}
        )
    verificationResponse = verifyGmailToken(payload.token)
    accountDetails = GmailAuthVerificationResponse(**verificationResponse)

    # check if account already exists
    existing_account: AccountsORM = getAccountByEmailId(emailId=accountDetails.email, db=db)
    if existing_account:
        return JSONResponse(
            status_code=400,
            content={"message": "Account with this email already exists"}
        )
    # create account
    new_account: AccountsORM = createAccount(accountDetails.email, str(user.id), db)
    return {
        "message": "Account created successfully",
        "accountId": str(new_account.id)
    }

@router.get("/{user_id}/accounts")
async def get_user_accounts(user_id: str, db: Session = Depends(get_db)):
    """Get all accounts for a specific user."""
    user = fetchUserById(user_id, db)
    if not user:
        return JSONResponse(
            status_code=404,
            content={"message": "User not found"}
        )
    accounts = getAccountsByUserId(user_id, db)
    if not accounts:
        return JSONResponse(
            status_code=404,
            content={"message": "No accounts found for this user"}
        )
    return {"accounts": accounts}

@router.post("/{id}/link-gmail", response_model=dict)
async def link_gmail_with_user(id: str, payload: UserAuthPayload, db: Session = Depends(get_db)):
    """Generate Gmail OAuth2 link URL for the user's account."""
    user = fetchUserById(id, db)
    if not user:
        return {"error": "User not found"}
    
    verificationResponse = verifyGmailToken(payload.token)
    accountDetails = GmailAuthVerificationResponse(**verificationResponse)

    # fetch from accounts table
    account: AccountsORM = getAccountByEmailId(emailId=accountDetails.email, db=db)
    if not account:
        account: AccountsORM = createAccount(accountDetails.email, str(user.id), db)
    
    # return success response
    return {
        "message": "Gmail linked successfully",
        "accountId": str(account.id)
    }

@router.post("/auth")
async def verify_token_and_get_access(payload: UserAuthPayload, db: Session = Depends(get_db)):
    """
    1. Verify Auth Token
    2. Check if user exists or not
    3. If not, then create in database
    4. Create gmail auth url
    5. send in response to user
    """
    verificationResponse = verifyGmailToken(payload.token)
    userDetails = GmailAuthVerificationResponse(**verificationResponse)
    user: UsersORM = fetchUserByEmail(email=userDetails.email, db=db)
    if not user:
        # create user
        user = createUser(email=userDetails.email, name=userDetails.name, db=db)
    
    return {
        "email": userDetails.email,
        "name": userDetails.name,
        "picture": userDetails.picture,
        "id": str(user.id),
    }


@router.get("/auth/callback")
async def gmail_auth_callback(state: str, code: str, db: Session = Depends(get_db)):
    """
    Handle Gmail OAuth2 callback
    """
    # TODO: state is set as accountId
    accountId = state
    gmailExchangeCodeForToken(accountId, code, db) 

    return {"message": "Gmail OAuth2 callback received", "code": code}

@router.get("/all")
async def list_users(db: Session = Depends(get_db)):
    """List all users in the database."""
    users = db.query(UsersORM).all()
    return users

@router.get("/{id}")
async def get_user(id: str, db: Session = Depends(get_db)):
    """Get a user by ID."""
    user = db.query(UsersORM).filter(UsersORM.id == id).first()
    if not user:
        return {"error": "User not found"}
    return user

@router.put("/{id}")
async def update_user(id: str, payload: UserUpdatePayload, db: Session = Depends(get_db)):
    """Update user by ID."""
    try:
        user = db.query(UsersORM).filter(UsersORM.id == id).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return JSONResponse(
                status_code=400,
                content={"message": "No fields to update"}
            )
        
        updated_user = updateUserById(id, update_data, db)
        return JSONResponse(
            status_code=200,
            content={"message": "User updated successfully", "user": {"id": str(updated_user.id)}}
        )
    except Exception as e:
        logger.exception(f"Error updating user {id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to update user", "error": str(e)}
        )

    
@router.get("/{id}/synchronize", response_model=dict)
async def scrapeEmailsRoute(id: str, db: Session = Depends(get_db)):
    """Route to scrape emails immediately"""
    try:
        user = db.query(UsersORM).filter(UsersORM.id == id).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        account = getAccountByEmailId(user.email, db)
        if not account or not account.gmailRefreshToken:
            return JSONResponse(
                status_code=400,
                content={"message": "Gmail not connected for this user"}
            )
        
        if not setSyncLock(str(account.id), db):
            return JSONResponse(
                status_code=204,
                content={"message": "Already syncing"}
            )
        
        payload: TaskQueuePayload = TaskQueuePayload(
            email=user.email,
            userId=str(id),
            accountId=str(account.id),
            token=account.gmailRefreshToken
        )

        enqueue_worker_task(payload.model_dump())
        return JSONResponse(
            status_code=200,
            content={"message": "Email scraping completed successfully", "status": "completed"}
        )
    except Exception as e:
        logger.exception(f"Error during email scraping: {e}")
        releaseSyncLock(str(account.id), db)
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to scrape emails", "error": str(e)}
        )

# create an endpoint to fetch transactions by userId
@router.get("/{userId}/transactions")
async def get_transactions_by_userId(userId: str, db: Session = Depends(get_db)):
    """Get transactions by User ID."""
    try:
        user = db.query(UsersORM).filter(UsersORM.id == userId).all()
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        transactions = db.query(TransactionORM).filter(TransactionORM.userId == userId).order_by(TransactionORM.date_time.desc()).all()
        return transactions
    except Exception as e:
        logger.exception(f"Error fetching transactions for userId {userId}: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to fetch transactions", "error": str(e)}
        )