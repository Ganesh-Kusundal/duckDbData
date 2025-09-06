"""Domain entities for scanners and trading signals."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any


class SignalType(Enum):
    """Types of trading signals."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class SignalStrength(Enum):
    """Strength levels for trading signals."""

    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


@dataclass(frozen=True)
class TradingSignal:
    """Trading signal entity."""

    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    timestamp: datetime
    price: Decimal
    confidence: float
    scanner_name: str
    metadata: Dict[str, Any]

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.scanner_name:
            raise ValueError("Scanner name cannot be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.price <= 0:
            raise ValueError("Price must be positive")

    @property
    def is_buy_signal(self) -> bool:
        """Check if this is a buy signal."""
        return self.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]

    @property
    def is_sell_signal(self) -> bool:
        """Check if this is a sell signal."""
        return self.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]

    @property
    def signal_score(self) -> float:
        """Calculate a numerical score for the signal."""
        base_score = self.confidence

        # Adjust based on signal strength
        strength_multiplier = {
            SignalStrength.WEAK: 0.25,
            SignalStrength.MODERATE: 0.5,
            SignalStrength.STRONG: 0.75,
            SignalStrength.VERY_STRONG: 1.0,
        }

        # Adjust based on signal type
        type_multiplier = {
            SignalType.BUY: 1.0,
            SignalType.SELL: -1.0,
            SignalType.STRONG_BUY: 1.5,
            SignalType.STRONG_SELL: -1.5,
            SignalType.HOLD: 0.0,
        }

        return base_score * strength_multiplier[self.strength] * type_multiplier[self.signal_type]


@dataclass(frozen=True)
class ScannerResult:
    """Result from a scanner execution."""

    scanner_name: str
    symbol: str
    timestamp: datetime
    signals: List[TradingSignal]
    metadata: Dict[str, Any]
    execution_time_ms: float

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.scanner_name:
            raise ValueError("Scanner name cannot be empty")
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.execution_time_ms < 0:
            raise ValueError("Execution time cannot be negative")

    @property
    def has_signals(self) -> bool:
        """Check if the result contains any signals."""
        return len(self.signals) > 0

    @property
    def buy_signals(self) -> List[TradingSignal]:
        """Get all buy signals."""
        return [s for s in self.signals if s.is_buy_signal]

    @property
    def sell_signals(self) -> List[TradingSignal]:
        """Get all sell signals."""
        return [s for s in self.signals if s.is_sell_signal]

    @property
    def strongest_signal(self) -> Optional[TradingSignal]:
        """Get the strongest signal by score."""
        if not self.signals:
            return None
        return max(self.signals, key=lambda s: abs(s.signal_score))


@dataclass(frozen=True)
class ScannerConfig:
    """Configuration for a scanner."""

    name: str
    description: str
    parameters: Dict[str, Any]
    enabled: bool = True
    priority: int = 1

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.name:
            raise ValueError("Scanner name cannot be empty")
        if not self.description:
            raise ValueError("Scanner description cannot be empty")
        if self.priority < 1:
            raise ValueError("Priority must be positive")

    @property
    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        return (
            self.name and
            self.description and
            self.parameters is not None and
            self.priority >= 1
        )


@dataclass(frozen=True)
class ScannerExecution:
    """Record of a scanner execution."""

    scanner_name: str
    start_time: datetime
    end_time: datetime
    symbols_processed: int
    signals_generated: int
    errors: List[str]
    status: str

    def __post_init__(self):
        """Validate entity after initialization."""
        if not self.scanner_name:
            raise ValueError("Scanner name cannot be empty")
        if self.start_time > self.end_time:
            raise ValueError("Start time cannot be after end time")
        if self.symbols_processed < 0:
            raise ValueError("Symbols processed cannot be negative")
        if self.signals_generated < 0:
            raise ValueError("Signals generated cannot be negative")

    @property
    def execution_time(self) -> float:
        """Get execution time in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def has_errors(self) -> bool:
        """Check if there were any errors."""
        return len(self.errors) > 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.symbols_processed == 0:
            return 0.0
        return (self.symbols_processed - len(self.errors)) / self.symbols_processed
