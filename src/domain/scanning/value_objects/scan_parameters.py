"""
Scanning Value Objects

This module defines value objects for scanning parameters and configurations.
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal
from typing import List, Optional, Dict, Any

from domain.shared.exceptions import DomainException


@dataclass(frozen=True)
class ScanTimeframe:
    """Value object for scan timeframe configuration."""
    start_time: time
    end_time: time
    timezone: str = "UTC"

    def __post_init__(self):
        """Validate timeframe."""
        if self.start_time >= self.end_time:
            raise DomainException("Start time must be before end time")

        if self.timezone not in ['UTC', 'EST', 'CST', 'MST', 'PST', 'IST']:
            raise DomainException("Unsupported timezone")

    def is_market_hours(self) -> bool:
        """Check if timeframe is within typical market hours."""
        market_open = time(9, 30)
        market_close = time(16, 0)
        return (self.start_time >= market_open and
                self.end_time <= market_close)

    def get_duration_hours(self) -> float:
        """Get timeframe duration in hours."""
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return (end_minutes - start_minutes) / 60.0


@dataclass(frozen=True)
class ScanFilters:
    """Value object for scan filtering criteria."""
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    min_volume: Optional[int] = None
    max_volume: Optional[int] = None
    symbols: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    market_cap_min: Optional[Decimal] = None
    market_cap_max: Optional[Decimal] = None
    volatility_min: Optional[Decimal] = None
    volatility_max: Optional[Decimal] = None

    def __post_init__(self):
        """Validate filters."""
        if self.min_price is not None and self.min_price < 0:
            raise DomainException("Minimum price cannot be negative")
        if self.max_price is not None and self.max_price < 0:
            raise DomainException("Maximum price cannot be negative")
        if self.min_price is not None and self.max_price is not None:
            if self.min_price >= self.max_price:
                raise DomainException("Minimum price must be less than maximum price")

        if self.min_volume is not None and self.min_volume < 0:
            raise DomainException("Minimum volume cannot be negative")
        if self.max_volume is not None and self.max_volume < 0:
            raise DomainException("Maximum volume cannot be negative")

        if self.market_cap_min is not None and self.market_cap_min < 0:
            raise DomainException("Minimum market cap cannot be negative")
        if self.market_cap_max is not None and self.market_cap_max < 0:
            raise DomainException("Maximum market cap cannot be negative")

    def matches_symbol(self, symbol: str) -> bool:
        """Check if symbol matches filter criteria."""
        if not self.symbols:
            return True
        return symbol in self.symbols

    def matches_price(self, price: Decimal) -> bool:
        """Check if price matches filter criteria."""
        if self.min_price is not None and price < self.min_price:
            return False
        if self.max_price is not None and price > self.max_price:
            return False
        return True

    def matches_volume(self, volume: int) -> bool:
        """Check if volume matches filter criteria."""
        if self.min_volume is not None and volume < self.min_volume:
            return False
        if self.max_volume is not None and volume > self.max_volume:
            return False
        return True

    def matches_market_cap(self, market_cap: Optional[Decimal]) -> bool:
        """Check if market cap matches filter criteria."""
        if market_cap is None:
            return self.market_cap_min is None and self.market_cap_max is None

        if self.market_cap_min is not None and market_cap < self.market_cap_min:
            return False
        if self.market_cap_max is not None and market_cap > self.market_cap_max:
            return False
        return True

    def get_filter_summary(self) -> Dict[str, Any]:
        """Get summary of applied filters."""
        summary = {}

        if self.min_price or self.max_price:
            summary['price_range'] = {
                'min': self.min_price,
                'max': self.max_price
            }

        if self.min_volume or self.max_volume:
            summary['volume_range'] = {
                'min': self.min_volume,
                'max': self.max_volume
            }

        if self.symbols:
            summary['symbols'] = len(self.symbols)

        if self.sectors:
            summary['sectors'] = len(self.sectors)

        if self.market_cap_min or self.market_cap_max:
            summary['market_cap_range'] = {
                'min': self.market_cap_min,
                'max': self.market_cap_max
            }

        return summary


@dataclass(frozen=True)
class SignalThresholds:
    """Value object for signal generation thresholds."""
    min_confidence: Decimal = Decimal('0.5')
    min_strength_score: Decimal = Decimal('0.7')
    max_signals_per_scan: int = 50
    signal_cooldown_minutes: int = 5

    def __post_init__(self):
        """Validate thresholds."""
        if not (0 < self.min_confidence <= 1):
            raise DomainException("Minimum confidence must be between 0 and 1")
        if not (0 < self.min_strength_score <= 1):
            raise DomainException("Minimum strength score must be between 0 and 1")
        if self.max_signals_per_scan <= 0:
            raise DomainException("Maximum signals per scan must be positive")
        if self.signal_cooldown_minutes < 0:
            raise DomainException("Signal cooldown cannot be negative")

    def should_generate_signal(self, confidence: Decimal, strength: Decimal) -> bool:
        """Check if signal meets threshold criteria."""
        return (confidence >= self.min_confidence and
                strength >= self.min_strength_score)

    def get_threshold_summary(self) -> Dict[str, Any]:
        """Get summary of signal thresholds."""
        return {
            'min_confidence': self.min_confidence,
            'min_strength_score': self.min_strength_score,
            'max_signals_per_scan': self.max_signals_per_scan,
            'signal_cooldown_minutes': self.signal_cooldown_minutes
        }


@dataclass(frozen=True)
class MarketCondition:
    """Value object for market condition assessment."""
    volatility_index: Decimal
    trend_direction: str  # 'BULLISH', 'BEARISH', 'SIDEWAYS'
    volume_level: str  # 'LOW', 'NORMAL', 'HIGH'
    market_open: bool = True
    assessment_time: datetime = datetime.utcnow()

    def __post_init__(self):
        """Validate market condition."""
        if self.volatility_index < 0:
            raise DomainException("Volatility index cannot be negative")
        if self.trend_direction not in ['BULLISH', 'BEARISH', 'SIDEWAYS']:
            raise DomainException("Trend direction must be BULLISH, BEARISH, or SIDEWAYS")
        if self.volume_level not in ['LOW', 'NORMAL', 'HIGH']:
            raise DomainException("Volume level must be LOW, NORMAL, or HIGH")

    def is_bullish_market(self) -> bool:
        """Check if market condition is bullish."""
        return self.trend_direction == 'BULLISH'

    def is_bearish_market(self) -> bool:
        """Check if market condition is bearish."""
        return self.trend_direction == 'BEARISH'

    def is_high_volatility(self, threshold: Decimal = Decimal('0.25')) -> bool:
        """Check if volatility is high."""
        return self.volatility_index >= threshold

    def is_high_volume(self) -> bool:
        """Check if volume level is high."""
        return self.volume_level == 'HIGH'

    def get_market_bias(self) -> str:
        """Get overall market bias assessment."""
        if self.is_bullish_market() and not self.is_high_volatility():
            return "STRONG_BULLISH"
        elif self.is_bullish_market() and self.is_high_volatility():
            return "VOLATILE_BULLISH"
        elif self.is_bearish_market() and not self.is_high_volatility():
            return "STRONG_BEARISH"
        elif self.is_bearish_market() and self.is_high_volatility():
            return "VOLATILE_BEARISH"
        else:
            return "NEUTRAL"

    def should_scan_for_breakouts(self) -> bool:
        """Check if market conditions are suitable for breakout scanning."""
        return (self.market_open and
                not self.is_high_volatility() and
                self.volume_level in ['NORMAL', 'HIGH'])

    def should_scan_for_reversals(self) -> bool:
        """Check if market conditions are suitable for reversal scanning."""
        return (self.market_open and
                self.is_high_volatility() and
                self.volume_level == 'HIGH')


@dataclass(frozen=True)
class ScanConfiguration:
    """Value object for complete scan configuration."""
    timeframe: ScanTimeframe
    filters: ScanFilters
    thresholds: SignalThresholds
    market_condition: Optional[MarketCondition] = None
    enabled_scan_types: List[str] = field(default_factory=lambda: ['breakout', 'consolidation'])
    max_execution_time_seconds: int = 300

    def __post_init__(self):
        """Validate scan configuration."""
        if self.max_execution_time_seconds <= 0:
            raise DomainException("Maximum execution time must be positive")

        valid_scan_types = ['breakout', 'consolidation', 'trend', 'volume', 'momentum', 'reversal']
        for scan_type in self.enabled_scan_types:
            if scan_type not in valid_scan_types:
                raise DomainException(f"Invalid scan type: {scan_type}")

    def is_scan_type_enabled(self, scan_type: str) -> bool:
        """Check if a scan type is enabled."""
        return scan_type in self.enabled_scan_types

    def should_execute_scan(self) -> bool:
        """Check if scan should be executed based on configuration."""
        if not self.timeframe.is_market_hours():
            return False

        if self.market_condition and not self.market_condition.market_open:
            return False

        return True

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of scan configuration."""
        return {
            'timeframe': {
                'start': self.timeframe.start_time.isoformat(),
                'end': self.timeframe.end_time.isoformat(),
                'timezone': self.timeframe.timezone
            },
            'filters': self.filters.get_filter_summary(),
            'thresholds': self.thresholds.get_threshold_summary(),
            'enabled_scan_types': self.enabled_scan_types,
            'max_execution_time': self.max_execution_time_seconds
        }
