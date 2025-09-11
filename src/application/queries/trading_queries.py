"""
Trading Domain Queries for CQRS Pattern

Queries for reading trading data including orders, positions,
portfolio information, and trading history.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base_query import Query


@dataclass
class GetOrderByIdQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get order details by ID

    Retrieves complete order information including status and executions.
    """

    order_id: str

    @property
    def query_type(self) -> str:
        return "GetOrderById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id
        }


@dataclass
class GetOrdersBySymbolQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get orders for a specific symbol

    Retrieves all orders for a given symbol within a date range.
    """

    symbol: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status_filter: Optional[List[str]] = None
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetOrdersBySymbol"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status_filter': self.status_filter,
            'limit': self.limit
        }


@dataclass
class GetOpenOrdersQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get all open orders

    Retrieves orders that are pending execution or partially filled.
    """

    symbol_filter: Optional[str] = None
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetOpenOrders"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol_filter': self.symbol_filter,
            'limit': self.limit
        }


@dataclass
class GetPositionByIdQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get position details by ID

    Retrieves complete position information including P&L and risk metrics.
    """

    position_id: str

    @property
    def query_type(self) -> str:
        return "GetPositionById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id
        }


@dataclass
class GetPositionsBySymbolQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get positions for a specific symbol

    Retrieves all positions for a given symbol.
    """

    symbol: str

    @property
    def query_type(self) -> str:
        return "GetPositionsBySymbol"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol
        }


@dataclass
class GetPortfolioSummaryQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get portfolio summary

    Retrieves overall portfolio metrics including total value, P&L, and allocations.
    """

    include_positions: bool = True
    include_orders: bool = False
    include_history: bool = False

    @property
    def query_type(self) -> str:
        return "GetPortfolioSummary"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'include_positions': self.include_positions,
            'include_orders': self.include_orders,
            'include_history': self.include_history
        }


@dataclass
class GetTradingHistoryQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get trading history

    Retrieves historical trading activity within a date range.
    """

    start_date: datetime
    end_date: datetime
    symbol_filter: Optional[str] = None
    strategy_filter: Optional[str] = None
    limit: int = 1000

    @property
    def query_type(self) -> str:
        return "GetTradingHistory"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'symbol_filter': self.symbol_filter,
            'strategy_filter': self.strategy_filter,
            'limit': self.limit
        }


@dataclass
class GetTradingStrategyQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get trading strategy details

    Retrieves strategy configuration and performance metrics.
    """

    strategy_id: str

    @property
    def query_type(self) -> str:
        return "GetTradingStrategy"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'strategy_id': self.strategy_id
        }


@dataclass
class GetTradingStrategiesQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get all trading strategies

    Retrieves list of all configured trading strategies.
    """

    active_only: bool = True
    strategy_type_filter: Optional[str] = None

    @property
    def query_type(self) -> str:
        return "GetTradingStrategies"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'active_only': self.active_only,
            'strategy_type_filter': self.strategy_type_filter
        }


@dataclass
class GetRiskMetricsQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get risk metrics for positions

    Retrieves risk metrics including VaR, drawdown, and exposure analysis.
    """

    position_id: Optional[str] = None
    symbol_filter: Optional[str] = None
    include_portfolio_level: bool = True

    @property
    def query_type(self) -> str:
        return "GetRiskMetrics"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'position_id': self.position_id,
            'symbol_filter': self.symbol_filter,
            'include_portfolio_level': self.include_portfolio_level
        }


@dataclass
class GetPerformanceMetricsQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get performance metrics

    Retrieves performance statistics including returns, Sharpe ratio, etc.
    """

    timeframe: str = "1M"  # "1D", "1W", "1M", "3M", "6M", "1Y", "ALL"
    include_benchmark: bool = True
    benchmark_symbol: Optional[str] = None

    @property
    def query_type(self) -> str:
        return "GetPerformanceMetrics"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'timeframe': self.timeframe,
            'include_benchmark': self.include_benchmark,
            'benchmark_symbol': self.benchmark_symbol
        }


@dataclass
class GetOrderExecutionDetailsQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get detailed order execution information

    Retrieves execution timeline, slippage analysis, and broker performance.
    """

    order_id: str

    @property
    def query_type(self) -> str:
        return "GetOrderExecutionDetails"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'order_id': self.order_id
        }


@dataclass
class GetDailyTradingActivityQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get daily trading activity summary

    Retrieves trading activity aggregated by day.
    """

    date: date
    symbol_filter: Optional[str] = None

    @property
    def query_type(self) -> str:
        return "GetDailyTradingActivity"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'date': self.date.isoformat(),
            'symbol_filter': self.symbol_filter
        }


@dataclass
class GetStrategyPerformanceQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get strategy performance metrics

    Retrieves performance statistics for specific trading strategies.
    """

    strategy_id: str
    start_date: datetime
    end_date: datetime

    @property
    def query_type(self) -> str:
        return "GetStrategyPerformance"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'strategy_id': self.strategy_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }


@dataclass
class GetTaxLotInformationQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get tax lot information for tax reporting

    Retrieves position information needed for tax calculations.
    """

    symbol: str
    tax_year: Optional[int] = None

    @property
    def query_type(self) -> str:
        return "GetTaxLotInformation"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'tax_year': self.tax_year
        }


@dataclass
class GetCommissionAnalysisQuery(Query):

    def __post_init__(self):
        # Initialize base Query attributes
        super().__init__()
    """
    Query to get commission and fee analysis

    Retrieves commission costs and fee analysis for trading activity.
    """

    start_date: datetime
    end_date: datetime
    symbol_filter: Optional[str] = None
    broker_filter: Optional[str] = None

    @property
    def query_type(self) -> str:
        return "GetCommissionAnalysis"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'symbol_filter': self.symbol_filter,
            'broker_filter': self.broker_filter
        }
