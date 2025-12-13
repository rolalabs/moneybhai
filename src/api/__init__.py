from fastapi import APIRouter, Depends
from src.api.v1 import api_router as v1_router
from src.core.auth import authorize

router = APIRouter()
router.include_router(
    v1_router, 
    prefix="/v1",
    dependencies=[Depends(authorize)]
)
