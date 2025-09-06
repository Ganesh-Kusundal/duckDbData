"""Domain entities for trading operations."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any


class OrderType(Enum):
    """Types of orders."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL_MARKET = "SL_MARKET"
    SL_LIMIT = "SL_LIMIT"


class OrderSide(Enum):
    """Order side (buy/sell)."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PositionType(Enum):
    """Position type."""

    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class Order:
    """Order entity."""

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[Decimal]
    trigger_price: Optional[Decimal]
    status: OrderStatus
    timestamp: datetime
    exchange: str = "NSE"
    product_type: str = "INTRADAY"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.order_id:
            raise ValueError("Order ID cannot be empty")
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price is not None and self.price <= 0:
            raise ValueError("Price must be positive")
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    @property
    def is_buy_order(self) -> bool:
        """Check if this is a buy order."""
        return self.side == OrderSide.BUY

    @property
    def is_sell_order(self) -> bool:
        """Check if this is a sell order."""
        return self.side == OrderSide.SELL

    @property
    def is_active(self) -> bool:
        """Check if order is active."""
        return self.status in [OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]

    @property
    def value(self) -> Optional[Decimal]:
        """Calculate order value."""
        if self.price is None:
            return None
        return self.price * self.quantity


@dataclass(frozen=True)
class Position:
    """Position entity."""

    symbol: str
    position_type: PositionType
    quantity: int
    average_price: Decimal
    current_price: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    realized_pnl: Decimal
    timestamp: datetime
    exchange: str = "NSE"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if self.average_price <= 0:
            raise ValueError("Average price must be positive")
        if self.realized_pnl is None:
            raise ValueError("Realized PnL cannot be None")
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    @property
    def market_value(self) -> Optional[Decimal]:
        """Calculate current market value."""
        if self.current_price is None:
            return None
        return self.current_price * self.quantity

    @property
    def total_pnl(self) -> Optional[Decimal]:
        """Calculate total PnL."""
        if self.unrealized_pnl is None:
            return None
        return self.realized_pnl + self.unrealized_pnl

    @property
    def is_long(self) -> bool:
        """Check if this is a long position."""
        return self.position_type == PositionType.LONG

    @property
    def is_short(self) -> bool:
        """Check if this is a short position."""
        return self.position_type == PositionType.SHORT


@dataclass(frozen=True)
class Trade:
    """Trade execution entity."""

    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    timestamp: datetime
    exchange: str = "NSE"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.trade_id:
            raise ValueError("Trade ID cannot be empty")
        if not self.order_id:
            raise ValueError("Order ID cannot be empty")
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    @property
    def value(self) -> Decimal:
        """Calculate trade value."""
        return self.price * self.quantity


@dataclass(frozen=True)
class Account:
    """Trading account entity."""

    account_id: str
    balance: Decimal
    margin_available: Decimal
    margin_used: Decimal
    timestamp: datetime
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.account_id:
            raise ValueError("Account ID cannot be empty")
        if self.balance < 0:
            raise ValueError("Balance cannot be negative")
        if self.margin_available < 0:
            raise ValueError("Available margin cannot be negative")
        if self.margin_used < 0:
            raise ValueError("Used margin cannot be negative")
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    @property
    def total_margin(self) -> Decimal:
        """Calculate total margin."""
        return self.margin_available + self.margin_used

    @property
    def margin_utilization(self) -> float:
        """Calculate margin utilization percentage."""
        if self.total_margin == 0:
            return 0.0
        return float(self.margin_used / self.total_margin)


@dataclass(frozen=True)
class BrokerCredentials:
    """Broker credentials entity."""

    client_id: str
    access_token: str
    broker_name: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.client_id:
            raise ValueError("Client ID cannot be empty")
        if not self.access_token:
            raise ValueError("Access token cannot be empty")
        if not self.broker_name:
            raise ValueError("Broker name cannot be empty")
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    @property
    def is_valid(self) -> bool:
        """Check if credentials appear valid."""
        return (
            len(self.client_id.strip()) > 0 and
            len(self.access_token.strip()) > 0 and
            self.client_id != "invalid_client_id" and
            self.access_token != "invalid_access_token"
        )


@dataclass(frozen=True)
class MarketDepth:
    """Market depth entity."""

    symbol: str
    bids: List[Dict[str, Any]]  # List of {'price': Decimal, 'quantity': int}
    asks: List[Dict[str, Any]]  # List of {'price': Decimal, 'quantity': int}
    timestamp: datetime
    depth_level: int = 5
    exchange: str = "NSE"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.depth_level <= 0:
            raise ValueError("Depth level must be positive")
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    @property
    def best_bid(self) -> Optional[Dict[str, Any]]:
        """Get best bid."""
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> Optional[Dict[str, Any]]:
        """Get best ask."""
        return self.asks[0] if self.asks else None

    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        if not self.best_bid or not self.best_ask:
            return None
        return self.best_ask['price'] - self.best_bid['price']

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price."""
        if not self.best_bid or not self.best_ask:
            return None
        return (self.best_bid['price'] + self.best_ask['price']) / 2
