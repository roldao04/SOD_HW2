"""
SQL Generation Prompts for Query Creator Bot.
Includes system prompts, few-shot examples, and constraint definitions.
"""

from typing import List
from src.api.services.schema_inspector import TableInfo


# System prompt template for Gemini SQL Generation
SYSTEM_PROMPT = """You are an expert SQL query generator for a European public procurement database.
Your task is to convert natural language questions into valid SQL queries.

# Important Rules:
1. Only generate SELECT queries - NO INSERT, UPDATE, DELETE, DROP, or ALTER
2. Use proper SQL syntax compatible with Dremio (similar to PostgreSQL)
3. Always qualify column names with table aliases when using joins
4. Use appropriate WHERE clauses, GROUP BY, and ORDER BY as needed
5. Limit results to reasonable numbers (use LIMIT clause)
6. Handle NULL values appropriately
7. Use proper date comparisons for date columns
8. Return ONLY the SQL query - no explanations or markdown

# Database Context:
{schema_context}

# Few-Shot Examples:

Question: Show me the top 10 countries by number of tenders
SQL: SELECT source_country, COUNT(*) as tender_count
FROM minio.gold.unified
WHERE source_country IS NOT NULL
GROUP BY source_country
ORDER BY tender_count DESC
LIMIT 10;

Question: What are the total contract values by country for 2024?
SQL: SELECT source_country, SUM(contract_value) as total_value
FROM minio.gold.unified
WHERE EXTRACT(YEAR FROM publication_date) = 2024
AND contract_value IS NOT NULL
GROUP BY source_country
ORDER BY total_value DESC;

Question: Find all tenders published in Portugal in the last month
SQL: SELECT source_id, contract_object, publication_date, contract_value
FROM minio.gold.unified
WHERE source_country = 'PT'
AND publication_date >= CURRENT_DATE - INTERVAL '1' MONTH
ORDER BY publication_date DESC
LIMIT 100;

Question: Show me tenders with values greater than 1 million euros
SQL: SELECT source_id, contract_object, contracting_authorities, contract_value, source_country
FROM minio.gold.unified
WHERE contract_value > 1000000
AND currency = 'EUR'
ORDER BY contract_value DESC
LIMIT 50;

Question: What is the average contract value by month in 2024?
SQL: SELECT
    EXTRACT(YEAR FROM publication_date) as year,
    EXTRACT(MONTH FROM publication_date) as month,
    AVG(contract_value) as avg_value,
    COUNT(*) as tender_count
FROM minio.gold.unified
WHERE EXTRACT(YEAR FROM publication_date) = 2024
AND contract_value IS NOT NULL
GROUP BY EXTRACT(YEAR FROM publication_date), EXTRACT(MONTH FROM publication_date)
ORDER BY year, month;

Question: Find tenders related to IT services or software
SQL: SELECT source_id, contract_object, contracting_authorities, publication_date, contract_value
FROM minio.gold.unified
WHERE LOWER(contract_object) LIKE '%software%'
OR LOWER(contract_object) LIKE '%information technology%'
OR LOWER(contract_object) LIKE '%it services%'
ORDER BY publication_date DESC
LIMIT 50;

# User Question:
{user_query}

# SQL Query:"""


def create_sql_generation_prompt(
    user_query: str,
    relevant_tables: List[TableInfo],
    include_all_schema: bool = False
) -> str:
    """
    Create a complete prompt for SQL generation.

    Args:
        user_query: User's natural language question
        relevant_tables: List of relevant tables to include in context
        include_all_schema: Include full schema details (slower but more accurate)

    Returns:
        Formatted prompt string
    """
    # Build schema context from relevant tables
    schema_parts = []

    for table in relevant_tables:
        schema_parts.append(f"\nTable: {table.full_name}")
        if table.description:
            schema_parts.append(f"  Description: {table.description}")
        if table.row_count:
            schema_parts.append(f"  Rows: ~{table.row_count:,}")

        schema_parts.append("  Columns:")
        for col in table.columns:
            col_line = f"    - {col.name} ({col.data_type})"
            if col.sample_values and include_all_schema:
                samples = ", ".join(str(v) for v in col.sample_values[:3])
                col_line += f" | Examples: {samples}"
            schema_parts.append(col_line)

    schema_context = "\n".join(schema_parts)

    # Fill in the template
    prompt = SYSTEM_PROMPT.format(
        schema_context=schema_context,
        user_query=user_query
    )

    return prompt


def create_refinement_prompt(
    original_query: str,
    original_sql: str,
    user_feedback: str
) -> str:
    """
    Create a prompt for refining an existing SQL query based on user feedback.

    Args:
        original_query: Original user question
        original_sql: Previously generated SQL
        user_feedback: User's feedback or refinement request

    Returns:
        Formatted refinement prompt
    """
    return f"""You are refining a SQL query based on user feedback.

Original Question: {original_query}

Previous SQL Query:
{original_sql}

User Feedback: {user_feedback}

Please generate an improved SQL query that addresses the user's feedback.
Return ONLY the SQL query - no explanations.

# Improved SQL Query:"""


def extract_sql_from_response(response: str) -> str:
    """
    Extract SQL query from LLM response.
    Handles various response formats and removes markdown/extra text.

    Args:
        response: Raw LLM response

    Returns:
        Cleaned SQL query
    """
    # Remove markdown code blocks
    if "```sql" in response:
        response = response.split("```sql")[1].split("```")[0]
    elif "```" in response:
        response = response.split("```")[1].split("```")[0]

    # Remove common prefixes
    prefixes = ["SQL:", "Query:", "SELECT", "WITH"]
    for prefix in prefixes:
        if response.strip().upper().startswith(prefix) and prefix != "SELECT" and prefix != "WITH":
            response = response[len(prefix):].strip()
        if response.strip().upper().startswith(prefix.lower()):
            response = response[len(prefix):].strip()

    # Clean up whitespace
    response = response.strip()

    # Ensure it ends with semicolon
    if not response.endswith(";"):
        response += ";"

    return response


# Domain-specific keywords for procurement data
PROCUREMENT_KEYWORDS = {
    "tender": "contract_object or source_id",
    "contract": "contract_object or contract_value",
    "authority": "contracting_authorities",
    "cpv": "cpv_codes",
    "country": "source_country",
    "value": "contract_value",
    "price": "contract_value",
    "cost": "contract_value",
    "date": "publication_date or closing_date",
    "published": "publication_date",
    "deadline": "closing_date",
    "currency": "currency",
    "award": "award_date or contractor_name",
    "winner": "contractor_name",
}


def get_domain_hints(user_query: str) -> List[str]:
    """
    Get domain-specific hints based on user query keywords.

    Args:
        user_query: User's natural language question

    Returns:
        List of helpful hints
    """
    query_lower = user_query.lower()
    hints = []

    # Check for common keywords
    for keyword, hint in PROCUREMENT_KEYWORDS.items():
        if keyword in query_lower:
            hints.append(f"For '{keyword}', consider using: {hint}")

    # Check for aggregation needs
    if any(word in query_lower for word in ["total", "sum", "average", "count", "how many"]):
        hints.append("This query requires aggregation (SUM, AVG, COUNT)")

    if any(word in query_lower for word in ["by country", "by month", "by category", "per"]):
        hints.append("Use GROUP BY clause")

    if any(word in query_lower for word in ["top", "highest", "lowest", "best", "worst"]):
        hints.append("Use ORDER BY with LIMIT")

    if any(word in query_lower for word in ["recent", "latest", "last"]):
        hints.append("Sort by publication_date DESC and use LIMIT")

    return hints
