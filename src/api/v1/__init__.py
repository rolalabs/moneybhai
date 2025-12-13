from fastapi import APIRouter
from src.api.v1 import emails

api_router = APIRouter()
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])