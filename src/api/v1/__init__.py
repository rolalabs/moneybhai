from fastapi import APIRouter
from src.api.v1 import emails, admin, users, transactions, analytics, accounts

api_router = APIRouter()
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(transactions.router)
api_router.include_router(analytics.router)