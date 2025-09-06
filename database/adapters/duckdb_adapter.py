"""DuckDB adapter for data persistence and querying."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb
import pandas as pd
from duckdb import DuckDBPyConnection

from ...domain.entities.market_data import MarketData, MarketDataBatch
from ...domain.entities.symbol import Symbol
from ..config.settings import get_settings
from ..logging import get_logger

logger = get_logger(__name__)


class DuckDBAdapter:
    """DuckDB adapter for financial data operations."""

    def __init__(self, database_path: Optional[str] = None):
        """Initialize DuckDB adapter."""
        self.settings = get_settings()
        self.database_path = database_path or self.settings.database.path
        self._connection: Optional[DuckDBPyConnection] = None

        # Ensure database directory exists
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("DuckDB adapter initialized", database_path=self.database_path)

    @property
    def connection(self) -> Optional[DuckDBPyConnection]:
        """Get the current database connection."""
        return self._connection

    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        if self._connection is None:
            # DuckDB configuration - only use valid options
            config = {
                'memory_limit': self.settings.database.memory_limit,
                'threads': self.settings.database.threads,
            }

            # Add read_only mode if supported and requested
            if hasattr(self.settings.database, 'read_only') and self.settings.database.read_only:
                # DuckDB uses different syntax for read-only mode
                config['access_mode'] = 'READ_ONLY'

            # Handle case where file exists but is not a valid DuckDB database
            if os.path.exists(self.database_path) and os.path.getsize(self.database_path) == 0:
                # Remove empty file so DuckDB can create a new database
                os.remove(self.database_path)

            self._connection = duckdb.connect(self.database_path, config=config)
            self._initialize_schema()

        try:
            yield self._connection
        except Exception as e:
            logger.error("Database operation failed", error=str(e))
            raise
        finally:
            # Keep connection alive for reuse
            pass

    def _initialize_schema(self):
        """Initialize database schema if not exists."""
        with self.get_connection() as conn:
            # Market data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    open DECIMAL(10,2) NOT NULL,
                    high DECIMAL(10,2) NOT NULL,
                    low DECIMAL(10,2) NOT NULL,
                    close DECIMAL(10,2) NOT NULL,
                    volume BIGINT NOT NULL,
                    timeframe VARCHAR NOT NULL,
                    date_partition DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, timestamp, timeframe)
                )
            """)

            # Symbols table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    sector VARCHAR,
                    industry VARCHAR,
                    exchange VARCHAR DEFAULT 'NSE',
                    first_date DATE,
                    last_date DATE,
                    total_records BIGINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scanner results table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scanner_results (
                    id VARCHAR PRIMARY KEY,
                    scanner_name VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    signals JSON,
                    execution_time_ms FLOAT,
                    success BOOLEAN DEFAULT TRUE,
                    error_message VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_date ON market_data(symbol, date_partition)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scanner_results_symbol ON scanner_results(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scanner_results_timestamp ON scanner_results(timestamp)")

            logger.info("Database schema initialized")

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame."""
        with self.get_connection() as conn:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            return result.df()

    def execute_command(self, command: str, params: Optional[List[Any]] = None) -> int:
        """Execute a command (INSERT, UPDATE, DELETE) and return affected rows."""
        with self.get_connection() as conn:
            if params:
                result = conn.execute(command, params)
            else:
                result = conn.execute(command)
            return result.rows_changed

    def insert_market_data(self, data: Union[MarketData, MarketDataBatch]) -> int:
        """Insert market data into database."""
        if isinstance(data, MarketData):
            return self._insert_single_market_data(data)
        elif isinstance(data, MarketDataBatch):
            return self._insert_market_data_batch(data)
        else:
            raise ValueError("Invalid data type for insertion")

    def _insert_single_market_data(self, data: MarketData) -> int:
        """Insert a single market data record."""
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
        """Insert a batch of market data records."""
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
        """Retrieve market data for a symbol and date range."""
        query = """
            SELECT * FROM market_data
            WHERE symbol = ?
            AND date_partition BETWEEN ? AND ?
            AND timeframe = ?
            ORDER BY timestamp
        """
        return self.execute_query(query, [symbol, start_date, end_date, timeframe])

    def get_latest_market_data(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """Get the most recent market data for a symbol."""
        query = """
            SELECT * FROM market_data
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        return self.execute_query(query, [symbol, limit])

    def upsert_symbol(self, symbol: Symbol) -> int:
        """Insert or update symbol information."""
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
        """Retrieve symbol information."""
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
        """Get all symbols from database."""
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
        """Save scanner execution results."""
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
            str(signals),  # JSON serialization
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
        """Retrieve scanner results with optional filtering."""
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
        """Get database statistics."""
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
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
