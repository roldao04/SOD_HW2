"""
Analytics Prompts for Analytics Bot.
Templates for data analysis, insights generation, and follow-up suggestions.
"""

from typing import Dict, Any, List
import json


ANALYTICS_SYSTEM_PROMPT = """You are an expert data analyst specializing in European public procurement data.
Your task is to analyze query results and provide clear, actionable insights.

# Guidelines:
1. Focus on key findings and trends
2. Highlight interesting patterns or anomalies
3. Provide context about procurement practices
4. Suggest follow-up questions for deeper analysis
5. Be concise but informative
6. Use numbers and percentages to support findings
7. Consider domain knowledge about public procurement

# Analysis Structure:
- **Summary**: High-level overview of the data
- **Key Insights**: 3-5 most important findings
- **Observations**: Detailed analysis of patterns
- **Recommendations**: Actionable follow-up questions or investigations
"""


def create_analytics_prompt(
    user_query: str,
    sql_query: str,
    results: List[Dict[str, Any]],
    stats: Dict[str, Any]
) -> str:
    """
    Create a comprehensive analytics prompt for Gemini.

    Args:
        user_query: Original user question
        sql_query: SQL query that was executed
        results: Query results (list of dicts)
        stats: Statistical summary of results

    Returns:
        Formatted prompt for analytics generation
    """
    # Limit results for prompt (avoid token overflow)
    max_rows_in_prompt = 50
    sample_results = results[:max_rows_in_prompt]
    is_truncated = len(results) > max_rows_in_prompt

    # Format results as table
    results_text = json.dumps(sample_results, indent=2, default=str)

    # Format stats summary
    stats_summary = _format_stats_summary(stats)

    prompt = f"""{ANALYTICS_SYSTEM_PROMPT}

# User Question:
{user_query}

# SQL Query Executed:
```sql
{sql_query}
```

# Query Results:
Total Rows: {stats.get('row_count', len(results))}
{"(Showing first " + str(max_rows_in_prompt) + " rows)" if is_truncated else ""}

{results_text}

# Statistical Summary:
{stats_summary}

# Your Task:
Analyze this procurement data and provide insights that answer the user's question.
Structure your response as follows:

## Summary
[Brief overview of what the data shows]

## Key Insights
[3-5 bullet points with the most important findings]

## Detailed Analysis
[Deeper analysis of patterns, trends, and anomalies]

## Follow-Up Questions
[3-5 suggested questions for further exploration]

Provide your analysis now:
"""

    return prompt


def _format_stats_summary(stats: Dict[str, Any]) -> str:
    """
    Format statistical summary in a readable way.

    Args:
        stats: Statistics dictionary

    Returns:
        Formatted string
    """
    if not stats or "columns" not in stats:
        return "No statistical summary available"

    lines = [f"Total Rows: {stats.get('row_count', 0)}"]
    lines.append(f"Total Columns: {stats.get('column_count', 0)}\n")

    for col_name, col_stats in stats.get("columns", {}).items():
        lines.append(f"**{col_name}** ({col_stats.get('type', 'unknown')})")

        if col_stats.get("null_count", 0) > 0:
            lines.append(f"  - Null values: {col_stats['null_count']} ({col_stats.get('null_percentage', 0):.1f}%)")

        # Numeric stats
        if "mean" in col_stats:
            lines.append(f"  - Range: {col_stats.get('min', 0):.2f} to {col_stats.get('max', 0):.2f}")
            lines.append(f"  - Average: {col_stats.get('mean', 0):.2f}")

        # Categorical stats
        if "unique_count" in col_stats:
            lines.append(f"  - Unique values: {col_stats['unique_count']}")
            if "top_values" in col_stats and col_stats["top_values"]:
                top_3 = list(col_stats["top_values"].items())[:3]
                top_str = ", ".join([f"{k} ({v})" for k, v in top_3])
                lines.append(f"  - Top values: {top_str}")

        # Date stats
        if "min_date" in col_stats:
            lines.append(f"  - Date range: {col_stats['min_date']} to {col_stats['max_date']}")

        lines.append("")  # Empty line between columns

    return "\n".join(lines)


def create_visualization_prompt(
    user_query: str,
    results: List[Dict[str, Any]],
    stats: Dict[str, Any]
) -> str:
    """
    Create prompt for suggesting data visualizations.

    Args:
        user_query: Original user question
        results: Query results
        stats: Statistical summary

    Returns:
        Formatted prompt
    """
    prompt = f"""Given this procurement data query and results, suggest the most appropriate data visualizations.

User Question: {user_query}

Data Summary:
- Total Rows: {stats.get('row_count', 0)}
- Columns: {list(stats.get('columns', {}).keys())}

Available chart types:
- Bar chart (for comparing categories)
- Line chart (for trends over time)
- Pie chart (for proportions)
- Scatter plot (for correlations)
- Table (for detailed data)
- Map (for geographic data)

Suggest up to 3 visualizations that would best represent this data. For each, provide:
1. Chart type
2. X-axis field
3. Y-axis field (if applicable)
4. Title
5. Brief explanation of why this visualization is helpful

Format as JSON array:
```json
[
  {{
    "type": "bar",
    "x_field": "country",
    "y_field": "tender_count",
    "title": "Tenders by Country",
    "explanation": "Shows distribution across countries"
  }}
]
```

Provide your suggestions now:
"""

    return prompt


def create_follow_up_questions_prompt(
    user_query: str,
    results: List[Dict[str, Any]],
    insights: str
) -> str:
    """
    Create prompt for generating follow-up questions.

    Args:
        user_query: Original user question
        results: Query results
        insights: Generated insights

    Returns:
        Formatted prompt
    """
    prompt = f"""Based on this procurement data analysis, suggest relevant follow-up questions for deeper exploration.

Original Question: {user_query}

Key Insights from Analysis:
{insights}

Generate 5 follow-up questions that would help the user:
1. Explore trends or patterns mentioned in the insights
2. Dig deeper into specific findings
3. Compare different aspects of the data
4. Investigate anomalies or outliers
5. Understand context or implications

Make questions specific and actionable. Format as a numbered list.

Follow-up questions:
"""

    return prompt


def create_comparison_prompt(
    user_query: str,
    dataset_a: Dict[str, Any],
    dataset_b: Dict[str, Any],
    comparison_context: str
) -> str:
    """
    Create prompt for comparing two datasets.

    Args:
        user_query: Original comparison question
        dataset_a: First dataset with results
        dataset_b: Second dataset with results
        comparison_context: Context about what's being compared

    Returns:
        Formatted prompt
    """
    prompt = f"""{ANALYTICS_SYSTEM_PROMPT}

# User Question:
{user_query}

# Comparison Context:
{comparison_context}

# Dataset A:
Results: {len(dataset_a.get('data', []))} rows
{json.dumps(dataset_a.get('data', [])[:10], indent=2, default=str)}

# Dataset B:
Results: {len(dataset_b.get('data', []))} rows
{json.dumps(dataset_b.get('data', [])[:10], indent=2, default=str)}

# Your Task:
Compare these two datasets and provide:
1. Key differences
2. Similarities
3. Trends or patterns that differ between them
4. Possible explanations for the differences
5. Recommendations based on the comparison

Provide your comparative analysis:
"""

    return prompt


def extract_insights_from_response(response: str) -> Dict[str, Any]:
    """
    Extract structured insights from LLM response.

    Args:
        response: Raw LLM response

    Returns:
        Dictionary with structured insights
    """
    # Basic parsing - extract sections
    insights = {
        "raw_response": response,
        "summary": "",
        "key_insights": [],
        "detailed_analysis": "",
        "follow_up_questions": []
    }

    try:
        # Split by sections
        sections = response.split("##")

        for idx, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # Summary section
            if section.lower().startswith("summary"):
                content_parts = section.split("\n", 1)
                if len(content_parts) > 1:
                    insights["summary"] = content_parts[1].strip()

            # Key insights section
            elif "key insight" in section.lower():
                content_parts = section.split("\n", 1)
                content = content_parts[1] if len(content_parts) > 1 else ""
                # Extract bullet points
                bullets = [
                    line.strip("- *").strip()
                    for line in content.split("\n")
                    if line.strip().startswith(("-", "*", "•"))
                ]
                insights["key_insights"] = bullets

            # Follow-up questions (check before detailed analysis to avoid misclassification)
            elif "follow" in section.lower() and "question" in section.lower():
                content_parts = section.split("\n", 1)
                content = content_parts[1] if len(content_parts) > 1 else ""
                # Extract numbered or bulleted items
                questions = [
                    line.strip("1234567890.- *").strip()
                    for line in content.split("\n")
                    if line.strip() and any(c.isdigit() or c in "-*•" for c in line[:3])
                ]
                insights["follow_up_questions"] = questions

            # Detailed analysis
            elif "detail" in section.lower() or "analysis" in section.lower():
                content_parts = section.split("\n", 1)
                if len(content_parts) > 1:
                    insights["detailed_analysis"] = content_parts[1].strip()

    except Exception as e:
        import traceback
        print(f"Error parsing insights: {e}")
        print(f"Traceback: {traceback.format_exc()}")

    return insights
