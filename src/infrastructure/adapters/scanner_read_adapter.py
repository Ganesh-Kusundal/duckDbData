"""
DuckDB Scanner Read Adapter

This adapter provides read-only access to market data for scanner operations.
It handles database connections and query execution for scanner components.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, time
import duckdb
import pandas as pd

from ..database.duckdb_adapter import DuckDBAdapter

logger = logging.getLogger(__name__)


class DuckDBScannerReadAdapter:
    """
    Read adapter for scanner operations using DuckDB.

    Provides optimized read operations for market data scanning,
    with connection pooling and query caching capabilities.
    """

    def __init__(self, db_path: str = ":memory:", max_connections: int = 5):
        """
        Initialize the scanner read adapter.

        Args:
            db_path: Path to DuckDB database file
            max_connections: Maximum number of connections to maintain
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.unified_manager = None

        # Initialize connection pool
        self._connection_pool = []
        self._init_connection_pool()

        logger.info(f"Initialized DuckDBScannerReadAdapter with db_path: {db_path}")

    @property
    def db_connection(self):
        """
        Get database connection for compatibility with rule engine.

        Returns:
            DuckDB connection object
        """
        return self.get_connection()

    def _init_connection_pool(self):
        """Initialize the connection pool."""
        try:
            for i in range(self.max_connections):
                conn = duckdb.connect(self.db_path, read_only=True)
                self._connection_pool.append({
                    'connection': conn,
                    'in_use': False,
                    'last_used': datetime.now()
                })
            logger.info(f"Initialized connection pool with {self.max_connections} connections")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    def get_connection(self):
        """
        Get a connection from the pool.

        Returns:
            DuckDB connection

        Raises:
            RuntimeError: If no connections are available
        """
        for conn_info in self._connection_pool:
            if not conn_info['in_use']:
                conn_info['in_use'] = True
                conn_info['last_used'] = datetime.now()
                return conn_info['connection']

        raise RuntimeError("No available connections in pool")

    def release_connection(self, connection):
        """
        Release a connection back to the pool.

        Args:
            connection: Connection to release
        """
        for conn_info in self._connection_pool:
            if conn_info['connection'] == connection:
                conn_info['in_use'] = False
                break

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a read query.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        conn = None
        try:
            conn = self.get_connection()
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)

            # Convert to list of dictionaries
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def get_market_data_for_date(self, scan_date: date, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get market data for a specific date.

        Args:
            scan_date: Date to get data for
            symbol: Optional symbol filter

        Returns:
            Pandas DataFrame with market data
        """
        date_str = scan_date.strftime('%Y-%m-%d')

        if symbol:
            query = """
                SELECT symbol, timestamp, open, high, low, close, volume
                FROM market_data
                WHERE DATE(timestamp) = ?
                AND symbol = ?
                ORDER BY timestamp
            """
            params = (date_str, symbol)
        else:
            query = """
                SELECT symbol, timestamp, open, high, low, close, volume
                FROM market_data
                WHERE DATE(timestamp) = ?
                ORDER BY symbol, timestamp
            """
            params = (date_str,)

        results = self.execute_query(query, params)

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results)

    def get_market_data_time_range(
        self,
        start_date: date,
        end_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get market data for a time range.

        Args:
            start_date: Start date
            end_date: End date
            start_time: Optional start time filter
            end_time: Optional end time filter
            symbol: Optional symbol filter

        Returns:
            Pandas DataFrame with market data
        """
        conditions = []
        params = []

        # Date range
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        conditions.append("DATE(timestamp) BETWEEN ? AND ?")
        params.extend([start_date_str, end_date_str])

        # Time range
        if start_time and end_time:
            start_time_str = start_time.strftime('%H:%M:%S')
            end_time_str = end_time.strftime('%H:%M:%S')
            conditions.append("TIME(timestamp) BETWEEN ? AND ?")
            params.extend([start_time_str, end_time_str])

        # Symbol filter
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT symbol, timestamp, open, high, low, close, volume
            FROM market_data
            WHERE {where_clause}
            ORDER BY symbol, timestamp
        """

        results = self.execute_query(query, tuple(params))

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results)

    def get_scanner_statistics(
        self,
        scan_date: date,
        scanner_type: str = "breakout"
    ) -> Dict[str, Any]:
        """
        Get scanner statistics for a date.

        Args:
            scan_date: Date to get statistics for
            scanner_type: Type of scanner

        Returns:
            Dictionary with scanner statistics
        """
        date_str = scan_date.strftime('%Y-%m-%d')

        query = """
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT symbol) as unique_symbols,
                AVG(volume) as avg_volume,
                MAX(high) as max_price,
                MIN(low) as min_price,
                AVG((high - low) / open) as avg_volatility
            FROM market_data
            WHERE DATE(timestamp) = ?
        """

        results = self.execute_query(query, (date_str,))

        if not results:
            return {
                'total_records': 0,
                'unique_symbols': 0,
                'avg_volume': 0,
                'max_price': 0,
                'min_price': 0,
                'avg_volatility': 0
            }

        return results[0]

    def get_price_at_time(
        self,
        symbol: str,
        target_date: date,
        target_time: time
    ) -> Optional[Dict[str, Any]]:
        """
        Get price data at a specific time.

        Args:
            symbol: Trading symbol
            target_date: Target date
            target_time: Target time

        Returns:
            Price data dictionary or None if not found
        """
        date_str = target_date.strftime('%Y-%m-%d')
        time_str = target_time.strftime('%H:%M:%S')

        query = """
            SELECT symbol, timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = ?
            AND DATE(timestamp) = ?
            AND TIME(timestamp) <= ?
            ORDER BY timestamp DESC
            LIMIT 1
        """

        results = self.execute_query(query, (symbol, date_str, time_str))

        if results:
            return results[0]
        return None

    def get_volume_analysis(
        self,
        symbol: str,
        scan_date: date,
        lookback_period: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze volume patterns for a symbol.

        Args:
            symbol: Trading symbol
            scan_date: Date to analyze
            lookback_period: Number of days to look back

        Returns:
            Volume analysis dictionary
        """
        date_str = scan_date.strftime('%Y-%m-%d')

        query = f"""
            SELECT
                AVG(volume) as avg_volume,
                MAX(volume) as max_volume,
                MIN(volume) as min_volume,
                STDDEV(volume) as volume_stddev
            FROM market_data
            WHERE symbol = ?
            AND DATE(timestamp) >= DATE(?, '-{lookback_period} days')
            AND DATE(timestamp) <= ?
        """

        results = self.execute_query(query, (symbol, date_str, date_str))

        if not results or not results[0]['avg_volume']:
            return {
                'avg_volume': 0,
                'max_volume': 0,
                'min_volume': 0,
                'volume_stddev': 0,
                'volume_ratio': 1.0
            }

        # Get current day's volume
        current_query = """
            SELECT volume
            FROM market_data
            WHERE symbol = ?
            AND DATE(timestamp) = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """

        current_results = self.execute_query(current_query, (symbol, date_str))
        current_volume = current_results[0]['volume'] if current_results else 0

        avg_volume = results[0]['avg_volume']

        return {
            'avg_volume': avg_volume,
            'max_volume': results[0]['max_volume'],
            'min_volume': results[0]['min_volume'],
            'volume_stddev': results[0]['volume_stddev'],
            'current_volume': current_volume,
            'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1.0
        }

    def close(self):
        """Close all connections in the pool."""
        for conn_info in self._connection_pool:
            try:
                conn_info['connection'].close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

        self._connection_pool.clear()
        logger.info("Closed all connections in scanner read adapter")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
