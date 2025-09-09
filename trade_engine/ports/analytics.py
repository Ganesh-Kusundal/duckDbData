"""
Analytics Port Interface
======================

Abstract interface for analytical computations.
Pure functions for scoring, technical indicators, and feature engineering.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import date, time
from decimal import Decimal

from ..domain.models import Bar, Score, LeaderScore


class AnalyticsPort(ABC):
    """Abstract interface for analytical computations"""

    @abstractmethod
    def compute_warmup_features(self, trading_date: date, symbols: List[str],
                               start_time: time, end_time: time) -> Dict[str, Score]:
        """
        Compute 09:15-09:50 warmup features and scores

        Args:
            trading_date: Trading date
            symbols: List of symbols to analyze
            start_time: Warmup start time (typically 09:15)
            end_time: Warmup end time (typically 09:50)

        Returns:
            Dictionary mapping symbol to Score object
        """
        pass

    @abstractmethod
    def compute_leader_scores(self, symbols: List[str], trading_date: date,
                             current_time: time, entry_timestamps: Dict[str, time]) -> Dict[str, LeaderScore]:
        """
        Compute real-time leader scores for position management

        Args:
            symbols: Symbols with active positions
            trading_date: Current trading date
            current_time: Current market time
            entry_timestamps: When each position was entered

        Returns:
            Dictionary mapping symbol to LeaderScore
        """
        pass

    @abstractmethod
    def calculate_atr(self, symbol: str, trading_date: date,
                     window: int = 14, timeframe: str = "5m") -> Optional[Decimal]:
        """
        Calculate Average True Range

        Args:
            symbol: Trading symbol
            trading_date: Trading date
            window: ATR period (default 14)
            timeframe: Bar timeframe for calculation

        Returns:
            ATR value or None if insufficient data
        """
        pass

    @abstractmethod
    def calculate_ema(self, symbol: str, period: int, trading_date: date,
                     timeframe: str = "1m") -> Optional[Decimal]:
        """
        Calculate Exponential Moving Average

        Args:
            symbol: Trading symbol
            period: EMA period
            trading_date: Trading date
            timeframe: Bar timeframe

        Returns:
            EMA value or None if insufficient data
        """
        pass

    @abstractmethod
    def calculate_obv(self, symbol: str, trading_date: date,
                     window: int = 10, timeframe: str = "1m") -> Optional[Decimal]:
        """
        Calculate On Balance Volume

        Args:
            symbol: Trading symbol
            trading_date: Trading date
            window: OBV window for delta calculation
            timeframe: Bar timeframe

        Returns:
            OBV delta or None if insufficient data
        """
        pass

    @abstractmethod
    def check_entry_triggers(self, symbol: str, current_bar: Bar,
                           ema_9: Optional[Decimal], ema_30: Optional[Decimal]) -> Dict[str, bool]:
        """
        Check entry trigger conditions

        Args:
            symbol: Trading symbol
            current_bar: Current market bar
            ema_9: 9-period EMA
            ema_30: 30-period EMA

        Returns:
            Dictionary of trigger states
        """
        pass
