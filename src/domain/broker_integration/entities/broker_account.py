"""
Broker Integration Broker Account Entity

This module defines the BrokerAccount entity for managing broker accounts,
portfolios, and account-specific operations in the Broker Integration domain.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import uuid4

from domain.shared.exceptions import DomainException
from .broker_connection import BrokerConnectionId


@dataclass(frozen=True)
class BrokerAccountId:
    """Value object for Broker Account ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("BrokerAccountId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'BrokerAccountId':
        """Generate a new unique BrokerAccountId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class AccountBalance:
    """Value object for account balance information."""
    cash: Decimal
    buying_power: Decimal
    total_value: Decimal
    day_trading_buying_power: Optional[Decimal] = None
    maintenance_margin: Optional[Decimal] = None
    equity: Optional[Decimal] = None

    def __post_init__(self):
        """Validate account balance."""
        if self.cash < 0:
            raise DomainException("Cash cannot be negative")
        if self.buying_power < 0:
            raise DomainException("Buying power cannot be negative")
        if self.total_value < 0:
            raise DomainException("Total value cannot be negative")

    def get_available_buying_power(self) -> Decimal:
        """Get available buying power for trading."""
        return min(self.cash, self.buying_power)

    def can_afford_trade(self, trade_value: Decimal) -> bool:
        """Check if account can afford a trade."""
        return self.get_available_buying_power() >= trade_value

    def get_leverage_ratio(self) -> Optional[Decimal]:
        """Get account leverage ratio."""
        if self.equity and self.equity > 0:
            return self.total_value / self.equity
        return None

    def is_margin_account(self) -> bool:
        """Check if this is a margin account."""
        return (self.maintenance_margin is not None and
                self.day_trading_buying_power is not None)


@dataclass(frozen=True)
class AccountPermissions:
    """Value object for account trading permissions."""
    can_trade_options: bool = False
    can_short_sell: bool = False
    can_trade_complex_orders: bool = False
    can_trade_forex: bool = False
    can_trade_futures: bool = False
    day_trading_restricted: bool = False
    margin_restricted: bool = False

    def can_execute_order_type(self, order_type: str) -> bool:
        """Check if account can execute specific order type."""
        if order_type == "option" and not self.can_trade_options:
            return False
        if order_type == "short" and not self.can_short_sell:
            return False
        if order_type in ["bracket", "one_cancels_all"] and not self.can_trade_complex_orders:
            return False
        if order_type == "forex" and not self.can_trade_forex:
            return False
        if order_type == "futures" and not self.can_trade_futures:
            return False

        return True

    def get_permission_summary(self) -> Dict[str, bool]:
        """Get summary of account permissions."""
        return {
            'options_trading': self.can_trade_options,
            'short_selling': self.can_short_sell,
            'complex_orders': self.can_trade_complex_orders,
            'forex_trading': self.can_trade_forex,
            'futures_trading': self.can_trade_futures,
            'day_trading_allowed': not self.day_trading_restricted,
            'margin_allowed': not self.margin_restricted
        }


@dataclass(frozen=True)
class AccountPosition:
    """Value object for individual account positions."""
    symbol: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal

    def __post_init__(self):
        """Validate account position."""
        if not self.symbol:
            raise DomainException("Symbol is required")
        if self.quantity == 0:
            raise DomainException("Position quantity cannot be zero")

    def is_long_position(self) -> bool:
        """Check if this is a long position."""
        return self.quantity > 0

    def is_short_position(self) -> bool:
        """Check if this is a short position."""
        return self.quantity < 0

    def get_total_pnl(self) -> Decimal:
        """Get total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl

    def get_position_size(self) -> Decimal:
        """Get absolute position size."""
        return abs(self.quantity)


@dataclass
class BrokerAccount:
    """
    Broker Account aggregate root.

    Represents a trading account at a broker with balance information,
    positions, permissions, and account management capabilities.
    """
    id: BrokerAccountId
    connection_id: BrokerConnectionId
    account_number: str
    account_type: str  # "cash", "margin", "retirement", etc.
    balance: AccountBalance
    permissions: AccountPermissions = field(default_factory=AccountPermissions)
    positions: List[AccountPosition] = field(default_factory=list)
    name: Optional[str] = None
    is_active: bool = True
    last_sync_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate broker account after initialization."""
        if not self.account_number:
            raise DomainException("Account number is required")
        if not self.account_type:
            raise DomainException("Account type is required")
        if self.name and len(self.name) > 100:
            raise DomainException("Account name cannot exceed 100 characters")

    def update_balance(self, new_balance: AccountBalance) -> None:
        """Update account balance."""
        self.balance = new_balance
        self.updated_at = datetime.utcnow()

    def add_position(self, position: AccountPosition) -> None:
        """Add a position to the account."""
        # Remove existing position for the same symbol if it exists
        self.positions = [p for p in self.positions if p.symbol != position.symbol]
        self.positions.append(position)
        self.updated_at = datetime.utcnow()

    def remove_position(self, symbol: str) -> None:
        """Remove a position from the account."""
        self.positions = [p for p in self.positions if p.symbol != symbol]
        self.updated_at = datetime.utcnow()

    def update_position(self, symbol: str, new_position: AccountPosition) -> None:
        """Update an existing position."""
        if new_position.symbol != symbol:
            raise DomainException("Position symbol mismatch")

        self.remove_position(symbol)
        self.add_position(new_position)

    def get_position(self, symbol: str) -> Optional[AccountPosition]:
        """Get position for a specific symbol."""
        for position in self.positions:
            if position.symbol == symbol:
                return position
        return None

    def get_total_portfolio_value(self) -> Decimal:
        """Get total portfolio value including cash."""
        position_values = sum(p.market_value for p in self.positions)
        return self.balance.total_value + position_values

    def get_total_unrealized_pnl(self) -> Decimal:
        """Get total unrealized P&L across all positions."""
        return sum(p.unrealized_pnl for p in self.positions)

    def get_total_realized_pnl(self) -> Decimal:
        """Get total realized P&L across all positions."""
        return sum(p.realized_pnl for p in self.positions)

    def can_afford_order(self, order_value: Decimal, symbol: str = None) -> bool:
        """Check if account can afford an order."""
        # Check buying power
        if not self.balance.can_afford_trade(order_value):
            return False

        # Check position-specific requirements
        if symbol:
            existing_position = self.get_position(symbol)
            if existing_position and existing_position.is_short_position():
                # Additional checks for short positions
                pass

        return True

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        return {
            'account_number': self.account_number,
            'account_type': self.account_type,
            'cash': self.balance.cash,
            'buying_power': self.balance.buying_power,
            'total_value': self.get_total_portfolio_value(),
            'positions_count': len(self.positions),
            'unrealized_pnl': self.get_total_unrealized_pnl(),
            'realized_pnl': self.get_total_realized_pnl(),
            'leverage_ratio': self.balance.get_leverage_ratio(),
            'is_margin_account': self.balance.is_margin_account(),
            'permissions': self.permissions.get_permission_summary()
        }

    def deactivate(self) -> None:
        """Deactivate the account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the account."""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def mark_synced(self) -> None:
        """Mark account as recently synced."""
        self.last_sync_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def needs_sync(self, max_age_minutes: int = 15) -> bool:
        """Check if account needs synchronization."""
        if not self.last_sync_at:
            return True

        age_minutes = (datetime.utcnow() - self.last_sync_at).total_seconds() / 60
        return age_minutes > max_age_minutes

