"""
Risk Management Domain Commands for CQRS Pattern

Commands for risk management operations including risk assessment,
limit management, and risk monitoring.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from .base_command import Command


@dataclass
class AssessPortfolioRiskCommand(Command):
    """
    Command to assess portfolio risk

    Performs comprehensive risk assessment on the entire portfolio.
    """

    portfolio_id: str
    risk_metrics: List[str]
    assessment_date: Optional[datetime] = None
    include_stress_tests: bool = True

    @property
    def command_type(self) -> str:
        return "AssessPortfolioRisk"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'portfolio_id': self.portfolio_id,
            'risk_metrics': self.risk_metrics,
            'assessment_date': self.assessment_date.isoformat() if self.assessment_date else None,
            'include_stress_tests': self.include_stress_tests
        }


@dataclass
class CreateRiskProfileCommand(Command):
    """
    Command to create a risk profile

    Defines a new risk management profile with limits and rules.
    """

    name: str
    description: str
    risk_tolerance: str
    position_limits: Dict[str, Any]
    portfolio_limits: Dict[str, Any]
    is_active: bool = True

    @property
    def command_type(self) -> str:
        return "CreateRiskProfile"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'risk_tolerance': self.risk_tolerance,
            'position_limits': self.position_limits,
            'portfolio_limits': self.portfolio_limits,
            'is_active': self.is_active
        }


@dataclass
class UpdateRiskLimitsCommand(Command):
    """
    Command to update risk limits

    Modifies risk limits for positions or portfolio.
    """

    target_type: str  # "position", "portfolio"
    target_id: str
    limit_updates: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "UpdateRiskLimits"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'target_type': self.target_type,
            'target_id': self.target_id,
            'limit_updates': self.limit_updates
        }


@dataclass
class ExecuteRiskCheckCommand(Command):
    """
    Command to execute risk checks

    Performs risk validation against current positions and orders.
    """

    check_type: str
    target_positions: Optional[List[str]] = None
    target_orders: Optional[List[str]] = None
    risk_profile_id: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "ExecuteRiskCheck"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'check_type': self.check_type,
            'target_positions': self.target_positions,
            'target_orders': self.target_orders,
            'risk_profile_id': self.risk_profile_id
        }


@dataclass
class HandleRiskBreachCommand(Command):
    """
    Command to handle risk breach

    Takes corrective actions when risk limits are breached.
    """

    breach_id: str
    action_type: str
    parameters: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "HandleRiskBreach"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'breach_id': self.breach_id,
            'action_type': self.action_type,
            'parameters': self.parameters
        }


@dataclass
class CalculateVaRCommand(Command):
    """
    Command to calculate Value at Risk

    Performs VaR calculations for positions or portfolio.
    """

    target_type: str  # "position", "portfolio"
    target_id: str
    confidence_level: float = 0.95
    time_horizon_days: int = 1
    method: str = "historical"

    @property
    def command_type(self) -> str:
        return "CalculateVaR"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'target_type': self.target_type,
            'target_id': self.target_id,
            'confidence_level': self.confidence_level,
            'time_horizon_days': self.time_horizon_days,
            'method': self.method
        }


@dataclass
class MonitorRiskLimitsCommand(Command):
    """
    Command to monitor risk limits

    Continuously monitors positions against risk limits.
    """

    monitoring_targets: List[str]
    alert_thresholds: Dict[str, float]
    monitoring_frequency: str = "realtime"

    @property
    def command_type(self) -> str:
        return "MonitorRiskLimits"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'monitoring_targets': self.monitoring_targets,
            'alert_thresholds': self.alert_thresholds,
            'monitoring_frequency': self.monitoring_frequency
        }


@dataclass
class GenerateRiskReportCommand(Command):
    """
    Command to generate risk report

    Creates comprehensive risk reports for portfolio or positions.
    """

    report_type: str
    target_id: str
    report_date: Optional[datetime] = None
    include_recommendations: bool = True

    @property
    def command_type(self) -> str:
        return "GenerateRiskReport"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'report_type': self.report_type,
            'target_id': self.target_id,
            'report_date': self.report_date.isoformat() if self.report_date else None,
            'include_recommendations': self.include_recommendations
        }


@dataclass
class StressTestPortfolioCommand(Command):
    """
    Command to stress test portfolio

    Performs stress testing under various market scenarios.
    """

    portfolio_id: str
    scenarios: List[Dict[str, Any]]
    shock_sizes: List[float]

    @property
    def command_type(self) -> str:
        return "StressTestPortfolio"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'portfolio_id': self.portfolio_id,
            'scenarios': self.scenarios,
            'shock_sizes': self.shock_sizes
        }


@dataclass
class SetPositionStopLossCommand(Command):
    """
    Command to set position stop loss

    Sets or updates stop loss levels for positions.
    """

    position_id: str
    stop_loss_price: Decimal
    stop_loss_type: str = "fixed"
    trailing_amount: Optional[Decimal] = None

    @property
    def command_type(self) -> str:
        return "SetPositionStopLoss"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'stop_loss_price': str(self.stop_loss_price),
            'stop_loss_type': self.stop_loss_type,
            'trailing_amount': str(self.trailing_amount) if self.trailing_amount else None
        }


@dataclass
class AdjustPortfolioAllocationCommand(Command):
    """
    Command to adjust portfolio allocation

    Rebalances portfolio to target allocations.
    """

    portfolio_id: str
    target_allocations: Dict[str, float]
    rebalance_method: str = "proportional"
    tolerance_percentage: float = 5.0

    @property
    def command_type(self) -> str:
        return "AdjustPortfolioAllocation"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'portfolio_id': self.portfolio_id,
            'target_allocations': self.target_allocations,
            'rebalance_method': self.rebalance_method,
            'tolerance_percentage': self.tolerance_percentage
        }


@dataclass
class EvaluateRiskRewardCommand(Command):
    """
    Command to evaluate risk-reward ratio

    Analyzes risk-reward characteristics of potential trades.
    """

    symbol: str
    entry_price: Decimal
    stop_loss_price: Decimal
    target_price: Decimal
    position_size: int

    @property
    def command_type(self) -> str:
        return "EvaluateRiskReward"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'entry_price': str(self.entry_price),
            'stop_loss_price': str(self.stop_loss_price),
            'target_price': str(self.target_price),
            'position_size': self.position_size
        }


@dataclass
class UpdateRiskProfileCommand(Command):
    """
    Command to update risk profile

    Modifies an existing risk profile's parameters.
    """

    profile_id: str
    updates: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "UpdateRiskProfile"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'profile_id': self.profile_id,
            'updates': self.updates
        }


@dataclass
class ArchiveRiskAssessmentCommand(Command):
    """
    Command to archive risk assessment

    Archives old risk assessments for historical reference.
    """

    assessment_ids: List[str]
    archive_reason: str

    @property
    def command_type(self) -> str:
        return "ArchiveRiskAssessment"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'assessment_ids': self.assessment_ids,
            'archive_reason': self.archive_reason
        }
