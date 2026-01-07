from fastapi.responses import JSONResponse
from src.modules.users.models import UserSyncModel
from src.modules.users.schema import UsersORM

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic

from src.core.database import get_db
from sqlalchemy.orm import Session

from src.utils.common import enqueue_worker_task
from src.utils.log import setup_logger

router = APIRouter()
security = HTTPBasic()

logger = setup_logger(__name__)


@router.get("/all")
async def list_users(db: Session = Depends(get_db)):
    """List all users in the database."""
    users = db.query(UsersORM).all()
    return users

@router.post("/")
async def create_user(email: str, name: str, db: Session = Depends(get_db)):
    """Create a new user in the database."""
    new_user = UsersORM(email=email, name=name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/{id}")
async def get_user(id: str, db: Session = Depends(get_db)):
    """Get a user by ID."""
    user = db.query(UsersORM).filter(UsersORM.id == id).first()
    if not user:
        return {"error": "User not found"}
    return user

    
@router.post("/{id}/synchronize", response_model=dict)
async def scrapeEmailsRoute(id: str, userSyncModel: UserSyncModel, db: Session = Depends(get_db)):
    """Route to scrape emails immediately"""
    try:

        
        user = db.query(UsersORM).filter(UsersORM.id == id).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={"message": "User not found"}
            )

        enqueue_worker_task({
            "email": user.email,
            "id": str(id),
            "token": userSyncModel.token
        })
        return JSONResponse(
            status_code=200,
            content={"message": "Email scraping completed successfully", "status": "completed"}
        )
    except Exception as e:
        logger.exception(f"Error during email scraping: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to scrape emails", "error": str(e)}
        )