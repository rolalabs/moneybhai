"""SQL validation utilities for ensuring query safety"""

import re
from typing import Tuple


class SQLValidator:
    """Validates SQL queries for safety and correctness"""
    
    # Forbidden keywords that could modify data
    FORBIDDEN_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
        'CALL', 'DECLARE', 'SET', 'COMMIT', 'ROLLBACK'
    ]
    
    # Allowed tables
    ALLOWED_TABLES = ['transactions', 'orders', 'order_items']
    
    @staticmethod
    def validate_query(sql: str) -> Tuple[bool, str]:
        """
        Validate SQL query for safety
        Returns: (is_valid, error_message)
        """
        
        if not sql or not sql.strip():
            return False, "SQL query is empty"
        
        sql_upper = sql.upper().strip()
        
        # Check if it starts with SELECT
        if not sql_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
        
        # Check for semicolons (prevent multiple statements)
        if ';' in sql.rstrip(';'):
            return False, "Multiple statements not allowed"
        
        # Check for forbidden keywords
        for keyword in SQLValidator.FORBIDDEN_KEYWORDS:
            # Use word boundary to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                return False, f"Forbidden keyword detected: {keyword}"
        
        # Check for excessive subqueries (max 1 level)
        subquery_count = sql_upper.count('SELECT') - 1
        if subquery_count > 1:
            return False, "Too many nested subqueries (max 1 level allowed)"
        
        # Check if LIMIT exists for non-aggregate queries
        has_aggregate = any(agg in sql_upper for agg in ['COUNT(', 'SUM(', 'AVG(', 'MIN(', 'MAX(', 'GROUP BY'])
        has_limit = 'LIMIT' in sql_upper
        
        if not has_aggregate and not has_limit:
            return False, "Non-aggregate queries must include LIMIT clause"
        
        # Check if using allowed tables only
        from_match = re.search(r'\bFROM\s+(\w+)', sql_upper)
        if from_match:
            table_name = from_match.group(1).lower()
            if table_name not in SQLValidator.ALLOWED_TABLES:
                return False, f"Table '{table_name}' is not allowed"
        
        # Check for JOIN tables
        join_matches = re.findall(r'\bJOIN\s+(\w+)', sql_upper)
        for table_name in join_matches:
            if table_name.lower() not in SQLValidator.ALLOWED_TABLES:
                return False, f"Table '{table_name}' is not allowed in JOIN"
        
        return True, ""
    
    @staticmethod
    def sanitize_limit(sql: str, max_limit: int = 200) -> str:
        """
        Ensure LIMIT doesn't exceed max_limit
        Returns: Modified SQL with capped LIMIT
        """
        
        limit_match = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            current_limit = int(limit_match.group(1))
            if current_limit > max_limit:
                sql = re.sub(
                    r'\bLIMIT\s+\d+',
                    f'LIMIT {max_limit}',
                    sql,
                    flags=re.IGNORECASE
                )
        
        return sql


# Singleton instance
sql_validator = SQLValidator()
