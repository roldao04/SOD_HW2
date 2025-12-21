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
    ValidateSQLRequest
)
from src.api.models.responses import (
    QueryCreatorResponse,
    AnalyticsResponse,
    QueryExecutionResponse,
    ErrorResponse
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
