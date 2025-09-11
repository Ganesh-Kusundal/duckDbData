"""
Market Data Repository Interface
Defines the contract for market data persistence operations
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.market_data import MarketData, MarketDataBatch


class MarketDataRepository(ABC):
    """
    Market Data Repository Interface

    This interface defines the contract for market data persistence operations.
    The infrastructure layer will provide concrete implementations.
    """

    @abstractmethod
    async def save(self, market_data: MarketData) -> bool:
        """
        Save a single market data record

        Args:
            market_data: MarketData entity to save

        Returns:
            True if successful, False otherwise

        Raises:
            RepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    async def save_batch(self, batch: MarketDataBatch) -> bool:
        """
        Save a batch of market data records efficiently

        Args:
            batch: MarketDataBatch to save

        Returns:
            True if successful, False otherwise

        Raises:
            RepositoryError: If save operation fails
        """
        pass

    @abstractmethod
    async def find_by_symbol_and_timeframe(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[MarketData]:
        """
        Find market data by symbol and timeframe

        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            timeframe: Timeframe (e.g., '1D', '1H')
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum number of records to return

        Returns:
            List of MarketData entities

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def find_latest_by_symbol(self, symbol: str, timeframe: str) -> Optional[MarketData]:
        """
        Find the latest market data record for a symbol

        Args:
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            Latest MarketData entity or None if not found

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 5000
    ) -> List[MarketData]:
        """
        Find market data within a date range

        Args:
            start_date: Start of date range
            end_date: End of date range
            symbol: Filter by symbol (optional)
            timeframe: Filter by timeframe (optional)
            limit: Maximum number of records

        Returns:
            List of MarketData entities

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def get_available_symbols(self) -> List[str]:
        """
        Get list of all available trading symbols

        Returns:
            List of unique symbol strings

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def get_symbol_count(self) -> int:
        """
        Get total count of unique symbols

        Returns:
            Number of unique symbols

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def get_data_count(self, symbol: Optional[str] = None) -> int:
        """
        Get count of market data records

        Args:
            symbol: Filter by specific symbol (optional)

        Returns:
            Number of records

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def delete_by_symbol_and_date_range(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """
        Delete market data records within date range

        Args:
            symbol: Trading symbol
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Number of records deleted

        Raises:
            RepositoryError: If delete operation fails
        """
        pass

    @abstractmethod
    async def get_ohlc_aggregate(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[dict]:
        """
        Get OHLC aggregate data for a period

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start of aggregation period
            end_date: End of aggregation period

        Returns:
            Dictionary with aggregated OHLCV data or None

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def get_volume_analysis(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[dict]:
        """
        Get volume analysis for a symbol over time period

        Args:
            symbol: Trading symbol
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Dictionary with volume statistics or None

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def exists(self, symbol: str, timestamp: str, timeframe: str) -> bool:
        """
        Check if market data record exists

        Args:
            symbol: Trading symbol
            timestamp: ISO timestamp string
            timeframe: Timeframe

        Returns:
            True if record exists, False otherwise

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def get_date_range(self, symbol: Optional[str] = None) -> Optional[tuple[datetime, datetime]]:
        """
        Get the date range of available data

        Args:
            symbol: Filter by specific symbol (optional)

        Returns:
            Tuple of (start_date, end_date) or None if no data

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """
        Perform repository health check

        Returns:
            Dictionary with health check results
        """
        pass


class RepositoryError(Exception):
    """
    Repository operation error
    Wraps underlying infrastructure errors
    """

    def __init__(self, message: str, operation: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.operation = operation
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"RepositoryError in {self.operation}: {self.message} (caused by: {self.cause})"
        return f"RepositoryError in {self.operation}: {self.message}"
