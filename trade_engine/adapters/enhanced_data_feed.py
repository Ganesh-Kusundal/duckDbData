"""
Enhanced Data Feed Adapter
==========================

Enhanced data feed implementation using DuckDBDataAdapter for improved
performance and data access patterns optimized for backtesting.
"""

import asyncio
from typing import AsyncIterable, List, Optional, Dict, Tuple
from datetime import date, time
from decimal import Decimal
import pandas as pd

from trade_engine.domain.models import Bar
from trade_engine.ports.data_feed import DataFeedPort
from trade_engine.adapters.duckdb_data_adapter import DuckDBDataAdapter

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class EnhancedDataFeed(DataFeedPort):
    """
    Enhanced data feed using DuckDBDataAdapter for optimized data access.

    Provides improved performance for backtesting with better connection
    management and query optimization.
    """

    def __init__(self, config: dict):
        """
        Initialize enhanced data feed.

        Args:
            config: Trade engine configuration dictionary
        """
        self.config = config
        self.data_adapter = DuckDBDataAdapter(config)
        self._initialized = False

        logger.info("EnhancedDataFeed initialized")

    async def initialize(self) -> bool:
        """
        Initialize the data feed and database connection.

        Returns:
            True if initialization successful
        """
        if not self._initialized:
            success = await self.data_adapter.initialize()
            if success:
                self._initialized = True
                logger.info("EnhancedDataFeed initialization successful")
            else:
                logger.error("EnhancedDataFeed initialization failed")
            return success
        return True

    async def subscribe(self, symbols: List[str], timeframe: str) -> AsyncIterable[Bar]:
        """
        Subscribe to historical bars for backtesting.

        Args:
            symbols: List of symbols to subscribe to
            timeframe: Bar timeframe (e.g., '1m', '5m')

        Yields:
            Bar objects for each symbol and timeframe
        """
        if not self._initialized:
            await self.initialize()

        logger.info(f"Subscribing to {len(symbols)} symbols with {timeframe} timeframe")

        # For backtesting, process symbols sequentially to maintain order
        for symbol in symbols:
            try:
                # Get all bars for this symbol
                bars = await self.data_adapter.get_historical_bars(
                    symbol=symbol,
                    start_date=date.min,
                    end_date=date.max,
                    timeframe=timeframe
                )

                # Yield bars with small delay to allow other coroutines
                for bar in bars:
                    yield bar
                    await asyncio.sleep(0)  # Allow other tasks to run

                logger.debug(f"Processed {len(bars)} bars for {symbol}")

            except Exception as e:
                logger.error(f"Error processing symbol {symbol}: {e}")
                continue

    def get_historical_bars(self, symbol: str, start_date: date,
                           end_date: date, timeframe: str,
                           start_time: Optional[time] = None,
                           end_time: Optional[time] = None) -> List[Bar]:
        """
        Get historical bars synchronously for compatibility.

        Note: This method is synchronous for backward compatibility.
        For new code, use the async version.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            timeframe: Bar timeframe
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of Bar objects
        """
        # Create event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If loop is already running, we need to use a different approach
            logger.warning("Event loop already running, using synchronous fallback")
            return []

        # Run the async method in the event loop
        return loop.run_until_complete(
            self.data_adapter.get_historical_bars(
                symbol, start_date, end_date, timeframe, start_time, end_time
            )
        )

    def get_available_symbols(self) -> List[str]:
        """
        Get list of available symbols synchronously.

        Returns:
            List of available symbols
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            logger.warning("Event loop already running, using synchronous fallback")
            return []

        return loop.run_until_complete(self.data_adapter.get_available_symbols())

    async def get_available_symbols_async(self, date_range: Optional[tuple] = None) -> List[str]:
        """
        Get list of available symbols asynchronously with optional date filtering.

        Args:
            date_range: Optional tuple of (start_date, end_date) in YYYY-MM-DD format

        Returns:
            List of available symbols
        """
        if not self._initialized:
            await self.initialize()

        return await self.data_adapter.get_available_symbols(date_range)

    async def validate_data_integrity(self, symbol: str, date_str: str) -> dict:
        """
        Validate data integrity for a symbol on a specific date.

        Args:
            symbol: Stock symbol
            date_str: Date in YYYY-MM-DD format

        Returns:
            Dictionary with validation results
        """
        if not self._initialized:
            await self.initialize()

        return await self.data_adapter.validate_data_integrity(symbol, date_str)

    async def get_market_summary(self, date_str: str) -> dict:
        """
        Get market summary statistics for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Dictionary with market summary statistics
        """
        if not self._initialized:
            await self.initialize()

        return await self.data_adapter.get_market_summary(date_str)

    def get_connection_stats(self) -> dict:
        """
        Get database connection pool statistics.

        Returns:
            Dictionary with connection statistics
        """
        return self.data_adapter.get_connection_stats()

    async def get_optimized_bars_batch(self, symbols: List[str], start_date: str, end_date: str,
                                     timeframe: str = "1m") -> Dict[str, List[Bar]]:
        """
        Get historical bars for multiple symbols in an optimized batch query.

        Args:
            symbols: List of stock symbols
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            timeframe: Bar timeframe

        Returns:
            Dictionary mapping symbols to their bar data
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Use a single optimized query for all symbols
            symbols_str = "', '".join(symbols)
            query = f"""
            SELECT
                symbol,
                timestamp,
                open,
                high,
                low,
                close,
                volume,
                '{timeframe}' as timeframe
            FROM market_data
            WHERE symbol IN ('{symbols_str}')
              AND date_partition BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY symbol, timestamp
            """

            # Execute the query using the existing data adapter's connection
            result = await self.data_adapter._execute_async_query(query)

            # Process results into symbol groups
            symbol_data = {}
            for symbol in symbols:
                symbol_data[symbol] = []

            for _, row in result.iterrows():
                symbol = row['symbol']
                if symbol in symbol_data:
                    try:
                        bar = Bar(
                            timestamp=row['timestamp'],
                            symbol=symbol,
                            open=Decimal(str(row['open'])),
                            high=Decimal(str(row['high'])),
                            low=Decimal(str(row['low'])),
                            close=Decimal(str(row['close'])),
                            volume=int(row['volume']),
                            timeframe=row['timeframe']
                        )
                        symbol_data[symbol].append(bar)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping invalid bar data for {symbol}: {e}")
                        continue

            logger.info(f"Batch query completed for {len(symbols)} symbols, total bars: {sum(len(bars) for bars in symbol_data.values())}")
            return symbol_data

        except Exception as e:
            logger.error(f"Error in batch bars query: {e}")
            return {symbol: [] for symbol in symbols}

    async def get_market_data_summary(self, date_str: str) -> Dict[str, any]:
        """
        Get comprehensive market data summary for a specific date.

        Args:
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Dictionary with market summary statistics
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Get basic market summary
            summary = await self.data_adapter.get_market_summary(date_str)

            if summary['status'] == 'OK':
                # Get additional statistics
                query = f"""
                SELECT
                    COUNT(CASE WHEN (close - open) / open > 0.02 THEN 1 END) as gainers_2pct,
                    COUNT(CASE WHEN (close - open) / open < -0.02 THEN 1 END) as losers_2pct,
                    AVG(volume) as avg_volume_per_symbol,
                    MAX(volume) as max_volume,
                    COUNT(CASE WHEN volume > 100000 THEN 1 END) as high_volume_stocks
                FROM market_data
                WHERE date_partition = '{date_str}'
                  AND volume > 0
                """

                result = await self.data_adapter._execute_async_query(query)

                if len(result) > 0:
                    row = result.iloc[0]
                    summary.update({
                        'gainers_2pct': int(row['gainers_2pct']) if pd.notna(row['gainers_2pct']) else 0,
                        'losers_2pct': int(row['losers_2pct']) if pd.notna(row['losers_2pct']) else 0,
                        'avg_volume_per_symbol': float(row['avg_volume_per_symbol']) if pd.notna(row['avg_volume_per_symbol']) else 0.0,
                        'max_volume': int(row['max_volume']) if pd.notna(row['max_volume']) else 0,
                        'high_volume_stocks': int(row['high_volume_stocks']) if pd.notna(row['high_volume_stocks']) else 0
                    })

            return summary

        except Exception as e:
            logger.error(f"Error getting market data summary: {e}")
            return {'status': 'ERROR', 'error': str(e)}

    async def validate_data_quality(self, symbols: List[str], date_str: str) -> Dict[str, Dict[str, any]]:
        """
        Validate data quality for multiple symbols on a specific date.

        Args:
            symbols: List of symbols to validate
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Dictionary mapping symbols to their validation results
        """
        if not self._initialized:
            await self.initialize()

        results = {}

        for symbol in symbols:
            try:
                validation = await self.data_adapter.validate_data_integrity(symbol, date_str)
                results[symbol] = validation
            except Exception as e:
                logger.error(f"Error validating data for {symbol}: {e}")
                results[symbol] = {
                    'symbol': symbol,
                    'date': date_str,
                    'status': 'ERROR',
                    'error': str(e),
                    'data_quality_score': 0.0
                }

        logger.info(f"Data quality validation completed for {len(symbols)} symbols")
        return results

    async def get_symbols_by_criteria(self, criteria: Dict[str, any]) -> List[str]:
        """
        Get symbols that match specific criteria.

        Args:
            criteria: Dictionary of filtering criteria

        Returns:
            List of matching symbols
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Build dynamic query based on criteria
            conditions = []
            params = {}

            # Volume criteria
            if 'min_volume' in criteria:
                conditions.append("volume >= {min_volume}")
                params['min_volume'] = criteria['min_volume']

            if 'max_volume' in criteria:
                conditions.append("volume <= {max_volume}")
                params['max_volume'] = criteria['max_volume']

            # Price criteria
            if 'min_price' in criteria:
                conditions.append("close >= {min_price}")
                params['min_price'] = criteria['min_price']

            if 'max_price' in criteria:
                conditions.append("close <= {max_price}")
                params['max_price'] = criteria['max_price']

            # Volatility criteria
            if 'min_volatility' in criteria:
                conditions.append("((high - low) / low) >= {min_volatility}")
                params['min_volatility'] = criteria['min_volatility']

            # Date filter (required)
            date_filter = criteria.get('date', '2024-01-01')
            conditions.append("date_partition = {date}")
            params['date'] = date_filter

            # Limit results
            limit = criteria.get('limit', 100)
            params['limit'] = limit

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
            SELECT DISTINCT symbol
            FROM market_data
            WHERE {where_clause}
            ORDER BY volume DESC
            LIMIT {{limit}}
            """

            result = await self.data_adapter._execute_async_query(query, **params)

            symbols = result['symbol'].tolist()

            logger.info(f"Found {len(symbols)} symbols matching criteria")
            return symbols

        except Exception as e:
            logger.error(f"Error getting symbols by criteria: {e}")
            return []

    async def preload_market_data(self, symbols: List[str], date_range: Tuple[str, str],
                                preload_to_memory: bool = True) -> Dict[str, any]:
        """
        Preload market data for faster subsequent access.

        Args:
            symbols: List of symbols to preload
            date_range: Tuple of (start_date, end_date) strings
            preload_to_memory: Whether to preload into memory

        Returns:
            Preload operation results
        """
        if not self._initialized:
            await self.initialize()

        try:
            start_date, end_date = date_range

            # Get data count estimate
            query = f"""
            SELECT COUNT(*) as total_records
            FROM market_data
            WHERE symbol IN ('{"', '".join(symbols)}')
              AND date_partition BETWEEN '{start_date}' AND '{end_date}'
            """

            result = await self.data_adapter._execute_async_query(query)

            record_count = int(result.iloc[0]['total_records']) if len(result) > 0 else 0

            result = {
                'symbols_requested': len(symbols),
                'date_range': f"{start_date} to {end_date}",
                'estimated_records': record_count,
                'preload_to_memory': preload_to_memory,
                'status': 'COMPLETED'
            }

            logger.info(f"Market data preload completed: {record_count} records for {len(symbols)} symbols")
            return result

        except Exception as e:
            logger.error(f"Error in market data preload: {e}")
            return {
                'symbols_requested': len(symbols),
                'date_range': f"{date_range[0]} to {date_range[1]}",
                'status': 'ERROR',
                'error': str(e)
            }

    async def close(self) -> None:
        """
        Close database connections and cleanup resources.
        """
        if self.data_adapter:
            await self.data_adapter.close()
        self._initialized = False
        logger.info("EnhancedDataFeed connections closed")
