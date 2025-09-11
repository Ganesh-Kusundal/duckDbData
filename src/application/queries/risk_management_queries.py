"""
Risk Management Domain Queries for CQRS Pattern

Queries for reading risk management data including risk assessments,
limits, profiles, and risk metrics.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base_query import Query


@dataclass
class GetRiskProfileByIdQuery(Query):
    """
    Query to get risk profile details by ID

    Retrieves complete risk profile information including limits and rules.
    """

    profile_id: str

    @property
    def query_type(self) -> str:
        return "GetRiskProfileById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'profile_id': self.profile_id
        }


@dataclass
class GetRiskProfilesQuery(Query):
    """
    Query to get risk profiles

    Retrieves list of available risk profiles with optional filtering.
    """

    active_only: bool = True
    risk_tolerance_filter: Optional[str] = None

    @property
    def query_type(self) -> str:
        return "GetRiskProfiles"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'active_only': self.active_only,
            'risk_tolerance_filter': self.risk_tolerance_filter
        }


@dataclass
class GetRiskAssessmentByIdQuery(Query):
    """
    Query to get risk assessment details by ID

    Retrieves complete risk assessment information including results and recommendations.
    """

    assessment_id: str

    @property
    def query_type(self) -> str:
        return "GetRiskAssessmentById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'assessment_id': self.assessment_id
        }


@dataclass
class GetRiskAssessmentsQuery(Query):
    """
    Query to get risk assessments

    Retrieves risk assessments within a date range with optional filtering.
    """

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    assessment_type_filter: Optional[str] = None
    target_filter: Optional[str] = None
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetRiskAssessments"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'assessment_type_filter': self.assessment_type_filter,
            'target_filter': self.target_filter,
            'limit': self.limit
        }


@dataclass
class GetPositionRiskMetricsQuery(Query):
    """
    Query to get risk metrics for a position

    Retrieves risk metrics including VaR, drawdown, and exposure for a specific position.
    """

    position_id: str
    metrics: List[str]  # e.g., ["var", "sharpe_ratio", "max_drawdown", "beta"]

    @property
    def query_type(self) -> str:
        return "GetPositionRiskMetrics"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'metrics': self.metrics
        }


@dataclass
class GetPortfolioRiskMetricsQuery(Query):
    """
    Query to get risk metrics for a portfolio

    Retrieves comprehensive risk metrics for the entire portfolio.
    """

    portfolio_id: str
    metrics: List[str]
    include_positions: bool = True

    @property
    def query_type(self) -> str:
        return "GetPortfolioRiskMetrics"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'portfolio_id': self.portfolio_id,
            'metrics': self.metrics,
            'include_positions': self.include_positions
        }


@dataclass
class GetRiskLimitsQuery(Query):
    """
    Query to get risk limits

    Retrieves current risk limits for positions, portfolio, or trading strategies.
    """

    target_type: str  # "position", "portfolio", "strategy"
    target_id: Optional[str] = None
    limit_types: Optional[List[str]] = None

    @property
    def query_type(self) -> str:
        return "GetRiskLimits"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'target_type': self.target_type,
            'target_id': self.target_id,
            'limit_types': self.limit_types
        }


@dataclass
class GetRiskBreachesQuery(Query):
    """
    Query to get risk breaches

    Retrieves list of risk limit breaches with details.
    """

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    breach_types: Optional[List[str]] = None
    resolved_only: bool = False
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetRiskBreaches"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'breach_types': self.breach_types,
            'resolved_only': self.resolved_only,
            'limit': self.limit
        }


@dataclass
class GetVaRAnalysisQuery(Query):
    """
    Query to get VaR analysis

    Retrieves Value at Risk calculations and analysis.
    """

    target_type: str  # "position", "portfolio"
    target_id: str
    confidence_levels: List[float]
    time_horizons: List[int]

    @property
    def query_type(self) -> str:
        return "GetVaRAnalysis"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'target_type': self.target_type,
            'target_id': self.target_id,
            'confidence_levels': self.confidence_levels,
            'time_horizons': self.time_horizons
        }


@dataclass
class GetStressTestResultsQuery(Query):
    """
    Query to get stress test results

    Retrieves results from portfolio stress testing.
    """

    portfolio_id: str
    scenario_ids: Optional[List[str]] = None
    shock_sizes: Optional[List[float]] = None

    @property
    def query_type(self) -> str:
        return "GetStressTestResults"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'portfolio_id': self.portfolio_id,
            'scenario_ids': self.scenario_ids,
            'shock_sizes': self.shock_sizes
        }


@dataclass
class GetRiskAlertsQuery(Query):
    """
    Query to get risk alerts

    Retrieves active risk alerts and warnings.
    """

    alert_types: Optional[List[str]] = None
    severity_levels: Optional[List[str]] = None
    acknowledged: bool = False
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetRiskAlerts"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'alert_types': self.alert_types,
            'severity_levels': self.severity_levels,
            'acknowledged': self.acknowledged,
            'limit': self.limit
        }


@dataclass
class GetRiskReportQuery(Query):
    """
    Query to get risk report

    Retrieves pre-generated risk reports.
    """

    report_id: str

    @property
    def query_type(self) -> str:
        return "GetRiskReport"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id
        }


@dataclass
class GetRiskProfilePerformanceQuery(Query):
    """
    Query to get risk profile performance

    Retrieves performance statistics for risk profiles.
    """

    profile_id: str
    start_date: datetime
    end_date: datetime

    @property
    def query_type(self) -> str:
        return "GetRiskProfilePerformance"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'profile_id': self.profile_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }


@dataclass
class GetPositionRiskLimitsQuery(Query):
    """
    Query to get risk limits for a specific position

    Retrieves all risk limits applicable to a position.
    """

    position_id: str

    @property
    def query_type(self) -> str:
        return "GetPositionRiskLimits"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id
        }


@dataclass
class GetPortfolioRiskExposureQuery(Query):
    """
    Query to get portfolio risk exposure

    Retrieves detailed risk exposure analysis for the portfolio.
    """

    portfolio_id: str
    exposure_types: List[str]  # e.g., ["sector", "asset_class", "geography", "currency"]

    @property
    def query_type(self) -> str:
        return "GetPortfolioRiskExposure"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'portfolio_id': self.portfolio_id,
            'exposure_types': self.exposure_types
        }


@dataclass
class GetRiskComplianceStatusQuery(Query):
    """
    Query to get risk compliance status

    Retrieves compliance status against risk policies and regulations.
    """

    target_type: str  # "position", "portfolio", "firm"
    target_id: str
    compliance_frameworks: List[str]

    @property
    def query_type(self) -> str:
        return "GetRiskComplianceStatus"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'target_type': self.target_type,
            'target_id': self.target_id,
            'compliance_frameworks': self.compliance_frameworks
        }


@dataclass
class GetRiskTrendAnalysisQuery(Query):
    """
    Query to get risk trend analysis

    Retrieves trend analysis for risk metrics over time.
    """

    target_type: str
    target_id: str
    metrics: List[str]
    start_date: datetime
    end_date: datetime
    trend_periods: int = 30

    @property
    def query_type(self) -> str:
        return "GetRiskTrendAnalysis"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'target_type': self.target_type,
            'target_id': self.target_id,
            'metrics': self.metrics,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'trend_periods': self.trend_periods
        }
