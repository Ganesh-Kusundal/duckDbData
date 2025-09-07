"""DuckDB implementation of market data repository."""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

import pandas as pd

from functools import lru_cache
from ...domain.entities.market_data import MarketData, MarketDataBatch, OHLCV
from ...domain.repositories.market_data_repo import MarketDataRepository
from ..adapters.duckdb_adapter import DuckDBAdapter
from ..logging import get_logger

logger = get_logger(__name__)


class DuckDBMarketDataRepository(MarketDataRepository):
    """DuckDB implementation of market data repository."""

    def __init__(self, adapter: Optional[DuckDBAdapter] = None):
        """Initialize repository with DuckDB adapter."""
        self.adapter = adapter or DuckDBAdapter()
        logger.info("DuckDB market data repository initialized")
    
    def _row_to_market_data(self, row) -> MarketData:
        """Convert a DataFrame row to MarketData entity with proper dtype mapping."""
        ohlcv = OHLCV(
            open=Decimal(str(row['open'])),
            high=Decimal(str(row['high'])),
            low=Decimal(str(row['low'])),
            close=Decimal(str(row['close'])),
            volume=int(row['volume'])
        )
    
        # Ensure date_partition is str as expected by entity
        date_part = row['date_partition']
        if hasattr(date_part, 'strftime'):
            date_part = date_part.strftime('%Y-%m-%d')
    
        return MarketData(
            symbol=row['symbol'],
            timestamp=row['timestamp'].to_pydatetime(),
            timeframe=row['timeframe'],
            ohlcv=ohlcv,
            date_partition=str(date_part)
        )

    def save(self, data: MarketData) -> None:
        """Save a single MarketData record to the database.

        Uses the adapter to perform the insertion and logs the outcome.

        Args:
            data (MarketData): The market data record to save.

        Raises:
            Exception: If saving fails.
        """
        try:
            affected_rows = self.adapter.insert_market_data(data)
            if affected_rows > 0:
                logger.info(
                    "Market data saved",
                    symbol=data.symbol,
                    timestamp=data.timestamp.isoformat(),
                    timeframe=data.timeframe
                )
            else:
                logger.warning(
                    "No rows affected when saving market data",
                    symbol=data.symbol,
                    timestamp=data.timestamp.isoformat()
                )
        except Exception as e:
            logger.error(
                "Failed to save market data",
                symbol=data.symbol,
                timestamp=data.timestamp.isoformat(),
                error=str(e)
            )
            raise

    def save_batch(self, batch: MarketDataBatch) -> None:
        """Save a batch of MarketData records to the database.

        Efficient bulk insertion for multiple records.

        Args:
            batch (MarketDataBatch): The batch of market data to save.

        Raises:
            Exception: If batch saving fails.
        """
        try:
            affected_rows = self.adapter.insert_market_data(batch)
            logger.info(
                "Market data batch saved",
                symbol=batch.symbol,
                timeframe=batch.timeframe,
                records_count=batch.record_count,
                affected_rows=affected_rows
            )
        except Exception as e:
            logger.error(
                "Failed to save market data batch",
                symbol=batch.symbol,
                timeframe=batch.timeframe,
                error=str(e)
            )
            raise

    def find_by_symbol_and_date_range(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        timeframe: str = "1D"
    ) -> List[MarketData]:
        """Find market data records for a symbol within a date range.

        Args:
            symbol (str): The stock symbol.
            start_date (date): Start date for the range.
            end_date (date): End date for the range.
            timeframe (str): Data timeframe, default '1D'.

        Returns:
            List[MarketData]: List of matching market data entities, sorted by timestamp.

        Raises:
            Exception: If retrieval fails.
        """
        try:
            df = self.adapter.get_market_data(
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                timeframe=timeframe
            )

            if df.empty:
                logger.info(
                    "No market data found",
                    symbol=symbol,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    timeframe=timeframe
                )
                return []

            market_data_list = []
            for _, row in df.iterrows():
                market_data = self._row_to_market_data(row)
                market_data_list.append(market_data)

            logger.info(
                "Market data retrieved",
                symbol=symbol,
                records_count=len(market_data_list),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                timeframe=timeframe
            )

            return market_data_list

        except Exception as e:
            logger.error(
                "Failed to find market data",
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                timeframe=timeframe,
                error=str(e)
            )
            raise

    @lru_cache(maxsize=128)
    def find_latest_by_symbol(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[MarketData]:
        """Find the latest market data records for a symbol, sorted by timestamp DESC.

        Args:
            symbol (str): The stock symbol.
            limit (int): Number of records to return, default 100.

        Returns:
            List[MarketData]: List of latest market data entities.

        Raises:
            Exception: If retrieval fails.
        """
        try:
            df = self.adapter.get_latest_market_data(symbol=symbol, limit=limit)

            if df.empty:
                logger.info("No latest market data found", symbol=symbol, limit=limit)
                return []

            market_data_list = []
            for _, row in df.iterrows():
                market_data = self._row_to_market_data(row)
                market_data_list.append(market_data)

            logger.info(
                "Latest market data retrieved",
                symbol=symbol,
                records_count=len(market_data_list),
                limit=limit
            )

            return market_data_list

        except Exception as e:
            logger.error(
                "Failed to find latest market data",
                symbol=symbol,
                limit=limit,
                error=str(e)
            )
            raise

    def exists(self, symbol: str, timestamp: str) -> bool:
        """Check if a market data record exists for the given symbol and timestamp.

        Args:
            symbol (str): The stock symbol.
            timestamp (str): The timestamp in ISO format.

        Returns:
            bool: True if the record exists, False otherwise.

        Raises:
            Exception: If check fails.
        """
        try:
            query = """
                SELECT COUNT(*) as count
                FROM market_data
                WHERE symbol = ? AND timestamp = ?
            """
            df = self.adapter.execute_query(query, [symbol, timestamp])
            exists = df.iloc[0]['count'] > 0

            logger.debug(
                "Market data existence check",
                symbol=symbol,
                timestamp=timestamp,
                exists=exists
            )

            return exists

        except Exception as e:
            logger.error(
                "Failed to check market data existence",
                symbol=symbol,
                timestamp=timestamp,
                error=str(e)
            )
            raise

    def count_by_symbol(self, symbol: str) -> int:
        """Count the total number of market data records for a symbol.

        Args:
            symbol (str): The stock symbol.

        Returns:
            int: The number of records for the symbol.

        Raises:
            Exception: If count query fails.
        """
        try:
            query = """
                SELECT COUNT(*) as count
                FROM market_data
                WHERE symbol = ?
            """
            df = self.adapter.execute_query(query, [symbol])
            count = int(df.iloc[0]['count'])

            logger.info("Market data count retrieved", symbol=symbol, count=count)
            return count

        except Exception as e:
            logger.error(
                "Failed to count market data",
                symbol=symbol,
                error=str(e)
            )
            raise

    def get_date_range(self, symbol: str) -> Optional[Tuple[date, date]]:
        """Get the date range (min/max date_partition) for a symbol's data.

        Args:
            symbol (str): The stock symbol.

        Returns:
            Optional[Tuple[date, date]]: Tuple of (start_date, end_date) or None if no data.

        Raises:
            Exception: If query fails.
        """
        try:
            query = """
                SELECT
                    MIN(date_partition) as start_date,
                    MAX(date_partition) as end_date
                FROM market_data
                WHERE symbol = ?
            """
            df = self.adapter.execute_query(query, [symbol])

            if df.empty or df.iloc[0]['start_date'] is None:
                logger.info("No date range found for symbol", symbol=symbol)
                return None

            start_date = df.iloc[0]['start_date']
            end_date = df.iloc[0]['end_date']

            logger.info(
                "Date range retrieved",
                symbol=symbol,
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None
            )

            return (start_date, end_date)

        except Exception as e:
            logger.error(
                "Failed to get date range",
                symbol=symbol,
                error=str(e)
            )
            raise
