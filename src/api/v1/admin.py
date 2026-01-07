from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import subprocess
import os
from sqlalchemy import text
from src.core.database import get_db
from sqlalchemy.orm import Session

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


@router.get("/db/check")
async def check_database_connection(
    user: str = Depends(verify_admin_credentials),
    db: Session = Depends(get_db)
):
    """
    Check database connection health.
    Returns database version and connection status.
    """
    try:
        # Execute a simple query to check connection
        result = db.execute(text("SELECT version()"))
        version = result.scalar()
        
        # Check if we can access the schema
        schema_check = db.execute(text("SELECT schema_name FROM information_schema.schemata"))
        schema_exists = schema_check.scalar() is not None
        
        return {
            "status": "success",
            "message": "Database connection is healthy",
            "database_version": version,
            "schema_exists": schema_exists
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Database connection failed",
                "error": str(e)
            }
        )


