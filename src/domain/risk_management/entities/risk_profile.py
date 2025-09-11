"""
Risk Management Risk Profile Entity

This module defines the RiskProfile entity and related value objects for the Risk Management domain.
Risk profiles define risk tolerance levels and trading limits for portfolios and strategies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from domain.shared.exceptions import DomainException


class RiskTolerance(Enum):
    """Risk tolerance levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    VERY_AGGRESSIVE = "very_aggressive"


class RiskProfileStatus(Enum):
    """Risk profile status states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


@dataclass(frozen=True)
class RiskProfileId:
    """Value object for Risk Profile ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("RiskProfileId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'RiskProfileId':
        """Generate a new unique RiskProfileId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class RiskProfileName:
    """Value object for Risk Profile Name."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("RiskProfileName must be a non-empty string")
        if len(self.value) > 100:
            raise DomainException("RiskProfileName cannot exceed 100 characters")


@dataclass(frozen=True)
class PositionLimit:
    """Value object for position size limits."""
    max_position_size: Decimal
    max_position_percentage: Decimal  # Percentage of portfolio

    def __post_init__(self):
        """Validate position limits."""
        if self.max_position_size <= 0:
            raise DomainException("Max position size must be positive")
        if not (0 < self.max_position_percentage <= 1):
            raise DomainException("Max position percentage must be between 0 and 1")

    def calculate_max_position(self, portfolio_value: Decimal) -> Decimal:
        """Calculate maximum position size for a given portfolio value."""
        return min(
            self.max_position_size,
            portfolio_value * self.max_position_percentage
        )


@dataclass(frozen=True)
class LossLimits:
    """Value object for loss limits and stop conditions."""
    max_daily_loss: Decimal
    max_total_loss: Decimal
    stop_loss_percentage: Decimal
    trailing_stop_percentage: Optional[Decimal] = None

    def __post_init__(self):
        """Validate loss limits."""
        if self.max_daily_loss <= 0:
            raise DomainException("Max daily loss must be positive")
        if self.max_total_loss <= 0:
            raise DomainException("Max total loss must be positive")
        if not (0 < self.stop_loss_percentage <= 1):
            raise DomainException("Stop loss percentage must be between 0 and 1")
        if self.trailing_stop_percentage is not None and self.trailing_stop_percentage <= 0:
            raise DomainException("Trailing stop percentage must be positive")

    def calculate_stop_loss_price(self, entry_price: Decimal, is_long: bool) -> Decimal:
        """Calculate stop loss price."""
        if is_long:
            return entry_price * (1 - self.stop_loss_percentage)
        else:
            return entry_price * (1 + self.stop_loss_percentage)


@dataclass(frozen=True)
class RiskMetrics:
    """Value object for risk measurement metrics."""
    volatility_limit: Decimal
    var_limit: Decimal  # Value at Risk limit
    max_drawdown_limit: Decimal
    concentration_limit: Decimal  # Max concentration in single asset

    def __post_init__(self):
        """Validate risk metrics."""
        if self.volatility_limit <= 0:
            raise DomainException("Volatility limit must be positive")
        if not (0 < self.var_limit <= 1):
            raise DomainException("VaR limit must be between 0 and 1")
        if not (0 < self.max_drawdown_limit <= 1):
            raise DomainException("Max drawdown limit must be between 0 and 1")
        if not (0 < self.concentration_limit <= 1):
            raise DomainException("Concentration limit must be between 0 and 1")

    def is_within_limits(
        self,
        current_volatility: Decimal,
        current_var: Decimal,
        current_drawdown: Decimal,
        current_concentration: Decimal
    ) -> bool:
        """Check if current risk metrics are within limits."""
        return (
            current_volatility <= self.volatility_limit and
            current_var <= self.var_limit and
            current_drawdown <= self.max_drawdown_limit and
            current_concentration <= self.concentration_limit
        )


@dataclass
class RiskProfile:
    """
    Risk Profile aggregate root.

    Defines the risk tolerance and limits for a trading strategy
    or portfolio, including position limits, loss limits, and risk metrics.
    """
    id: RiskProfileId
    name: RiskProfileName
    risk_tolerance: RiskTolerance
    position_limits: PositionLimit
    loss_limits: LossLimits
    risk_metrics: RiskMetrics
    status: RiskProfileStatus = RiskProfileStatus.ACTIVE
    description: Optional[str] = None
    associated_strategies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate risk profile after initialization."""
        if self.description and len(self.description) > 500:
            raise DomainException("Description cannot exceed 500 characters")

    def activate(self) -> None:
        """Activate the risk profile."""
        if self.status == RiskProfileStatus.EXPIRED:
            raise DomainException("Cannot activate expired risk profile")
        self.status = RiskProfileStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the risk profile."""
        self.status = RiskProfileStatus.INACTIVE
        self.updated_at = datetime.utcnow()

    def suspend(self) -> None:
        """Suspend the risk profile."""
        self.status = RiskProfileStatus.SUSPENDED
        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if risk profile is active."""
        return self.status == RiskProfileStatus.ACTIVE

    def can_accept_trade(
        self,
        trade_value: Decimal,
        portfolio_value: Decimal,
        current_volatility: Decimal,
        current_var: Decimal,
        current_drawdown: Decimal,
        asset_concentration: Decimal
    ) -> bool:
        """
        Check if a trade can be accepted based on risk limits.

        Args:
            trade_value: Value of the proposed trade
            portfolio_value: Current portfolio value
            current_volatility: Current portfolio volatility
            current_var: Current Value at Risk
            current_drawdown: Current drawdown
            asset_concentration: Concentration in the traded asset

        Returns:
            bool: True if trade can be accepted
        """
        # Check position limits
        max_position = self.position_limits.calculate_max_position(portfolio_value)
        if trade_value > max_position:
            return False

        # Check risk metrics
        if not self.risk_metrics.is_within_limits(
            current_volatility, current_var, current_drawdown, asset_concentration
        ):
            return False

        return True

    def get_risk_score(self) -> str:
        """Get risk score description based on tolerance."""
        scores = {
            RiskTolerance.CONSERVATIVE: "LOW",
            RiskTolerance.MODERATE: "MEDIUM",
            RiskTolerance.AGGRESSIVE: "HIGH",
            RiskTolerance.VERY_AGGRESSIVE: "VERY_HIGH"
        }
        return scores[self.risk_tolerance]

    def get_risk_parameters_summary(self) -> Dict[str, Any]:
        """Get summary of risk parameters."""
        return {
            'risk_tolerance': self.risk_tolerance.value,
            'max_position_size': self.position_limits.max_position_size,
            'max_position_percentage': self.position_limits.max_position_percentage,
            'max_daily_loss': self.loss_limits.max_daily_loss,
            'max_total_loss': self.loss_limits.max_total_loss,
            'stop_loss_percentage': self.loss_limits.stop_loss_percentage,
            'volatility_limit': self.risk_metrics.volatility_limit,
            'var_limit': self.risk_metrics.var_limit,
            'max_drawdown_limit': self.risk_metrics.max_drawdown_limit,
            'concentration_limit': self.risk_metrics.concentration_limit
        }

    def add_strategy(self, strategy_id: str) -> None:
        """Add a strategy to this risk profile."""
        if strategy_id not in self.associated_strategies:
            self.associated_strategies.append(strategy_id)
            self.updated_at = datetime.utcnow()

    def remove_strategy(self, strategy_id: str) -> None:
        """Remove a strategy from this risk profile."""
        if strategy_id in self.associated_strategies:
            self.associated_strategies.remove(strategy_id)
            self.updated_at = datetime.utcnow()
