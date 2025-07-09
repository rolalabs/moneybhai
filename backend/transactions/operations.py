from backend.transactions.models import TransactionORM
from backend.utils.connectors import DB_SESSION


def get_last_transaction():
    last_record = DB_SESSION.query(TransactionORM).order_by(TransactionORM.id.desc()).first()
    DB_SESSION.close()
    return last_record