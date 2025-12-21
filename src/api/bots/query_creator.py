"""
Query Creator Bot - Natural Language to SQL conversion.
Uses HuggingFace SQLCoder model with schema context.
"""

import logging
from typing import Dict, Any, Optional, List

from src.api.services.llm_service import LLMService, ModelType
from src.api.services.schema_inspector import SchemaInspector, TableInfo
from src.api.prompts.sql_prompts import (
    create_sql_generation_prompt,
    create_refinement_prompt,
    extract_sql_from_response,
    get_domain_hints
)
from src.api.utils.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


class QueryCreatorBot:
    """
    Natural language to SQL query creator.
    Generates safe, validated SQL queries from user questions.
    """

    def __init__(
        self,
        llm_service: LLMService,
        schema_inspector: SchemaInspector
    ):
        """
        Initialize Query Creator Bot.

        Args:
            llm_service: LLM service for text generation
            schema_inspector: Schema inspector for database context
        """
        self.llm = llm_service
        self.schema = schema_inspector
        self.validator = SQLValidator()

        logger.info("Query Creator Bot initialized")

    def generate_sql(
        self,
        user_query: str,
        include_explanation: bool = True,
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Generate SQL query from natural language.

        Args:
            user_query: User's natural language question
            include_explanation: Include query explanation in response
            max_attempts: Maximum attempts to generate valid SQL

        Returns:
            Dictionary with:
                - success: bool
                - sql: Generated SQL query (if successful)
                - explanation: Query explanation (if requested)
                - confidence: Confidence score (0-1)
                - error: Error message (if failed)
                - hints: Domain hints for the query
        """
        logger.info(f"Generating SQL for query: {user_query}")

        try:
            # Refresh schema cache if needed
            if not self.schema._is_cache_valid():
                logger.info("Refreshing schema cache...")
                self.schema.refresh_schema()

            # Get relevant tables based on user query
            relevant_tables = self.schema.get_relevant_tables(user_query)

            if not relevant_tables:
                logger.warning("No relevant tables found for query")
                return {
                    "success": False,
                    "error": "Could not find relevant tables for this query",
                    "hints": get_domain_hints(user_query)
                }

            logger.info(f"Using {len(relevant_tables)} relevant tables")

            # Generate SQL with retry logic
            for attempt in range(max_attempts):
                logger.debug(f"Generation attempt {attempt + 1}/{max_attempts}")

                # Create prompt
                prompt = create_sql_generation_prompt(
                    user_query=user_query,
                    relevant_tables=relevant_tables,
                    include_all_schema=(attempt > 0)  # Include more details on retry
                )

                # Generate SQL using LLM
                response = self.llm.generate(
                    prompt=prompt,
                    model_type=ModelType.QUERY_CREATOR,
                    temperature=0.1,  # Low temperature for deterministic SQL
                    max_tokens=512
                )

                if not response:
                    if attempt == max_attempts - 1:
                        return {
                            "success": False,
                            "error": "Failed to generate SQL query",
                            "hints": get_domain_hints(user_query)
                        }
                    continue

                # Extract SQL from response
                sql = extract_sql_from_response(response)

                # Validate SQL
                is_valid, error_msg = self.validator.validate(sql)

                if is_valid:
                    # Success!
                    logger.info("SQL generated and validated successfully")

                    result = {
                        "success": True,
                        "sql": sql,
                        "confidence": self._calculate_confidence(sql, user_query, attempt),
                        "hints": get_domain_hints(user_query),
                        "tables_used": [t.full_name for t in relevant_tables]
                    }

                    if include_explanation:
                        result["explanation"] = self.validator.explain_query(sql)

                    return result

                else:
                    logger.warning(f"Validation failed (attempt {attempt + 1}): {error_msg}")
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        return {
                            "success": False,
                            "error": f"Generated SQL failed validation: {error_msg}",
                            "sql": sql,  # Include for debugging
                            "hints": get_domain_hints(user_query)
                        }

            # Should not reach here, but just in case
            return {
                "success": False,
                "error": "Failed to generate valid SQL after all attempts",
                "hints": get_domain_hints(user_query)
            }

        except Exception as e:
            logger.error(f"Error in generate_sql: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
                "hints": get_domain_hints(user_query)
            }

    def refine_sql(
        self,
        original_query: str,
        original_sql: str,
        feedback: str
    ) -> Dict[str, Any]:
        """
        Refine an existing SQL query based on user feedback.

        Args:
            original_query: Original natural language question
            original_sql: Previously generated SQL
            feedback: User's feedback or refinement request

        Returns:
            Dictionary with refined SQL and metadata
        """
        logger.info(f"Refining SQL based on feedback: {feedback}")

        try:
            # Create refinement prompt
            prompt = create_refinement_prompt(
                original_query=original_query,
                original_sql=original_sql,
                user_feedback=feedback
            )

            # Generate refined SQL
            response = self.llm.generate(
                prompt=prompt,
                model_type=ModelType.QUERY_CREATOR,
                temperature=0.1,
                max_tokens=512
            )

            if not response:
                return {
                    "success": False,
                    "error": "Failed to refine SQL query"
                }

            # Extract and validate
            sql = extract_sql_from_response(response)
            is_valid, error_msg = self.validator.validate(sql)

            if not is_valid:
                return {
                    "success": False,
                    "error": f"Refined SQL failed validation: {error_msg}",
                    "sql": sql
                }

            return {
                "success": True,
                "sql": sql,
                "explanation": self.validator.explain_query(sql),
                "confidence": 0.85  # Slightly lower for refined queries
            }

        except Exception as e:
            logger.error(f"Error in refine_sql: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Internal error: {str(e)}"
            }

    def validate_user_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate a user-provided SQL query.

        Args:
            sql: SQL query to validate

        Returns:
            Dictionary with validation results
        """
        logger.info("Validating user-provided SQL")

        try:
            is_valid, error_msg = self.validator.validate(sql)

            return {
                "success": is_valid,
                "sql": sql if is_valid else None,
                "error": error_msg,
                "explanation": self.validator.explain_query(sql) if is_valid else None
            }

        except Exception as e:
            logger.error(f"Error validating SQL: {e}")
            return {
                "success": False,
                "error": f"Validation error: {str(e)}"
            }

    def _calculate_confidence(
        self,
        sql: str,
        user_query: str,
        attempt: int
    ) -> float:
        """
        Calculate confidence score for generated SQL.

        Args:
            sql: Generated SQL query
            user_query: Original user question
            attempt: Which generation attempt succeeded (0-indexed)

        Returns:
            Confidence score between 0 and 1
        """
        # Start with base confidence
        confidence = 1.0

        # Penalize multiple attempts
        confidence -= (attempt * 0.15)

        # Check query complexity (simpler = higher confidence)
        sql_upper = sql.upper()
        if sql_upper.count('JOIN') > 2:
            confidence -= 0.1
        if sql_upper.count('SELECT') > 2:  # Subqueries
            confidence -= 0.1

        # Boost confidence if query has common patterns
        if 'LIMIT' in sql_upper:
            confidence += 0.05
        if 'WHERE' in sql_upper:
            confidence += 0.05

        # Ensure confidence is in valid range
        return max(0.1, min(1.0, confidence))

    def get_schema_summary(self) -> Dict[str, Any]:
        """
        Get a summary of available database schema.

        Returns:
            Dictionary with schema information
        """
        try:
            all_tables = self.schema.get_all_tables()

            return {
                "success": True,
                "table_count": len(all_tables),
                "tables": [
                    {
                        "name": table.full_name,
                        "description": table.description,
                        "columns": len(table.columns),
                        "rows": table.row_count
                    }
                    for table in all_tables
                ]
            }

        except Exception as e:
            logger.error(f"Error getting schema summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
