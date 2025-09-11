"""
Analytics Statistics Value Objects

This module defines value objects for statistical calculations
and analytical measures used in the Analytics domain.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from domain.shared.exceptions import DomainException


@dataclass(frozen=True)
class Mean:
    """Value object for arithmetic mean."""
    value: Decimal

    def __post_init__(self):
        # Mean can be any decimal value
        pass


@dataclass(frozen=True)
class StandardDeviation:
    """Value object for standard deviation."""
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise DomainException("Standard deviation cannot be negative")


@dataclass(frozen=True)
class Variance:
    """Value object for variance."""
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise DomainException("Variance cannot be negative")


@dataclass(frozen=True)
class Correlation:
    """Value object for correlation coefficient."""
    value: Decimal

    def __post_init__(self):
        if not (-1 <= self.value <= 1):
            raise DomainException("Correlation must be between -1 and 1")

    def is_strong_positive(self, threshold: Decimal = Decimal('0.7')) -> bool:
        """Check if correlation is strongly positive."""
        return self.value >= threshold

    def is_strong_negative(self, threshold: Decimal = Decimal('0.7')) -> bool:
        """Check if correlation is strongly negative."""
        return self.value <= -threshold

    def is_weak(self, threshold: Decimal = Decimal('0.3')) -> bool:
        """Check if correlation is weak."""
        return -threshold < self.value < threshold

    def get_strength_description(self) -> str:
        """Get human-readable correlation strength."""
        abs_value = abs(self.value)

        if abs_value >= 0.8:
            return "Very Strong"
        elif abs_value >= 0.6:
            return "Strong"
        elif abs_value >= 0.4:
            return "Moderate"
        elif abs_value >= 0.2:
            return "Weak"
        else:
            return "Very Weak"


@dataclass(frozen=True)
class SharpeRatio:
    """Value object for Sharpe ratio."""
    value: Decimal

    def __post_init__(self):
        # Sharpe ratio can be any value, including negative
        pass

    def is_attractive(self, threshold: Decimal = Decimal('1.0')) -> bool:
        """Check if Sharpe ratio is attractive."""
        return self.value >= threshold

    def get_rating(self) -> str:
        """Get Sharpe ratio rating."""
        if self.value >= 2.0:
            return "Excellent"
        elif self.value >= 1.0:
            return "Good"
        elif self.value >= 0.5:
            return "Fair"
        elif self.value >= 0:
            return "Poor"
        else:
            return "Negative"


@dataclass(frozen=True)
class Volatility:
    """Value object for volatility measure."""
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise DomainException("Volatility cannot be negative")

    def get_risk_level(self) -> str:
        """Get risk level description."""
        if self.value >= 0.5:
            return "Very High"
        elif self.value >= 0.3:
            return "High"
        elif self.value >= 0.15:
            return "Moderate"
        elif self.value >= 0.05:
            return "Low"
        else:
            return "Very Low"


@dataclass(frozen=True)
class ReturnMetrics:
    """Value object for return-related metrics."""
    total_return: Decimal
    annualized_return: Decimal
    max_drawdown: Decimal
    win_rate: Decimal  # Between 0 and 1

    def __post_init__(self):
        """Validate return metrics."""
        if not (0 <= self.win_rate <= 1):
            raise DomainException("Win rate must be between 0 and 1")

        if self.max_drawdown > 0:
            raise DomainException("Max drawdown should be negative or zero")

    def is_profitable(self) -> bool:
        """Check if strategy is profitable."""
        return self.total_return > 0

    def get_performance_rating(self) -> str:
        """Get performance rating."""
        if self.total_return > 0.5 and self.win_rate > 0.6:
            return "Excellent"
        elif self.total_return > 0.2 and self.win_rate > 0.5:
            return "Good"
        elif self.total_return > 0 and self.win_rate > 0.4:
            return "Fair"
        elif self.total_return > 0:
            return "Poor"
        else:
            return "Loss"


@dataclass(frozen=True)
class StatisticalSummary:
    """Value object for statistical summary of data."""
    count: int
    mean: Mean
    median: Decimal
    std_dev: StandardDeviation
    minimum: Decimal
    maximum: Decimal
    quartiles: List[Decimal]  # Q1, Q2 (median), Q3

    def __post_init__(self):
        """Validate statistical summary."""
        if self.count <= 0:
            raise DomainException("Count must be positive")

        if len(self.quartiles) != 3:
            raise DomainException("Must provide exactly 3 quartiles (Q1, Q2, Q3)")

        # Validate quartile ordering
        q1, q2, q3 = self.quartiles
        if not (self.minimum <= q1 <= q2 <= q3 <= self.maximum):
            raise DomainException("Quartiles must be properly ordered")

    @property
    def range(self) -> Decimal:
        """Get data range."""
        return self.maximum - self.minimum

    @property
    def iqr(self) -> Decimal:
        """Get interquartile range."""
        return self.quartiles[2] - self.quartiles[0]

    def get_distribution_shape(self) -> str:
        """Get distribution shape description."""
        mean_val = float(self.mean.value)
        median_val = float(self.median)

        if abs(mean_val - median_val) < 0.1 * float(self.std_dev.value):
            return "Symmetric"
        elif mean_val > median_val:
            return "Right-skewed"
        else:
            return "Left-skewed"


@dataclass(frozen=True)
class TrendAnalysis:
    """Value object for trend analysis results."""
    trend_direction: str  # 'UP', 'DOWN', 'SIDEWAYS'
    trend_strength: Decimal  # Between 0 and 1
    duration_days: int
    slope: Decimal
    r_squared: Decimal  # Goodness of fit

    def __post_init__(self):
        """Validate trend analysis."""
        if self.trend_direction not in ['UP', 'DOWN', 'SIDEWAYS']:
            raise DomainException("Trend direction must be UP, DOWN, or SIDEWAYS")

        if not (0 <= self.trend_strength <= 1):
            raise DomainException("Trend strength must be between 0 and 1")

        if not (0 <= self.r_squared <= 1):
            raise DomainException("R-squared must be between 0 and 1")

        if self.duration_days <= 0:
            raise DomainException("Duration must be positive")

    def is_strong_trend(self, threshold: Decimal = Decimal('0.7')) -> bool:
        """Check if trend is strong."""
        return self.trend_strength >= threshold and self.r_squared >= Decimal('0.8')

    def is_uptrend(self) -> bool:
        """Check if trend is upward."""
        return self.trend_direction == 'UP'

    def is_downtrend(self) -> bool:
        """Check if trend is downward."""
        return self.trend_direction == 'DOWN'

    def get_trend_description(self) -> str:
        """Get human-readable trend description."""
        direction = self.trend_direction.lower()
        strength = "strong" if self.is_strong_trend() else "weak"
        return f"{strength} {direction}trend"

