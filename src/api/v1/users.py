from src.modules.users.schema import UsersORM

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic

from src.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
security = HTTPBasic()


@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    """List all users in the database."""
    users = db.query(UsersORM).all()
    return users

@router.post("/users")
async def create_user(email: str, name: str, db: Session = Depends(get_db)):
    """Create a new user in the database."""
    new_user = UsersORM(email=email, name=name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user