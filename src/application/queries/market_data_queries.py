"""
Market Data Queries for CQRS Pattern
Queries for market data read operations
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .base_query import Query


@dataclass
class GetMarketDataQuery(Query):
    """
    Query to get current market data for a symbol
    Retrieves latest price and volume information
    """

    symbol: str
    timeframe: str = "1D"

    @property
    def query_type(self) -> str:
        return "GetMarketData"

    def _get_query_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe
        }


@dataclass
class GetMarketDataHistoryQuery(Query):
    """
    Query to get historical market data
    Retrieves price history over a specified time period
    """

    symbol: str
    timeframe: str = "1D"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 1000
    include_extended_hours: bool = False

    def __post_init__(self):
        # Set default date range if not provided (last 30 days)
        if self.end_date is None:
            self.end_date = datetime.now()
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=30)

    @property
    def query_type(self) -> str:
        return "GetMarketDataHistory"

    def _get_query_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'limit': self.limit,
            'include_extended_hours': self.include_extended_hours
        }


@dataclass
class GetMarketDataSummaryQuery(Query):
    """
    Query to get market data summary statistics
    Provides overview of price movements and volume analysis
    """

    symbol: str
    timeframe: str = "1D"
    analysis_period_days: int = 30

    @property
    def query_type(self) -> str:
        return "GetMarketDataSummary"

    def _get_query_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'analysis_period_days': self.analysis_period_days
        }


@dataclass
class GetTechnicalIndicatorsQuery(Query):
    """
    Query to get technical indicators
    Calculates and returns various technical analysis indicators
    """

    symbol: str
    timeframe: str = "1D"
    indicators: List[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    parameters: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.indicators is None:
            self.indicators = ['SMA', 'EMA', 'RSI']
        if self.parameters is None:
            self.parameters = {'sma_period': 20, 'ema_period': 20, 'rsi_period': 14}

        # Set default date range if not provided
        if self.end_date is None:
            self.end_date = datetime.now()
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=90)  # 3 months for indicators

    @property
    def query_type(self) -> str:
        return "GetTechnicalIndicators"

    def _get_query_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'indicators': self.indicators,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'parameters': self.parameters
        }


@dataclass
class GetMarketAnomaliesQuery(Query):
    """
    Query to get market anomalies
    Detects unusual price movements or volume spikes
    """

    symbol: str
    timeframe: str = "1D"
    anomaly_types: List[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sensitivity_threshold: float = 0.05

    def __post_init__(self):
        if self.anomaly_types is None:
            self.anomaly_types = ['price_spike', 'volume_spike', 'gap_up', 'gap_down']

        # Set default date range if not provided
        if self.end_date is None:
            self.end_date = datetime.now()
        if self.start_date is None:
            self.start_date = self.end_date - timedelta(days=30)

    @property
    def query_type(self) -> str:
        return "GetMarketAnomalies"

    def _get_query_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'anomaly_types': self.anomaly_types,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'sensitivity_threshold': self.sensitivity_threshold
        }


@dataclass
class GetMarketDataByCriteriaQuery(Query):
    """
    Query to get market data by custom criteria
    Flexible query for complex filtering requirements
    """

    criteria: Dict[str, Any]
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    limit: int = 1000
    offset: int = 0

    @property
    def query_type(self) -> str:
        return "GetMarketDataByCriteria"

    def _get_query_data(self) -> dict:
        return {
            'criteria': self.criteria,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
            'limit': self.limit,
            'offset': self.offset
        }


@dataclass
class GetAvailableSymbolsQuery(Query):
    """
    Query to get list of available symbols
    Returns all trading symbols with market data
    """

    exchange: Optional[str] = None
    has_recent_data: bool = True  # Only symbols with data in last 30 days
    min_data_points: int = 1

    @property
    def query_type(self) -> str:
        return "GetAvailableSymbols"

    def _get_query_data(self) -> dict:
        return {
            'exchange': self.exchange,
            'has_recent_data': self.has_recent_data,
            'min_data_points': self.min_data_points
        }


@dataclass
class GetMarketDataStatisticsQuery(Query):
    """
    Query to get market data statistics
    Provides database-level statistics and metadata
    """

    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    include_data_quality: bool = True
    include_date_coverage: bool = True

    @property
    def query_type(self) -> str:
        return "GetMarketDataStatistics"

    def _get_query_data(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'include_data_quality': self.include_data_quality,
            'include_date_coverage': self.include_date_coverage
        }


@dataclass
class SearchMarketDataQuery(Query):
    """
    Query to search market data with text-based criteria
    Supports flexible search across multiple fields
    """

    search_term: str
    search_fields: List[str] = None
    limit: int = 50
    exact_match: bool = False

    def __post_init__(self):
        if self.search_fields is None:
            self.search_fields = ['symbol']

    @property
    def query_type(self) -> str:
        return "SearchMarketData"

    def _get_query_data(self) -> dict:
        return {
            'search_term': self.search_term,
            'search_fields': self.search_fields,
            'limit': self.limit,
            'exact_match': self.exact_match
        }
