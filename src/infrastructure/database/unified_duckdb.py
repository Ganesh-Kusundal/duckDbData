"""
Unified DuckDB Integration Layer
================================

Consolidates multiple DuckDB connection flows into a single, well-architected abstraction
that provides efficient connection management, unified query execution, and proper resource handling.
"""

import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Dict, List, Optional, Union, Protocol

import duckdb
import pandas as pd
from duckdb import DuckDBPyConnection

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DuckDBConfig:
    """Configuration for unified DuckDB operations."""
    database_path: str
    max_connections: int = 10
    connection_timeout: float = 30.0
    memory_limit: str = "2GB"
    threads: int = 4
    enable_object_cache: bool = True
    enable_profiling: bool = False
    read_only: bool = False
    enable_httpfs: bool = True
    parquet_root: Optional[str] = None
    parquet_glob: Optional[str] = None
    use_parquet_in_unified_view: bool = True


class ConnectionPool:
    """Thread-safe connection pool for DuckDB connections."""

    def __init__(self, config: DuckDBConfig):
        self.config = config
        self._pool: Queue[DuckDBPyConnection] = Queue(maxsize=config.max_connections)
        self._lock = threading.Lock()
        self._active_connections = 0
        self._closed = False

        # Ensure database directory exists
        db_path = Path(config.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Connection pool initialized", max_connections=config.max_connections)

    def get_connection(self) -> DuckDBPyConnection:
        """Get a connection from the pool, creating one if necessary."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        try:
            # Try to get existing connection from pool
            conn = self._pool.get_nowait()
            logger.debug("Reusing connection from pool")
            return conn
        except Empty:
            pass

        # Create new connection if pool is not full
        with self._lock:
            if self._active_connections >= self.config.max_connections:
                raise RuntimeError(f"Connection pool exhausted (max: {self.config.max_connections})")

            self._active_connections += 1

        try:
            conn = self._create_connection()
            logger.debug("Created new connection")
            return conn
        except Exception as e:
            with self._lock:
                self._active_connections -= 1
            raise

    def release_connection(self, conn: DuckDBPyConnection) -> None:
        """Return a connection to the pool."""
        if self._closed:
            conn.close()
            return

        try:
            # Test if connection is still valid
            conn.execute("SELECT 1").fetchone()
            self._pool.put_nowait(conn)
            logger.debug("Connection returned to pool")
        except Exception:
            # Connection is invalid, close it and reduce active count
            conn.close()
            with self._lock:
                self._active_connections -= 1
            logger.warning("Invalid connection discarded from pool")

    def close_all(self) -> None:
        """Close all connections in the pool."""
        self._closed = True

        # Close connections currently in pool
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break

        with self._lock:
            self._active_connections = 0

        logger.info("All connections closed")

    def _create_connection(self) -> DuckDBPyConnection:
        """Create a new DuckDB connection with proper configuration."""
        # DuckDB configuration - only use valid options
        config = {
            'memory_limit': self.config.memory_limit,
            'threads': self.config.threads,
        }

        # Add read_only mode if supported and requested
        if self.config.read_only:
            config['access_mode'] = 'READ_ONLY'

        # Handle case where file exists but is not a valid DuckDB database
        if os.path.exists(self.config.database_path) and os.path.getsize(self.config.database_path) == 0:
            os.remove(self.config.database_path)

        conn = duckdb.connect(self.config.database_path, config=config)

        # Performance switches
        try:
            if self.config.enable_object_cache:
                conn.execute("SET enable_object_cache=true")
            if self.config.threads:
                conn.execute(f"SET threads={int(self.config.threads)}")
            if self.config.enable_profiling:
                conn.execute("PRAGMA enable_profiling='json'")
                conn.execute("PRAGMA profiling_output='duckdb_profile.json'")
        except Exception:
            # Non-fatal if DuckDB rejects any PRAGMA/SET on older versions
            pass

        # Enable HTTPFS for external data access if requested
        if self.config.enable_httpfs:
            try:
                conn.execute("INSTALL httpfs;")
                conn.execute("LOAD httpfs;")
            except Exception:
                logger.warning("Failed to enable HTTPFS extension")

        return conn

    @property
    def active_connections(self) -> int:
        """Get the number of currently active connections."""
        return self._active_connections

    @property
    def available_connections(self) -> int:
        """Get the number of available connections in the pool."""
        return self._pool.qsize()


class SchemaManager:
    """Manages database schema initialization and validation."""

    def __init__(self, config: DuckDBConfig, connection_pool: ConnectionPool):
        self.config = config
        self.connection_pool = connection_pool
        self._schema_initialized = False
        self._lock = threading.Lock()

    def initialize_schema(self) -> None:
        """Initialize database schema if not already done."""
        if self._schema_initialized:
            return

        with self._lock:
            if self._schema_initialized:
                return

            with self._get_connection() as conn:
                self._create_tables(conn)
                self._create_indexes(conn)
                self._initialize_external_parquet_view_if_configured(conn)

            self._schema_initialized = True
            logger.info("Database schema initialized")

    def _create_tables(self, conn: DuckDBPyConnection) -> None:
        """Create database tables from schema configuration."""
        # Load schema from config if available
        try:
            from src.infrastructure.config.config_manager import ConfigManager
            config_manager = ConfigManager()
            schema_config = config_manager.get_config('database').get('db_schema', {})
        except Exception:
            # Fallback to default schema
            schema_config = self._get_default_schema()

        # Create tables
        for table_name, table_config in schema_config.items():
            if 'create_sql' in table_config:
                conn.execute(table_config['create_sql'])
                logger.debug(f"Created table: {table_name}")

    def _create_indexes(self, conn: DuckDBPyConnection) -> None:
        """Create database indexes from schema configuration."""
        try:
            from src.infrastructure.config.config_manager import ConfigManager
            config_manager = ConfigManager()
            schema_config = config_manager.get_config('database').get('db_schema', {})

            if 'indexes' in schema_config:
                for index_name, index_sql in schema_config['indexes'].items():
                    conn.execute(index_sql)
                    logger.debug(f"Created index: {index_name}")
        except Exception:
            logger.warning("Could not load schema configuration for indexes")

    def _initialize_external_parquet_view_if_configured(self, conn: DuckDBPyConnection) -> None:
        """Create unified view combining table + parquet data."""
        if not self.config.use_parquet_in_unified_view:
            return

        glob = self._parquet_glob()
        if not glob:
            return

        # Check if market_data table exists
        table_exists = False
        cols = set()
        try:
            exists_row = conn.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'market_data'
                """
            ).fetchone()
            table_exists = exists_row is not None

            if table_exists:
                col_rows = conn.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'market_data'
                    """
                ).fetchall()
                cols = {r[0] for r in col_rows}
        except Exception:
            table_exists = False

        # Unified schema columns
        unified_cols = [
            "symbol", "timestamp", "open", "high", "low", "close", "volume", "timeframe", "date_partition"
        ]

        # Build table projection
        table_select = None
        if table_exists:
            parts = [
                "CAST(symbol AS VARCHAR) AS symbol" if "symbol" in cols else "CAST(NULL AS VARCHAR) AS symbol",
                "CAST(timestamp AS TIMESTAMP) AS timestamp" if "timestamp" in cols else "CAST(NULL AS TIMESTAMP) AS timestamp",
                "CAST(open AS DOUBLE) AS open" if "open" in cols else "CAST(NULL AS DOUBLE) AS open",
                "CAST(high AS DOUBLE) AS high" if "high" in cols else "CAST(NULL AS DOUBLE) AS high",
                "CAST(low AS DOUBLE) AS low" if "low" in cols else "CAST(NULL AS DOUBLE) AS low",
                "CAST(close AS DOUBLE) AS close" if "close" in cols else "CAST(NULL AS DOUBLE) AS close",
                "CAST(volume AS BIGINT) AS volume" if "volume" in cols else "CAST(NULL AS BIGINT) AS volume",
                "COALESCE(timeframe, '1m') AS timeframe" if "timeframe" in cols else "'1m' AS timeframe",
                (
                    "date_partition" if "date_partition" in cols
                    else ("CAST(timestamp AS DATE) AS date_partition" if "timestamp" in cols else "CAST(NULL AS DATE) AS date_partition")
                ),
            ]
            table_select = "SELECT " + ", ".join(parts) + " FROM market_data"

        # Build parquet projection
        parquet_select = f"""
        SELECT
            COALESCE(symbol, regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1)) AS symbol,
            CAST(timestamp AS TIMESTAMP) AS timestamp,
            CAST(open AS DOUBLE) AS open,
            CAST(high AS DOUBLE) AS high,
            CAST(low AS DOUBLE) AS low,
            CAST(close AS DOUBLE) AS close,
            CAST(COALESCE(volume, 0) AS BIGINT) AS volume,
            COALESCE(timeframe, '1m') AS timeframe,
            COALESCE(CAST(timestamp AS DATE), CURRENT_DATE) AS date_partition
        FROM read_parquet('{glob}', filename=true)
        """

        if table_select:
            view_sql = f"""
            CREATE OR REPLACE VIEW market_data_unified AS
            {table_select}
            UNION ALL
            {parquet_select}
            """
        else:
            view_sql = f"CREATE OR REPLACE VIEW market_data_unified AS {parquet_select}"

        conn.execute(view_sql)
        logger.info("Unified market_data_unified view created", parquet_glob=glob, table_included=table_select is not None)

    def _parquet_glob(self) -> Optional[str]:
        """Build glob pattern for partitioned parquet files."""
        root = self.config.parquet_root
        if not root:
            return None

        custom = self.config.parquet_glob
        if custom:
            return custom

        # Default recursive glob for the expected structure
        return str(Path(root) / "*" / "*" / "*" / "*.parquet")

    def _get_default_schema(self) -> Dict[str, Any]:
        """Get default schema configuration."""
        return {
            'market_data': {
                'create_sql': """
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol VARCHAR,
                    timestamp TIMESTAMP,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    timeframe VARCHAR DEFAULT '1m',
                    date_partition DATE,
                    PRIMARY KEY (symbol, timestamp, timeframe)
                )
                """
            },
            'symbols': {
                'create_sql': """
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    sector VARCHAR,
                    industry VARCHAR,
                    exchange VARCHAR,
                    first_date DATE,
                    last_date DATE,
                    total_records BIGINT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            },
            'scanner_results': {
                'create_sql': """
                CREATE TABLE IF NOT EXISTS scanner_results (
                    id VARCHAR PRIMARY KEY,
                    scanner_name VARCHAR,
                    symbol VARCHAR,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    signals JSON,
                    execution_time_ms DOUBLE,
                    success BOOLEAN,
                    error_message VARCHAR
                )
                """
            },
            'indexes': {
                'idx_market_data_symbol_date': "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_date ON market_data(symbol, date_partition)",
                'idx_market_data_timestamp': "CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)",
                'idx_scanner_results_scanner': "CREATE INDEX IF NOT EXISTS idx_scanner_results_scanner ON scanner_results(scanner_name)",
                'idx_scanner_results_symbol': "CREATE INDEX IF NOT EXISTS idx_scanner_results_symbol ON scanner_results(symbol)"
            }
        }

    @contextmanager
    def _get_connection(self):
        """Get a connection for schema operations."""
        conn = self.connection_pool.get_connection()
        try:
            yield conn
        finally:
            self.connection_pool.release_connection(conn)


class QueryExecutor:
    """Unified query execution interface for both analytics and persistence operations."""

    def __init__(self, connection_pool: ConnectionPool):
        self.connection_pool = connection_pool

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame."""
        with self._get_connection() as conn:
            try:
                if params:
                    result = conn.execute(query, params)
                else:
                    result = conn.execute(query)
                return result.df()
            except Exception as e:
                logger.error(
                    "Query failed",
                    error=str(e),
                    query=query[:200] + '...' if len(query) > 200 else query,
                    params_count=len(params) if params else 0,
                )
                raise

    def execute_command(self, command: str, params: Optional[List[Any]] = None) -> int:
        """Execute a DML command (INSERT, UPDATE, DELETE) and return affected rows."""
        with self._get_connection() as conn:
            try:
                if params:
                    result = conn.execute(command, params)
                else:
                    result = conn.execute(command)
                return result.rows_changed
            except Exception as e:
                logger.error(
                    "Command failed",
                    error=str(e),
                    command=command[:200] + '...' if len(command) > 200 else command,
                    params_count=len(params) if params else 0,
                )
                raise

    def execute_analytics_query(self, query: str, **params) -> pd.DataFrame:
        """Execute analytics query with parameter substitution."""
        with self._get_connection() as conn:
            try:
                # Replace placeholders with actual values
                formatted_query = query
                for key, value in params.items():
                    if isinstance(value, str):
                        formatted_query = formatted_query.replace(f"{{{key}}}", f"'{value}'")
                    else:
                        formatted_query = formatted_query.replace(f"{{{key}}}", str(value))

                logger.debug(f"Executing analytics query: {formatted_query[:100]}...")
                result = conn.execute(formatted_query).df()
                logger.info(f"Analytics query returned {len(result)} rows")
                return result

            except Exception as e:
                logger.error(
                    "Analytics query failed",
                    error=str(e),
                    query=query[:200] + '...' if len(query) > 200 else query,
                    params_count=len(params),
                )
                raise

    def execute_parquet_query(self, parquet_path: str, query: str = "") -> pd.DataFrame:
        """Execute a query directly on a Parquet file."""
        with self._get_connection() as conn:
            try:
                base = f"SELECT * FROM read_parquet('{parquet_path}')"
                full_query = f"{base} {query}" if query else base
                result = conn.execute(full_query)
                return result.df()
            except Exception as e:
                logger.error(
                    "Parquet query failed",
                    error=str(e),
                    parquet_path=parquet_path,
                    query=query[:200] + '...' if len(query) > 200 else query,
                )
                raise

    @contextmanager
    def _get_connection(self):
        """Get a connection for query execution."""
        conn = self.connection_pool.get_connection()
        try:
            yield conn
        finally:
            self.connection_pool.release_connection(conn)


class UnifiedDuckDBManager:
    """Main facade for unified DuckDB operations."""

    def __init__(self, config: DuckDBConfig):
        self.config = config
        self.connection_pool = ConnectionPool(config)
        self.schema_manager = SchemaManager(config, self.connection_pool)
        self.query_executor = QueryExecutor(self.connection_pool)

        # Initialize schema on first use
        self.schema_manager.initialize_schema()

        logger.info("Unified DuckDB manager initialized", database_path=config.database_path)

    def analytics_query(self, query: str, **params) -> pd.DataFrame:
        """Execute analytics-focused query with parameter substitution."""
        return self.query_executor.execute_analytics_query(query, **params)

    def persistence_query(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """Execute persistence-focused SELECT query."""
        return self.query_executor.execute_query(query, params)

    def persistence_command(self, command: str, params: Optional[List[Any]] = None) -> int:
        """Execute data persistence command (INSERT, UPDATE, DELETE)."""
        return self.query_executor.execute_command(command, params)

    def parquet_query(self, parquet_path: str, query: str = "") -> pd.DataFrame:
        """Execute query directly on Parquet file."""
        return self.query_executor.execute_parquet_query(parquet_path, query)

    def get_connection_stats(self) -> Dict[str, int]:
        """Get connection pool statistics."""
        return {
            'active_connections': self.connection_pool.active_connections,
            'available_connections': self.connection_pool.available_connections,
            'max_connections': self.config.max_connections
        }

    def close(self) -> None:
        """Close all connections and cleanup resources."""
        self.connection_pool.close_all()
        logger.info("Unified DuckDB manager closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
