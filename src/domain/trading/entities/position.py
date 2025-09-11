"""
Trading Position Entity

This module defines the Position entity for tracking portfolio holdings
and position management in the Trading domain.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from domain.shared.exceptions import DomainException
from .order import Symbol, Quantity, Price


@dataclass(frozen=True)
class PositionId:
    """Value object for Position ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("PositionId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'PositionId':
        """Generate a new unique PositionId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class AveragePrice:
    """Value object for average position price."""
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise DomainException("Average price cannot be negative")


@dataclass(frozen=True)
class UnrealizedPnL:
    """Value object for unrealized profit/loss."""
    value: Decimal


@dataclass(frozen=True)
class RealizedPnL:
    """Value object for realized profit/loss."""
    value: Decimal


@dataclass(frozen=True)
class PositionQuantity:
    """Value object for position quantity (can be negative for short positions)."""
    value: Decimal

    def __post_init__(self):
        if self.value == 0:
            raise DomainException("Position quantity cannot be zero")
        if self.value.as_integer_ratio()[1] != 1:  # Check if it's an integer
            raise DomainException("Position quantity must be a whole number")

    @property
    def is_long(self) -> bool:
        """Check if this represents a long position."""
        return self.value > 0

    @property
    def is_short(self) -> bool:
        """Check if this represents a short position."""
        return self.value < 0

    @property
    def size(self) -> Decimal:
        """Get the absolute size of the position."""
        return abs(self.value)


@dataclass
class Position:
    """
    Position aggregate root.

    Represents a trading position in a financial instrument, tracking
    quantity, average price, and P&L information.
    """
    id: PositionId
    symbol: Symbol
    quantity: PositionQuantity
    average_price: AveragePrice
    current_price: Price
    market_value: Decimal = field(init=False)
    unrealized_pnl: UnrealizedPnL = field(init=False)
    realized_pnl: RealizedPnL = field(default_factory=lambda: RealizedPnL(Decimal('0')))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    trades: List['PositionTrade'] = field(default_factory=list)

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        self._calculate_market_value()
        self._calculate_unrealized_pnl()

    def _calculate_market_value(self):
        """Calculate current market value of position."""
        self.market_value = self.quantity.value * self.current_price.value

    def _calculate_unrealized_pnl(self):
        """Calculate unrealized profit/loss."""
        cost_basis = self.quantity.value * self.average_price.value
        current_value = self.quantity.value * self.current_price.value
        pnl_value = current_value - cost_basis
        self.unrealized_pnl = UnrealizedPnL(pnl_value)

    def update_price(self, new_price: Price) -> None:
        """Update position with new market price."""
        self.current_price = new_price
        self._calculate_market_value()
        self._calculate_unrealized_pnl()
        self.updated_at = datetime.utcnow()

    def add_trade(self, trade: 'PositionTrade') -> None:
        """Add a trade to the position."""
        if trade.symbol != self.symbol:
            raise DomainException("Trade symbol does not match position symbol")

        self.trades.append(trade)

        # Update position quantity and average price
        if trade.side == 'BUY':
            self._handle_buy_trade(trade)
        else:  # SELL
            self._handle_sell_trade(trade)

        self.updated_at = datetime.utcnow()

    def _handle_buy_trade(self, trade: 'PositionTrade') -> None:
        """Handle buying into the position."""
        old_quantity = self.quantity.value
        old_cost = old_quantity * self.average_price.value

        new_quantity = old_quantity + trade.quantity.value
        new_cost = old_cost + (trade.quantity.value * trade.price.value)

        if new_quantity > 0:
            self.quantity = PositionQuantity(new_quantity)
            self.average_price = AveragePrice(new_cost / new_quantity)
        else:
            # This shouldn't happen for a buy trade
            raise DomainException("Buy trade resulted in negative position")

    def _handle_sell_trade(self, trade: 'PositionTrade') -> None:
        """Handle selling from the position."""
        if trade.quantity.value > self.quantity.value:
            raise DomainException("Cannot sell more than position quantity")

        # Calculate realized P&L for this trade
        realized_pnl = (trade.price.value - self.average_price.value) * trade.quantity.value
        self.realized_pnl = RealizedPnL(self.realized_pnl.value + realized_pnl)

        # Update position quantity
        new_quantity = self.quantity.value - trade.quantity.value

        if new_quantity == 0:
            # Position closed - quantity remains as is for reference
            pass  # Keep average price for reference
        else:
            self.quantity = PositionQuantity(new_quantity)

    def is_long(self) -> bool:
        """Check if this is a long position."""
        return self.quantity.value > 0

    def is_short(self) -> bool:
        """Check if this is a short position."""
        return self.quantity.value < 0

    def is_closed(self) -> bool:
        """Check if position is closed."""
        return self.quantity.value == 0

    def get_total_pnl(self) -> Decimal:
        """Get total P&L (realized + unrealized)."""
        return self.realized_pnl.value + self.unrealized_pnl.value

    def get_position_size(self) -> Decimal:
        """Get absolute position size."""
        return abs(self.quantity.value)


@dataclass
class PositionTrade:
    """
    Position trade record for tracking individual trades within a position.
    """
    symbol: Symbol
    side: str  # 'BUY' or 'SELL'
    quantity: PositionQuantity
    price: Price
    timestamp: datetime = field(default_factory=datetime.utcnow)
    order_id: Optional[str] = None
    trade_id: Optional[str] = None

    def __post_init__(self):
        """Validate trade after initialization."""
        if self.side not in ['BUY', 'SELL']:
            raise DomainException("Trade side must be 'BUY' or 'SELL'")
