"""
Query Executor Service - Executes SQL queries on Dremio.
Wraps Dremio client with additional features like caching and error handling.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime

from src.api.services.dremio_client import DremioClient
from src.api.utils.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


class QueryExecutor:
    """
    Executes validated SQL queries and returns formatted results.
    """

    def __init__(self, dremio_client: DremioClient):
        """
        Initialize query executor.

        Args:
            dremio_client: DremioClient instance
        """
        self.dremio = dremio_client
        self.validator = SQLValidator()

        logger.info("Query Executor initialized")

    def execute(
        self,
        sql: str,
        validate: bool = True,
        include_stats: bool = True
    ) -> Dict[str, Any]:
        """
        Execute SQL query and return results with metadata.

        Args:
            sql: SQL query to execute
            validate: Whether to validate SQL before execution
            include_stats: Include statistical summary of results

        Returns:
            Dictionary with results and metadata
        """
        logger.info("Executing query...")
        start_time = datetime.now()

        try:
            # Validate if requested
            if validate:
                is_valid, error_msg = self.validator.validate(sql)
                if not is_valid:
                    logger.warning(f"SQL validation failed: {error_msg}")
                    return {
                        "success": False,
                        "error": f"Invalid SQL: {error_msg}",
                        "sql": sql
                    }

            # Execute query via Dremio
            result = self.dremio.execute_query(sql)

            if not result["success"]:
                logger.error(f"Query execution failed: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "sql": sql,
                    "execution_time": result.get("execution_time", 0)
                }

            # Build response
            response = {
                "success": True,
                "data": result["data"],
                "columns": result["columns"],
                "row_count": result["row_count"],
                "truncated": result.get("truncated", False),
                "execution_time": result["execution_time"],
                "sql": sql
            }

            # Add statistical summary if requested
            if include_stats and result["data"]:
                response["stats"] = self._generate_stats(result["data"], result["columns"])

            logger.info(f"Query executed successfully: {result['row_count']} rows in {result['execution_time']:.2f}s")
            return response

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error executing query: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "sql": sql,
                "execution_time": execution_time
            }

    def _generate_stats(self, data: list, columns: list) -> Dict[str, Any]:
        """
        Generate statistical summary of query results.

        Args:
            data: Query result data (list of dicts)
            columns: Column names

        Returns:
            Dictionary with statistical summary
        """
        try:
            if not data:
                return {"row_count": 0}

            df = pd.DataFrame(data)

            stats = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": {}
            }

            # Generate stats for each column
            for col in df.columns:
                col_stats = {
                    "type": str(df[col].dtype),
                    "null_count": int(df[col].isna().sum()),
                    "null_percentage": float(df[col].isna().sum() / len(df) * 100)
                }

                # Numeric columns
                if pd.api.types.is_numeric_dtype(df[col]):
                    non_null = df[col].dropna()
                    if len(non_null) > 0:
                        col_stats.update({
                            "min": float(non_null.min()),
                            "max": float(non_null.max()),
                            "mean": float(non_null.mean()),
                            "median": float(non_null.median()),
                            "std": float(non_null.std()) if len(non_null) > 1 else 0.0
                        })

                # Categorical/string columns
                elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                    non_null = df[col].dropna()
                    if len(non_null) > 0:
                        col_stats.update({
                            "unique_count": int(non_null.nunique()),
                            "top_values": non_null.value_counts().head(5).to_dict()
                        })

                # Date columns
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    non_null = df[col].dropna()
                    if len(non_null) > 0:
                        col_stats.update({
                            "min_date": str(non_null.min()),
                            "max_date": str(non_null.max())
                        })

                stats["columns"][col] = col_stats

            return stats

        except Exception as e:
            logger.error(f"Error generating stats: {e}")
            return {"error": "Failed to generate statistics"}

    def test_query(self, sql: str) -> Dict[str, Any]:
        """
        Test a query without executing it (dry run).
        Validates syntax and estimates complexity.

        Args:
            sql: SQL query to test

        Returns:
            Dictionary with test results
        """
        logger.info("Testing query...")

        try:
            # Validate SQL
            is_valid, error_msg = self.validator.validate(sql)

            if not is_valid:
                return {
                    "success": False,
                    "error": error_msg,
                    "sql": sql
                }

            # Get explanation
            explanation = self.validator.explain_query(sql)

            return {
                "success": True,
                "valid": True,
                "explanation": explanation,
                "sql": sql
            }

        except Exception as e:
            logger.error(f"Error testing query: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql": sql
            }
