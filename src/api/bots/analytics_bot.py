"""
Analytics Bot - Data analysis and insights generation.
Executes queries and uses Gemini API to generate insights.
"""

import logging
from typing import Dict, Any, Optional, List

from src.api.services.llm_service import LLMService, ModelType
from src.api.services.dremio_client import DremioClient
from src.api.services.query_executor import QueryExecutor
from src.api.prompts.analytics_prompts import (
    create_analytics_prompt,
    create_visualization_prompt,
    create_follow_up_questions_prompt,
    extract_insights_from_response
)

logger = logging.getLogger(__name__)


class AnalyticsBot:
    """
    Executes analytical queries and generates insights.
    Uses Gemini API for natural language analysis.
    """

    def __init__(
        self,
        llm_service: LLMService,
        dremio_client: DremioClient
    ):
        """
        Initialize Analytics Bot.

        Args:
            llm_service: LLM service for text generation
            dremio_client: Dremio client for query execution
        """
        self.llm = llm_service
        self.executor = QueryExecutor(dremio_client)

        logger.info("Analytics Bot initialized")

    def analyze_query(
        self,
        user_query: str,
        sql: str,
        include_visualizations: bool = True
    ) -> Dict[str, Any]:
        """
        Execute SQL query and generate analytical insights.

        Args:
            user_query: Original natural language question
            sql: SQL query to execute
            include_visualizations: Include visualization suggestions

        Returns:
            Dictionary with results, insights, and suggestions
        """
        logger.info(f"Analyzing query: {user_query}")

        try:
            # Execute the query
            logger.info("Executing query...")
            execution_result = self.executor.execute(
                sql=sql,
                validate=True,
                include_stats=True
            )

            if not execution_result["success"]:
                logger.error(f"Query execution failed: {execution_result.get('error')}")
                return {
                    "success": False,
                    "error": execution_result.get("error"),
                    "sql": sql
                }

            # Check if we have results
            if not execution_result["data"] or execution_result["row_count"] == 0:
                return {
                    "success": True,
                    "results": execution_result,
                    "insights": {
                        "summary": "The query returned no results.",
                        "key_insights": [
                            "No data matches the query criteria",
                            "Consider broadening the search parameters",
                            "Verify the filters and date ranges"
                        ],
                        "detailed_analysis": "The query executed successfully but returned an empty result set. This could indicate that no data exists for the specified criteria, or the filters may be too restrictive.",
                        "follow_up_questions": [
                            "What is the total count of records in the table?",
                            "What date ranges are available in the data?",
                            "Are there any similar records with slightly different criteria?"
                        ]
                    },
                    "execution_time": execution_result["execution_time"]
                }

            # Generate insights using Gemini
            logger.info("Generating insights...")
            insights = self._generate_insights(
                user_query=user_query,
                sql=sql,
                results=execution_result["data"],
                stats=execution_result.get("stats", {})
            )

            response = {
                "success": True,
                "results": execution_result,
                "insights": insights,
                "execution_time": execution_result["execution_time"]
            }

            # Add visualization suggestions if requested
            if include_visualizations:
                logger.info("Generating visualization suggestions...")
                visualizations = self._suggest_visualizations(
                    user_query=user_query,
                    results=execution_result["data"],
                    stats=execution_result.get("stats", {})
                )
                response["visualizations"] = visualizations

            logger.info("Analysis complete")
            return response

        except Exception as e:
            logger.error(f"Error in analyze_query: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Analysis error: {str(e)}",
                "sql": sql
            }

    def _generate_insights(
        self,
        user_query: str,
        sql: str,
        results: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate insights from query results using Gemini.

        Args:
            user_query: Original user question
            sql: Executed SQL query
            results: Query results
            stats: Statistical summary

        Returns:
            Dictionary with structured insights
        """
        try:
            # Create analytics prompt
            prompt = create_analytics_prompt(
                user_query=user_query,
                sql_query=sql,
                results=results,
                stats=stats
            )

            # Generate insights using Gemini
            response = self.llm.generate(
                prompt=prompt,
                model_type=ModelType.ANALYTICS
            )

            if not response:
                logger.warning("Failed to generate insights from Gemini")
                return {
                    "summary": "Unable to generate insights at this time.",
                    "key_insights": [],
                    "detailed_analysis": "",
                    "follow_up_questions": []
                }

            # Parse and structure the response
            insights = extract_insights_from_response(response)

            return insights

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {
                "summary": f"Error generating insights: {str(e)}",
                "key_insights": [],
                "detailed_analysis": "",
                "follow_up_questions": []
            }

    def _suggest_visualizations(
        self,
        user_query: str,
        results: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Suggest appropriate visualizations for the data.

        Args:
            user_query: Original user question
            results: Query results
            stats: Statistical summary

        Returns:
            List of visualization suggestions
        """
        try:
            # Create visualization prompt
            prompt = create_visualization_prompt(
                user_query=user_query,
                results=results,
                stats=stats
            )

            # Generate suggestions using Gemini
            response = self.llm.generate(
                prompt=prompt,
                model_type=ModelType.ANALYTICS
            )

            if not response:
                return self._default_visualizations(results, stats)

            # Try to parse JSON response
            import json
            import re

            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            try:
                visualizations = json.loads(json_str)
                return visualizations if isinstance(visualizations, list) else []
            except json.JSONDecodeError:
                logger.warning("Could not parse visualization suggestions as JSON")
                return self._default_visualizations(results, stats)

        except Exception as e:
            logger.error(f"Error suggesting visualizations: {e}")
            return self._default_visualizations(results, stats)

    def _default_visualizations(
        self,
        results: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate default visualization suggestions based on data types.

        Args:
            results: Query results
            stats: Statistical summary

        Returns:
            List of default visualization suggestions
        """
        if not results or not stats.get("columns"):
            return []

        visualizations = []
        columns = stats.get("columns", {})

        # If we have numeric and categorical columns, suggest bar chart
        numeric_cols = [col for col, info in columns.items() if "mean" in info]
        categorical_cols = [col for col, info in columns.items() if "unique_count" in info]

        if numeric_cols and categorical_cols:
            visualizations.append({
                "type": "bar",
                "x_field": categorical_cols[0],
                "y_field": numeric_cols[0],
                "title": f"{numeric_cols[0]} by {categorical_cols[0]}",
                "explanation": "Bar chart showing distribution across categories"
            })

        # If we have date columns, suggest line chart
        date_cols = [col for col, info in columns.items() if "min_date" in info]
        if date_cols and numeric_cols:
            visualizations.append({
                "type": "line",
                "x_field": date_cols[0],
                "y_field": numeric_cols[0],
                "title": f"{numeric_cols[0]} over time",
                "explanation": "Line chart showing trends over time"
            })

        # Always suggest table view
        visualizations.append({
            "type": "table",
            "title": "Detailed Data Table",
            "explanation": "Full data table with all columns and rows"
        })

        return visualizations[:3]  # Limit to 3 suggestions

    def analyze_specific_data(
        self,
        data: List[Dict[str, Any]],
        analysis_request: str
    ) -> Dict[str, Any]:
        """
        Analyze specific data without executing a query.
        Useful for analyzing pre-fetched or cached results.

        Args:
            data: Data to analyze (list of dicts)
            analysis_request: What kind of analysis to perform

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing specific data: {analysis_request}")

        try:
            # Generate basic stats
            import pandas as pd
            df = pd.DataFrame(data)

            stats = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": {}
            }

            # Create a simple prompt for analysis
            prompt = f"""Analyze this procurement data and provide insights about: {analysis_request}

Data Sample:
{df.head(20).to_string()}

Summary Statistics:
{df.describe().to_string()}

Provide a brief analysis:
"""

            # Generate insights
            response = self.llm.generate(
                prompt=prompt,
                model_type=ModelType.ANALYTICS
            )

            return {
                "success": True,
                "analysis": response or "Unable to generate analysis",
                "data_summary": {
                    "rows": len(df),
                    "columns": list(df.columns)
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing data: {e}")
            return {
                "success": False,
                "error": str(e)
            }
