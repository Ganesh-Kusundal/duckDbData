"""Domain repository interfaces for market data."""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Tuple

from ..entities.market_data import MarketData, MarketDataBatch


class MarketDataRepository(ABC):
    """Abstract repository for market data operations."""

    @abstractmethod
    def save(self, data: MarketData) -> None:
        """Save a single market data record."""
        pass

    @abstractmethod
    def save_batch(self, batch: MarketDataBatch) -> None:
        """Save a batch of market data records."""
        pass

    @abstractmethod
    def find_by_symbol_and_date_range(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        timeframe: str = "1D"
    ) -> List[MarketData]:
        """Find market data by symbol and date range."""
        pass

    @abstractmethod
    def find_latest_by_symbol(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[MarketData]:
        """Find the latest market data records for a symbol."""
        pass

    @abstractmethod
    def exists(self, symbol: str, timestamp: str) -> bool:
        """Check if market data exists for the given symbol and timestamp."""
        pass

    @abstractmethod
    def count_by_symbol(self, symbol: str) -> int:
        """Count total records for a symbol."""
        pass

    @abstractmethod
    def get_date_range(self, symbol: str) -> Optional[Tuple[date, date]]:
        """Get the date range for a symbol's data."""
        pass
