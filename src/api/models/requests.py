"""
Request models for API endpoints.
Pydantic models for validating incoming requests.
"""

from pydantic import BaseModel, Field
from typing import Optional


class QueryCreatorRequest(BaseModel):
    """Request model for query creator endpoint."""

    message: str = Field(
        ...,
        description="Natural language question to convert to SQL",
        min_length=3,
        max_length=500,
        examples=["Show me the top 10 countries by number of tenders"]
    )

    include_explanation: bool = Field(
        default=True,
        description="Include human-readable explanation of the query"
    )

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum attempts to generate valid SQL"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are the total contract values by country for 2025?",
                "include_explanation": True,
                "max_attempts": 3
            }
        }


class AnalyticsRequest(BaseModel):
    """Request model for analytics endpoint."""

    sql: str = Field(
        ...,
        description="SQL query to execute and analyze",
        min_length=10,
        max_length=5000
    )

    message: Optional[str] = Field(
        default=None,
        description="Optional context or specific analysis request",
        max_length=500
    )

    include_visualizations: bool = Field(
        default=True,
        description="Include visualization suggestions"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT source_country, COUNT(*) as tender_count FROM minio.gold.unified GROUP BY source_country ORDER BY tender_count DESC LIMIT 10;",
                "message": "Focus on trends and anomalies",
                "include_visualizations": True
            }
        }


class ExecuteSQLRequest(BaseModel):
    """Request model for direct SQL execution."""

    sql: str = Field(
        ...,
        description="SQL query to execute",
        min_length=10,
        max_length=5000
    )

    validate: bool = Field(
        default=True,
        description="Validate SQL before execution"
    )

    include_stats: bool = Field(
        default=True,
        description="Include statistical summary of results"
    )

    max_rows: Optional[int] = Field(
        default=None,
        ge=1,
        le=10000,
        description="Maximum rows to return"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT * FROM minio.gold.unified LIMIT 100;",
                "validate": True,
                "include_stats": True
            }
        }


class RefineQueryRequest(BaseModel):
    """Request model for refining SQL queries."""

    original_query: str = Field(
        ...,
        description="Original natural language question",
        min_length=3,
        max_length=500
    )

    original_sql: str = Field(
        ...,
        description="Previously generated SQL",
        min_length=10,
        max_length=5000
    )

    feedback: str = Field(
        ...,
        description="User feedback or refinement request",
        min_length=3,
        max_length=500
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "Show me tenders from Portugal",
                "original_sql": "SELECT * FROM minio.gold.unified WHERE source_country = 'PT';",
                "feedback": "Only show tenders from the last month"
            }
        }


class ValidateSQLRequest(BaseModel):
    """Request model for SQL validation."""

    sql: str = Field(
        ...,
        description="SQL query to validate",
        min_length=10,
        max_length=5000
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT source_country, COUNT(*) FROM minio.gold.unified GROUP BY source_country;"
            }
        }


class UnifiedChatRequest(BaseModel):
    """Request model for unified chat endpoint (full flow)."""

    message: str = Field(
        ...,
        description="Natural language question",
        min_length=3,
        max_length=500,
        examples=["What are the top 10 countries by tender count?"]
    )

    include_explanation: bool = Field(
        default=True,
        description="Include SQL explanation in response"
    )

    include_visualizations: bool = Field(
        default=True,
        description="Include visualization suggestions"
    )

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum SQL generation attempts"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are the total contract values by country?",
                "include_explanation": True,
                "include_visualizations": True,
                "max_attempts": 3
            }
        }
