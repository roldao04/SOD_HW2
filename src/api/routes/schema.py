"""
Schema endpoints for database structure information.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
import logging

from src.api.models.responses import SchemaResponse, TableSchema
from src.api.dependencies import get_schema_inspector

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/schema",
    response_model=SchemaResponse,
    summary="Get database schema information",
    description="Returns information about all available tables and their columns"
)
async def get_schema(
    refresh: bool = Query(
        default=False,
        description="Force refresh schema cache"
    ),
    inspector = Depends(get_schema_inspector)
):
    """
    Get comprehensive database schema information.

    Returns all available tables with their columns, types, and sample values.
    Schema information is cached for performance.

    Args:
        refresh: If True, force refresh the schema cache

    Returns:
        SchemaResponse with all table information
    """
    try:
        logger.info(f"Schema request (refresh={refresh})")

        # Refresh if requested
        if refresh:
            inspector.refresh_schema(force=True)

        # Get all tables
        all_tables = inspector.get_all_tables()

        # Format response
        tables_data = []
        for table in all_tables:
            table_data = {
                "name": table.full_name,
                "schema": table.schema,
                "description": table.description,
                "columns": [
                    {
                        "name": col.name,
                        "type": col.data_type,
                        "nullable": col.nullable,
                        "sample_values": col.sample_values
                    }
                    for col in table.columns
                ],
                "row_count": table.row_count
            }
            tables_data.append(TableSchema(**table_data))

        return SchemaResponse(
            success=True,
            table_count=len(tables_data),
            tables=tables_data
        )

    except Exception as e:
        logger.error(f"Error in get_schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/schema/{table_name:path}",
    response_model=TableSchema,
    summary="Get specific table schema",
    description="Returns detailed schema information for a specific table"
)
async def get_table_schema(
    table_name: str,
    inspector = Depends(get_schema_inspector)
):
    """
    Get schema information for a specific table.

    Args:
        table_name: Fully qualified table name (e.g., 'minio.gold.unified')
                   or just the table name (e.g., 'unified')

    Returns:
        TableSchema with detailed table information
    """
    try:
        logger.info(f"Table schema request: {table_name}")

        # Get table information
        table = inspector.get_table(table_name)

        if not table:
            raise HTTPException(
                status_code=404,
                detail=f"Table not found: {table_name}"
            )

        # Format response
        table_data = {
            "name": table.full_name,
            "schema": table.schema,
            "description": table.description,
            "columns": [
                {
                    "name": col.name,
                    "type": col.data_type,
                    "nullable": col.nullable,
                    "sample_values": col.sample_values
                }
                for col in table.columns
            ],
            "row_count": table.row_count
        }

        return TableSchema(**table_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_table_schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/schema/search",
    response_model=SchemaResponse,
    summary="Search for relevant tables",
    description="Find tables relevant to a natural language query"
)
async def search_schema(
    query: str = Query(
        ...,
        description="Natural language query to find relevant tables",
        min_length=3,
        max_length=500
    ),
    inspector = Depends(get_schema_inspector)
):
    """
    Search for tables relevant to a natural language query.

    Uses keyword matching to identify tables that might be useful
    for answering the user's question.

    Args:
        query: Natural language query

    Returns:
        SchemaResponse with relevant tables
    """
    try:
        logger.info(f"Schema search: {query}")

        # Get relevant tables
        relevant_tables = inspector.get_relevant_tables(query)

        # Format response
        tables_data = []
        for table in relevant_tables:
            table_data = {
                "name": table.full_name,
                "schema": table.schema,
                "description": table.description,
                "columns": [
                    {
                        "name": col.name,
                        "type": col.data_type,
                        "nullable": col.nullable,
                        "sample_values": col.sample_values
                    }
                    for col in table.columns
                ],
                "row_count": table.row_count
            }
            tables_data.append(TableSchema(**table_data))

        return SchemaResponse(
            success=True,
            table_count=len(tables_data),
            tables=tables_data
        )

    except Exception as e:
        logger.error(f"Error in search_schema: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
