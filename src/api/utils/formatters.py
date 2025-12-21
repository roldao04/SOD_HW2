"""
Result Formatters - Format data for API responses.
Handles JSON serialization, data transformation, and formatting.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal
import pandas as pd


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling special types."""

    def default(self, obj):
        """Handle special object types for JSON serialization."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if pd.isna(obj):
            return None
        return super().default(obj)


def format_query_results(
    results: Dict[str, Any],
    format_type: str = "json"
) -> Dict[str, Any]:
    """
    Format query results for API response.

    Args:
        results: Raw query results from executor
        format_type: Output format (json, csv, table)

    Returns:
        Formatted results dictionary
    """
    if format_type == "json":
        return _format_as_json(results)
    elif format_type == "csv":
        return _format_as_csv(results)
    elif format_type == "table":
        return _format_as_table(results)
    else:
        return results


def _format_as_json(results: Dict[str, Any]) -> Dict[str, Any]:
    """Format results as JSON-serializable dictionary."""
    # Already in correct format, just ensure serialization
    return {
        "success": results.get("success", False),
        "data": results.get("data", []),
        "columns": results.get("columns", []),
        "row_count": results.get("row_count", 0),
        "execution_time": results.get("execution_time", 0),
        "truncated": results.get("truncated", False),
        "stats": results.get("stats", {})
    }


def _format_as_csv(results: Dict[str, Any]) -> Dict[str, Any]:
    """Format results as CSV string."""
    if not results.get("data"):
        return {
            "success": results.get("success", False),
            "csv": "",
            "row_count": 0
        }

    df = pd.DataFrame(results["data"])
    csv_string = df.to_csv(index=False)

    return {
        "success": results.get("success", False),
        "csv": csv_string,
        "row_count": len(df),
        "columns": list(df.columns)
    }


def _format_as_table(results: Dict[str, Any]) -> Dict[str, Any]:
    """Format results as ASCII table string."""
    if not results.get("data"):
        return {
            "success": results.get("success", False),
            "table": "No data",
            "row_count": 0
        }

    df = pd.DataFrame(results["data"])
    table_string = df.to_string(index=False, max_rows=50)

    return {
        "success": results.get("success", False),
        "table": table_string,
        "row_count": len(df),
        "columns": list(df.columns)
    }


def format_insights(insights: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format analytical insights for API response.

    Args:
        insights: Raw insights from analytics bot

    Returns:
        Formatted insights dictionary
    """
    return {
        "summary": insights.get("summary", ""),
        "key_insights": insights.get("key_insights", []),
        "detailed_analysis": insights.get("detailed_analysis", ""),
        "follow_up_questions": insights.get("follow_up_questions", []),
        "raw_response": insights.get("raw_response", "")
    }


def format_error_response(
    error: str,
    error_type: str = "error",
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format error response.

    Args:
        error: Error message
        error_type: Type of error
        details: Additional error details

    Returns:
        Formatted error dictionary
    """
    response = {
        "success": False,
        "error": error,
        "error_type": error_type,
        "timestamp": datetime.now().isoformat()
    }

    if details:
        response["details"] = details

    return response


def format_schema_info(tables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format schema information for API response.

    Args:
        tables: List of table information dictionaries

    Returns:
        Formatted schema dictionary
    """
    return {
        "success": True,
        "table_count": len(tables),
        "tables": [
            {
                "name": table.get("name", ""),
                "schema": table.get("schema", ""),
                "description": table.get("description", ""),
                "columns": table.get("columns", []),
                "row_count": table.get("row_count")
            }
            for table in tables
        ]
    }


def truncate_large_response(
    data: List[Dict[str, Any]],
    max_rows: int = 1000
) -> tuple[List[Dict[str, Any]], bool]:
    """
    Truncate large result sets.

    Args:
        data: Result data
        max_rows: Maximum rows to return

    Returns:
        Tuple of (truncated_data, was_truncated)
    """
    if len(data) <= max_rows:
        return data, False

    return data[:max_rows], True


def summarize_large_dataset(
    data: List[Dict[str, Any]],
    threshold: int = 100
) -> Dict[str, Any]:
    """
    Create summary for large datasets instead of returning all data.

    Args:
        data: Full dataset
        threshold: Row threshold for summarization

    Returns:
        Summary dictionary
    """
    if len(data) < threshold:
        return {
            "full_data": data,
            "is_summary": False
        }

    # Create summary
    df = pd.DataFrame(data)

    summary = {
        "is_summary": True,
        "total_rows": len(df),
        "sample_rows": data[:20],  # First 20 rows
        "summary_stats": {},
        "unique_counts": {}
    }

    # Add statistics for numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        summary["summary_stats"][col] = {
            "min": float(df[col].min()),
            "max": float(df[col].max()),
            "mean": float(df[col].mean()),
            "median": float(df[col].median())
        }

    # Add unique counts for categorical columns
    categorical_cols = df.select_dtypes(include=['object', 'string']).columns
    for col in categorical_cols:
        summary["unique_counts"][col] = int(df[col].nunique())

    return summary


def format_visualization_suggestions(
    visualizations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Format visualization suggestions for frontend.

    Args:
        visualizations: List of visualization suggestions

    Returns:
        Formatted visualization list
    """
    formatted = []

    for viz in visualizations:
        formatted_viz = {
            "type": viz.get("type", "table"),
            "title": viz.get("title", ""),
            "explanation": viz.get("explanation", ""),
            "config": {}
        }

        # Add configuration based on type
        if "x_field" in viz:
            formatted_viz["config"]["x_field"] = viz["x_field"]
        if "y_field" in viz:
            formatted_viz["config"]["y_field"] = viz["y_field"]
        if "color_field" in viz:
            formatted_viz["config"]["color_field"] = viz["color_field"]

        formatted.append(formatted_viz)

    return formatted


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Safely serialize object to JSON string.

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments for json.dumps

    Returns:
        JSON string
    """
    return json.dumps(obj, cls=JSONEncoder, **kwargs)


def format_api_response(
    success: bool,
    data: Optional[Any] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Standard API response formatter.

    Args:
        success: Whether the operation succeeded
        data: Response data
        error: Error message if failed
        metadata: Additional metadata

    Returns:
        Formatted API response
    """
    response = {
        "success": success,
        "timestamp": datetime.now().isoformat()
    }

    if data is not None:
        response["data"] = data

    if error:
        response["error"] = error

    if metadata:
        response["metadata"] = metadata

    return response
