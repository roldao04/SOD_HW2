"""
Response models for API endpoints.
Pydantic models for API responses.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class QueryCreatorResponse(BaseModel):
    """Response model for query creator endpoint."""

    success: bool = Field(..., description="Whether SQL generation succeeded")

    sql: Optional[str] = Field(
        default=None,
        description="Generated SQL query"
    )

    explanation: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of the query"
    )

    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the generated SQL"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if generation failed"
    )

    hints: List[str] = Field(
        default_factory=list,
        description="Domain hints and suggestions"
    )

    tables_used: List[str] = Field(
        default_factory=list,
        description="Tables referenced in the query"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "sql": "SELECT source_country, COUNT(*) as tender_count FROM minio.gold.unified GROUP BY source_country ORDER BY tender_count DESC LIMIT 10;",
                "explanation": "This query retrieves data from the unified table grouped by country sorted in descending order limited to 10 results.",
                "confidence": 0.95,
                "hints": ["For 'country', consider using: source_country"],
                "tables_used": ["minio.gold.unified"]
            }
        }


class InsightsResponse(BaseModel):
    """Response model for analytical insights."""

    summary: str = Field(..., description="Brief summary of findings")

    key_insights: List[str] = Field(
        default_factory=list,
        description="Key insights (bullet points)"
    )

    detailed_analysis: str = Field(
        default="",
        description="Detailed analysis text"
    )

    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions"
    )


class VisualizationSuggestion(BaseModel):
    """Model for a single visualization suggestion."""

    type: str = Field(..., description="Visualization type (bar, line, pie, table, etc.)")
    title: str = Field(..., description="Suggested title for the visualization")
    explanation: str = Field(..., description="Why this visualization is appropriate")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration (x_field, y_field, etc.)"
    )


class QueryExecutionResponse(BaseModel):
    """Response model for query execution."""

    success: bool = Field(..., description="Whether execution succeeded")

    data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Query result data"
    )

    columns: List[str] = Field(
        default_factory=list,
        description="Column names"
    )

    row_count: int = Field(default=0, description="Number of rows returned")

    truncated: bool = Field(
        default=False,
        description="Whether results were truncated"
    )

    execution_time: float = Field(..., description="Execution time in seconds")

    sql: str = Field(..., description="Executed SQL query")

    stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Statistical summary of results"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )


class AnalyticsResponse(BaseModel):
    """Response model for analytics endpoint."""

    success: bool = Field(..., description="Whether analysis succeeded")

    results: Optional[QueryExecutionResponse] = Field(
        default=None,
        description="Query execution results"
    )

    insights: Optional[InsightsResponse] = Field(
        default=None,
        description="Analytical insights"
    )

    visualizations: List[VisualizationSuggestion] = Field(
        default_factory=list,
        description="Visualization suggestions"
    )

    execution_time: float = Field(
        default=0.0,
        description="Total execution time in seconds"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if analysis failed"
    )


class TableSchema(BaseModel):
    """Model for table schema information."""

    name: str = Field(..., description="Fully qualified table name")
    schema: str = Field(..., description="Schema name")
    description: Optional[str] = Field(
        default=None,
        description="Table description"
    )
    columns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Column information"
    )
    row_count: Optional[int] = Field(
        default=None,
        description="Approximate number of rows"
    )


class SchemaResponse(BaseModel):
    """Response model for schema endpoints."""

    success: bool = Field(..., description="Whether request succeeded")

    table_count: int = Field(default=0, description="Number of tables")

    tables: List[TableSchema] = Field(
        default_factory=list,
        description="Table information"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if request failed"
    )


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Overall status (ok, error)")

    api_version: str = Field(..., description="API version")

    services: Dict[str, bool] = Field(
        ...,
        description="Service availability status"
    )

    models: Dict[str, str] = Field(
        ...,
        description="Configured models"
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    success: bool = Field(default=False, description="Always false for errors")

    error: str = Field(..., description="Error message")

    error_type: str = Field(
        default="error",
        description="Error type/category"
    )

    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Error timestamp"
    )
