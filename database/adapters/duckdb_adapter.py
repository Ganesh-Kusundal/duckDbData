"""DuckDB adapter for data persistence and querying using unified infrastructure."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb
import pandas as pd
import json
from duckdb import DuckDBPyConnection

from src.domain.entities.market_data import MarketData, MarketDataBatch
from src.domain.entities.symbol import Symbol
from src.infrastructure.config.settings import get_settings
from src.infrastructure.logging import get_logger
from src.infrastructure.database import UnifiedDuckDBManager, DuckDBConfig

logger = get_logger(__name__)


class DuckDBAdapter:
    """DuckDB adapter for financial data operations using unified infrastructure.

    Refactored to use the UnifiedDuckDBManager for consistent connection handling,
    eliminating multiple connection flows and improving resource management.
    """

    def __init__(self, database_path: Optional[str] = None):
        """Initialize the DuckDB adapter with unified infrastructure.

        Args:
            database_path (Optional[str]): Path to the DuckDB database file. If not provided, uses default from settings.

        Raises:
            ValueError: If invalid path is provided.
        """
        self.settings = get_settings()
        self.database_path = database_path or self.settings.database.path

        # Build unified configuration
        config = self._build_unified_config()

        # Initialize unified manager (handles schema, connections, etc.)
        self.db_manager = UnifiedDuckDBManager(config)

        logger.info("DuckDB adapter initialized with unified infrastructure", database_path=self.database_path)

    def _build_unified_config(self) -> DuckDBConfig:
        """Build unified DuckDB configuration from settings."""
        return DuckDBConfig(
            database_path=self.database_path,
            max_connections=getattr(self.settings.database, 'max_connections', 10),
            connection_timeout=getattr(self.settings.database, 'connection_timeout', 30.0),
            memory_limit=getattr(self.settings.database, 'memory_limit', '2GB'),
            threads=getattr(self.settings.database, 'threads', 4),
            enable_object_cache=getattr(self.settings.database, 'enable_object_cache', True),
            enable_profiling=getattr(self.settings.database, 'enable_profiling', False),
            read_only=getattr(self.settings.database, 'read_only', False),
            enable_httpfs=getattr(self.settings.database, 'enable_httpfs', True),
            parquet_root=getattr(self.settings.database, 'parquet_root', './data/'),
            parquet_glob=getattr(self.settings.database, 'parquet_glob', None),
            use_parquet_in_unified_view=getattr(self.settings.database, 'use_parquet_in_unified_view', True)
        )

    @property
    def connection(self) -> Optional[DuckDBPyConnection]:
        """Get the current database connection from unified manager.

        Returns:
            Optional[DuckDBPyConnection]: For backward compatibility, returns None since unified manager handles connections internally.
        """
        # For backward compatibility, return None since unified manager handles connections internally
        return None

    def get_connection_stats(self) -> Dict[str, int]:
        """Get connection pool statistics from unified manager."""
        return self.db_manager.get_connection_stats()

    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup using unified manager.

        Yields:
            DuckDBPyConnection: The connection object for use in with block.

        Raises:
            Exception: If connection fails.
        """
        # For backward compatibility, provide a context that yields None
        # Most operations should use the unified manager methods directly
        yield None

    def _initialize_schema(self):
        """Initialize database schema if not exists.

        Loads schema definitions from configs/database.yaml and executes them.
        Includes table creation and index setup.
        """
        # Load schema from config
        schema_config = get_settings().database.db_schema

        with self.get_connection() as conn:
            # Create tables
            for table_name, table_config in schema_config.items():
                if 'create_sql' in table_config:
                    conn.execute(table_config['create_sql'])

            # Create indexes
            if 'indexes' in schema_config:
                for index_name, index_sql in schema_config['indexes'].items():
                    conn.execute(index_sql)

            logger.info("Database schema initialized from config")

    def _parquet_glob(self) -> Optional[str]:
        """Build glob for partitioned parquet files from settings.

        Supports directory structure: YYYY/MM/DD/SYMBOL_minute_YYYY-MM-DD.parquet
        """
        root = getattr(self.settings.database, 'parquet_root', None)
        if not root:
            return None
        custom = getattr(self.settings.database, 'parquet_glob', None)
        if custom:
            return custom
        # Default recursive glob to match the given structure
        return str(Path(root) / "*" / "*" / "*" / "*.parquet")

    def _initialize_external_parquet_view_if_configured(self):
        """Create a unified view that unions table + parquet scan when enabled.

        View name: market_data_unified
        Left side: persistent table `market_data`
        Right side: direct parquet scan via read_parquet(glob, filename=true)
        """
        try:
            if not getattr(self.settings.database, 'use_parquet_in_unified_view', True):
                return
            glob = self._parquet_glob()
            if not glob:
                return

            with self.get_connection() as conn:
                # Detect market_data presence and columns
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
                    cols = set()

                # Target unified schema
                unified_cols = [
                    "symbol", "timestamp", "open", "high", "low", "close", "volume", "timeframe", "date_partition"
                ]

                # Build table projection, adding literals/defaults if columns missing
                table_select = None
                if table_exists:
                    parts = [
                        "symbol" if "symbol" in cols else "CAST(NULL AS VARCHAR) AS symbol",
                        "timestamp" if "timestamp" in cols else "CAST(NULL AS TIMESTAMP) AS timestamp",
                        "open" if "open" in cols else "CAST(NULL AS DOUBLE) AS open",
                        "high" if "high" in cols else "CAST(NULL AS DOUBLE) AS high",
                        "low" if "low" in cols else "CAST(NULL AS DOUBLE) AS low",
                        "close" if "close" in cols else "CAST(NULL AS DOUBLE) AS close",
                        "volume" if "volume" in cols else "CAST(NULL AS BIGINT) AS volume",
                        ("COALESCE(timeframe, '1m') AS timeframe" if "timeframe" in cols else "'1m' AS timeframe"),
                        (
                            "COALESCE(date_partition, CAST(timestamp AS DATE)) AS date_partition"
                            if "date_partition" in cols and "timestamp" in cols
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
                    COALESCE(date_partition, CAST(timestamp AS DATE)) AS date_partition
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
        except Exception as e:
            # Log and continue; unified view is optional
            logger.warning("Failed to create market_data_unified view", error=str(e))

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame.

        Args:
            query (str): SQL SELECT query string.
            params (Optional[List[Any]]): List of parameters for parameterized query.

        Returns:
            pd.DataFrame: Query results as Pandas DataFrame.

        Raises:
            Exception: If query execution fails.
        """
        try:
            with self.get_connection() as conn:
                if params:
                    result = conn.execute(query, params)
                else:
                    result = conn.execute(query)
                return result.df()
        except Exception as e:
            # Log context-rich error and re-raise
            snippet = (query or "")
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."
            logger.error(
                "Query failed",
                error=str(e),
                query=snippet,
                params_count=len(params) if params else 0,
            )
            raise

    def execute_command(self, command: str, params: Optional[List[Any]] = None) -> int:
        """Execute a DML command (INSERT, UPDATE, DELETE) and return number of affected rows.

        Args:
            command (str): SQL DML command string.
            params (Optional[List[Any]]): List of parameters for parameterized command.

        Returns:
            int: Number of rows affected by the command.

        Raises:
            Exception: If command execution fails.
        """
        try:
            with self.get_connection() as conn:
                if params:
                    result = conn.execute(command, params)
                else:
                    result = conn.execute(command)
                return result.rows_changed
        except Exception as e:
            snippet = (command or "")
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."
            logger.error(
                "Command failed",
                error=str(e),
                command=snippet,
                params_count=len(params) if params else 0,
            )
            raise

    def insert_market_data(self, data: Union[MarketData, MarketDataBatch]) -> int:
        """Insert market data into the database, supporting single records or batches.

        Args:
            data (Union[MarketData, MarketDataBatch]): Single record or batch to insert.

        Returns:
            int: Number of rows inserted.

        Raises:
            ValueError: If invalid data type.
            Exception: If insertion fails.
        """
        if isinstance(data, MarketData):
            return self._insert_single_market_data(data)
        elif isinstance(data, MarketDataBatch):
            return self._insert_market_data_batch(data)
        else:
            raise ValueError("Invalid data type for insertion")

    def _insert_single_market_data(self, data: MarketData) -> int:
        """Insert a single MarketData record into the market_data table.

        Args:
            data (MarketData): The market data record to insert.

        Returns:
            int: Number of rows affected (1 if successful).

        Raises:
            Exception: If insertion fails.
        """
        query = """
            INSERT OR REPLACE INTO market_data
            (symbol, timestamp, open, high, low, close, volume, timeframe, date_partition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            data.symbol,
            data.timestamp,
            float(data.ohlcv.open),
            float(data.ohlcv.high),
            float(data.ohlcv.low),
            float(data.ohlcv.close),
            data.ohlcv.volume,
            data.timeframe,
            data.date_partition,
        ]
        return self.execute_command(query, params)

    def _insert_market_data_batch(self, batch: MarketDataBatch) -> int:
        """Insert a batch of MarketData records using efficient bulk operation.

        Args:
            batch (MarketDataBatch): The batch of market data to insert.

        Returns:
            int: Number of records inserted.

        Raises:
            Exception: If bulk insertion fails.
        """
        if not batch.data:
            return 0

        # Convert to DataFrame for efficient bulk insert
        records = []
        for data in batch.data:
            records.append({
                'symbol': data.symbol,
                'timestamp': data.timestamp,
                'open': float(data.ohlcv.open),
                'high': float(data.ohlcv.high),
                'low': float(data.ohlcv.low),
                'close': float(data.ohlcv.close),
                'volume': data.ohlcv.volume,
                'timeframe': data.timeframe,
                'date_partition': data.date_partition,
            })

        df = pd.DataFrame(records)

        with self.get_connection() as conn:
            # Use DuckDB's efficient bulk insert
            conn.register('temp_data', df)
            conn.execute("""
                INSERT OR REPLACE INTO market_data
                (symbol, timestamp, open, high, low, close, volume, timeframe, date_partition)
                SELECT symbol, timestamp, open, high, low, close, volume, timeframe, date_partition
                FROM temp_data
            """)
            return len(records)

    def get_market_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str = "1D"
    ) -> pd.DataFrame:
        """Retrieve market data for a symbol within a date range.

        Args:
            symbol (str): Stock symbol.
            start_date (str): Start date in 'YYYY-MM-DD' format.
            end_date (str): End date in 'YYYY-MM-DD' format.
            timeframe (str): Data timeframe, e.g., '1D', '1H'.

        Returns:
            pd.DataFrame: Market data records.

        Raises:
            Exception: If query fails.
        """
        query = """
            SELECT * FROM market_data
            WHERE symbol = ?
            AND date_partition BETWEEN ? AND ?
            AND timeframe = ?
            ORDER BY timestamp
        """
        return self.execute_query(query, [symbol, start_date, end_date, timeframe])

    def get_latest_market_data(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """Get the most recent market data records for a symbol.

        Args:
            symbol (str): Stock symbol.
            limit (int): Number of records to return, default 100.

        Returns:
            pd.DataFrame: Latest market data records, sorted by timestamp DESC.

        Raises:
            Exception: If query fails.
        """
        query = """
            SELECT * FROM market_data
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        return self.execute_query(query, [symbol, limit])

    def upsert_symbol(self, symbol: Symbol) -> int:
        """Insert or update symbol information in the symbols table.

        Args:
            symbol (Symbol): The symbol entity to upsert.

        Returns:
            int: Number of rows affected.

        Raises:
            Exception: If upsert fails.
        """
        query = """
            INSERT OR REPLACE INTO symbols
            (symbol, name, sector, industry, exchange, first_date, last_date, total_records, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = [
            symbol.symbol,
            symbol.name,
            symbol.sector,
            symbol.industry,
            symbol.exchange,
            symbol.first_date,
            symbol.last_date,
            symbol.total_records,
        ]
        return self.execute_command(query, params)

    def get_symbol(self, symbol: str) -> Optional[Symbol]:
        """Retrieve symbol information from the symbols table.

        Args:
            symbol (str): The symbol code to retrieve.

        Returns:
            Optional[Symbol]: The symbol entity or None if not found.

        Raises:
            Exception: If query fails.
        """
        query = "SELECT * FROM symbols WHERE symbol = ?"
        df = self.execute_query(query, [symbol])

        if df.empty:
            return None

        row = df.iloc[0]
        return Symbol(
            symbol=row['symbol'],
            name=row['name'],
            sector=row['sector'],
            industry=row['industry'],
            exchange=row['exchange'],
            first_date=row['first_date'],
            last_date=row['last_date'],
            total_records=row['total_records'],
        )

    def get_all_symbols(self) -> List[Symbol]:
        """Get all symbols from the symbols table, sorted by symbol code.

        Returns:
            List[Symbol]: List of all symbol entities.

        Raises:
            Exception: If query fails.
        """
        query = "SELECT * FROM symbols ORDER BY symbol"
        df = self.execute_query(query)

        symbols = []
        for _, row in df.iterrows():
            symbols.append(Symbol(
                symbol=row['symbol'],
                name=row['name'],
                sector=row['sector'],
                industry=row['industry'],
                exchange=row['exchange'],
                first_date=row['first_date'],
                last_date=row['last_date'],
                total_records=row['total_records'],
            ))
        return symbols

    def save_scanner_result(
        self,
        scanner_name: str,
        symbol: str,
        signals: List[Dict[str, Any]],
        execution_time_ms: float,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """Save scanner execution results to the scanner_results table.

        Args:
            scanner_name (str): Name of the scanner.
            symbol (str): Symbol scanned.
            signals (List[Dict[str, Any]]): List of signal dictionaries.
            execution_time_ms (float): Execution time in milliseconds.
            success (bool): Whether the scan was successful.
            error_message (Optional[str]): Error message if failed.

        Returns:
            str: The generated result ID.

        Raises:
            Exception: If insertion fails.
        """
        import uuid
        result_id = str(uuid.uuid4())

        query = """
            INSERT INTO scanner_results
            (id, scanner_name, symbol, timestamp, signals, execution_time_ms, success, error_message)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
        """
        params = [
            result_id,
            scanner_name,
            symbol,
            json.dumps(signals),  # JSON serialization
            execution_time_ms,
            success,
            error_message,
        ]
        self.execute_command(query, params)
        return result_id

    def get_scanner_results(
        self,
        scanner_name: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """Retrieve scanner results with optional filtering.

        Args:
            scanner_name (Optional[str]): Filter by scanner name.
            symbol (Optional[str]): Filter by symbol.
            limit (int): Maximum number of results, default 100.

        Returns:
            pd.DataFrame: Filtered scanner results, sorted by timestamp DESC.

        Raises:
            Exception: If query fails.
        """
        conditions = []
        params = []

        if scanner_name:
            conditions.append("scanner_name = ?")
            params.append(scanner_name)

        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM scanner_results
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        return self.execute_query(query, params)

    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics.

        Returns:
            Dict[str, Any]: Dictionary with stats for market_data, symbols, scanner_results.

        Raises:
            Exception: If any stats query fails.
        """
        stats = {}

        # Market data stats
        market_stats = self.execute_query("""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT symbol) as unique_symbols,
                MIN(date_partition) as earliest_date,
                MAX(date_partition) as latest_date
            FROM market_data
        """)
        if not market_stats.empty:
            stats['market_data'] = market_stats.iloc[0].to_dict()

        # Symbol stats
        symbol_stats = self.execute_query("SELECT COUNT(*) as total_symbols FROM symbols")
        if not symbol_stats.empty:
            stats['symbols'] = symbol_stats.iloc[0].to_dict()

        # Scanner results stats
        scanner_stats = self.execute_query("""
            SELECT
                COUNT(*) as total_results,
                COUNT(DISTINCT scanner_name) as unique_scanners
            FROM scanner_results
        """)
        if not scanner_stats.empty:
            stats['scanner_results'] = scanner_stats.iloc[0].to_dict()

        return stats

    def close(self):
        """Close the database connection.

        Ensures resources are cleaned up.
        """
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point, closes connection."""
        self.close()

    def execute_parquet_query(self, parquet_path: str, query: str = "") -> pd.DataFrame:
        """Execute a query on a Parquet file using DuckDB.

        Args:
            parquet_path (str): Path to the Parquet file.
            query (str): Additional SQL query to append after SELECT * FROM parquet.

        Returns:
            pd.DataFrame: Results from the Parquet query.

        Raises:
            Exception: If query fails.
        """
        with self.get_connection() as conn:
            # Support both file and glob paths; use read_parquet for better control
            base = f"SELECT * FROM read_parquet('{parquet_path}')"
            full_query = f"{base} {query}" if query else base
            result = conn.execute(full_query)
            return result.df()
