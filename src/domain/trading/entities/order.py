"""
Trading Order Entity

This module defines the Order entity and related value objects for the Trading domain.
Orders represent trading instructions to buy or sell financial instruments.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from domain.shared.exceptions import DomainException


class OrderType(Enum):
    """Types of trading orders."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Side of the trade (buy or sell)."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status states."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(Enum):
    """Time in force instructions."""
    DAY = "day"  # Valid for the trading day
    GTC = "gtc"  # Good till cancelled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill


@dataclass(frozen=True)
class OrderId:
    """Value object for Order ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("OrderId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'OrderId':
        """Generate a new unique OrderId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class Quantity:
    """Value object for order quantity."""
    value: Decimal

    def __post_init__(self):
        if self.value <= 0:
            raise DomainException("Quantity must be positive")
        if self.value.as_integer_ratio()[1] != 1:  # Check if it's an integer
            raise DomainException("Quantity must be a whole number")


@dataclass(frozen=True)
class FilledQuantity:
    """Value object for filled quantity (allows zero)."""
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise DomainException("Filled quantity cannot be negative")
        if self.value.as_integer_ratio()[1] != 1:  # Check if it's an integer
            raise DomainException("Filled quantity must be a whole number")


@dataclass(frozen=True)
class Price:
    """Value object for order price."""
    value: Decimal

    def __post_init__(self):
        if self.value <= 0:
            raise DomainException("Price must be positive")


@dataclass(frozen=True)
class Symbol:
    """Value object for financial instrument symbol."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("Symbol must be a non-empty string")
        if len(self.value) > 20:
            raise DomainException("Symbol cannot exceed 20 characters")


@dataclass
class Order:
    """
    Order aggregate root.

    Represents a trading order with its lifecycle and associated fills.
    """
    id: OrderId
    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    quantity: FilledQuantity
    status: OrderStatus = OrderStatus.PENDING
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[Price] = None
    stop_price: Optional[Price] = None
    filled_quantity: FilledQuantity = field(default_factory=lambda: FilledQuantity(Decimal('0')))
    remaining_quantity: FilledQuantity = field(init=False)
    average_fill_price: Optional[Price] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    fills: List['Fill'] = field(default_factory=list)

    def __post_init__(self):
        """Validate order after initialization."""
        self._validate_order()
        self._calculate_remaining_quantity()

    def _validate_order(self):
        """Validate order parameters."""
        # Validate limit price for limit orders
        if self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if self.limit_price is None:
                raise DomainException(f"Limit price required for {self.order_type.value} orders")

        # Validate stop price for stop orders
        if self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if self.stop_price is None:
                raise DomainException(f"Stop price required for {self.order_type.value} orders")

        # Validate stop price logic
        if self.stop_price and self.limit_price:
            if self.side == OrderSide.BUY:
                if self.stop_price.value >= self.limit_price.value:
                    raise DomainException("Stop price must be below limit price for buy orders")
            else:  # SELL
                if self.stop_price.value <= self.limit_price.value:
                    raise DomainException("Stop price must be above limit price for sell orders")

    def _calculate_remaining_quantity(self):
        """Calculate remaining quantity to be filled."""
        self.remaining_quantity = FilledQuantity(self.quantity.value - self.filled_quantity.value)

    def submit(self) -> None:
        """Submit the order for execution."""
        if self.status != OrderStatus.PENDING:
            raise DomainException(f"Cannot submit order with status: {self.status.value}")

        self.status = OrderStatus.SUBMITTED
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel the order."""
        if self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            raise DomainException(f"Cannot cancel order with status: {self.status.value}")

        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def reject(self, reason: str) -> None:
        """Reject the order."""
        if self.status != OrderStatus.SUBMITTED:
            raise DomainException(f"Cannot reject order with status: {self.status.value}")

        self.status = OrderStatus.REJECTED
        self.updated_at = datetime.utcnow()

    def add_fill(self, fill: 'Fill') -> None:
        """Add a fill to the order."""
        if fill.order_id != self.id:
            raise DomainException("Fill does not belong to this order")

        self.fills.append(fill)
        self.filled_quantity = FilledQuantity(self.filled_quantity.value + fill.quantity.value)
        self._calculate_remaining_quantity()

        # Update average fill price
        if self.filled_quantity.value > 0:
            total_value = sum(f.quantity.value * f.price.value for f in self.fills)
            self.average_fill_price = Price(total_value / self.filled_quantity.value)

        # Update status
        if self.filled_quantity.value >= self.quantity.value:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity.value > 0:
            self.status = OrderStatus.PARTIALLY_FILLED

        self.updated_at = datetime.utcnow()

    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED

    def is_active(self) -> bool:
        """Check if order is still active."""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]


@dataclass(frozen=True)
class FillId:
    """Value object for Fill ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("FillId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'FillId':
        """Generate a new unique FillId."""
        return cls(str(uuid4()))


@dataclass
class Fill:
    """
    Fill entity representing a partial or complete execution of an order.
    """
    id: FillId
    order_id: OrderId
    quantity: FilledQuantity
    price: Price
    timestamp: datetime = field(default_factory=datetime.utcnow)
    commission: Optional[Decimal] = None
    exchange_fee: Optional[Decimal] = None

    def __post_init__(self):
        """Validate fill after initialization."""
        if self.commission is not None and self.commission < 0:
            raise DomainException("Commission cannot be negative")
        if self.exchange_fee is not None and self.exchange_fee < 0:
            raise DomainException("Exchange fee cannot be negative")
