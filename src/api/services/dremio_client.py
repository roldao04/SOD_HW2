"""
Dremio client using PyArrow Flight for SQL query execution.
Provides connection management, query execution, and schema introspection.
"""

import pyarrow as pa
import pyarrow.flight as flight
import pandas as pd
from typing import Optional, Dict, List, Any
import logging
from datetime import datetime
import base64

from src.api.config import settings

logger = logging.getLogger(__name__)


class DremioClient:
    """
    Client for interacting with Dremio via Arrow Flight.
    """

    def __init__(self):
        """Initialize Dremio client with configuration from settings."""
        self.host = settings.DREMIO_HOST
        self.port = settings.DREMIO_PORT
        self.username = settings.DREMIO_USERNAME
        self.password = settings.DREMIO_PASSWORD
        self.tls = settings.DREMIO_TLS
        self.timeout = settings.DREMIO_TIMEOUT

        self._client: Optional[flight.FlightClient] = None
        self._auth_token: Optional[bytes] = None

        logger.info(f"Dremio client initialized for {self.host}:{self.port}")

    def _get_client(self) -> flight.FlightClient:
        """
        Get or create Flight client connection.
        """
        if self._client is None:
            try:
                # Determine scheme
                scheme = "grpc+tls" if self.tls else "grpc"
                location = f"{scheme}://{self.host}:{self.port}"

                logger.info(f"Connecting to Dremio at {location}")
                self._client = flight.FlightClient(location)

                # Authenticate
                self._authenticate()

            except Exception as e:
                logger.error(f"Failed to connect to Dremio: {e}")
                raise

        return self._client

    def _authenticate(self):
        """
        Authenticate with Dremio and get auth token.
        """
        try:
            # Encode credentials in base64 for Basic authentication
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode()

            # For Dremio, we use basic auth in headers
            logger.info(f"Authenticating as {self.username}")
            # Store credentials for future requests
            self._auth_token = f"Basic {credentials}".encode()

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def _get_call_options(self) -> flight.FlightCallOptions:
        """
        Get call options with authentication.
        """
        if self._auth_token:
            return flight.FlightCallOptions(
                headers=[(b"authorization", self._auth_token)],
                timeout=self.timeout
            )
        return flight.FlightCallOptions(timeout=self.timeout)

    def execute_query(
        self,
        sql: str,
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute SQL query and return results.

        Args:
            sql: SQL query to execute
            max_rows: Maximum number of rows to return (default from settings)

        Returns:
            Dictionary with results, metadata, and execution info
        """
        max_rows = max_rows or settings.MAX_RESULT_ROWS
        start_time = datetime.now()

        try:
            client = self._get_client()
            call_options = self._get_call_options()

            logger.info(f"Executing query: {sql[:100]}...")

            # Create flight descriptor
            flight_desc = flight.FlightDescriptor.for_command(sql.encode('utf-8'))

            # Get flight info
            flight_info = client.get_flight_info(flight_desc, call_options)

            # Read all batches
            reader = client.do_get(flight_info.endpoints[0].ticket, call_options)

            # Convert to pandas DataFrame
            table = reader.read_all()
            df = table.to_pandas()

            # Limit rows if needed
            if len(df) > max_rows:
                logger.warning(f"Result truncated from {len(df)} to {max_rows} rows")
                df = df.head(max_rows)
                truncated = True
            else:
                truncated = False

            execution_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"Query executed successfully: {len(df)} rows in {execution_time:.2f}s")

            return {
                "success": True,
                "data": df.to_dict(orient='records'),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "row_count": len(df),
                "truncated": truncated,
                "execution_time": execution_time,
                "sql": sql
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Query execution failed: {e}")

            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time": execution_time,
                "sql": sql
            }

    def get_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        Get list of tables from Dremio.

        Args:
            schema: Optional schema name to filter (e.g., 'minio.gold')

        Returns:
            List of table names
        """
        try:
            if schema:
                sql = f"SHOW TABLES IN {schema}"
            else:
                # Get all tables from common schemas
                sql = """
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA IN ('minio.bronze', 'minio.silver', 'minio.gold')
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """

            result = self.execute_query(sql)

            if result["success"]:
                if schema:
                    return [row["TABLE_NAME"] for row in result["data"]]
                else:
                    return [
                        f"{row['TABLE_SCHEMA']}.{row['TABLE_NAME']}"
                        for row in result["data"]
                    ]
            else:
                logger.error(f"Failed to get tables: {result['error']}")
                return []

        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []

    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema information for a specific table.

        Args:
            table_name: Fully qualified table name (e.g., 'minio.gold.unified')

        Returns:
            Dictionary with column names, types, and sample values
        """
        try:
            # Get column information
            sql = f"DESCRIBE {table_name}"
            result = self.execute_query(sql)

            if not result["success"]:
                logger.error(f"Failed to describe table {table_name}: {result['error']}")
                return None

            columns = result["data"]

            # Get sample values
            sample_sql = f"SELECT * FROM {table_name} LIMIT 5"
            sample_result = self.execute_query(sample_sql)

            sample_values = {}
            if sample_result["success"] and sample_result["data"]:
                df = pd.DataFrame(sample_result["data"])
                for col in df.columns:
                    # Get unique non-null values
                    unique_vals = df[col].dropna().unique()[:5].tolist()
                    sample_values[col] = [str(v) for v in unique_vals]

            return {
                "table_name": table_name,
                "columns": columns,
                "sample_values": sample_values
            }

        except Exception as e:
            logger.error(f"Error getting table schema for {table_name}: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Test if connection to Dremio is working.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = self.execute_query("SELECT 1 as test")
            return result["success"]
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def close(self):
        """Close Dremio connection."""
        if self._client is not None:
            try:
                self._client.close()
                logger.info("Dremio connection closed")
            except Exception as e:
                logger.error(f"Error closing Dremio connection: {e}")
            finally:
                self._client = None
                self._auth_token = None
