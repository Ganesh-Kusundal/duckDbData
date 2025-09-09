"""
Domain Models for Trade Engine
============================

Core aggregates and value objects following DDD principles.
All models are immutable where possible and use type hints for clarity.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class SignalType(Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ADD_POSITION = "ADD_POSITION"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class TSLMode(Enum):
    ATR = "ATR"
    CHANDELIER = "CHANDELIER"
    EMA_CLOSE = "EMA_CLOSE"


@dataclass(frozen=True)
class Bar:
    """Market data bar - immutable value object"""
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    timeframe: str  # "1m", "5m", "1h", etc.

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def range_pct(self) -> Decimal:
        if self.open == 0:
            return Decimal('0')
        return ((self.high - self.low) / self.open) * 100


@dataclass
class Signal:
    """Trading signal with reasoning"""
    symbol: str
    signal_type: SignalType
    timestamp: datetime
    price: Decimal
    quantity: int
    reason: str
    id: str = field(default_factory=lambda: str(uuid4()))
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderIntent:
    """Order intent before broker submission"""
    symbol: str
    side: Side
    quantity: int
    order_type: OrderType
    time_in_force: str = "DAY"
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    """Order entity with broker tracking"""
    id: str
    symbol: str
    side: Side
    quantity: int
    order_type: OrderType
    broker_order_id: Optional[str] = None
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.PENDING
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    avg_fill_price: Optional[Decimal] = None
    timestamp: datetime = field(default_factory=datetime.now)
    fills: List['Fill'] = field(default_factory=list)


@dataclass
class Fill:
    """Order fill details"""
    timestamp: datetime
    quantity: int
    price: Decimal
    fee: Decimal = Decimal('0')
    broker_fill_id: Optional[str] = None


@dataclass
class Position:
    """Portfolio position with P&L tracking"""
    symbol: str
    quantity: int
    avg_cost: Decimal
    entry_timestamp: datetime = field(default_factory=datetime.now)
    current_price: Optional[Decimal] = None
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    stops: List['StopLevel'] = field(default_factory=list)
    ladder_stage: int = 0  # 0=initial, 1=first_add, 2=second_add, 3=third_add

    @property
    def market_value(self) -> Decimal:
        if self.current_price is None:
            return Decimal('0')
        return self.current_price * abs(self.quantity)


@dataclass
class StopLevel:
    """Trailing stop loss configuration"""
    stop_price: Decimal
    tsl_mode: TSLMode
    k_atr: Optional[float] = None
    floor_price: Optional[Decimal] = None


@dataclass
class RiskBudget:
    """Risk management parameters"""
    per_trade_r_pct: float
    daily_dd_stop_pct: float
    sector_cap_pct: float
    max_reentries_15m: int = 3
    max_adds: int = 3


@dataclass
class Score:
    """Scoring components for symbol selection"""
    symbol: str
    date: date
    ret_0915_0950: float
    vspike_10m: float
    obv_delta_35m: float
    sector_strength: float
    range_compression: float
    spread_penalty: float
    illiq_penalty: float
    total_score: float
    components_json: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeaderScore:
    """Real-time leader scoring"""
    symbol: str
    timestamp: datetime
    ret_since_entry: float
    vspike_5m: float
    obv_delta_10m: float
    total_score: float
    is_leader: bool = False


@dataclass
class AccountState:
    """Broker account snapshot"""
    timestamp: datetime
    cash: Decimal
    margin_used: Decimal
    margin_available: Decimal
    day_pnl: Decimal
    total_pnl: Decimal
    positions: List[Position] = field(default_factory=list)


@dataclass
class RunMetadata:
    """Trade run metadata for analytics"""
    run_id: str
    mode: str  # "backtest" or "live"
    start_date: date
    start_time: time = field(default_factory=lambda: time(9, 15))
    end_time: time = field(default_factory=lambda: time(15, 15))
    end_date: Optional[date] = None
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
