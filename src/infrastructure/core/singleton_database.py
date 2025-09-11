"""
Simple DuckDB Database Connector

A simple, lightweight database connector for DuckDB that provides basic
database connectivity without complex abstractions or connection pooling.
"""

import duckdb
import os
from typing import Optional, List, Dict, Any, Union
import pandas as pd
from contextlib import contextmanager


class SimpleDuckDBConnector:
    """
    Simple database connector for DuckDB.
    Provides basic connectivity without complex abstractions.
    """

    def __init__(self, db_path: str = "data/financial_data.duckdb",
                 read_only: bool = True):
        """
        Initialize simple database connector.

        Args:
            db_path: Path to DuckDB database file
            read_only: Whether to open database in read-only mode
        """
        self.db_path = db_path
        self.read_only = read_only
        self._connection = None

    def connect(self):
        """Connect to the database."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        self._connection = duckdb.connect(self.db_path, read_only=self.read_only)

        # Basic configuration
        self._connection.execute("SET memory_limit='2GB'")
        self._connection.execute("SET threads=2")

        return self._connection

    def get_connection(self):
        """Get database connection, connecting if necessary."""
        if self._connection is None:
            self.connect()
        return self._connection

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries."""
        conn = self.get_connection()

        try:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)

            column_names = [desc[0] for desc in result.description]
            rows = result.fetchall()
            return [dict(zip(column_names, row)) for row in rows]
        except Exception as e:
            # If connection error, try reconnecting once
            if "Connection" in str(e) or "closed" in str(e).lower():
                self._connection = None
                conn = self.get_connection()
                if params:
                    result = conn.execute(query, params)
                else:
                    result = conn.execute(query)

                column_names = [desc[0] for desc in result.description]
                rows = result.fetchall()
                return [dict(zip(column_names, row)) for row in rows]
            raise

    def execute_custom_query(self, query: str, params: Optional[Union[List[Any], Dict[str, Any]]] = None) -> pd.DataFrame:
        """Execute custom query and return results as DataFrame."""
        conn = self.get_connection()

        try:
            if params:
                if isinstance(params, dict):
                    formatted_query = query
                    param_values = []
                    for key, value in params.items():
                        placeholder = f":{key}"
                        if placeholder in formatted_query:
                            formatted_query = formatted_query.replace(placeholder, "?")
                            param_values.append(value)
                    result = conn.execute(formatted_query, param_values)
                elif isinstance(params, list):
                    result = conn.execute(query, params)
                else:
                    result = conn.execute(query, [params])
            else:
                result = conn.execute(query)

            return result.fetchdf()
        except Exception as e:
            # If connection error, try reconnecting once
            if "Connection" in str(e) or "closed" in str(e).lower():
                self._connection = None
                conn = self.get_connection()
                if params:
                    if isinstance(params, dict):
                        formatted_query = query
                        param_values = []
                        for key, value in params.items():
                            placeholder = f":{key}"
                            if placeholder in formatted_query:
                                formatted_query = formatted_query.replace(placeholder, "?")
                                param_values.append(value)
                        result = conn.execute(formatted_query, param_values)
                    elif isinstance(params, list):
                        result = conn.execute(query, params)
                    else:
                        result = conn.execute(query, [params])
                else:
                    result = conn.execute(query)

                return result.fetchdf()
            raise

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols."""
        query = "SELECT DISTINCT symbol FROM market_data_unified ORDER BY symbol"
        results = self.execute_query(query)
        return [row['symbol'] for row in results]

    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    @contextmanager
    def connection_context(self, read_only: bool = True):
        """Context manager for database operations."""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            pass  # Connection stays open for reuse


# Backward compatibility aliases
DuckDBConnectionManager = SimpleDuckDBConnector
SingletonDuckDBManager = SimpleDuckDBConnector


def create_db_manager(db_path: str = "data/financial_data.duckdb",
                     read_only: bool = True) -> SimpleDuckDBConnector:
    """Create a simple database connector."""
    return SimpleDuckDBConnector(db_path, read_only)


def get_db_manager(db_path: str = "data/financial_data.duckdb",
                  read_only: bool = True) -> SimpleDuckDBConnector:
    """Get a database connector instance."""
    return create_db_manager(db_path, read_only)
