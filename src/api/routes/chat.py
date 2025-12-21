"""
Chat endpoints for Query Creator and Analytics bots.
"""

from fastapi import APIRouter, HTTPException, Depends
import logging

from src.api.models.requests import (
    QueryCreatorRequest,
    AnalyticsRequest,
    ExecuteSQLRequest,
    RefineQueryRequest,
    ValidateSQLRequest,
    UnifiedChatRequest
)
from src.api.models.responses import (
    QueryCreatorResponse,
    AnalyticsResponse,
    QueryExecutionResponse,
    ErrorResponse,
    UnifiedChatResponse
)
from src.api.dependencies import (
    get_query_creator_bot,
    get_analytics_bot,
    get_dremio_client
)
from src.api.services.query_executor import QueryExecutor

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat/query-creator",
    response_model=QueryCreatorResponse,
    summary="Generate SQL from natural language",
    description="Converts a natural language question into a validated SQL query"
)
async def query_creator(
    request: QueryCreatorRequest,
    bot = Depends(get_query_creator_bot)
):
    """
    Generate SQL query from natural language.

    This endpoint uses a fine-tuned LLM to convert natural language questions
    into valid SQL queries for the procurement database.

    Returns:
        QueryCreatorResponse with generated SQL and metadata
    """
    try:
        logger.info(f"Query creator request: {request.message}")

        result = bot.generate_sql(
            user_query=request.message,
            include_explanation=request.include_explanation,
            max_attempts=request.max_attempts
        )

        return QueryCreatorResponse(**result)

    except Exception as e:
        logger.error(f"Error in query_creator: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/chat/analytics",
    response_model=AnalyticsResponse,
    summary="Execute SQL and generate insights",
    description="Executes a SQL query and provides analytical insights using AI"
)
async def analytics(
    request: AnalyticsRequest,
    bot = Depends(get_analytics_bot)
):
    """
    Execute SQL query and generate analytical insights.

    This endpoint executes the provided SQL query, analyzes the results,
    and generates insights, trends, and visualization suggestions.

    Returns:
        AnalyticsResponse with results and insights
    """
    try:
        logger.info(f"Analytics request with SQL: {request.sql[:100]}...")

        # Add user message to query if provided
        user_query = request.message or "Analyze this data"

        result = bot.analyze_query(
            user_query=user_query,
            sql=request.sql,
            include_visualizations=request.include_visualizations
        )

        if not result["success"]:
            return AnalyticsResponse(
                success=False,
                error=result.get("error", "Unknown error")
            )

        # Build response
        response = AnalyticsResponse(
            success=True,
            results=QueryExecutionResponse(**result["results"]),
            insights=result.get("insights"),
            visualizations=result.get("visualizations", []),
            execution_time=result.get("execution_time", 0)
        )

        return response

    except Exception as e:
        logger.error(f"Error in analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/execute-sql",
    response_model=QueryExecutionResponse,
    summary="Execute SQL query directly",
    description="Execute a SQL query without analytics"
)
async def execute_sql(
    request: ExecuteSQLRequest,
    dremio_client = Depends(get_dremio_client)
):
    """
    Execute SQL query directly without generating insights.

    Useful for testing queries or when you only need the raw results.

    Returns:
        QueryExecutionResponse with query results
    """
    try:
        logger.info(f"Direct SQL execution: {request.sql[:100]}...")

        executor = QueryExecutor(dremio_client)

        result = executor.execute(
            sql=request.sql,
            validate=request.validate,
            include_stats=request.include_stats
        )

        return QueryExecutionResponse(**result)

    except Exception as e:
        logger.error(f"Error in execute_sql: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/chat/refine",
    response_model=QueryCreatorResponse,
    summary="Refine existing SQL query",
    description="Refine a SQL query based on user feedback"
)
async def refine_query(
    request: RefineQueryRequest,
    bot = Depends(get_query_creator_bot)
):
    """
    Refine an existing SQL query based on user feedback.

    Takes a previously generated query and user feedback to produce
    an improved version.

    Returns:
        QueryCreatorResponse with refined SQL
    """
    try:
        logger.info(f"Refining query: {request.feedback}")

        result = bot.refine_sql(
            original_query=request.original_query,
            original_sql=request.original_sql,
            feedback=request.feedback
        )

        return QueryCreatorResponse(**result)

    except Exception as e:
        logger.error(f"Error in refine_query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/validate-sql",
    summary="Validate SQL query",
    description="Validate SQL syntax and security without executing"
)
async def validate_sql(
    request: ValidateSQLRequest,
    bot = Depends(get_query_creator_bot)
):
    """
    Validate a SQL query without executing it.

    Checks for:
    - SQL syntax errors
    - Security issues (forbidden keywords)
    - Complexity limits

    Returns:
        Validation results with explanation
    """
    try:
        logger.info("SQL validation request")

        result = bot.validate_user_sql(request.sql)

        return result

    except Exception as e:
        logger.error(f"Error in validate_sql: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post(
    "/chat/ask",
    response_model=UnifiedChatResponse,
    summary="Unified chat endpoint (full flow)",
    description="Natural language question -> SQL generation -> Execution -> AI insights (all in one)"
)
async def unified_chat(
    request: UnifiedChatRequest,
    query_bot = Depends(get_query_creator_bot),
    analytics_bot = Depends(get_analytics_bot)
):
    """
    Unified endpoint that handles the complete flow:
    1. Generate SQL from natural language question
    2. Execute the SQL query on Dremio
    3. Generate AI-powered insights and analysis
    4. Return everything in a single response

    This is the main endpoint for the frontend chatbot interface.

    Returns:
        UnifiedChatResponse with SQL, results, and insights
    """
    import time
    import re
    from src.api.dependencies import get_schema_inspector

    start_time = time.time()
    MAX_RETRIES = 2  # Max retries for schema-related errors

    try:
        logger.info(f"Unified chat request: {request.message}")

        for attempt in range(MAX_RETRIES):
            # Step 1: Generate SQL from natural language
            logger.info(f"Step 1: Generating SQL query (attempt {attempt + 1}/{MAX_RETRIES})...")
            sql_result = query_bot.generate_sql(
                user_query=request.message,
                include_explanation=request.include_explanation,
                max_attempts=request.max_attempts
            )

            if not sql_result["success"]:
                # Failed to generate SQL
                logger.error(f"SQL generation failed: {sql_result.get('error')}")
                return UnifiedChatResponse(
                    success=False,
                    error=_create_user_friendly_error("generate SQL", sql_result.get("error")),
                    hints=sql_result.get("hints", []),
                    execution_time=time.time() - start_time
                )

            sql = sql_result["sql"]
            logger.info(f"SQL generated successfully: {sql[:100]}...")

            # Step 2: Execute SQL and generate insights
            logger.info("Step 2: Executing query and generating insights...")
            analytics_result = analytics_bot.analyze_query(
                user_query=request.message,
                sql=sql,
                include_visualizations=request.include_visualizations
            )

            if not analytics_result["success"]:
                error_msg = analytics_result.get("error", "")

                # Check if it's a column/schema error
                is_schema_error = any(keyword in error_msg.lower() for keyword in
                    ["column", "not found", "table", "does not exist"])

                if is_schema_error and attempt < MAX_RETRIES - 1:
                    # Schema error - refresh schema and retry
                    logger.warning(f"Schema error detected: {error_msg}. Refreshing schema and retrying...")
                    schema_inspector = get_schema_inspector()
                    schema_inspector.refresh_schema(force=True)
                    continue  # Retry with fresh schema

                # Non-schema error or last attempt - return error with helpful message
                logger.error(f"Analytics failed: {error_msg}")

                # Try to extract column name from error
                column_match = re.search(r"Column '(\w+)' not found", error_msg)
                helpful_hints = sql_result.get("hints", [])

                if column_match:
                    missing_column = column_match.group(1)
                    helpful_hints.append(f"The column '{missing_column}' doesn't exist in the database")

                    # Get available columns from schema
                    schema_inspector = get_schema_inspector()
                    table_info = schema_inspector.get_table("minio.gold.unified")
                    if table_info:
                        available_cols = [col.name for col in table_info.columns[:10]]
                        helpful_hints.append(f"Available columns include: {', '.join(available_cols)}")

                return UnifiedChatResponse(
                    success=False,
                    sql=sql,
                    sql_explanation=sql_result.get("explanation"),
                    confidence=sql_result.get("confidence"),
                    error=_create_user_friendly_error("execute the query", error_msg),
                    hints=helpful_hints,
                    execution_time=time.time() - start_time
                )

            # Step 3: Build successful response
            logger.info("Query completed successfully")

            response = UnifiedChatResponse(
                success=True,
                sql=sql,
                sql_explanation=sql_result.get("explanation"),
                confidence=sql_result.get("confidence"),
                results=analytics_result.get("results"),
                insights=analytics_result.get("insights"),
                visualizations=analytics_result.get("visualizations", []),
                hints=sql_result.get("hints", []),
                execution_time=time.time() - start_time
            )

            return response

    except Exception as e:
        logger.error(f"Error in unified_chat: {e}", exc_info=True)
        return UnifiedChatResponse(
            success=False,
            error=_create_user_friendly_error("process your request", str(e)),
            execution_time=time.time() - start_time
        )


def _create_user_friendly_error(action: str, technical_error: str) -> str:
    """
    Convert technical errors to user-friendly messages.

    Args:
        action: What we were trying to do (e.g., "execute the query")
        technical_error: Technical error message

    Returns:
        User-friendly error message
    """
    if "column" in technical_error.lower() and "not found" in technical_error.lower():
        return f"I tried to {action}, but used a column name that doesn't exist in the database. Let me try rephrasing your question with the correct column names."
    elif "table" in technical_error.lower() and "not found" in technical_error.lower():
        return f"I couldn't {action} because the table doesn't exist. Please make sure your data has been loaded into the database."
    elif "connection" in technical_error.lower() or "timeout" in technical_error.lower():
        return f"I couldn't {action} due to a database connection issue. Please try again in a moment."
    elif "permission" in technical_error.lower() or "denied" in technical_error.lower():
        return f"I don't have permission to {action}. Please contact your administrator."
    else:
        # Generic friendly message
        return f"I encountered an error trying to {action}: {technical_error[:200]}"
