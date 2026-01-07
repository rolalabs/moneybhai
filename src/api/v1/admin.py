from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import subprocess
import os

router = APIRouter()
security = HTTPBasic()


def verify_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Simple admin authentication"""
    correct_username = secrets.compare_digest(credentials.username, "money")
    correct_password = secrets.compare_digest(credentials.password, "bhai")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@router.post("/migrate/upgrade")
async def upgrade_migrations(user: str = Depends(verify_admin_credentials)):
    """
    Run database migrations to upgrade to head.
    Requires basic auth (same as docs).
    """
    try:
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )
        
        if result.returncode == 0:
            return {
                "status": "success",
                "message": "Migrations completed successfully",
                "output": result.stdout
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": "Migration failed",
                    "error": result.stderr
                }
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Migration timeout - operation took longer than 5 minutes"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )
