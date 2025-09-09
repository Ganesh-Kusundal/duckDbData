"""
Data Feed Port Interface
=======================

Abstract interface for market data feeds.
Supports both historical (backtest) and live data streams.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterable, List
from datetime import date, time

from ..domain.models import Bar


class DataFeedPort(ABC):
    """Abstract interface for market data feeds"""

    @abstractmethod
    async def subscribe(self, symbols: List[str], timeframe: str) -> AsyncIterable[Bar]:
        """
        Subscribe to real-time or historical bar data

        Args:
            symbols: List of symbols to subscribe to
            timeframe: Bar timeframe ("1m", "5m", etc.)

        Yields:
            Bar: Market data bars as they become available
        """
        pass

    @abstractmethod
    async def get_historical_bars(self, symbol: str, start_date: date,
                                  end_date: date, timeframe: str,
                                  start_time: time = None, end_time: time = None) -> List[Bar]:
        """
        Get historical bars for backtesting

        Args:
            symbol: Trading symbol
            start_date: Start date for data
            end_date: End date for data
            timeframe: Bar timeframe
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of historical bars
        """
        pass

    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        pass
