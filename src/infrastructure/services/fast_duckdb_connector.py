"""
Fast DuckDB Connector with Connection Pooling
==============================================

High-performance DuckDB connector with connection pooling and caching
for fast database operations in development and testing environments.
"""

import time
import threading
from typing import Optional, Any, List, Dict
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Queue, Empty
import duckdb
import logging

from src.infrastructure.config.settings import get_settings
from src.domain.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolStats:
    """Statistics for connection pool performance monitoring."""
    total_connections_created: int = 0
    active_connections: int = 0
    connections_reused: int = 0
    connection_wait_time: float = 0.0
    pool_hits: int = 0
    pool_misses: int = 0


class ConnectionPool:
    """Thread-safe connection pool for DuckDB connections."""

    def __init__(self, db_path: str, pool_size: int = 10, timeout: float = 30.0):
        """
        Initialize the connection pool.

        Args:
            db_path: Path to the DuckDB database file
            pool_size: Maximum number of connections in the pool
            timeout: Timeout for getting a connection from the pool
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._stats = ConnectionPoolStats()

        # Pre-populate the pool with connections
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool with initial connections."""
        for _ in range(min(self.pool_size, 3)):  # Start with 3 connections
            try:
                conn = self._create_connection()
                self._pool.put(conn)
                with self._lock:
                    self._stats.active_connections += 1
            except Exception as e:
                logger.warning(f"Failed to create initial connection: {e}")

    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a new DuckDB connection."""
        try:
            # If it's a test file (temporary), delete it first to ensure clean slate
            import os
            if os.path.exists(self.db_path) and self.db_path.endswith('.db'):
                try:
                    os.unlink(self.db_path)
                except:
                    pass  # Ignore if can't delete

            conn = duckdb.connect(self.db_path, read_only=False)
            # Enable HTTPFS for S3 access if needed
            conn.execute("INSTALL httpfs;")
            conn.execute("LOAD httpfs;")
            with self._lock:
                self._stats.total_connections_created += 1
            return conn
        except Exception as e:
            raise DatabaseConnectionError(
                f"Failed to create DuckDB connection: {str(e)}",
                'create_connection',
                context={'db_path': self.db_path}
            )

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Get a connection from the pool.

        Returns:
            DuckDB connection

        Raises:
            DatabaseConnectionError: If unable to get connection
        """
        start_time = time.time()

        try:
            # Try to get connection from pool
            conn = self._pool.get(timeout=self.timeout)
            with self._lock:
                self._stats.pool_hits += 1
                self._stats.connection_wait_time += (time.time() - start_time)
            return conn
        except Empty:
            # Pool is empty, create new connection
            with self._lock:
                self._stats.pool_misses += 1
                self._stats.connection_wait_time += (time.time() - start_time)

            if self._stats.active_connections >= self.pool_size:
                raise DatabaseConnectionError(
                    "Connection pool exhausted",
                    'get_connection',
                    context={
                        'pool_size': self.pool_size,
                        'active_connections': self._stats.active_connections
                    }
                )

            conn = self._create_connection()
            with self._lock:
                self._stats.active_connections += 1
            return conn

    def return_connection(self, conn: duckdb.DuckDBPyConnection):
        """
        Return a connection to the pool.

        Args:
            conn: Connection to return
        """
        try:
            # Test if connection is still valid
            conn.execute("SELECT 1").fetchone()

            # Return to pool if not full
            if self._pool.qsize() < self.pool_size:
                self._pool.put(conn)
                with self._lock:
                    self._stats.connections_reused += 1
            else:
                # Pool is full, close connection
                conn.close()
                with self._lock:
                    self._stats.active_connections -= 1
        except Exception as e:
            logger.warning(f"Connection is invalid, closing: {e}")
            try:
                conn.close()
            except:
                pass
            with self._lock:
                self._stats.active_connections -= 1

    def close_all(self):
        """Close all connections in the pool."""
        closed_count = 0
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
                closed_count += 1
            except:
                pass

        with self._lock:
            self._stats.active_connections -= closed_count

        logger.info(f"Closed {closed_count} connections from pool")

    def get_stats(self) -> ConnectionPoolStats:
        """Get pool statistics."""
        with self._lock:
            return self._stats

    @property
    def pool_efficiency(self) -> float:
        """Calculate pool efficiency as hit ratio."""
        total_requests = self._stats.pool_hits + self._stats.pool_misses
        if total_requests == 0:
            return 0.0
        return (self._stats.pool_hits / total_requests) * 100.0


class FastDuckDBConnector:
    """
    High-performance DuckDB connector with connection pooling.

    This connector provides fast database operations by reusing connections
    and implementing performance optimizations for development workflows.
    """

    def __init__(self, db_path: Optional[str] = None, pool_size: int = 10):
        """
        Initialize the fast DuckDB connector.

        Args:
            db_path: Path to DuckDB database file
            pool_size: Size of connection pool
        """
        settings = get_settings()

        self.db_path = db_path or settings.database.path
        self.pool_size = pool_size or settings.performance.connection_pool_size
        self.fast_mode = settings.performance.is_fast_mode

        # Initialize connection pool
        self._pool = ConnectionPool(
            db_path=self.db_path,
            pool_size=self.pool_size,
            timeout=settings.performance.connection_pool_timeout
        )

        # Query cache for fast mode
        self._query_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = settings.performance.query_cache_ttl

        logger.info(
            "FastDuckDBConnector initialized",
            db_path=self.db_path,
            pool_size=self.pool_size,
            fast_mode=self.fast_mode
        )

    @contextmanager
    def get_connection(self):
        """
        Context manager for getting a connection from the pool.

        Yields:
            DuckDB connection
        """
        conn = self._pool.get_connection()
        try:
            yield conn
        finally:
            self._pool.return_connection(conn)

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """
        Execute a query using the connection pool.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query result
        """
        start_time = time.time()

        # Check cache in fast mode
        if self.fast_mode and self._should_cache_query(query):
            cached_result = self._get_cached_result(query, params)
            if cached_result is not None:
                execution_time = time.time() - start_time
                logger.debug(
                    "Query served from cache",
                    query=query[:100],
                    execution_time=execution_time,
                    cached=True
                )
                return cached_result

        # Execute query using pooled connection
        with self.get_connection() as conn:
            try:
                if params:
                    result = conn.execute(query, params).fetchall()
                else:
                    result = conn.execute(query).fetchall()

                execution_time = time.time() - start_time

                # Cache result in fast mode
                if self.fast_mode and self._should_cache_query(query):
                    self._cache_result(query, params, result, execution_time)

                logger.debug(
                    "Query executed",
                    query=query[:100],
                    execution_time=execution_time,
                    rows_returned=len(result) if result else 0,
                    cached=False
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Query execution failed: {str(e)}",
                    extra={
                        'query': query[:100],
                        'execution_time': execution_time
                    }
                )
                raise DatabaseConnectionError(
                    f"Query execution failed: {str(e)}",
                    'execute_query',
                    context={
                        'query': query[:100],
                        'execution_time': execution_time
                    }
                )

    def execute_query_df(self, query: str, params: Optional[List[Any]] = None):
        """
        Execute a query and return result as pandas DataFrame.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            pandas DataFrame
        """
        import pandas as pd

        with self.get_connection() as conn:
            if params:
                return conn.execute(query, params).fetchdf()
            else:
                return conn.execute(query).fetchdf()

    def _should_cache_query(self, query: str) -> bool:
        """Determine if a query should be cached."""
        # Only cache SELECT queries that are not too complex
        query_upper = query.strip().upper()
        return (
            query_upper.startswith('SELECT') and
            len(query) < 1000 and  # Not too long
            'NOW()' not in query_upper and  # Not time-dependent
            'CURRENT_TIMESTAMP' not in query_upper
        )

    def _get_cached_result(self, query: str, params: Optional[List[Any]]) -> Optional[Any]:
        """Get cached result if available and not expired."""
        cache_key = f"{query}:{str(params) if params else ''}"

        if cache_key in self._query_cache:
            cached_item = self._query_cache[cache_key]
            if time.time() - cached_item['timestamp'] < self._cache_ttl:
                return cached_item['result']

            # Remove expired cache entry
            del self._query_cache[cache_key]

        return None

    def _cache_result(self, query: str, params: Optional[List[Any]], result: Any, execution_time: float):
        """Cache query result."""
        cache_key = f"{query}:{str(params) if params else ''}"

        self._query_cache[cache_key] = {
            'result': result,
            'timestamp': time.time(),
            'execution_time': execution_time
        }

        # Limit cache size (simple LRU eviction)
        if len(self._query_cache) > 100:
            oldest_key = min(
                self._query_cache.keys(),
                key=lambda k: self._query_cache[k]['timestamp']
            )
            del self._query_cache[oldest_key]

    def get_pool_stats(self) -> ConnectionPoolStats:
        """Get connection pool statistics."""
        return self._pool.get_stats()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        stats = self._pool.get_stats()

        return {
            'pool_efficiency': self._pool.pool_efficiency,
            'total_connections_created': stats.total_connections_created,
            'active_connections': stats.active_connections,
            'connections_reused': stats.connections_reused,
            'pool_hits': stats.pool_hits,
            'pool_misses': stats.pool_misses,
            'avg_connection_wait_time': (
                stats.connection_wait_time / (stats.pool_hits + stats.pool_misses)
                if (stats.pool_hits + stats.pool_misses) > 0 else 0
            ),
            'cache_size': len(self._query_cache),
            'fast_mode_enabled': self.fast_mode
        }

    def close(self):
        """Close the connector and cleanup resources."""
        self._pool.close_all()
        self._query_cache.clear()
        logger.info("FastDuckDBConnector closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
