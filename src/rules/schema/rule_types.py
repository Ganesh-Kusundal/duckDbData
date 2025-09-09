"""
Rule Types and Enums

This module defines all the enumeration types and constants used in the rule system.
"""

from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass


class RuleType(Enum):
    """Types of trading rules supported by the system."""
    BREAKOUT = "breakout"
    CRP = "crp"
    TECHNICAL = "technical"
    VOLUME = "volume"
    MOMENTUM = "momentum"
    REVERSAL = "reversal"
    TREND = "trend"
    CUSTOM = "custom"


class SignalType(Enum):
    """Types of trading signals that can be generated."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    ALERT = "ALERT"


class ConfidenceMethod(Enum):
    """Methods for calculating signal confidence."""
    WEIGHTED_AVERAGE = "weighted_average"
    MAX_CONDITION = "max_condition"
    MIN_CONDITION = "min_condition"
    CUSTOM = "custom"


class MarketCondition(Enum):
    """Market condition filters."""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    ALL = "all"


class RiskLevel(Enum):
    """Risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LiquidityRequirement(Enum):
    """Liquidity requirement levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RuleMetadata:
    """Metadata structure for rules."""
    author: str
    created_at: str
    updated_at: str
    version: str
    tags: list[str]
    performance_expectations: Dict[str, Any]
    risk_assessment: Dict[str, Any]


@dataclass
class TimeWindow:
    """Time window specification."""
    start: str  # HH:MM format
    end: str    # HH:MM format

    def validate(self) -> bool:
        """Validate time format."""
        import re
        # Require HH:MM format (not H:MM)
        time_pattern = r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$'
        return bool(re.match(time_pattern, self.start) and re.match(time_pattern, self.end))


@dataclass
class BreakoutConditions:
    """Conditions specific to breakout rules."""
    min_price_move_pct: float = 0.02
    max_price_move_pct: float = 0.10
    min_volume_multiplier: float = 1.5
    volume_comparison_period: int = 10
    breakout_direction: str = "up"


@dataclass
class CRPConditions:
    """Conditions specific to CRP rules."""
    close_threshold_pct: float = 2.0
    range_threshold_pct: float = 3.0
    consolidation_period: int = 5
    close_position_preference: str = "any"


@dataclass
class TechnicalConditions:
    """Technical indicator conditions."""
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    rsi_condition: str = None

    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    macd_condition: str = None

    use_sma_20: bool = False
    use_sma_50: bool = False
    use_ema_12: bool = False
    use_ema_26: bool = False

    bb_period: int = 20
    bb_deviations: float = 2.0
    bb_condition: str = None


@dataclass
class RiskManagement:
    """Risk management parameters."""
    stop_loss_pct: float = None
    take_profit_pct: float = None
    max_position_size_pct: float = None
    max_drawdown_pct: float = None


@dataclass
class AlertSettings:
    """Alert and notification settings."""
    email_notification: bool = False
    sms_notification: bool = False
    webhook_url: str = None
    alert_threshold: float = 0.7


@dataclass
class ExecutionSettings:
    """Trade execution settings."""
    auto_execute: bool = False
    max_slippage_pct: float = None
    execution_delay_seconds: int = 0
