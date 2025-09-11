"""
Position Repository Interface

This module defines the repository interface for Position entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from decimal import Decimal

from ..entities.position import Position, PositionId, Symbol


class PositionRepository(ABC):
    """
    Repository interface for Position entities.

    Defines the contract for position data persistence and retrieval.
    """

    @abstractmethod
    def save(self, position: Position) -> None:
        """Save a position to the repository."""
        pass

    @abstractmethod
    def find_by_id(self, position_id: PositionId) -> Optional[Position]:
        """Find a position by its ID."""
        pass

    @abstractmethod
    def find_by_symbol(self, symbol: Symbol) -> Optional[Position]:
        """Find position for a specific symbol."""
        pass

    @abstractmethod
    def find_all_positions(self) -> List[Position]:
        """Find all positions."""
        pass

    @abstractmethod
    def find_open_positions(self) -> List[Position]:
        """Find all open (non-zero quantity) positions."""
        pass

    @abstractmethod
    def find_long_positions(self) -> List[Position]:
        """Find all long positions."""
        pass

    @abstractmethod
    def find_short_positions(self) -> List[Position]:
        """Find all short positions."""
        pass

    @abstractmethod
    def delete(self, position_id: PositionId) -> None:
        """Delete a position from the repository."""
        pass

    @abstractmethod
    def exists(self, position_id: PositionId) -> bool:
        """Check if a position exists in the repository."""
        pass

    @abstractmethod
    def get_portfolio_summary(self) -> dict:
        """
        Get portfolio summary statistics.

        Returns:
            dict: Summary with total value, P&L, position counts, etc.
        """
        pass

    @abstractmethod
    def get_total_unrealized_pnl(self) -> Decimal:
        """Get total unrealized P&L across all positions."""
        pass

    @abstractmethod
    def get_total_realized_pnl(self) -> Decimal:
        """Get total realized P&L across all positions."""
        pass

    @abstractmethod
    def update_position_prices(self, price_updates: dict) -> None:
        """
        Update multiple position prices in batch.

        Args:
            price_updates: Dict mapping symbol to new price
        """
        pass

