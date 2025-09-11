"""
Indicator Repository Interface

This module defines the repository interface for Indicator entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.indicator import Indicator, IndicatorId, IndicatorType, Symbol
from ..entities.analysis import Analysis, AnalysisId


class IndicatorRepository(ABC):
    """
    Repository interface for Indicator entities.

    Defines the contract for indicator data persistence and retrieval.
    """

    @abstractmethod
    def save(self, indicator: Indicator) -> None:
        """Save an indicator to the repository."""
        pass

    @abstractmethod
    def find_by_id(self, indicator_id: IndicatorId) -> Optional[Indicator]:
        """Find an indicator by its ID."""
        pass

    @abstractmethod
    def find_by_symbol(self, symbol: Symbol) -> List[Indicator]:
        """Find all indicators for a specific symbol."""
        pass

    @abstractmethod
    def find_by_type(self, indicator_type: IndicatorType) -> List[Indicator]:
        """Find all indicators of a specific type."""
        pass

    @abstractmethod
    def find_active_indicators(self) -> List[Indicator]:
        """Find all active indicators."""
        pass

    @abstractmethod
    def find_indicators_by_symbol_and_type(self, symbol: Symbol, indicator_type: IndicatorType) -> List[Indicator]:
        """Find indicators for a symbol and type combination."""
        pass

    @abstractmethod
    def delete(self, indicator_id: IndicatorId) -> None:
        """Delete an indicator from the repository."""
        pass

    @abstractmethod
    def exists(self, indicator_id: IndicatorId) -> bool:
        """Check if an indicator exists in the repository."""
        pass

    @abstractmethod
    def count_indicators_by_symbol(self, symbol: Symbol) -> int:
        """Count indicators for a specific symbol."""
        pass

    @abstractmethod
    def get_indicator_summary(self) -> dict:
        """
        Get indicator summary statistics.

        Returns:
            dict: Summary with counts by type, symbol, etc.
        """
        pass

    @abstractmethod
    def deactivate_indicator(self, indicator_id: IndicatorId) -> None:
        """Deactivate an indicator."""
        pass

    @abstractmethod
    def activate_indicator(self, indicator_id: IndicatorId) -> None:
        """Activate an indicator."""
        pass

