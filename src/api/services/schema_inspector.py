"""
Schema Inspector - Introspects Dremio database schema.
Provides table and column information for context-aware SQL generation.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from src.api.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    nullable: bool = True
    sample_values: List[str] = field(default_factory=list)


@dataclass
class TableInfo:
    """Information about a database table."""
    full_name: str  # e.g., minio.gold.unified
    schema: str  # e.g., minio.gold
    table_name: str  # e.g., unified
    columns: List[ColumnInfo] = field(default_factory=list)
    row_count: Optional[int] = None
    description: Optional[str] = None


class SchemaInspector:
    """
    Inspects Dremio database schema and caches metadata.
    Provides context for SQL generation.
    """

    def __init__(self, dremio_client):
        """
        Initialize schema inspector.

        Args:
            dremio_client: DremioClient instance
        """
        self.dremio = dremio_client
        self._cache: Dict[str, TableInfo] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=settings.SCHEMA_CACHE_TTL)

        logger.info("Schema Inspector initialized")

    def _is_cache_valid(self) -> bool:
        """Check if schema cache is still valid."""
        if self._cache_timestamp is None:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_ttl

    def refresh_schema(self, force: bool = False):
        """
        Refresh schema cache from Dremio.

        Args:
            force: Force refresh even if cache is valid
        """
        if not force and self._is_cache_valid():
            logger.info("Schema cache is still valid, skipping refresh")
            return

        logger.info("Refreshing schema cache...")
        self._cache.clear()

        try:
            # Get all tables from relevant schemas
            schemas = ["minio.gold", "minio.silver", "minio.bronze"]

            for schema in schemas:
                try:
                    tables = self._get_tables_in_schema(schema)
                    logger.info(f"Found {len(tables)} tables in {schema}")

                    for table_name in tables:
                        full_name = f"{schema}.{table_name}"
                        table_info = self._inspect_table(full_name, schema, table_name)
                        if table_info:
                            self._cache[full_name] = table_info

                except Exception as e:
                    logger.error(f"Error inspecting schema {schema}: {e}")
                    continue

            self._cache_timestamp = datetime.now()
            logger.info(f"Schema cache refreshed: {len(self._cache)} tables loaded")

        except Exception as e:
            logger.error(f"Error refreshing schema: {e}")

    def _get_tables_in_schema(self, schema: str) -> List[str]:
        """Get list of tables in a schema."""
        try:
            result = self.dremio.execute_query(f"SHOW TABLES IN {schema}")
            if result["success"]:
                # Extract table names from results
                return [row.get("TABLE_NAME", row.get("name", "")) for row in result["data"]]
            return []
        except Exception as e:
            logger.error(f"Error getting tables from {schema}: {e}")
            return []

    def _inspect_table(
        self,
        full_name: str,
        schema: str,
        table_name: str
    ) -> Optional[TableInfo]:
        """
        Inspect a single table and gather metadata.

        Args:
            full_name: Fully qualified table name
            schema: Schema name
            table_name: Table name

        Returns:
            TableInfo object or None if inspection failed
        """
        try:
            logger.debug(f"Inspecting table: {full_name}")

            # Get column information using DESCRIBE
            describe_result = self.dremio.execute_query(f"DESCRIBE {full_name}")
            if not describe_result["success"]:
                logger.warning(f"Could not describe table {full_name}")
                return None

            columns = []
            for row in describe_result["data"]:
                col_name = row.get("COLUMN_NAME", row.get("col_name", ""))
                col_type = row.get("DATA_TYPE", row.get("data_type", ""))
                nullable = row.get("IS_NULLABLE", "YES") == "YES"

                if col_name:
                    columns.append(ColumnInfo(
                        name=col_name,
                        data_type=col_type,
                        nullable=nullable
                    ))

            # Get sample values for each column (first 5 unique values)
            sample_result = self.dremio.execute_query(
                f"SELECT * FROM {full_name} LIMIT 100"
            )

            if sample_result["success"] and sample_result["data"]:
                import pandas as pd
                import numpy as np
                df = pd.DataFrame(sample_result["data"])

                for col in columns:
                    if col.name in df.columns:
                        try:
                            # Get unique non-null values
                            # Skip ARRAY columns or other unhashable types
                            if col.data_type.upper() == 'ARRAY':
                                col.sample_values = ["[array]"]
                                continue

                            # Filter out None/NaN values
                            non_null = df[col.name].dropna()
                            if len(non_null) == 0:
                                continue

                            # Try to get unique values, handle unhashable types
                            try:
                                unique_vals = non_null.unique()[:5].tolist()
                                col.sample_values = [str(v) for v in unique_vals if v is not None]
                            except (TypeError, np.core._exceptions._UFuncNoLoopError):
                                # Column contains unhashable types (arrays, dicts, etc.)
                                col.sample_values = [str(non_null.iloc[0])][:50]  # Just take first value

                        except Exception as e:
                            logger.debug(f"Could not get sample values for column {col.name}: {e}")
                            continue

            # Get row count (approximate)
            count_result = self.dremio.execute_query(
                f"SELECT COUNT(*) as cnt FROM {full_name}"
            )
            row_count = None
            if count_result["success"] and count_result["data"]:
                row_count = count_result["data"][0].get("cnt", None)

            # Create description based on schema and table name
            description = self._generate_table_description(schema, table_name)

            return TableInfo(
                full_name=full_name,
                schema=schema,
                table_name=table_name,
                columns=columns,
                row_count=row_count,
                description=description
            )

        except Exception as e:
            logger.error(f"Error inspecting table {full_name}: {e}")
            return None

    def _generate_table_description(self, schema: str, table_name: str) -> str:
        """Generate a description for a table based on its name and schema."""
        descriptions = {
            "unified": "Unified procurement tender data from all sources",
            "country_stats": "Aggregated statistics by country",
            "monthly_trends": "Monthly tender trends and volumes",
            "category_analysis": "Tender categories and CPV code analysis",
            "authority_stats": "Contracting authority statistics",
            "value_distribution": "Contract value distribution analysis"
        }

        desc = descriptions.get(table_name, f"Table containing {table_name} data")

        if "gold" in schema:
            return f"{desc} (aggregated/unified layer)"
        elif "silver" in schema:
            return f"{desc} (cleaned/processed layer)"
        elif "bronze" in schema:
            return f"{desc} (raw data layer)"

        return desc

    def get_all_tables(self) -> List[TableInfo]:
        """
        Get information about all available tables.

        Returns:
            List of TableInfo objects
        """
        if not self._is_cache_valid():
            self.refresh_schema()

        return list(self._cache.values())

    def get_table(self, table_name: str) -> Optional[TableInfo]:
        """
        Get information about a specific table.

        Args:
            table_name: Fully qualified table name or just table name

        Returns:
            TableInfo object or None if not found
        """
        if not self._is_cache_valid():
            self.refresh_schema()

        # Try exact match first
        if table_name in self._cache:
            return self._cache[table_name]

        # Try partial match (table name without schema)
        for full_name, table_info in self._cache.items():
            if table_info.table_name == table_name:
                return table_info

        logger.warning(f"Table not found: {table_name}")
        return None

    def get_schema_context(self, max_tables: Optional[int] = None) -> str:
        """
        Get formatted schema context for LLM prompts.

        Args:
            max_tables: Maximum number of tables to include (None = all)

        Returns:
            Formatted string with schema information
        """
        if not self._is_cache_valid():
            self.refresh_schema()

        tables = list(self._cache.values())
        if max_tables:
            # Prioritize gold layer tables
            gold_tables = [t for t in tables if "gold" in t.schema]
            other_tables = [t for t in tables if "gold" not in t.schema]
            tables = gold_tables[:max_tables] + other_tables[:max(0, max_tables - len(gold_tables))]

        context_parts = ["# Database Schema\n"]

        for table in tables:
            context_parts.append(f"\n## Table: {table.full_name}")
            if table.description:
                context_parts.append(f"Description: {table.description}")
            if table.row_count:
                context_parts.append(f"Rows: ~{table.row_count:,}")

            context_parts.append("\nColumns:")
            for col in table.columns:
                col_info = f"- {col.name} ({col.data_type})"
                if col.sample_values:
                    samples = ", ".join(col.sample_values[:3])
                    col_info += f" | Examples: {samples}"
                context_parts.append(col_info)

        return "\n".join(context_parts)

    def get_relevant_tables(self, user_query: str) -> List[TableInfo]:
        """
        Get tables most relevant to a user query.
        Uses simple keyword matching for now.

        Args:
            user_query: User's natural language query

        Returns:
            List of relevant TableInfo objects
        """
        if not self._is_cache_valid():
            self.refresh_schema()

        query_lower = user_query.lower()
        relevant_tables = []

        # Prioritize gold layer for most queries
        for table in self._cache.values():
            if "gold" in table.schema:
                relevant_tables.append(table)

        # If query mentions specific keywords, filter further
        keywords_to_tables = {
            "country": ["country_stats", "unified"],
            "month": ["monthly_trends", "unified"],
            "category": ["category_analysis", "unified"],
            "cpv": ["category_analysis", "unified"],
            "authority": ["authority_stats", "unified"],
            "value": ["value_distribution", "unified"],
            "contract": ["unified"],
            "tender": ["unified"],
        }

        for keyword, table_names in keywords_to_tables.items():
            if keyword in query_lower:
                for table_name in table_names:
                    table = self.get_table(table_name)
                    if table and table not in relevant_tables:
                        relevant_tables.append(table)

        # If no specific matches, return all gold tables
        if not relevant_tables:
            relevant_tables = [t for t in self._cache.values() if "gold" in t.schema]

        return relevant_tables[:5]  # Limit to top 5
