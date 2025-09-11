"""
Analytics Indicator Entity

This module defines the Indicator entity and related value objects for the Analytics domain.
Indicators represent technical analysis calculations and their parameters.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from domain.shared.exceptions import DomainException


class IndicatorType(Enum):
    """Types of technical indicators."""
    MOVING_AVERAGE = "moving_average"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    STOCHASTIC = "stochastic"
    VOLUME = "volume"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    TREND = "trend"


class CalculationPeriod(Enum):
    """Time periods for indicator calculations."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


@dataclass(frozen=True)
class IndicatorId:
    """Value object for Indicator ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("IndicatorId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'IndicatorId':
        """Generate a new unique IndicatorId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class IndicatorName:
    """Value object for Indicator Name."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("IndicatorName must be a non-empty string")
        if len(self.value) > 100:
            raise DomainException("IndicatorName cannot exceed 100 characters")


@dataclass(frozen=True)
class Symbol:
    """Value object for financial instrument symbol."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("Symbol must be a non-empty string")
        if len(self.value) > 20:
            raise DomainException("Symbol cannot exceed 20 characters")


@dataclass(frozen=True)
class IndicatorParameters:
    """Value object for indicator calculation parameters."""
    period: int
    additional_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.period <= 0:
            raise DomainException("Period must be positive")

        # Validate specific parameters based on indicator type
        if 'fast_period' in self.additional_params and 'slow_period' in self.additional_params:
            if self.additional_params['fast_period'] >= self.additional_params['slow_period']:
                raise DomainException("Fast period must be less than slow period for MACD")

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get a parameter value with optional default."""
        return self.additional_params.get(key, default)


@dataclass
class Indicator:
    """
    Indicator aggregate root.

    Represents a technical indicator with its configuration,
    parameters, and calculated values.
    """
    id: IndicatorId
    name: IndicatorName
    indicator_type: IndicatorType
    symbol: Symbol
    parameters: IndicatorParameters
    period: CalculationPeriod
    is_active: bool = True
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    calculated_values: List['IndicatorValue'] = field(default_factory=list)

    def __post_init__(self):
        """Validate indicator after initialization."""
        if self.description and len(self.description) > 500:
            raise DomainException("Description cannot exceed 500 characters")

    def add_value(self, value: 'IndicatorValue') -> None:
        """Add a calculated value to the indicator."""
        if value.indicator_id != self.id:
            raise DomainException("Value does not belong to this indicator")

        self.calculated_values.append(value)
        self.updated_at = datetime.utcnow()

    def get_latest_value(self) -> Optional['IndicatorValue']:
        """Get the most recent calculated value."""
        if not self.calculated_values:
            return None

        return max(self.calculated_values, key=lambda v: v.timestamp)

    def get_values_in_range(self, start_date: datetime, end_date: datetime) -> List['IndicatorValue']:
        """Get indicator values within a date range."""
        return [
            value for value in self.calculated_values
            if start_date <= value.timestamp <= end_date
        ]

    def clear_values(self) -> None:
        """Clear all calculated values."""
        self.calculated_values.clear()
        self.updated_at = datetime.utcnow()

    def is_ready_for_calculation(self, data_points: int) -> bool:
        """
        Check if indicator has sufficient data for calculation.

        Args:
            data_points: Number of available data points

        Returns:
            bool: True if calculation can proceed
        """
        min_points = self.parameters.period

        # Some indicators need more data points
        if self.indicator_type == IndicatorType.MACD:
            slow_period = self.parameters.get_parameter('slow_period', 26)
            min_points = max(min_points, slow_period)

        return data_points >= min_points


@dataclass
class IndicatorValue:
    """
    Indicator value entity representing a single calculation result.
    """
    indicator_id: IndicatorId
    value: Decimal
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate value after initialization."""
        # Some indicators can have negative values (e.g., momentum)
        # but most should be non-negative
        if self.indicator_type in [IndicatorType.RSI, IndicatorType.STOCHASTIC]:
            if not (0 <= self.value <= 100):
                raise DomainException(f"{self.indicator_type.value} must be between 0 and 100")

    @property
    def indicator_type(self) -> IndicatorType:
        """Get indicator type from metadata."""
        return self.metadata.get('indicator_type', IndicatorType.MOVING_AVERAGE)

    def get_signal(self) -> Optional[str]:
        """Get trading signal from indicator value."""
        signal = self.metadata.get('signal')
        return signal if signal in ['BUY', 'SELL', 'NEUTRAL'] else None

    def get_confidence(self) -> Optional[Decimal]:
        """Get signal confidence level."""
        confidence = self.metadata.get('confidence')
        if isinstance(confidence, (int, float)):
            return Decimal(str(confidence))
        return None
