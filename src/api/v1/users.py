from fastapi.responses import JSONResponse
from src.modules.transactions.schema import TransactionORM
from packages.models import TaskQueuePayload
from src.modules.users.models import UserAuthPayload, GmailAuthVerificationResponse, UserUpdatePayload
from src.modules.users.schema import UsersORM
from src.modules.users.operations import createUser, gmailExchangeCodeForToken, verifyGmailToken, fetchUserByEmail, generateGmailAccessUrl, setSyncLock, releaseSyncLock, updateUserById

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic

from src.core.database import get_db
from sqlalchemy.orm import Session

from src.utils.common import enqueue_worker_task
from src.utils.log import setup_logger

router = APIRouter()
security = HTTPBasic()

logger = setup_logger(__name__)

@router.post("/auth")
async def verify_token_and_get_access(payload: UserAuthPayload ,db: Session = Depends(get_db)):
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
    
    gmail_access_url = generateGmailAccessUrl(str(user.id))

    return {
        "gmailAccessUrl": gmail_access_url,
        "user": {
            "email": userDetails.email,
            "name": userDetails.name,
            "picture": userDetails.picture,
            "id": str(user.id),
            "gmailRefreshToken": user.gmailRefreshToken
        }
    }

@router.get("/auth/callback")
async def gmail_auth_callback(state: str, code: str, db: Session = Depends(get_db)):
    """
    Handle Gmail OAuth2 callback
    """
    # TODO: state is set as userId
    userId = state
    token = gmailExchangeCodeForToken(userId, code, db)

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
        
        if not setSyncLock(id, db):
            return JSONResponse(
                status_code=204,
                content={"message": "Already syncing"}
            )
        
        payload: TaskQueuePayload = TaskQueuePayload(
            email=user.email,
            userId=str(id),
            token=user.gmailRefreshToken
        )

        enqueue_worker_task(payload.model_dump())
        return JSONResponse(
            status_code=200,
            content={"message": "Email scraping completed successfully", "status": "completed"}
        )
    except Exception as e:
        logger.exception(f"Error during email scraping: {e}")
        releaseSyncLock(id, db)
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to scrape emails", "error": str(e)}
        )

@router.post("/{id}/unlock")
async def unlockSyncRoute(id: str, db: Session = Depends(get_db)):
    """Release sync lock for user - to be called by worker after completion"""
    try:
        user = db.query(UsersORM).filter(UsersORM.id == id).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )
        
        releaseSyncLock(id, db)
        return JSONResponse(
            status_code=200,
            content={"message": "Sync lock released successfully"}
        )
    except Exception as e:
        logger.exception(f"Error releasing sync lock: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to release sync lock", "error": str(e)}
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