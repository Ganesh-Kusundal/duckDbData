"""
OHLCV Value Object
Represents Open, High, Low, Close, Volume data for a trading period
"""

from typing import Dict, Any
from dataclasses import dataclass, asdict
from decimal import Decimal


@dataclass(frozen=True)
class OHLCV:
    """
    OHLCV Value Object - Immutable representation of price/volume data

    This is a value object in Domain-Driven Design terms, meaning:
    - Immutable (frozen=True)
    - Equality based on values, not identity
    - No side effects
    - Can be shared safely
    """

    open: float
    high: float
    low: float
    close: float
    volume: int

    def __post_init__(self):
        """Validate OHLCV data after initialization"""
        self._validate_price_data()
        self._validate_volume_data()

    def _validate_price_data(self):
        """Validate price relationships"""
        if self.open <= 0:
            raise ValueError("Open price must be positive")
        if self.high <= 0:
            raise ValueError("High price must be positive")
        if self.low <= 0:
            raise ValueError("Low price must be positive")
        if self.close <= 0:
            raise ValueError("Close price must be positive")

        # Validate OHLC relationships
        if self.low > self.open or self.low > self.high or self.low > self.close:
            raise ValueError("Low price cannot be higher than OHLC prices")

        if self.high < self.open or self.high < self.low or self.high < self.close:
            raise ValueError("High price cannot be lower than OHLC prices")

    def _validate_volume_data(self):
        """Validate volume data"""
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")

    @property
    def price_range(self) -> float:
        """Calculate price range (high - low)"""
        return self.high - self.low

    @property
    def body_range(self) -> float:
        """Calculate body range (absolute difference between open and close)"""
        return abs(self.open - self.close)

    @property
    def upper_shadow(self) -> float:
        """Calculate upper shadow length"""
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        """Calculate lower shadow length"""
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)"""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish (close < open)"""
        return self.close < self.open

    @property
    def is_doji(self) -> bool:
        """Check if candle is a doji (very small body)"""
        body_size = self.body_range
        total_range = self.price_range
        return total_range > 0 and (body_size / total_range) < 0.05

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OHLCV':
        """Create OHLCV from dictionary"""
        return cls(**data)

    def __str__(self) -> str:
        """String representation"""
        direction = "📈" if self.is_bullish else "📉" if self.is_bearish else "➡️"
        return f"{direction} O:{self.open:.2f} H:{self.high:.2f} L:{self.low:.2f} C:{self.close:.2f} V:{self.volume}"

    def __repr__(self) -> str:
        """Detailed string representation"""
        return (f"OHLCV(open={self.open}, high={self.high}, low={self.low}, "
                f"close={self.close}, volume={self.volume})")
