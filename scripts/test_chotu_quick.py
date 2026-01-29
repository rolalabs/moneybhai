"""
Quick test script for Chotu Chat Agent
Usage: python scripts/test_chotu_quick.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.sql_validator import sql_validator


def test_sql_validation():
    """Test SQL validation logic"""
    print("🧪 Testing SQL Validation...\n")
    
    test_cases = [
        # Valid queries
        ("SELECT amount FROM transactions WHERE userId = 'test' LIMIT 10", True),
        ("SELECT COUNT(*) FROM transactions WHERE userId = 'test'", True),
        ("SELECT SUM(amount) FROM transactions GROUP BY mode", True),
        
        # Invalid queries
        ("INSERT INTO transactions VALUES (1, 100)", False),
        ("UPDATE transactions SET amount = 100", False),
        ("DELETE FROM transactions WHERE id = '1'", False),
        ("SELECT * FROM transactions; DROP TABLE users;", False),
        ("SELECT * FROM transactions WHERE userId = 'test'", False),  # No LIMIT
        ("SELECT * FROM users LIMIT 10", False),  # Invalid table
    ]
    
    passed = 0
    failed = 0
    
    for sql, should_pass in test_cases:
        is_valid, error = sql_validator.validate_query(sql)
        
        if is_valid == should_pass:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"
        
        print(f"{status}: {sql[:60]}...")
        if error:
            print(f"   Error: {error}")
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_sql_sanitization():
    """Test SQL limit sanitization"""
    print("\n🧪 Testing SQL Sanitization...\n")
    
    sql = "SELECT * FROM transactions WHERE userId = 'test' LIMIT 1000"
    sanitized = sql_validator.sanitize_limit(sql, max_limit=200)
    
    if "LIMIT 200" in sanitized:
        print("✅ PASS: Excessive limit capped to 200")
        return True
    else:
        print("❌ FAIL: Limit not properly sanitized")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Chotu Chat Agent - Quick Tests")
    print("=" * 60)
    print()
    
    validation_ok = test_sql_validation()
    sanitization_ok = test_sql_sanitization()
    
    print("\n" + "=" * 60)
    if validation_ok and sanitization_ok:
        print("✅ All tests passed!")
        print("\nYou can now:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Start the server: python main.py")
        print("3. Test the API endpoint")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
