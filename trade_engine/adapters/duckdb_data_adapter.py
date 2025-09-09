"""
DuckDB Data Access Adapter
==========================

Integrates trade engine with UnifiedDuckDBManager for efficient market data access.
Provides optimized data retrieval for backtesting and scanner operations.
"""

import asyncio
from typing import Dict, List, Optional, Tuple, AsyncIterable, Union
from datetime import date, time
from decimal import Decimal
import pandas as pd

from trade_engine.domain.models import Bar
from trade_engine.ports.data_feed import DataFeedPort
from src.infrastructure.database import UnifiedDuckDBManager, DuckDBConfig
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class DuckDBDataAdapter:
    """
    Enhanced DuckDB data access adapter using UnifiedDuckDBManager.

    Provides optimized data retrieval for backtesting with proper connection
    management, error handling, and performance monitoring.
    """

    def __init__(self, config: Dict[str, any]):
        """
        Initialize with configuration.

        Args:
            config: Configuration dictionary with database settings
        """
        self.config = config
        self.db_manager: Optional[UnifiedDuckDBManager] = None
        self._query_cache: Dict[str, pd.DataFrame] = {}

        logger.info("DuckDBDataAdapter initialized")

    async def initialize(self) -> bool:
        """
        Initialize database connection and validate setup.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Build DuckDB configuration from trade engine config
            db_config = DuckDBConfig(
                database_path=self.config.get('data', {}).get('duckdb_path', 'data/financial_data.duckdb'),
                max_connections=self.config.get('database', {}).get('max_connections', 5),
                connection_timeout=self.config.get('database', {}).get('connection_timeout', 30.0),
                memory_limit=self.config.get('database', {}).get('memory_limit', '2GB'),
                threads=self.config.get('database', {}).get('threads', 2),
                enable_object_cache=True,
                enable_profiling=False,
                read_only=True,  # Read-only for data access
                enable_httpfs=True,
                use_parquet_in_unified_view=True
            )

            # Initialize unified manager
            self.db_manager = UnifiedDuckDBManager(db_config)

            # Test connection with a simple query
            test_result = await self._execute_async_query("SELECT 1 as test")
            if test_result is not None and len(test_result) > 0:
                logger.info("Database connection established successfully")
                return True
            else:
                logger.error("Database connection test failed")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            return False

    async def _execute_async_query(self, query: str, **params) -> pd.DataFrame:
        """
        Execute query asynchronously using the unified manager.

        Args:
            query: SQL query string
            **params: Query parameters

        Returns:
            Query results as DataFrame
        """
        if not self.db_manager:
            raise RuntimeError("Database manager not initialized")

        try:
            # Use analytics_query for parameter substitution queries
            if params:
                result = self.db_manager.analytics_query(query, **params)
            else:
                result = self.db_manager.persistence_query(query)

            logger.debug(f"Query executed successfully, returned {len(result)} rows")
            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    async def get_available_symbols(self, date_range: Optional[Tuple[str, str]] = None) -> List[str]:
        """
        Get list of available symbols with optional date filtering.

        Args:
            date_range: Optional tuple of (start_date, end_date) in YYYY-MM-DD format

        Returns:
            List of available symbols
        """
        query = """
        SELECT DISTINCT symbol
        FROM market_data
        WHERE 1=1
        """

        params = {}

        if date_range:
            query += " AND date_partition BETWEEN {start_date} AND {end_date}"
            params['start_date'] = date_range[0]
            params['end_date'] = date_range[1]

        query += " ORDER BY symbol"

        try:
            result = await self._execute_async_query(query, **params)
            symbols = result['symbol'].tolist()
            logger.info(f"Retrieved {len(symbols)} available symbols")
            return symbols
        except Exception as e:
            logger.error(f"Failed to get available symbols: {e}")
            return []

    async def get_historical_bars(self, symbol: str, start_date: Union[date, str],
                                end_date: Union[date, str], timeframe: str = "1m",
                                start_time: Optional[time] = None,
                                end_time: Optional[time] = None) -> List[Bar]:
        """
        Get historical bars for a symbol within date/time range.

        Args:
            symbol: Stock symbol
            start_date: Start date for data
            end_date: End date for data
            timeframe: Bar timeframe (e.g., '1m', '5m')
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of Bar objects
        """
        query = """
        SELECT
            timestamp,
            symbol,
            open,
            high,
            low,
            close,
            volume,
            COALESCE(timeframe, {timeframe}) as timeframe,
            date_partition
        FROM market_data
        WHERE symbol = {symbol}
          AND date_partition BETWEEN {start_date} AND {end_date}
        """

        # Handle both date objects and strings
        start_date_str = start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date)
        end_date_str = end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date)

        params = {
            'symbol': symbol,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'timeframe': timeframe
        }

        # Add time filters if specified
        if start_time and end_time:
            query += """
            AND CAST(timestamp AS TIME) BETWEEN {start_time} AND {end_time}
            """
            params['start_time'] = start_time.isoformat()
            params['end_time'] = end_time.isoformat()

        query += " ORDER BY timestamp"

        try:
            result = await self._execute_async_query(query, **params)

            bars = []
            for _, row in result.iterrows():
                try:
                    bar = Bar(
                        timestamp=row['timestamp'],
                        symbol=row['symbol'],
                        open=Decimal(str(row['open'])),
                        high=Decimal(str(row['high'])),
                        low=Decimal(str(row['low'])),
                        close=Decimal(str(row['close'])),
                        volume=int(row['volume']),
                        timeframe=row['timeframe']
                    )
                    bars.append(bar)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid bar data for {symbol}: {e}")
                    continue

            logger.info(f"Retrieved {len(bars)} bars for {symbol}")
            return bars

        except Exception as e:
            logger.error(f"Failed to get historical bars for {symbol}: {e}")
            return []

    async def validate_data_integrity(self, symbol: str, date: str) -> Dict[str, any]:
        """
        Validate data integrity for a symbol on a specific date.

        Args:
            symbol: Stock symbol
            date: Date in YYYY-MM-DD format

        Returns:
            Dictionary with validation results
        """
        query = """
        SELECT
            COUNT(*) as total_records,
            COUNT(CASE WHEN open > 0 AND close > 0 THEN 1 END) as valid_records,
            AVG(volume) as avg_volume,
            MIN(low) as min_price,
            MAX(high) as max_price,
            COUNT(CASE WHEN high < low THEN 1 END) as invalid_price_records
        FROM market_data
        WHERE symbol = {symbol}
          AND date_partition = {date}
        """

        try:
            result = await self._execute_async_query(query, symbol=symbol, date=date)

            if len(result) == 0:
                return {
                    'symbol': symbol,
                    'date': date,
                    'status': 'NO_DATA',
                    'total_records': 0,
                    'valid_records': 0,
                    'data_quality_score': 0.0
                }

            row = result.iloc[0]
            total_records = row['total_records']
            valid_records = row['valid_records']
            invalid_price_records = row['invalid_price_records']

            # Calculate data quality score
            quality_score = 0.0
            if total_records > 0:
                validity_ratio = valid_records / total_records
                price_validity_ratio = 1.0 - (invalid_price_records / total_records)
                quality_score = (validity_ratio + price_validity_ratio) / 2.0

            return {
                'symbol': symbol,
                'date': date,
                'status': 'VALID' if quality_score > 0.8 else 'WARNING' if quality_score > 0.5 else 'ERROR',
                'total_records': int(total_records),
                'valid_records': int(valid_records),
                'invalid_price_records': int(invalid_price_records),
                'avg_volume': float(row['avg_volume']) if pd.notna(row['avg_volume']) else 0.0,
                'min_price': float(row['min_price']) if pd.notna(row['min_price']) else 0.0,
                'max_price': float(row['max_price']) if pd.notna(row['max_price']) else 0.0,
                'data_quality_score': round(quality_score, 3)
            }

        except Exception as e:
            logger.error(f"Failed to validate data integrity for {symbol} on {date}: {e}")
            return {
                'symbol': symbol,
                'date': date,
                'status': 'ERROR',
                'error': str(e),
                'data_quality_score': 0.0
            }

    async def get_market_summary(self, date: str) -> Dict[str, any]:
        """
        Get market summary statistics for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Dictionary with market summary statistics
        """
        query = """
        SELECT
            COUNT(DISTINCT symbol) as total_symbols,
            SUM(volume) as total_volume,
            AVG((close - open) / open) as avg_return,
            COUNT(CASE WHEN (close - open) / open > 0 THEN 1 END) as advancing_stocks,
            COUNT(CASE WHEN (close - open) / open < 0 THEN 1 END) as declining_stocks
        FROM market_data
        WHERE date_partition = {date}
          AND volume > 0
        """

        try:
            result = await self._execute_async_query(query, date=date)

            if len(result) == 0:
                return {
                    'date': date,
                    'status': 'NO_DATA',
                    'total_symbols': 0,
                    'total_volume': 0,
                    'avg_return': 0.0,
                    'advancing_stocks': 0,
                    'declining_stocks': 0
                }

            row = result.iloc[0]
            return {
                'date': date,
                'status': 'OK',
                'total_symbols': int(row['total_symbols']),
                'total_volume': int(row['total_volume']) if pd.notna(row['total_volume']) else 0,
                'avg_return': float(row['avg_return']) if pd.notna(row['avg_return']) else 0.0,
                'advancing_stocks': int(row['advancing_stocks']) if pd.notna(row['advancing_stocks']) else 0,
                'declining_stocks': int(row['declining_stocks']) if pd.notna(row['declining_stocks']) else 0
            }

        except Exception as e:
            logger.error(f"Failed to get market summary for {date}: {e}")
            return {
                'date': date,
                'status': 'ERROR',
                'error': str(e)
            }

    def get_connection_stats(self) -> Dict[str, int]:
        """
        Get database connection pool statistics.

        Returns:
            Dictionary with connection statistics
        """
        if self.db_manager:
            return self.db_manager.get_connection_stats()
        return {
            'active_connections': 0,
            'available_connections': 0,
            'max_connections': 0
        }

    async def close(self) -> None:
        """
        Close database connections and cleanup resources.
        """
        if self.db_manager:
            self.db_manager.close()
            logger.info("DuckDBDataAdapter connections closed")
        self._query_cache.clear()
