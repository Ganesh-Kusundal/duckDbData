"""
Broker Port Interface
===================

Abstract interface for broker integrations.
Handles order placement, modification, and position management.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from decimal import Decimal

from ..domain.models import OrderIntent, Order, Fill, Position, AccountState


class BrokerPort(ABC):
    """Abstract interface for broker integrations"""

    @abstractmethod
    async def place_order(self, order_intent: OrderIntent) -> Order:
        """
        Place a new order

        Args:
            order_intent: Order parameters

        Returns:
            Order object with broker tracking
        """
        pass

    @abstractmethod
    async def amend_order(self, order_id: str, price: Optional[Decimal] = None,
                         quantity: Optional[int] = None) -> Order:
        """
        Amend an existing order

        Args:
            order_id: Internal order ID
            price: New price (for limit orders)
            quantity: New quantity

        Returns:
            Updated Order object
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order

        Args:
            order_id: Internal order ID

        Returns:
            True if cancellation successful
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """
        Get current status of an order

        Args:
            order_id: Internal order ID

        Returns:
            Order object or None if not found
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get current positions

        Returns:
            List of current positions
        """
        pass

    @abstractmethod
    async def get_account_state(self) -> AccountState:
        """
        Get current account state

        Returns:
            Account state snapshot
        """
        pass

    @abstractmethod
    def apply_slippage_and_fees(self, order_intent: OrderIntent,
                               market_price: Decimal) -> OrderIntent:
        """
        Apply slippage and fee adjustments to order

        Args:
            order_intent: Original order intent
            market_price: Current market price

        Returns:
            Adjusted order intent
        """
        pass
