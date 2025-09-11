"""
Order Execution Service

This module defines the OrderExecutionService domain service
for handling order lifecycle and execution logic.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal

from domain.shared.exceptions import DomainException
from ..entities.order import Order, OrderId, Fill, FillId, Quantity, Price
from ..entities.position import Position, PositionTrade
from ..value_objects.trading_strategy import TradingSignal
from ..repositories.order_repository import OrderRepository
from ..repositories.position_repository import PositionRepository


class OrderExecutionService:
    """
    Domain service for order execution and lifecycle management.

    Handles the business logic for order processing, validation,
    and position updates.
    """

    def __init__(
        self,
        order_repository: OrderRepository,
        position_repository: PositionRepository
    ):
        self.order_repository = order_repository
        self.position_repository = position_repository

    def execute_order(self, order: Order) -> Order:
        """
        Execute an order through the trading system.

        This is the main entry point for order execution.
        """
        # Validate order before execution
        self._validate_order_for_execution(order)

        # Submit the order
        order.submit()

        # Save the submitted order
        self.order_repository.save(order)

        # For now, simulate immediate fill (this would integrate with broker)
        # In a real system, this would be asynchronous
        self._simulate_fill(order)

        return order

    def cancel_order(self, order_id: OrderId) -> Order:
        """Cancel an existing order."""
        order = self.order_repository.find_by_id(order_id)
        if not order:
            raise DomainException(f"Order {order_id.value} not found")

        if not order.is_active():
            raise DomainException(f"Order {order_id.value} cannot be cancelled")

        order.cancel()
        self.order_repository.save(order)

        return order

    def process_signal(self, signal: TradingSignal) -> Optional[Order]:
        """
        Process a trading signal and create an order if appropriate.

        This method implements the signal-to-order conversion logic.
        """
        if not signal.is_buy_signal() and not signal.is_sell_signal():
            return None  # Skip hold signals

        # Create order from signal
        order = self._create_order_from_signal(signal)

        # Execute the order
        return self.execute_order(order)

    def _validate_order_for_execution(self, order: Order) -> None:
        """Validate an order before execution."""
        # Check if symbol exists (basic validation)
        if not order.symbol.value:
            raise DomainException("Order must have a valid symbol")

        # Check quantity limits
        if order.quantity.value <= 0:
            raise DomainException("Order quantity must be positive")

        # Check price limits for limit orders
        if order.limit_price and order.limit_price.value <= 0:
            raise DomainException("Limit price must be positive")

        # Additional business rules can be added here
        self._apply_business_rules(order)

    def _apply_business_rules(self, order: Order) -> None:
        """Apply business-specific validation rules."""
        # Example: Check position limits
        if order.side.name == 'BUY':
            # Check if we have sufficient buying power (would integrate with account service)
            pass
        elif order.side.name == 'SELL':
            # Check if we have sufficient position to sell
            position = self.position_repository.find_by_symbol(order.symbol)
            if position and position.quantity.value < order.quantity.value:
                raise DomainException(f"Insufficient position for {order.symbol.value}")

    def _create_order_from_signal(self, signal: TradingSignal) -> Order:
        """Create an order from a trading signal."""
        from ..entities.order import Order, OrderType, OrderSide, Symbol, Quantity, Price

        # Determine order side from signal
        side = OrderSide.BUY if signal.is_buy_signal() else OrderSide.SELL

        # Create order with market execution for signals
        # In a real system, you might use limit orders based on signal parameters
        order = Order(
            id=OrderId.generate(),
            symbol=Symbol(signal.symbol),
            side=side,
            order_type=OrderType.MARKET,
            quantity=Quantity(Decimal('100')),  # Default quantity, would be configurable
            limit_price=None  # Market order
        )

        return order

    def _simulate_fill(self, order: Order) -> None:
        """Simulate order fill (for development/testing)."""
        # In a real system, this would be handled by broker integration
        # For now, create a full fill at the requested price

        fill_price = order.limit_price.value if order.limit_price else Decimal('100.00')

        fill = Fill(
            id=FillId.generate(),
            order_id=order.id,
            quantity=order.quantity,
            price=Price(fill_price)
        )

        order.add_fill(fill)

        # Update position
        self._update_position_from_fill(order, fill)

        # Save updated order
        self.order_repository.save(order)

    def _update_position_from_fill(self, order: Order, fill: Fill) -> None:
        """Update position based on order fill."""
        from ..entities.position import Position, PositionId, AveragePrice

        # Find existing position or create new one
        position = self.position_repository.find_by_symbol(order.symbol)

        if not position:
            # Create new position
            position = Position(
                id=PositionId.generate(),
                symbol=order.symbol,
                quantity=Quantity(Decimal('0')),
                average_price=AveragePrice(fill.price.value),
                current_price=fill.price
            )

        # Add trade to position
        trade = PositionTrade(
            symbol=order.symbol,
            side=order.side.value,
            quantity=fill.quantity,
            price=fill.price,
            order_id=order.id.value,
            trade_id=fill.id.value
        )

        position.add_trade(trade)
        self.position_repository.save(position)

    def get_order_execution_summary(self, symbol: Optional[str] = None) -> dict:
        """Get execution summary for orders."""
        # This would aggregate execution statistics
        return {
            'total_orders': 0,
            'filled_orders': 0,
            'pending_orders': 0,
            'cancelled_orders': 0
        }

    def get_position_summary(self) -> dict:
        """Get current position summary."""
        return self.position_repository.get_portfolio_summary()

