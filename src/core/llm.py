import json
from typing import Dict, Any
from langsmith import traceable
from src.core.connectors import VERTEXT_CLIENT
from src.core.environment import ENV_SETTINGS


class LLMService:
    """Service for interacting with LLM with LangSmith tracing"""
    
    def __init__(self):
        self.client = VERTEXT_CLIENT
        self.model_name = "gemini-2.5-flash"
    
    @traceable(
        name="llm_generate_sql",
        tags=["step:sql_generation", "chotu"],
        project_name=ENV_SETTINGS.LANGSMITH_PROJECT
    )
    def generate_sql_from_question(
        self,
        user_question: str,
        system_context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Convert user question to SQL query
        Returns: {"sql": "SELECT ...", "confidence": 0.0-1.0}
        """
        
        prompt = self._build_sql_generation_prompt(user_question, system_context)
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        )
        
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            return {
                "sql": None,
                "confidence": 0.0,
                "error": "Failed to parse LLM response"
            }
    
    @traceable(
        name="llm_generate_answer",
        tags=["step:answer_generation", "chotu"],
        project_name=ENV_SETTINGS.LANGSMITH_PROJECT
    )
    def generate_answer_from_results(
        self,
        user_question: str,
        sql_query: str,
        sql_results: list,
        system_context: Dict[str, Any],
        user_id: str
    ) -> str:
        """
        Generate natural language answer from SQL results
        Returns: Natural language explanation
        """
        
        prompt = self._build_answer_generation_prompt(
            user_question,
            sql_query,
            sql_results,
            system_context
        )
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "temperature": 0.3
            }
        )
        
        return response.text.strip()
    
    def _build_sql_generation_prompt(
        self,
        user_question: str,
        system_context: Dict[str, Any]
    ) -> str:
        """Build prompt for SQL generation"""
        
        schema_info = """
        Database Schema:

        Table: transactions
        - id (String, PK)
        - amount (Float) - transaction amount
        - transaction_type (String) - type of transaction (Enum: 'debit', 'credit')
        - 'debit' = money spent / outgoing
        - 'credit' = money received / incoming
        - source_identifier (String) - source of transaction
        - destination (String) - destination of transaction
        - mode (String) - payment mode (UPI, Card, etc)
        - date_time (DateTime) - UTC timestamp
        - email_sender (String) - email sender
        - email_id (String) - email ID
        - reference_number (String) - transaction reference
        - user_id (UUID, FK) - user ID
        - account_id (UUID, FK) - account ID
        - is_include_analytics (Boolean) - include in analytics

        Table: orders
        - id (UUID, PK)
        - order_id (String, unique) - vendor order ID
        - message_id (String) - email message ID
        - vendor (String) - vendor name (Amazon, Flipkart, etc)
        - order_date (DateTime) - UTC timestamp
        - currency (String) - currency code
        - sub_total (Float) - subtotal amount
        - total (Float) - total amount including discounts
        - account_id (UUID, FK) - account ID
        - created_at (DateTime) - record creation time

        Table: order_items
        - id (UUID, PK)
        - order_id (UUID, FK) - references orders.id
        - account_id (UUID, FK) - account ID
        - name (String) - item name
        - item_type (String) - type of item
        - quantity (Float) - quantity ordered
        - unit_type (String) - unit measurement
        - unit_price (Float) - price per unit
        - total (Float) - total price for item
        """

        prompt = f"""You are a SQL query generator for a financial transaction database.

        {schema_info}

        Context:
        - User ID: {system_context['userId']}
        - Timezone: {system_context['timezone']}
        - Today's Date: {system_context['today']}

        BUSINESS DEFINITIONS:
        - "spend", "spending", "expense", "spent", "paid" → transaction_type = 'debit'
        - "income", "earned", "received", "credited" → transaction_type = 'credit'
        - If user asks for "total spendings" or "how much did I spend", always filter transaction_type = 'debit'
        - If user asks for "transactions" without qualifiers, include both debit and credit

        STRICT RULES:
        1. Generate SELECT queries ONLY
        2. Use only the tables and columns defined above
        3. Always filter by userId = '{system_context['userId']}' in transactions table
        4. Always filter by account_id in orders/order_items (accounts belong to user)
        5. For date filters, use DATE() function or date_time/order_date columns
        6. Add LIMIT 20 for list queries (non-aggregate)
        7. Use proper SQL syntax for PostgreSQL
        8. If time period is mentioned (last month, this year), calculate dates
        9. Total amounts in orders.total already include discounts
        10. All dates are stored in UTC
        11. For spending/expenditure queries, ALWAYS filter by transaction_type = 'debit'
        12. For income/credit queries, filter by transaction_type = 'credit'
        13. transaction_type can ONLY be 'debit' or 'credit'. Never invent other values.

        User Question: {user_question}

        Generate a SQL query and assign confidence:
        - 0.9-1.0: Clear, unambiguous question
        - 0.7-0.8: Minor ambiguity but answerable
        - 0.5-0.6: Significant ambiguity or missing info
        - < 0.5: Cannot generate reliable query

        Respond ONLY with valid JSON:
        {{
        "sql": "SELECT ... FROM ... WHERE ...",
        "confidence": 0.85,
        "reasoning": "Brief explanation of query logic"
        }}

        If confidence < 0.6, set sql to null and explain what information is needed.
        """
        
        return prompt
    
    def _build_answer_generation_prompt(
        self,
        user_question: str,
        sql_query: str,
        sql_results: list,
        system_context: Dict[str, Any]
    ) -> str:
        """Build prompt for answer generation"""
        
        results_summary = f"{len(sql_results)} rows returned"
        if len(sql_results) <= 10:
            results_str = json.dumps(sql_results, indent=2, default=str)
        else:
            results_str = json.dumps(sql_results[:10], indent=2, default=str) + f"\n... ({len(sql_results) - 10} more rows)"
        
        prompt = f"""You are a financial assistant explaining query results to a user.

User Question: {user_question}

SQL Query Executed:
{sql_query}

Results ({results_summary}):
{results_str}

Context:
- Timezone: {system_context['timezone']}

STRICT RULES:
1. Provide a short, factual answer (2-4 sentences)
2. Do NOT show SQL queries to the user
3. Do NOT show raw data rows
4. Do NOT calculate or guess numbers - use only the data provided
5. If results show totals, state them clearly with currency
6. If no results, say "No data found for this query"
7. If results are incomplete, mention it briefly
8. Use natural language, be conversational
9. Always append ₹ to the amounts
10. Currency will always be INR (symbol: ₹)

Generate a natural language answer that directly addresses the user's question.
"""
        
        return prompt


# Singleton instance
llm_service = LLMService()