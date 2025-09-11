"""
DuckDB Adapter Implementation
Provides database connection management and query execution for DuckDB
"""

import duckdb
import asyncio
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Thread-safe connection pool for DuckDB
    Manages database connections efficiently
    """

    def __init__(self, database_path: str, max_connections: int = 10):
        self.database_path = database_path
        self.max_connections = max_connections
        self.connections = []
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_connections)

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a database connection from the pool"""
        with self.lock:
            if len(self.connections) < self.max_connections:
                conn = duckdb.connect(self.database_path)
                self.connections.append(conn)
                logger.debug(f"Created new DuckDB connection. Pool size: {len(self.connections)}")
                return conn
            else:
                # Return existing connection (DuckDB handles concurrency)
                return self.connections[0]

    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            for conn in self.connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            self.connections.clear()
            logger.info("Closed all DuckDB connections")

    def __del__(self):
        """Cleanup on destruction"""
        self.close_all()


class DuckDBAdapter:
    """
    DuckDB Adapter implementing database operations
    Provides async interface for database operations using thread pool
    """

    def __init__(self, database_path: str):
        self.database_path = database_path
        self.connection_pool = ConnectionPool(database_path)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            List of dictionaries representing result rows
        """
        def _execute():
            conn = self.connection_pool.get_connection()
            try:
                if parameters:
                    result = conn.execute(query, parameters)
                else:
                    result = conn.execute(query)

                # Convert to list of dicts
                columns = [desc[0] for desc in result.description]
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]

            except Exception as e:
                self.logger.error(f"Query execution failed: {query}", exc_info=True)
                raise

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.connection_pool.executor, _execute
            )
            self.logger.debug(f"Executed query successfully: {query[:100]}...")
            return result
        except Exception as e:
            self.logger.error(f"Async query execution failed: {e}")
            raise

    async def execute_update(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            Number of affected rows
        """
        def _execute():
            conn = self.connection_pool.get_connection()
            try:
                if parameters:
                    result = conn.execute(query, parameters)
                else:
                    result = conn.execute(query)

                # Get affected row count
                if hasattr(result, 'rowcount'):
                    return result.rowcount
                else:
                    # For DuckDB, try to get affected rows differently
                    return 1  # Default assumption

            except Exception as e:
                self.logger.error(f"Update execution failed: {query}", exc_info=True)
                raise

        try:
            affected_rows = await asyncio.get_event_loop().run_in_executor(
                self.connection_pool.executor, _execute
            )
            self.logger.debug(f"Executed update successfully: {query[:100]}... ({affected_rows} rows affected)")
            return affected_rows
        except Exception as e:
            self.logger.error(f"Async update execution failed: {e}")
            raise

    async def execute_batch(self, queries: List[Dict[str, Any]]) -> List[int]:
        """
        Execute multiple queries in batch

        Args:
            queries: List of query dictionaries with 'query' and 'parameters' keys

        Returns:
            List of affected row counts
        """
        results = []

        for query_item in queries:
            query = query_item['query']
            parameters = query_item.get('parameters')

            if 'SELECT' in query.upper():
                # For SELECT queries, return result count
                result = await self.execute_query(query, parameters)
                results.append(len(result))
            else:
                # For modification queries, return affected rows
                affected = await self.execute_update(query, parameters)
                results.append(affected)

        return results

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions
        Note: DuckDB has limited transaction support, this is a best-effort implementation
        """
        conn = self.connection_pool.get_connection()
        try:
            # DuckDB transactions are not fully async, so we handle them synchronously
            conn.begin()
            self.logger.debug("Started database transaction")

            yield conn

            conn.commit()
            self.logger.debug("Committed database transaction")

        except Exception as e:
            try:
                conn.rollback()
                self.logger.warning(f"Rolled back transaction due to error: {e}")
            except Exception as rollback_error:
                self.logger.error(f"Failed to rollback transaction: {rollback_error}")

            raise
        finally:
            # Connection is managed by pool, don't close here
            pass

    async def create_table(self, table_name: str, schema: Dict[str, str]) -> bool:
        """
        Create a table with given schema

        Args:
            table_name: Name of the table to create
            schema: Dictionary mapping column names to SQL types

        Returns:
            True if successful
        """
        columns = [f"{name} {sql_type}" for name, sql_type in schema.items()]
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"

        try:
            await self.execute_update(query)
            self.logger.info(f"Created table: {table_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create table {table_name}: {e}")
            return False

    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists
        """
        query = """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
        UNION ALL
        SELECT name FROM duckdb_tables() WHERE name=?
        """

        try:
            result = await self.execute_query(query, [table_name, table_name])
            return len(result) > 0
        except Exception:
            # Fallback query for DuckDB
            try:
                query = "SELECT 1 FROM information_schema.tables WHERE table_name = ?"
                result = await self.execute_query(query, [table_name])
                return len(result) > 0
            except Exception as e:
                self.logger.warning(f"Could not check if table exists: {e}")
                return False

    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, str]]:
        """
        Get table schema information

        Args:
            table_name: Name of the table

        Returns:
            Dictionary mapping column names to types, or None if table doesn't exist
        """
        query = f"DESCRIBE {table_name}"

        try:
            result = await self.execute_query(query)
            if result:
                return {row['column_name']: row['column_type'] for row in result}
            return None
        except Exception as e:
            self.logger.error(f"Failed to get schema for {table_name}: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check

        Returns:
            Health check results
        """
        health_info = {
            'timestamp': datetime.now().isoformat(),
            'database_path': self.database_path,
            'status': 'unknown',
            'tables_count': 0,
            'connection_pool_size': len(self.connection_pool.connections)
        }

        try:
            # Simple query to test connectivity
            result = await self.execute_query("SELECT 1 as test")
            if result and result[0]['test'] == 1:
                health_info['status'] = 'healthy'

            # Count tables
            tables_result = await self.execute_query("""
                SELECT COUNT(*) as count FROM (
                    SELECT name FROM sqlite_master WHERE type='table'
                    UNION ALL
                    SELECT name FROM duckdb_tables()
                )
            """)

            if tables_result:
                health_info['tables_count'] = tables_result[0]['count']

        except Exception as e:
            health_info['status'] = 'unhealthy'
            health_info['error'] = str(e)
            self.logger.error(f"Health check failed: {e}")

        return health_info

    def close(self):
        """Close all connections and cleanup resources"""
        self.connection_pool.close_all()
        self.connection_pool.executor.shutdown(wait=True)
        self.logger.info("DuckDB adapter closed")


# Global adapter instance for singleton pattern
_adapter_instance: Optional[DuckDBAdapter] = None
_adapter_lock = threading.Lock()


def get_duckdb_adapter(database_path: str) -> DuckDBAdapter:
    """
    Get singleton DuckDB adapter instance

    Args:
        database_path: Path to DuckDB database file

    Returns:
        DuckDBAdapter instance
    """
    global _adapter_instance

    with _adapter_lock:
        if _adapter_instance is None or _adapter_instance.database_path != database_path:
            if _adapter_instance:
                _adapter_instance.close()
            _adapter_instance = DuckDBAdapter(database_path)

    return _adapter_instance
