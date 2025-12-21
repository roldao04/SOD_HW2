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
9. **CRITICAL**: The columns "year" and "month" are SQL reserved words - ALWAYS wrap them in double quotes: "year", "month"
10. **DATA COVERAGE - IMPORTANT FOR VALUE QUERIES**:
   - **2025**: Most complete year (682K records, all sources). Best for financial analysis.
   - **2024**: Limited data - only Portugal BASE/H&M (~200 records, €441M total). TED 2024 has 12K records but ALL have zero values.
   - **2018-2023**: TED records exist but ALL have zero/null values (tender announcements, not contract awards).
   - **RULE**: When users ask about tender VALUES/spending/contracts, ALWAYS add `WHERE tender_value_amount > 0` and prefer year 2025.
   - **RULE**: When users ask about tender COUNTS (number of tenders), all years can be used but note pre-2024 TED data = announcements only.

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

Question: What are the total contract values by country for 2025?
SQL: SELECT source_country, 
       SUM(tender_value_amount) as total_value,
       COUNT(*) as tender_count
FROM minio.gold.unified
WHERE "year" = 2025
AND tender_value_amount IS NOT NULL
GROUP BY source_country
ORDER BY total_value DESC;

Question: Find all tenders published in Portugal in the last month
SQL: SELECT tender_id, tender_title, publication_date, tender_value_amount, tender_value_currency
FROM minio.gold.unified
WHERE source_country = 'portugal'
AND CAST(publication_date AS DATE) >= CURRENT_DATE - INTERVAL '1' MONTH
ORDER BY publication_date DESC
LIMIT 100;

Question: Show me tenders with values greater than 1 million euros
SQL: SELECT tender_id, tender_title, buyer_name, tender_value_amount, tender_value_currency, source_country
FROM minio.gold.unified
WHERE tender_value_amount > 1000000
AND tender_value_currency = 'EUR'
ORDER BY tender_value_amount DESC
LIMIT 50;

Question: What is the average contract value by month in 2025?
SQL: SELECT
    "year",
    "month",
    AVG(tender_value_amount) as avg_value,
    COUNT(*) as tender_count
FROM minio.gold.unified
WHERE "year" = 2025
AND tender_value_amount IS NOT NULL
GROUP BY "year", "month"
ORDER BY "year", "month";

Question: Find tenders related to IT services or software
SQL: SELECT tender_id, tender_title, tender_description, buyer_name, publication_date, tender_value_amount
FROM minio.gold.unified
WHERE LOWER(tender_title) LIKE '%software%'
OR LOWER(tender_title) LIKE '%information technology%'
OR LOWER(tender_title) LIKE '%it services%'
OR LOWER(tender_description) LIKE '%software%'
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
    "tender": "tender_title or tender_id",
    "contract": "tender_title or tender_value_amount",
    "authority": "buyer_name",
    "cpv": "cpv_codes",
    "country": "source_country",
    "value": "tender_value_amount",
    "price": "tender_value_amount",
    "cost": "tender_value_amount",
    "date": "publication_date or closing_date",
    "published": "publication_date",
    "deadline": "closing_date",
    "currency": "tender_value_currency",
    "award": "award_date or supplier_name",
    "winner": "supplier_name",
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
