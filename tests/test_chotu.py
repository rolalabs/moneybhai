"""
Test script for Chotu chat agent endpoint
Run with: python -m pytest test_chotu.py -v
"""

import pytest
from src.utils.sql_validator import sql_validator


class TestSQLValidator:
    """Test SQL validation logic"""
    
    def test_valid_select_query(self):
        """Test valid SELECT query"""
        sql = "SELECT amount, date_time FROM transactions WHERE userId = 'test' LIMIT 10"
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is True
        assert error == ""
    
    def test_rejects_insert(self):
        """Test rejection of INSERT query"""
        sql = "INSERT INTO transactions (id, amount) VALUES ('1', 100)"
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is False
        assert "SELECT" in error
    
    def test_rejects_update(self):
        """Test rejection of UPDATE query"""
        sql = "UPDATE transactions SET amount = 100 WHERE id = '1'"
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is False
    
    def test_rejects_delete(self):
        """Test rejection of DELETE query"""
        sql = "DELETE FROM transactions WHERE id = '1'"
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is False
    
    def test_rejects_multiple_statements(self):
        """Test rejection of multiple statements"""
        sql = "SELECT * FROM transactions; DROP TABLE transactions;"
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is False
        assert "Multiple statements" in error
    
    def test_requires_limit_for_list_queries(self):
        """Test that non-aggregate queries require LIMIT"""
        sql = "SELECT * FROM transactions WHERE userId = 'test'"
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is False
        assert "LIMIT" in error
    
    def test_aggregate_query_without_limit(self):
        """Test that aggregate queries don't require LIMIT"""
        sql = "SELECT COUNT(*) FROM transactions WHERE userId = 'test'"
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is True
    
    def test_rejects_too_many_subqueries(self):
        """Test rejection of deeply nested subqueries"""
        sql = """
        SELECT * FROM transactions 
        WHERE id IN (
            SELECT id FROM (
                SELECT id FROM orders
            )
        ) LIMIT 10
        """
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is False
        assert "subqueries" in error.lower()
    
    def test_rejects_invalid_table(self):
        """Test rejection of queries on disallowed tables"""
        sql = "SELECT * FROM users LIMIT 10"
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is False
        assert "not allowed" in error.lower()
    
    def test_allows_valid_join(self):
        """Test valid JOIN query"""
        sql = """
        SELECT t.amount, o.vendor 
        FROM transactions t 
        JOIN orders o ON t.emailId = o.message_id 
        WHERE t.userId = 'test' 
        LIMIT 10
        """
        is_valid, error = sql_validator.validate_query(sql)
        assert is_valid is True
    
    def test_sanitize_limit_caps_excessive_limit(self):
        """Test that sanitize_limit caps excessive limits"""
        sql = "SELECT * FROM transactions WHERE userId = 'test' LIMIT 1000"
        sanitized = sql_validator.sanitize_limit(sql, max_limit=200)
        assert "LIMIT 200" in sanitized
        assert "LIMIT 1000" not in sanitized
    
    def test_sanitize_limit_preserves_valid_limit(self):
        """Test that sanitize_limit preserves valid limits"""
        sql = "SELECT * FROM transactions WHERE userId = 'test' LIMIT 50"
        sanitized = sql_validator.sanitize_limit(sql, max_limit=200)
        assert "LIMIT 50" in sanitized


# Example integration test (requires running server)
class TestChouIntegration:
    """Integration tests - requires server to be running"""
    
    @pytest.mark.skip(reason="Requires server and database")
    def test_basic_query(self):
        """Test basic query through API"""
        import requests
        
        response = requests.post(
            "http://localhost:8000/chotu/query",
            json={
                "userId": "test-user-id",
                "message": "How much did I spend last month?"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "confidence" in data
        assert 0 <= data["confidence"] <= 1


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
