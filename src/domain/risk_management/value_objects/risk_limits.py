"""
Risk Management Value Objects

This module defines value objects for risk limits, thresholds, and parameters
used in the Risk Management domain.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from domain.shared.exceptions import DomainException


@dataclass(frozen=True)
class PortfolioLimits:
    """Value object for portfolio-level risk limits."""
    max_portfolio_value: Decimal
    max_daily_loss_percentage: Decimal
    max_total_loss_percentage: Decimal
    max_sector_exposure_percentage: Decimal
    max_single_asset_exposure_percentage: Decimal
    min_diversification_ratio: int  # Minimum number of assets
    max_correlation_threshold: Decimal  # Maximum allowed correlation

    def __post_init__(self):
        """Validate portfolio limits."""
        if self.max_portfolio_value <= 0:
            raise DomainException("Max portfolio value must be positive")
        if not (0 < self.max_daily_loss_percentage <= 1):
            raise DomainException("Max daily loss percentage must be between 0 and 1")
        if not (0 < self.max_total_loss_percentage <= 1):
            raise DomainException("Max total loss percentage must be between 0 and 1")
        if not (0 < self.max_sector_exposure_percentage <= 1):
            raise DomainException("Max sector exposure percentage must be between 0 and 1")
        if not (0 < self.max_single_asset_exposure_percentage <= 1):
            raise DomainException("Max single asset exposure percentage must be between 0 and 1")
        if self.min_diversification_ratio <= 0:
            raise DomainException("Min diversification ratio must be positive")
        if not (0 <= self.max_correlation_threshold <= 1):
            raise DomainException("Max correlation threshold must be between 0 and 1")

    def validate_portfolio_composition(
        self,
        total_value: Decimal,
        daily_loss: Decimal,
        total_loss: Decimal,
        sector_exposures: Dict[str, Decimal],
        asset_exposures: Dict[str, Decimal],
        num_assets: int,
        correlations: Dict[str, Decimal]
    ) -> List[str]:
        """
        Validate portfolio against limits.

        Returns:
            List of violation messages (empty if compliant)
        """
        violations = []

        # Check portfolio value
        if total_value > self.max_portfolio_value:
            violations.append(f"Portfolio value {total_value} exceeds limit {self.max_portfolio_value}")

        # Check loss limits
        if daily_loss > self.max_daily_loss_percentage:
            violations.append(f"Daily loss {daily_loss:.2%} exceeds limit {self.max_daily_loss_percentage:.2%}")

        if total_loss > self.max_total_loss_percentage:
            violations.append(f"Total loss {total_loss:.2%} exceeds limit {self.max_total_loss_percentage:.2%}")

        # Check sector exposures
        for sector, exposure in sector_exposures.items():
            if exposure > self.max_sector_exposure_percentage:
                violations.append(f"Sector {sector} exposure {exposure:.2%} exceeds limit {self.max_sector_exposure_percentage:.2%}")

        # Check single asset exposures
        for asset, exposure in asset_exposures.items():
            if exposure > self.max_single_asset_exposure_percentage:
                violations.append(f"Asset {asset} exposure {exposure:.2%} exceeds limit {self.max_single_asset_exposure_percentage:.2%}")

        # Check diversification
        if num_assets < self.min_diversification_ratio:
            violations.append(f"Portfolio has {num_assets} assets, minimum required is {self.min_diversification_ratio}")

        # Check correlations
        for pair, correlation in correlations.items():
            if abs(correlation) > self.max_correlation_threshold:
                violations.append(f"Asset pair {pair} correlation {correlation:.2f} exceeds threshold {self.max_correlation_threshold:.2f}")

        return violations


@dataclass(frozen=True)
class TradingLimits:
    """Value object for trading-specific risk limits."""
    max_trades_per_day: int
    max_order_value: Decimal
    max_position_size: Decimal
    min_order_value: Decimal
    max_slippage_percentage: Decimal
    cooldown_period_seconds: int
    max_concurrent_positions: int

    def __post_init__(self):
        """Validate trading limits."""
        if self.max_trades_per_day <= 0:
            raise DomainException("Max trades per day must be positive")
        if self.max_order_value <= 0:
            raise DomainException("Max order value must be positive")
        if self.max_position_size <= 0:
            raise DomainException("Max position size must be positive")
        if self.min_order_value <= 0:
            raise DomainException("Min order value must be positive")
        if self.min_order_value >= self.max_order_value:
            raise DomainException("Min order value must be less than max order value")
        if not (0 < self.max_slippage_percentage <= 1):
            raise DomainException("Max slippage percentage must be between 0 and 1")
        if self.cooldown_period_seconds < 0:
            raise DomainException("Cooldown period cannot be negative")
        if self.max_concurrent_positions <= 0:
            raise DomainException("Max concurrent positions must be positive")

    def can_place_order(
        self,
        order_value: Decimal,
        current_positions: int,
        trades_today: int,
        last_trade_time: Optional[datetime]
    ) -> tuple[bool, List[str]]:
        """
        Check if an order can be placed.

        Returns:
            Tuple of (can_place, violation_messages)
        """
        violations = []

        # Check order value limits
        if order_value < self.min_order_value:
            violations.append(f"Order value {order_value} below minimum {self.min_order_value}")
        if order_value > self.max_order_value:
            violations.append(f"Order value {order_value} exceeds maximum {self.max_order_value}")

        # Check daily trade limit
        if trades_today >= self.max_trades_per_day:
            violations.append(f"Daily trade limit {self.max_trades_per_day} reached")

        # Check concurrent positions
        if current_positions >= self.max_concurrent_positions:
            violations.append(f"Concurrent position limit {self.max_concurrent_positions} reached")

        # Check cooldown period
        if last_trade_time:
            time_since_last_trade = (datetime.utcnow() - last_trade_time).total_seconds()
            if time_since_last_trade < self.cooldown_period_seconds:
                violations.append(f"Cooldown period not met. Wait {self.cooldown_period_seconds - time_since_last_trade:.0f} more seconds")

        return len(violations) == 0, violations


@dataclass(frozen=True)
class RiskThresholds:
    """Value object for risk monitoring thresholds."""
    volatility_alert_threshold: Decimal
    drawdown_alert_threshold: Decimal
    var_alert_threshold: Decimal
    correlation_alert_threshold: Decimal
    liquidity_alert_threshold: Decimal
    concentration_alert_threshold: Decimal

    def __post_init__(self):
        """Validate risk thresholds."""
        if not (0 < self.volatility_alert_threshold <= 1):
            raise DomainException("Volatility alert threshold must be between 0 and 1")
        if not (0 < self.drawdown_alert_threshold <= 1):
            raise DomainException("Drawdown alert threshold must be between 0 and 1")
        if not (0 < self.var_alert_threshold <= 1):
            raise DomainException("VaR alert threshold must be between 0 and 1")
        if not (0 <= self.correlation_alert_threshold <= 1):
            raise DomainException("Correlation alert threshold must be between 0 and 1")
        if not (0 < self.liquidity_alert_threshold <= 1):
            raise DomainException("Liquidity alert threshold must be between 0 and 1")
        if not (0 < self.concentration_alert_threshold <= 1):
            raise DomainException("Concentration alert threshold must be between 0 and 1")

    def check_thresholds(
        self,
        volatility: Decimal,
        drawdown: Decimal,
        var: Decimal,
        max_correlation: Decimal,
        liquidity_ratio: Decimal,
        max_concentration: Decimal
    ) -> Dict[str, bool]:
        """
        Check if any risk metrics exceed thresholds.

        Returns:
            Dict mapping risk type to whether it's breached
        """
        return {
            'volatility': volatility > self.volatility_alert_threshold,
            'drawdown': drawdown > self.drawdown_alert_threshold,
            'var': var > self.var_alert_threshold,
            'correlation': max_correlation > self.correlation_alert_threshold,
            'liquidity': liquidity_ratio < self.liquidity_alert_threshold,
            'concentration': max_concentration > self.concentration_alert_threshold
        }

    def get_breach_summary(
        self,
        breaches: Dict[str, bool]
    ) -> Dict[str, Any]:
        """Get summary of threshold breaches."""
        breached_items = [k for k, v in breaches.items() if v]

        return {
            'has_breaches': len(breached_items) > 0,
            'breached_thresholds': breached_items,
            'breach_count': len(breached_items),
            'severity': 'HIGH' if len(breached_items) >= 3 else 'MEDIUM' if breached_items else 'LOW'
        }


@dataclass(frozen=True)
class RiskMonitoringConfig:
    """Value object for risk monitoring configuration."""
    monitoring_interval_seconds: int
    alert_cooldown_minutes: int
    auto_hedging_enabled: bool
    position_reduction_enabled: bool
    emergency_stop_enabled: bool
    max_alerts_per_hour: int
    notification_channels: List[str]

    def __post_init__(self):
        """Validate monitoring configuration."""
        if self.monitoring_interval_seconds <= 0:
            raise DomainException("Monitoring interval must be positive")
        if self.alert_cooldown_minutes < 0:
            raise DomainException("Alert cooldown cannot be negative")
        if self.max_alerts_per_hour <= 0:
            raise DomainException("Max alerts per hour must be positive")

        valid_channels = ['email', 'sms', 'slack', 'webhook', 'dashboard']
        for channel in self.notification_channels:
            if channel not in valid_channels:
                raise DomainException(f"Invalid notification channel: {channel}")

    def should_send_alert(
        self,
        last_alert_time: Optional[datetime],
        alerts_this_hour: int
    ) -> bool:
        """Check if an alert should be sent."""
        # Check cooldown period
        if last_alert_time:
            cooldown_end = last_alert_time + timedelta(minutes=self.alert_cooldown_minutes)
            if datetime.utcnow() < cooldown_end:
                return False

        # Check hourly limit
        if alerts_this_hour >= self.max_alerts_per_hour:
            return False

        return True

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary."""
        return {
            'monitoring_interval_seconds': self.monitoring_interval_seconds,
            'alert_cooldown_minutes': self.alert_cooldown_minutes,
            'auto_hedging_enabled': self.auto_hedging_enabled,
            'position_reduction_enabled': self.position_reduction_enabled,
            'emergency_stop_enabled': self.emergency_stop_enabled,
            'max_alerts_per_hour': self.max_alerts_per_hour,
            'notification_channels': self.notification_channels
        }

