"""Database query executor with safety checks"""

from typing import Any, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DatabaseError
from src.utils.sql_validator import sql_validator
from src.utils.log import setup_logger

logger = setup_logger(__name__)


class QueryExecutor:
    """Execute SQL queries with safety constraints"""
    
    def __init__(self, read_only_db: Session):
        self.max_rows = 200
        self.timeout_seconds = 3
        self.read_only_db = read_only_db
    
    def execute_read_only_query(
        self,
        sql: str,
        user_id: str
    ) -> Tuple[bool, Any]:
        """
        Execute a read-only SQL query with safety checks
        Returns: (success, results_or_error)
        """
        
        # Validate SQL
        is_valid, error_msg = sql_validator.validate_query(sql)
        if not is_valid:
            logger.warning(f"SQL validation failed for user {user_id}: {error_msg}")
            return False, f"Invalid SQL: {error_msg}"
        
        # Sanitize LIMIT
        sql = sql_validator.sanitize_limit(sql, self.max_rows)
        
        try:
            
            # Set statement timeout
            self.read_only_db.execute(text(f"SET statement_timeout = {self.timeout_seconds * 1000}"))
            
            # Execute query
            result = self.read_only_db.execute(text(sql))
            
            # Fetch results
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to list of dicts
            results = [
                dict(zip(columns, row))
                for row in rows
            ]
            
            logger.info(f"Query executed successfully for user {user_id}: {len(results)} rows")
            return True, results
        
        except OperationalError as e:
            if "timeout" in str(e).lower() or "canceling statement" in str(e).lower():
                error_msg = f"Query timeout exceeded ({self.timeout_seconds}s)"
                logger.error(f"Query timeout for user {user_id}: {sql}")
                return False, error_msg
            else:
                error_msg = f"Database error: {str(e)}"
                logger.error(f"Database error for user {user_id}: {str(e)}")
                return False, error_msg
        
        except DatabaseError as e:
            error_msg = f"Database error: {str(e)}"
            logger.error(f"Database error for user {user_id}: {str(e)}")
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error for user {user_id}: {str(e)}")
            return False, error_msg

