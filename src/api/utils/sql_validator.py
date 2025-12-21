"""
SQL Query Validator - Security and complexity checks.
Ensures generated SQL queries are safe and within acceptable limits.
"""

import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Token
from sqlparse.tokens import Keyword, DML
from typing import Tuple, List, Optional
import logging

from src.api.config import settings

logger = logging.getLogger(__name__)


class SQLValidationError(Exception):
    """Exception raised for SQL validation failures."""
    pass


class SQLValidator:
    """
    Validates SQL queries for security and complexity.
    """

    # Forbidden SQL keywords (case-insensitive)
    FORBIDDEN_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE',
        'CREATE', 'ALTER', 'GRANT', 'REVOKE', 'EXEC',
        'EXECUTE', 'CALL', 'MERGE', 'REPLACE'
    ]

    # Dangerous functions
    DANGEROUS_FUNCTIONS = [
        'LOAD_FILE', 'INTO OUTFILE', 'INTO DUMPFILE',
        'SYSTEM', 'SHELL', 'EVAL'
    ]

    def __init__(self):
        """Initialize SQL validator."""
        self.max_joins = settings.MAX_JOINS
        self.max_subquery_depth = settings.MAX_SUBQUERY_DEPTH

    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query.

        Args:
            sql: SQL query string to validate

        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
        """
        try:
            # Clean and normalize SQL
            sql = sql.strip()

            # Check if empty
            if not sql:
                return False, "Empty SQL query"

            # Parse SQL
            try:
                parsed = sqlparse.parse(sql)
                if not parsed:
                    return False, "Unable to parse SQL query"
            except Exception as e:
                return False, f"SQL parsing error: {str(e)}"

            # Security checks
            is_safe, safety_msg = self._check_security(sql, parsed)
            if not is_safe:
                return False, safety_msg

            # Type check - must be SELECT
            is_select, select_msg = self._check_is_select(parsed)
            if not is_select:
                return False, select_msg

            # Complexity checks
            is_simple, complexity_msg = self._check_complexity(sql, parsed)
            if not is_simple:
                return False, complexity_msg

            logger.info("SQL query validation passed")
            return True, None

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation error: {str(e)}"

    def _check_security(
        self,
        sql: str,
        parsed: List[sqlparse.sql.Statement]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for dangerous SQL patterns and keywords.

        Args:
            sql: SQL query string
            parsed: Parsed SQL statements

        Returns:
            Tuple of (is_safe, error_message)
        """
        sql_upper = sql.upper()

        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                return False, f"Forbidden keyword detected: {keyword}"

        # Check for dangerous functions
        for func in self.DANGEROUS_FUNCTIONS:
            if func in sql_upper:
                return False, f"Dangerous function detected: {func}"

        # Check for comment injection attempts
        if '--' in sql or '/*' in sql or '*/' in sql:
            # Allow legitimate comments but check for injection patterns
            comment_patterns = [
                r'--.*DROP',
                r'--.*DELETE',
                r'/\*.*DROP.*\*/',
                r'/\*.*DELETE.*\*/',
            ]
            for pattern in comment_patterns:
                if re.search(pattern, sql_upper):
                    return False, "Potential SQL injection detected in comments"

        # Check for semicolon chaining (multiple statements)
        statements = [s for s in parsed if s.get_type() != 'UNKNOWN']
        if len(statements) > 1:
            return False, "Multiple SQL statements not allowed"

        # Check for UNION injection attempts
        union_count = sql_upper.count('UNION')
        if union_count > 2:
            return False, "Excessive UNION operations detected"

        return True, None

    def _check_is_select(
        self,
        parsed: List[sqlparse.sql.Statement]
    ) -> Tuple[bool, Optional[str]]:
        """
        Ensure query is a SELECT statement.

        Args:
            parsed: Parsed SQL statements

        Returns:
            Tuple of (is_select, error_message)
        """
        if not parsed:
            return False, "No SQL statement found"

        statement = parsed[0]

        # Get first significant token
        first_token = statement.token_first(skip_ws=True, skip_cm=True)

        if first_token is None:
            return False, "Empty SQL statement"

        # Check if it's a SELECT or WITH (for CTEs)
        if first_token.ttype == DML and first_token.value.upper() in ('SELECT', 'WITH'):
            return True, None

        # Also check the normalized value
        if statement.get_type() == 'SELECT':
            return True, None

        return False, f"Only SELECT queries are allowed, got: {first_token.value}"

    def _check_complexity(
        self,
        sql: str,
        parsed: List[sqlparse.sql.Statement]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check query complexity limits.

        Args:
            sql: SQL query string
            parsed: Parsed SQL statements

        Returns:
            Tuple of (is_acceptable, error_message)
        """
        sql_upper = sql.upper()

        # Check number of JOIN operations
        join_count = sql_upper.count(' JOIN ')
        if join_count > self.max_joins:
            return False, f"Too many JOINs: {join_count} (max: {self.max_joins})"

        # Check subquery depth
        subquery_depth = self._count_subquery_depth(sql)
        if subquery_depth > self.max_subquery_depth:
            return False, f"Subquery nesting too deep: {subquery_depth} (max: {self.max_subquery_depth})"

        return True, None

    def _count_subquery_depth(self, sql: str) -> int:
        """
        Count maximum depth of nested subqueries.

        Args:
            sql: SQL query string

        Returns:
            Maximum nesting depth
        """
        # Remove string literals to avoid counting parentheses in strings
        sql_no_strings = re.sub(r"'[^']*'", "", sql)
        sql_no_strings = re.sub(r'"[^"]*"', "", sql_no_strings)

        max_depth = 0
        current_depth = 0

        # Track depth by counting parentheses
        # We need to be smarter: only count SELECT within parentheses
        in_subquery = False
        depth_stack = []

        tokens = sqlparse.parse(sql)[0].flatten()
        paren_depth = 0

        for token in tokens:
            if token.value == '(':
                paren_depth += 1
            elif token.value == ')':
                paren_depth -= 1
            elif token.ttype == DML and token.value.upper() == 'SELECT' and paren_depth > 0:
                # SELECT inside parentheses = subquery
                max_depth = max(max_depth, paren_depth)

        return max_depth

    def sanitize_sql(self, sql: str) -> str:
        """
        Sanitize SQL query by formatting and removing extra whitespace.

        Args:
            sql: Raw SQL query

        Returns:
            Sanitized SQL query
        """
        # Format SQL for readability
        formatted = sqlparse.format(
            sql,
            reindent=True,
            keyword_case='upper',
            strip_comments=False
        )

        # Remove excessive whitespace
        formatted = re.sub(r'\s+', ' ', formatted)
        formatted = formatted.strip()

        # Ensure ends with semicolon
        if not formatted.endswith(';'):
            formatted += ';'

        return formatted

    def explain_query(self, sql: str) -> str:
        """
        Generate a human-readable explanation of the SQL query.

        Args:
            sql: SQL query

        Returns:
            Plain English explanation
        """
        explanation_parts = []

        sql_upper = sql.upper()

        # Identify main clauses
        if 'SELECT' in sql_upper:
            explanation_parts.append("This query retrieves data")

        if 'FROM' in sql_upper:
            # Extract table names
            from_match = re.search(r'FROM\s+([^\s;WHERE,GROUP,ORDER,LIMIT]+)', sql_upper)
            if from_match:
                table = from_match.group(1)
                explanation_parts.append(f"from the {table} table")

        if 'WHERE' in sql_upper:
            explanation_parts.append("with specific filtering conditions")

        if 'GROUP BY' in sql_upper:
            explanation_parts.append("grouped by certain attributes")

        if 'ORDER BY' in sql_upper:
            if 'DESC' in sql_upper:
                explanation_parts.append("sorted in descending order")
            else:
                explanation_parts.append("sorted in ascending order")

        if 'LIMIT' in sql_upper:
            limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
            if limit_match:
                limit_val = limit_match.group(1)
                explanation_parts.append(f"limited to {limit_val} results")

        if 'JOIN' in sql_upper:
            join_count = sql_upper.count('JOIN')
            explanation_parts.append(f"combining data from {join_count + 1} tables")

        return " ".join(explanation_parts) + "."


# Global validator instance
_validator = None


def get_validator() -> SQLValidator:
    """Get or create global SQL validator instance."""
    global _validator
    if _validator is None:
        _validator = SQLValidator()
    return _validator


def validate_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to validate SQL.

    Args:
        sql: SQL query to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = get_validator()
    return validator.validate(sql)
