"""
Repository Port Interface
=======================

Abstract interface for data persistence.
Handles all trade artifacts, analytics, and telemetry.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from decimal import Decimal

from ..domain.models import Bar, Signal, Order, Fill, Position, Score, RunMetadata


class RepositoryPort(ABC):
    """Abstract interface for data persistence"""

    @abstractmethod
    def save_bars(self, bars: List[Bar]) -> bool:
        """Save market data bars"""
        pass

    @abstractmethod
    def save_signals(self, signals: List[Signal]) -> bool:
        """Save trading signals"""
        pass

    @abstractmethod
    def save_orders(self, orders: List[Order]) -> bool:
        """Save order information"""
        pass

    @abstractmethod
    def save_fills(self, fills: List[Fill]) -> bool:
        """Save order fills"""
        pass

    @abstractmethod
    def save_positions(self, positions: List[Position]) -> bool:
        """Save position snapshots"""
        pass

    @abstractmethod
    def save_scores(self, scores: List[Score]) -> bool:
        """Save scoring data"""
        pass

    @abstractmethod
    def save_run_metadata(self, metadata: RunMetadata) -> bool:
        """Save run metadata"""
        pass

    @abstractmethod
    def load_bars(self, symbol: str, start_date: date, end_date: date,
                  timeframe: str = "1m") -> List[Bar]:
        """Load historical bars"""
        pass

    @abstractmethod
    def load_signals(self, run_id: str, symbol: Optional[str] = None) -> List[Signal]:
        """Load trading signals for a run"""
        pass

    @abstractmethod
    def get_pnl_series(self, run_id: str, symbol: Optional[str] = None) -> Dict[datetime, Decimal]:
        """Get P&L time series"""
        pass

    @abstractmethod
    def get_run_metrics(self, run_id: str) -> Dict[str, Any]:
        """Get run performance metrics"""
        pass

    @abstractmethod
    def initialize_tables(self) -> bool:
        """Initialize database tables"""
        pass
