"""
Scanning Domain Queries for CQRS Pattern

Queries for reading scanning data including scan results, signals,
rules, and templates.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base_query import Query


@dataclass
class GetScanByIdQuery(Query):
    """
    Query to get scan details by ID

    Retrieves complete scan information including results and signals.
    """

    scan_id: str

    @property
    def query_type(self) -> str:
        return "GetScanById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'scan_id': self.scan_id
        }


@dataclass
class GetScanResultsQuery(Query):
    """
    Query to get scan results

    Retrieves results from a specific scan execution.
    """

    scan_id: str
    symbol_filter: Optional[str] = None
    min_confidence: float = 0.0
    limit: int = 1000

    @property
    def query_type(self) -> str:
        return "GetScanResults"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'scan_id': self.scan_id,
            'symbol_filter': self.symbol_filter,
            'min_confidence': self.min_confidence,
            'limit': self.limit
        }


@dataclass
class GetScanningRuleByIdQuery(Query):
    """
    Query to get scanning rule details by ID

    Retrieves complete rule information including parameters and conditions.
    """

    rule_id: str

    @property
    def query_type(self) -> str:
        return "GetScanningRuleById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id
        }


@dataclass
class GetScanningRulesQuery(Query):
    """
    Query to get scanning rules

    Retrieves list of available scanning rules with optional filtering.
    """

    rule_type_filter: Optional[str] = None
    active_only: bool = True
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetScanningRules"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'rule_type_filter': self.rule_type_filter,
            'active_only': self.active_only,
            'limit': self.limit
        }


@dataclass
class GetScanTemplatesQuery(Query):
    """
    Query to get scan templates

    Retrieves list of available scan templates.
    """

    scan_type_filter: Optional[str] = None
    active_only: bool = True

    @property
    def query_type(self) -> str:
        return "GetScanTemplates"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'scan_type_filter': self.scan_type_filter,
            'active_only': self.active_only
        }


@dataclass
class GetScanHistoryQuery(Query):
    """
    Query to get scan history

    Retrieves historical scan executions within a date range.
    """

    start_date: datetime
    end_date: datetime
    scan_type_filter: Optional[str] = None
    symbol_filter: Optional[str] = None
    limit: int = 500

    @property
    def query_type(self) -> str:
        return "GetScanHistory"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'scan_type_filter': self.scan_type_filter,
            'symbol_filter': self.symbol_filter,
            'limit': self.limit
        }


@dataclass
class GetSignalsBySymbolQuery(Query):
    """
    Query to get signals for a specific symbol

    Retrieves trading signals generated for a symbol within a date range.
    """

    symbol: str
    signal_types: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_confidence: float = 0.0
    limit: int = 1000

    @property
    def query_type(self) -> str:
        return "GetSignalsBySymbol"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'signal_types': self.signal_types,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'min_confidence': self.min_confidence,
            'limit': self.limit
        }


@dataclass
class GetRulePerformanceQuery(Query):
    """
    Query to get rule performance metrics

    Retrieves performance statistics for scanning rules.
    """

    rule_id: str
    start_date: datetime
    end_date: datetime
    performance_metrics: List[str]  # e.g., ["hit_rate", "profit_factor", "max_drawdown"]

    @property
    def query_type(self) -> str:
        return "GetRulePerformance"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'performance_metrics': self.performance_metrics
        }


@dataclass
class GetScanStatisticsQuery(Query):
    """
    Query to get scan statistics

    Retrieves statistical information about scan performance and results.
    """

    scan_type: str
    start_date: datetime
    end_date: datetime
    group_by: str = "day"  # "day", "week", "month"

    @property
    def query_type(self) -> str:
        return "GetScanStatistics"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'scan_type': self.scan_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'group_by': self.group_by
        }


@dataclass
class GetTopPerformingRulesQuery(Query):
    """
    Query to get top performing scanning rules

    Retrieves rules ranked by performance metrics.
    """

    metric: str
    timeframe: str = "30D"
    limit: int = 10
    rule_types: Optional[List[str]] = None

    @property
    def query_type(self) -> str:
        return "GetTopPerformingRules"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'metric': self.metric,
            'timeframe': self.timeframe,
            'limit': self.limit,
            'rule_types': self.rule_types
        }


@dataclass
class GetRuleBacktestResultsQuery(Query):
    """
    Query to get rule backtest results

    Retrieves detailed backtest results for a specific rule.
    """

    rule_id: str
    backtest_id: str

    @property
    def query_type(self) -> str:
        return "GetRuleBacktestResults"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'backtest_id': self.backtest_id
        }


@dataclass
class GetSignalDistributionQuery(Query):
    """
    Query to get signal distribution analysis

    Retrieves analysis of signal distribution across different criteria.
    """

    criteria: str  # e.g., "by_symbol", "by_rule", "by_time", "by_confidence"
    start_date: datetime
    end_date: datetime
    signal_types: Optional[List[str]] = None

    @property
    def query_type(self) -> str:
        return "GetSignalDistribution"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'criteria': self.criteria,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'signal_types': self.signal_types
        }


@dataclass
class GetScanAlertsQuery(Query):
    """
    Query to get scan alerts

    Retrieves alerts generated from scan results.
    """

    alert_types: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    acknowledged: bool = False
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetScanAlerts"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'alert_types': self.alert_types,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'acknowledged': self.acknowledged,
            'limit': self.limit
        }


@dataclass
class GetScanningRuleValidationQuery(Query):
    """
    Query to get rule validation results

    Retrieves validation test results for scanning rules.
    """

    rule_id: str
    validation_type: str = "backtest"

    @property
    def query_type(self) -> str:
        return "GetScanningRuleValidation"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'validation_type': self.validation_type
        }


@dataclass
class GetMarketScanSummaryQuery(Query):
    """
    Query to get market scan summary

    Retrieves high-level summary of market scanning activity.
    """

    date: date
    scan_types: Optional[List[str]] = None

    @property
    def query_type(self) -> str:
        return "GetMarketScanSummary"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'scan_types': self.scan_types
        }


@dataclass
class GetSignalQualityMetricsQuery(Query):
    """
    Query to get signal quality metrics

    Retrieves metrics about signal accuracy and reliability.
    """

    signal_type: str
    start_date: datetime
    end_date: datetime
    quality_metrics: List[str]  # e.g., ["precision", "recall", "f1_score", "profit_factor"]

    @property
    def query_type(self) -> str:
        return "GetSignalQualityMetrics"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'signal_type': self.signal_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'quality_metrics': self.quality_metrics
        }
