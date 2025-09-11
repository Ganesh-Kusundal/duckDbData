"""
Analytics Domain Queries for CQRS Pattern

Queries for reading analytics data including indicators, analysis results,
and statistical information.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base_query import Query


@dataclass
class GetIndicatorByIdQuery(Query):
    """
    Query to get indicator details by ID

    Retrieves complete indicator information including parameters and values.
    """

    indicator_id: str

    @property
    def query_type(self) -> str:
        return "GetIndicatorById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'indicator_id': self.indicator_id
        }


@dataclass
class GetIndicatorsBySymbolQuery(Query):
    """
    Query to get indicators for a specific symbol

    Retrieves all indicators calculated for a given symbol and timeframe.
    """

    symbol: str
    timeframe: str
    indicator_names: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def query_type(self) -> str:
        return "GetIndicatorsBySymbol"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'indicator_names': self.indicator_names,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }


@dataclass
class GetAnalysisByIdQuery(Query):
    """
    Query to get analysis details by ID

    Retrieves complete analysis information including results and signals.
    """

    analysis_id: str

    @property
    def query_type(self) -> str:
        return "GetAnalysisById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'analysis_id': self.analysis_id
        }


@dataclass
class GetAnalysisHistoryQuery(Query):
    """
    Query to get analysis history for a symbol

    Retrieves historical analysis results within a date range.
    """

    symbol: str
    timeframe: str
    analysis_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetAnalysisHistory"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'analysis_type': self.analysis_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'limit': self.limit
        }


@dataclass
class GetIndicatorValuesQuery(Query):
    """
    Query to get indicator values within a date range

    Retrieves time series of indicator values for analysis.
    """

    indicator_id: str
    start_date: datetime
    end_date: datetime

    @property
    def query_type(self) -> str:
        return "GetIndicatorValues"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'indicator_id': self.indicator_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }


@dataclass
class GetTechnicalSignalsQuery(Query):
    """
    Query to get technical signals

    Retrieves trading signals generated from technical analysis.
    """

    symbol: str
    timeframe: str
    signal_types: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_confidence: float = 0.0

    @property
    def query_type(self) -> str:
        return "GetTechnicalSignals"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'signal_types': self.signal_types,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'min_confidence': self.min_confidence
        }


@dataclass
class GetAnalysisTemplatesQuery(Query):
    """
    Query to get available analysis templates

    Retrieves list of predefined analysis templates.
    """

    analysis_type_filter: Optional[str] = None
    active_only: bool = True

    @property
    def query_type(self) -> str:
        return "GetAnalysisTemplates"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'analysis_type_filter': self.analysis_type_filter,
            'active_only': self.active_only
        }


@dataclass
class GetStatisticalSummaryQuery(Query):
    """
    Query to get statistical summary of market data

    Retrieves statistical measures for price and volume data.
    """

    symbol: str
    timeframe: str
    statistics: List[str]  # e.g., ["mean", "std", "min", "max", "skew", "kurtosis"]
    periods: int = 252  # Trading days to analyze

    @property
    def query_type(self) -> str:
        return "GetStatisticalSummary"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'statistics': self.statistics,
            'periods': self.periods
        }


@dataclass
class GetCorrelationAnalysisQuery(Query):
    """
    Query to get correlation analysis between symbols

    Retrieves correlation matrix and analysis for multiple symbols.
    """

    symbols: List[str]
    timeframe: str
    correlation_method: str = "pearson"
    periods: int = 252

    @property
    def query_type(self) -> str:
        return "GetCorrelationAnalysis"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbols': self.symbols,
            'timeframe': self.timeframe,
            'correlation_method': self.correlation_method,
            'periods': self.periods
        }


@dataclass
class GetVolatilityAnalysisQuery(Query):
    """
    Query to get volatility analysis

    Retrieves volatility measures and analysis for a symbol.
    """

    symbol: str
    timeframe: str
    volatility_measures: List[str]  # e.g., ["historical", "ewma", "garch"]
    periods: int = 252

    @property
    def query_type(self) -> str:
        return "GetVolatilityAnalysis"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'volatility_measures': self.volatility_measures,
            'periods': self.periods
        }


@dataclass
class GetMarketRegimeQuery(Query):
    """
    Query to get current market regime classification

    Retrieves market regime analysis (bull, bear, sideways, volatile).
    """

    symbol: str
    timeframe: str
    regime_indicators: List[str]
    lookback_periods: int = 252

    @property
    def query_type(self) -> str:
        return "GetMarketRegime"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'regime_indicators': self.regime_indicators,
            'lookback_periods': self.lookback_periods
        }


@dataclass
class GetIndicatorComparisonQuery(Query):
    """
    Query to compare multiple indicators

    Retrieves comparison analysis between different indicators.
    """

    symbol: str
    timeframe: str
    indicator_configs: List[Dict[str, Any]]
    comparison_metrics: List[str]  # e.g., ["correlation", "divergence", "signal_quality"]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def query_type(self) -> str:
        return "GetIndicatorComparison"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'indicator_configs': self.indicator_configs,
            'comparison_metrics': self.comparison_metrics,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }


@dataclass
class GetAnalysisPerformanceQuery(Query):
    """
    Query to get analysis performance metrics

    Retrieves performance statistics for analysis accuracy and reliability.
    """

    analysis_type: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime

    @property
    def query_type(self) -> str:
        return "GetAnalysisPerformance"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'analysis_type': self.analysis_type,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }


@dataclass
class GetDataQualityMetricsQuery(Query):
    """
    Query to get data quality metrics

    Retrieves metrics about data completeness, accuracy, and reliability.
    """

    symbol: str
    timeframe: str
    quality_checks: List[str]  # e.g., ["missing_data", "outliers", "consistency"]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def query_type(self) -> str:
        return "GetDataQualityMetrics"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'quality_checks': self.quality_checks,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }
