# Chotu Chat Agent - Example Queries

## Overview
Chotu is a production-grade chat agent that answers questions about your financial data using natural language processing and SQL queries.

## API Endpoint

**POST** `/chotu/query`

### Request
```json
{
  "userId": "user-uuid-here",
  "message": "How much did I spend last month?"
}
```

### Response
```json
{
  "answer": "Based on your transactions, you spent ₹45,320 last month.",
  "confidence": 0.92
}
```

## Example Queries

### Transaction Queries

#### 1. Total Spending in a Time Period
**Question:** "How much did I spend last month?"
**Expected SQL:** 
```sql
SELECT SUM(amount) as total_spent 
FROM transactions 
WHERE userId = 'user-id' 
  AND date_time >= '2026-01-01' 
  AND date_time < '2026-02-01'
  AND is_include_analytics = true
```

#### 2. Spending by Payment Mode
**Question:** "How much did I spend using UPI this year?"
**Expected SQL:**
```sql
SELECT SUM(amount) as total_upi_spending 
FROM transactions 
WHERE userId = 'user-id' 
  AND mode = 'UPI'
  AND date_time >= '2026-01-01'
  AND is_include_analytics = true
```

#### 3. Recent Transactions
**Question:** "Show me my last 10 transactions"
**Expected SQL:**
```sql
SELECT amount, destination, mode, date_time 
FROM transactions 
WHERE userId = 'user-id'
  AND is_include_analytics = true
ORDER BY date_time DESC 
LIMIT 10
```

### Order Queries

#### 4. Amazon Orders This Year
**Question:** "How many Amazon orders did I make this year?"
**Expected SQL:**
```sql
SELECT COUNT(*) as order_count, SUM(total) as total_amount
FROM orders
WHERE vendor = 'Amazon'
  AND order_date >= '2026-01-01'
```

#### 5. Total Order Value
**Question:** "What's my total spending on online orders last month?"
**Expected SQL:**
```sql
SELECT SUM(total) as total_order_spending
FROM orders
WHERE order_date >= '2026-01-01'
  AND order_date < '2026-02-01'
```

#### 6. Recent Orders
**Question:** "Show me my recent orders"
**Expected SQL:**
```sql
SELECT vendor, order_date, total
FROM orders
ORDER BY order_date DESC
LIMIT 20
```

### Comparison Queries

#### 7. UPI vs Card Usage
**Question:** "Compare my UPI and card spending this month"
**Expected SQL:**
```sql
SELECT 
  mode,
  SUM(amount) as total_amount,
  COUNT(*) as transaction_count
FROM transactions
WHERE userId = 'user-id'
  AND date_time >= '2026-01-01'
  AND mode IN ('UPI', 'Card')
  AND is_include_analytics = true
GROUP BY mode
```

#### 8. Top Destinations
**Question:** "Where did I spend the most money last month?"
**Expected SQL:**
```sql
SELECT 
  destination,
  SUM(amount) as total_spent
FROM transactions
WHERE userId = 'user-id'
  AND date_time >= '2026-01-01'
  AND date_time < '2026-02-01'
  AND is_include_analytics = true
GROUP BY destination
ORDER BY total_spent DESC
LIMIT 20
```

### Complex Queries

#### 9. Monthly Spending Trend
**Question:** "Show my spending for each month this year"
**Expected SQL:**
```sql
SELECT 
  DATE_TRUNC('month', date_time) as month,
  SUM(amount) as total_spent
FROM transactions
WHERE userId = 'user-id'
  AND date_time >= '2026-01-01'
  AND is_include_analytics = true
GROUP BY DATE_TRUNC('month', date_time)
ORDER BY month
```

#### 10. Order Items by Category
**Question:** "What types of items did I order most?"
**Expected SQL:**
```sql
SELECT 
  item_type,
  COUNT(*) as item_count,
  SUM(total) as total_spent
FROM order_items
GROUP BY item_type
ORDER BY total_spent DESC
LIMIT 20
```

## Testing with cURL

### Example 1: Basic Query
```bash
curl -X POST http://localhost:8000/chotu/query \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "your-user-id",
    "message": "How much did I spend last month?"
  }'
```

### Example 2: Amazon Orders
```bash
curl -X POST http://localhost:8000/chotu/query \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "your-user-id",
    "message": "Show me all Amazon orders this year"
  }'
```

### Example 3: Payment Mode Comparison
```bash
curl -X POST http://localhost:8000/chotu/query \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "your-user-id",
    "message": "Compare my UPI and card spending"
  }'
```

## Testing with Python

```python
import requests

API_URL = "http://localhost:8000/chotu/query"
USER_ID = "your-user-id"

def test_query(message: str):
    response = requests.post(
        API_URL,
        json={
            "userId": USER_ID,
            "message": message
        }
    )
    result = response.json()
    print(f"Question: {message}")
    print(f"Answer: {result['answer']}")
    print(f"Confidence: {result['confidence']}")
    print("-" * 50)

# Run tests
test_query("How much did I spend last month?")
test_query("Show me my Amazon orders")
test_query("What did I spend on UPI transactions?")
test_query("Compare my spending this month vs last month")
```

## Confidence Levels

- **0.9-1.0**: Clear, unambiguous question - high confidence answer
- **0.7-0.8**: Minor ambiguity but query is answerable
- **0.6-0.7**: Some ambiguity, answer provided with caveats
- **< 0.6**: Too ambiguous - clarification requested

## Error Handling

### Low Confidence
If confidence < 0.6, the system returns a clarification request:
```json
{
  "answer": "I need some clarification: Please specify the time period you want to analyze.",
  "confidence": 0.5
}
```

### Invalid SQL
If the generated SQL fails validation:
```json
{
  "error": "Query execution failed",
  "detail": "Invalid SQL: Only SELECT queries are allowed"
}
```

### No Data Found
If query returns no results:
```json
{
  "answer": "No data found for this query. Try a different time period or search criteria.",
  "confidence": 0.85
}
```

## LangSmith Tracing

All LLM calls are traced in LangSmith with:
- **Tags**: `step:sql_generation`, `step:answer_generation`, `chotu`
- **Metadata**: `userId`, `confidence`
- **Project**: MoneyBhai

View traces at: https://smith.langchain.com/

## Safety Features

1. **Read-Only Queries**: Only SELECT statements allowed
2. **SQL Validation**: Validates all queries before execution
3. **Timeout Protection**: 3-second query timeout
4. **Row Limits**: Maximum 200 rows returned
5. **Table Restrictions**: Only allowed tables can be queried
6. **User Isolation**: Queries always filtered by userId
7. **No Arbitrary Execution**: LLM cannot execute code

## Database Schema

### Transactions Table
- `amount`: Transaction amount
- `mode`: Payment mode (UPI, Card, etc.)
- `destination`: Where money was sent
- `date_time`: UTC timestamp
- `userId`: User identifier
- `is_include_analytics`: Include in analytics

### Orders Table
- `vendor`: Vendor name (Amazon, Flipkart, etc.)
- `order_date`: UTC timestamp
- `total`: Total order amount (includes discounts)
- `account_id`: Account identifier

### Order Items Table
- `name`: Item name
- `item_type`: Category of item
- `quantity`: Quantity ordered
- `total`: Total item price
- `order_id`: Reference to orders table
