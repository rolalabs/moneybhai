from sqlalchemy.orm import Session
from src.modules.users.schema import UsersORM
from src.utils.log import setup_logger

logger = setup_logger(__name__)

def fetch_user_by_id(user_id: str, db: Session):
    user = db.query(UsersORM).filter(UsersORM.id == user_id).first()
    if not user:
        logger.error(f"User with ID {user_id} not found.") 
    return user