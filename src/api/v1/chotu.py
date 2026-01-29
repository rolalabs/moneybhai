from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from src.api.v1.schemas.chotu_schemas import QueryRequest, QueryResponse, ErrorResponse
from src.core.llm import llm_service
from src.utils.query_executor import QueryExecutor
from src.utils.log import setup_logger
from src.core.database import get_read_only_db

router = APIRouter(prefix="/chotu", tags=["chotu"])
logger = setup_logger(__name__)


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def process_query(request: QueryRequest, read_only_db: Session = Depends(get_read_only_db)) -> QueryResponse:
    """
    Process natural language query and return answer based on SQL data
    
    Flow:
    1. Inject system context
    2. LLM Call #1: Question → SQL
    3. SQL Validation
    4. SQL Execution
    5. LLM Call #2: Result → Answer
    """
    
    try:
        # STEP 1: Inject system context
        ist_offset = timedelta(hours=5, minutes=30)
        system_context = {
            "userId": request.user_id,
            "timezone": "Asia/Kolkata",
            "today": (datetime.now(timezone.utc) + ist_offset).strftime("%Y-%m-%d")
        }
        
        logger.info(f"Processing query for user {request.user_id}: {request.message}")
        
        # STEP 2: LLM Call #1 - Question → SQL
        sql_result = llm_service.generate_sql_from_question(
            user_question=request.message,
            system_context=system_context,
            user_id=request.user_id
        )
        
        confidence = sql_result.get("confidence", 0.0)
        generated_sql = sql_result.get("sql")
        
        # Check if confidence is too low
        if confidence < 0.6:
            clarification = sql_result.get("reasoning", "I need more information to answer this question accurately.")
            logger.info(f"Low confidence ({confidence}) for user {request.user_id}, requesting clarification")
            return QueryResponse(
                answer=f"I need some clarification: {clarification}",
                confidence=confidence,
                query=""
            )
        
        # Check if SQL was generated
        if not generated_sql:
            error_msg = sql_result.get("reasoning", "Could not generate a valid SQL query")
            logger.warning(f"No SQL generated for user {request.user_id}: {error_msg}")
            return QueryResponse(
                answer=f"I couldn't understand that query. {error_msg}",
                confidence=0.0,
                query=""
            )
        
        logger.info(f"Generated SQL for user {request.user_id}: {generated_sql}")
        
        # STEP 3: SQL Validation (handled in executor)
        # STEP 4: SQL Execution

        # Singleton instance
        query_executor = QueryExecutor(read_only_db)
        success, results_or_error = query_executor.execute_read_only_query(
            sql=generated_sql,
            user_id=request.user_id
        )
        
        if not success:
            logger.error(f"Query execution failed for user {request.user_id}: {results_or_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query execution failed: {results_or_error}"
            )
        
        sql_results = results_or_error
        
        # Check if no results
        if not sql_results or len(sql_results) == 0:
            logger.info(f"No results found for user {request.user_id}")
            return QueryResponse(
                answer="No data found for this query. Try a different time period or search criteria.",
                confidence=confidence,
                query=generated_sql
            )
        
        logger.info(f"Query returned {len(sql_results)} rows for user {request.user_id}")
        
        # STEP 5: LLM Call #2 - Result → Answer
        answer = llm_service.generate_answer_from_results(
            user_question=request.message,
            sql_query=generated_sql,
            sql_results=sql_results,
            system_context=system_context,
            user_id=request.user_id
        )
        
        logger.info(f"Successfully generated answer for user {request.user_id}")
        
        return QueryResponse(
            answer=answer,
            confidence=confidence,
            query=generated_sql
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error processing query for user {request.user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query"
        )
    finally:
        read_only_db.close()
