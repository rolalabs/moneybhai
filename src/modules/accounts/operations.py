from datetime import datetime, timezone
from src.modules.accounts.schema import AccountsORM
from sqlalchemy.orm import Session

from src.utils.log import setup_logger

logger = setup_logger(__name__)

# get accounts by emailId
def getAccountByEmailId(emailId: str, db: Session) -> AccountsORM | None:
    account = db.query(AccountsORM).filter(AccountsORM.emailId == emailId).first()
    return account

def getAccountById(accountId: str, db: Session) -> AccountsORM | None:
    account = db.query(AccountsORM).filter(AccountsORM.id == accountId).first()
    return account

def getAccountsByUserId(userId: str, db: Session) -> list[AccountsORM]:
    accounts = db.query(AccountsORM).filter(AccountsORM.userId == userId).all()
    return accounts

# create account
def createAccount(email: str, id: str, db: Session):

    newAccount: AccountsORM = AccountsORM(
        emailId=email,
        userId=id,
        createdAt=datetime.now(timezone.utc),
        isSyncing=False,
        lastSyncedAt=None
    )
    db.add(newAccount)
    db.commit()
    db.refresh(newAccount)
    return newAccount


def updateAccountById(accountId: str, update_data: dict, db: Session):
    account = db.query(AccountsORM).filter(AccountsORM.id == accountId).first()
    if not account:
        logger.error(f"Account with ID {accountId} not found for update.")
        return None
    for key, value in update_data.items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    logger.info(f"Updated account with ID {accountId}.")
    return account

def setSyncLock(accountId: str, db: Session) -> bool:
    """Set sync lock for account. Returns True if lock was set, False if already syncing."""
    account = db.query(AccountsORM).filter(AccountsORM.id == accountId).first()
    if not account:
        logger.error(f"Account with ID {accountId} not found.")
        return False
    if account.isSyncing:
        logger.info(f"Account {accountId} is already syncing.")
        return False
    account.isSyncing = True
    db.commit()
    logger.info(f"Sync lock set for account {accountId}.")
    return True

def releaseSyncLock(accountId: str, db: Session) -> bool:
    """Release sync lock for account. Returns True if lock was released."""
    account = db.query(AccountsORM).filter(AccountsORM.id == accountId).first()
    if not account:
        logger.error(f"Account with ID {accountId} not found.")
        return False
    account.isSyncing = False
    db.commit()
    logger.info(f"Sync lock released for account {accountId}.")
    return True