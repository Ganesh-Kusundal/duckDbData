"""
Order Repository Interface

This module defines the repository interface for Order entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.order import Order, OrderId, OrderStatus, Symbol


class OrderRepository(ABC):
    """
    Repository interface for Order entities.

    Defines the contract for order data persistence and retrieval.
    """

    @abstractmethod
    def save(self, order: Order) -> None:
        """Save an order to the repository."""
        pass

    @abstractmethod
    def find_by_id(self, order_id: OrderId) -> Optional[Order]:
        """Find an order by its ID."""
        pass

    @abstractmethod
    def find_by_symbol(self, symbol: Symbol) -> List[Order]:
        """Find all orders for a specific symbol."""
        pass

    @abstractmethod
    def find_by_status(self, status: OrderStatus) -> List[Order]:
        """Find all orders with a specific status."""
        pass

    @abstractmethod
    def find_active_orders(self) -> List[Order]:
        """Find all active (non-final) orders."""
        pass

    @abstractmethod
    def find_orders_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Order]:
        """Find orders within a date range."""
        pass

    @abstractmethod
    def find_orders_by_symbol_and_date_range(
        self,
        symbol: Symbol,
        start_date: datetime,
        end_date: datetime
    ) -> List[Order]:
        """Find orders for a symbol within a date range."""
        pass

    @abstractmethod
    def delete(self, order_id: OrderId) -> None:
        """Delete an order from the repository."""
        pass

    @abstractmethod
    def exists(self, order_id: OrderId) -> bool:
        """Check if an order exists in the repository."""
        pass

    @abstractmethod
    def count_active_orders(self) -> int:
        """Count the number of active orders."""
        pass

    @abstractmethod
    def get_order_summary(self, symbol: Optional[Symbol] = None) -> dict:
        """
        Get order summary statistics.

        Returns:
            dict: Summary with counts by status, total value, etc.
        """
        pass

