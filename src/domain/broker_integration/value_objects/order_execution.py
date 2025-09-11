"""
Broker Integration Order Execution Value Objects

This module defines value objects for order execution parameters and
broker-specific order handling in the Broker Integration domain.
"""

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from typing import List, Optional, Dict, Any

from domain.shared.exceptions import DomainException


@dataclass(frozen=True)
class ExecutionParameters:
    """Value object for order execution parameters."""
    time_in_force: str  # "DAY", "GTC", "IOC", "FOK"
    route: Optional[str] = None  # Specific execution venue/route
    algo_strategy: Optional[str] = None  # Algorithmic execution strategy
    min_quantity: Optional[int] = None  # Minimum quantity to execute
    max_show_quantity: Optional[int] = None  # Maximum displayed quantity
    execution_style: str = "market"  # "market", "limit", "stop", "stop_limit"

    def __post_init__(self):
        """Validate execution parameters."""
        valid_tif = ["DAY", "GTC", "IOC", "FOK", "GTD"]
        if self.time_in_force not in valid_tif:
            raise DomainException(f"Invalid time in force: {self.time_in_force}")

        valid_styles = ["market", "limit", "stop", "stop_limit", "trailing_stop"]
        if self.execution_style not in valid_styles:
            raise DomainException(f"Invalid execution style: {self.execution_style}")

        if self.min_quantity is not None and self.min_quantity <= 0:
            raise DomainException("Minimum quantity must be positive")

        if self.max_show_quantity is not None and self.max_show_quantity <= 0:
            raise DomainException("Maximum show quantity must be positive")

    def is_market_order(self) -> bool:
        """Check if this is a market order."""
        return self.execution_style == "market"

    def is_limit_order(self) -> bool:
        """Check if this is a limit order."""
        return self.execution_style == "limit"

    def is_immediate_execution(self) -> bool:
        """Check if order requires immediate execution."""
        return self.time_in_force in ["IOC", "FOK"]

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution parameters summary."""
        return {
            'time_in_force': self.time_in_force,
            'route': self.route,
            'algo_strategy': self.algo_strategy,
            'min_quantity': self.min_quantity,
            'max_show_quantity': self.max_show_quantity,
            'execution_style': self.execution_style
        }


@dataclass(frozen=True)
class BrokerOrder:
    """Value object for broker-specific order representation."""
    broker_order_id: str
    symbol: str
    side: str  # "BUY", "SELL", "SHORT"
    quantity: int
    order_type: str
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    trail_amount: Optional[Decimal] = None
    execution_params: ExecutionParameters = ExecutionParameters(time_in_force="DAY", execution_style="market")

    def __post_init__(self):
        """Validate broker order."""
        if not self.broker_order_id:
            raise DomainException("Broker order ID is required")
        if not self.symbol:
            raise DomainException("Symbol is required")
        if self.side not in ["BUY", "SELL", "SHORT"]:
            raise DomainException(f"Invalid side: {self.side}")
        if self.quantity <= 0:
            raise DomainException("Quantity must be positive")
        if self.order_type not in ["MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAIL"]:
            raise DomainException(f"Invalid order type: {self.order_type}")

        # Validate price requirements
        if self.order_type in ["LIMIT", "STOP_LIMIT"] and self.price is None:
            raise DomainException(f"Price required for {self.order_type} orders")
        if self.order_type in ["STOP", "STOP_LIMIT"] and self.stop_price is None:
            raise DomainException(f"Stop price required for {self.order_type} orders")
        if self.order_type == "TRAIL" and self.trail_amount is None:
            raise DomainException("Trail amount required for TRAIL orders")

    def is_buy_order(self) -> bool:
        """Check if this is a buy order."""
        return self.side == "BUY"

    def is_sell_order(self) -> bool:
        """Check if this is a sell order."""
        return self.side in ["SELL", "SHORT"]

    def is_short_order(self) -> bool:
        """Check if this is a short sell order."""
        return self.side == "SHORT"

    def get_order_value(self, current_price: Optional[Decimal] = None) -> Optional[Decimal]:
        """Get the value of the order."""
        price = self.price or current_price
        if price is None:
            return None
        return price * Decimal(str(self.quantity))

    def get_broker_format(self) -> Dict[str, Any]:
        """Get order in broker-specific format."""
        order_data = {
            'order_id': self.broker_order_id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'time_in_force': self.execution_params.time_in_force
        }

        if self.price is not None:
            order_data['price'] = self.price
        if self.stop_price is not None:
            order_data['stop_price'] = self.stop_price
        if self.trail_amount is not None:
            order_data['trail_amount'] = self.trail_amount
        if self.execution_params.route:
            order_data['route'] = self.execution_params.route
        if self.execution_params.algo_strategy:
            order_data['algo_strategy'] = self.execution_params.algo_strategy

        return order_data


@dataclass(frozen=True)
class ExecutionReport:
    """Value object for order execution reports."""
    execution_id: str
    broker_order_id: str
    symbol: str
    executed_quantity: int
    executed_price: Decimal
    execution_time: datetime
    commission: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    venue: Optional[str] = None
    liquidity: Optional[str] = None  # "added", "removed", "neutral"

    def __post_init__(self):
        """Validate execution report."""
        if not self.execution_id:
            raise DomainException("Execution ID is required")
        if not self.broker_order_id:
            raise DomainException("Broker order ID is required")
        if not self.symbol:
            raise DomainException("Symbol is required")
        if self.executed_quantity <= 0:
            raise DomainException("Executed quantity must be positive")
        if self.executed_price <= 0:
            raise DomainException("Executed price must be positive")
        if self.commission is not None and self.commission < 0:
            raise DomainException("Commission cannot be negative")
        if self.fees is not None and self.fees < 0:
            raise DomainException("Fees cannot be negative")

    def get_execution_value(self) -> Decimal:
        """Get the value of the execution."""
        return self.executed_price * Decimal(str(self.executed_quantity))

    def get_total_cost(self) -> Decimal:
        """Get total cost including commissions and fees."""
        total = self.get_execution_value()
        if self.commission:
            total += self.commission
        if self.fees:
            total += self.fees
        return total

    def get_effective_price(self) -> Decimal:
        """Get effective price including costs."""
        total_cost = self.get_total_cost()
        return total_cost / Decimal(str(self.executed_quantity))

    def is_liquidity_providing(self) -> bool:
        """Check if execution provided liquidity."""
        return self.liquidity == "added"

    def is_liquidity_taking(self) -> bool:
        """Check if execution took liquidity."""
        return self.liquidity == "removed"


@dataclass(frozen=True)
class OrderStatusUpdate:
    """Value object for order status updates from broker."""
    broker_order_id: str
    status: str  # "pending", "partial", "filled", "cancelled", "rejected"
    filled_quantity: int
    remaining_quantity: int
    average_fill_price: Optional[Decimal] = None
    last_fill_price: Optional[Decimal] = None
    status_message: Optional[str] = None
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self):
        """Validate order status update."""
        if not self.broker_order_id:
            raise DomainException("Broker order ID is required")
        if self.status not in ["pending", "partial", "filled", "cancelled", "rejected", "expired"]:
            raise DomainException(f"Invalid status: {self.status}")
        if self.filled_quantity < 0:
            raise DomainException("Filled quantity cannot be negative")
        if self.remaining_quantity < 0:
            raise DomainException("Remaining quantity cannot be negative")
        if self.average_fill_price is not None and self.average_fill_price <= 0:
            raise DomainException("Average fill price must be positive")
        if self.last_fill_price is not None and self.last_fill_price <= 0:
            raise DomainException("Last fill price must be positive")

    def is_pending(self) -> bool:
        """Check if order is pending."""
        return self.status == "pending"

    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.status == "partial"

    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == "filled"

    def is_cancelled(self) -> bool:
        """Check if order is cancelled."""
        return self.status == "cancelled"

    def is_rejected(self) -> bool:
        """Check if order is rejected."""
        return self.status == "rejected"

    def get_fill_percentage(self) -> float:
        """Get fill percentage."""
        total_quantity = self.filled_quantity + self.remaining_quantity
        if total_quantity == 0:
            return 0.0
        return (self.filled_quantity / total_quantity) * 100.0


@dataclass(frozen=True)
class BrokerCapabilities:
    """Value object for broker API capabilities."""
    supports_market_orders: bool = True
    supports_limit_orders: bool = True
    supports_stop_orders: bool = True
    supports_stop_limit_orders: bool = True
    supports_trailing_stop_orders: bool = False
    supports_bracket_orders: bool = False
    supports_one_cancels_all: bool = False
    supports_options_trading: bool = False
    supports_futures_trading: bool = False
    supports_forex_trading: bool = False
    supports_margin_trading: bool = False
    supports_short_selling: bool = False
    supports_fractional_shares: bool = False
    realtime_data_available: bool = True
    historical_data_available: bool = True
    max_orders_per_second: int = 10
    supported_timeframes: List[str] = None

    def __post_init__(self):
        """Validate broker capabilities."""
        if self.max_orders_per_second <= 0:
            raise DomainException("Max orders per second must be positive")

        if self.supported_timeframes is None:
            object.__setattr__(self, 'supported_timeframes',
                             ["1m", "5m", "15m", "30m", "1h", "1d"])

    def supports_order_type(self, order_type: str) -> bool:
        """Check if broker supports specific order type."""
        order_type_map = {
            "market": self.supports_market_orders,
            "limit": self.supports_limit_orders,
            "stop": self.supports_stop_orders,
            "stop_limit": self.supports_stop_limit_orders,
            "trailing_stop": self.supports_trailing_stop_orders,
            "bracket": self.supports_bracket_orders,
            "one_cancels_all": self.supports_one_cancels_all
        }
        return order_type_map.get(order_type, False)

    def supports_asset_class(self, asset_class: str) -> bool:
        """Check if broker supports specific asset class."""
        asset_class_map = {
            "stocks": True,  # Assume all brokers support stocks
            "options": self.supports_options_trading,
            "futures": self.supports_futures_trading,
            "forex": self.supports_forex_trading
        }
        return asset_class_map.get(asset_class, False)

    def can_use_timeframe(self, timeframe: str) -> bool:
        """Check if broker supports specific timeframe."""
        return timeframe in self.supported_timeframes

    def get_capability_summary(self) -> Dict[str, Any]:
        """Get capabilities summary."""
        return {
            'order_types': {
                'market': self.supports_market_orders,
                'limit': self.supports_limit_orders,
                'stop': self.supports_stop_orders,
                'stop_limit': self.supports_stop_limit_orders,
                'trailing_stop': self.supports_trailing_stop_orders,
                'bracket': self.supports_bracket_orders,
                'one_cancels_all': self.supports_one_cancels_all
            },
            'asset_classes': {
                'stocks': True,
                'options': self.supports_options_trading,
                'futures': self.supports_futures_trading,
                'forex': self.supports_forex_trading
            },
            'trading_features': {
                'margin_trading': self.supports_margin_trading,
                'short_selling': self.supports_short_selling,
                'fractional_shares': self.supports_fractional_shares
            },
            'data_services': {
                'realtime_data': self.realtime_data_available,
                'historical_data': self.historical_data_available
            },
            'limits': {
                'max_orders_per_second': self.max_orders_per_second,
                'supported_timeframes': self.supported_timeframes
            }
        }

