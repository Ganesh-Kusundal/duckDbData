"""
Broker Integration Domain Queries for CQRS Pattern

Queries for reading broker integration data including connections,
accounts, orders, and executions.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from .base_query import Query


@dataclass
class GetBrokerConnectionByIdQuery(Query):
    """
    Query to get broker connection details by ID

    Retrieves complete connection information including status and configuration.
    """

    connection_id: str

    @property
    def query_type(self) -> str:
        return "GetBrokerConnectionById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id
        }


@dataclass
class GetBrokerConnectionsQuery(Query):
    """
    Query to get broker connections

    Retrieves list of broker connections with optional filtering.
    """

    broker_filter: Optional[str] = None
    status_filter: Optional[str] = None
    active_only: bool = True

    @property
    def query_type(self) -> str:
        return "GetBrokerConnections"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'broker_filter': self.broker_filter,
            'status_filter': self.status_filter,
            'active_only': self.active_only
        }


@dataclass
class GetBrokerAccountByIdQuery(Query):
    """
    Query to get broker account details by ID

    Retrieves complete account information including balances and positions.
    """

    account_id: str

    @property
    def query_type(self) -> str:
        return "GetBrokerAccountById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'account_id': self.account_id
        }


@dataclass
class GetBrokerAccountsQuery(Query):
    """
    Query to get broker accounts

    Retrieves list of broker accounts with optional filtering.
    """

    connection_id_filter: Optional[str] = None
    account_type_filter: Optional[str] = None
    active_only: bool = True

    @property
    def query_type(self) -> str:
        return "GetBrokerAccounts"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id_filter': self.connection_id_filter,
            'account_type_filter': self.account_type_filter,
            'active_only': self.active_only
        }


@dataclass
class GetBrokerOrdersQuery(Query):
    """
    Query to get broker orders

    Retrieves orders from broker integration with filtering.
    """

    connection_id: Optional[str] = None
    account_id: Optional[str] = None
    symbol_filter: Optional[str] = None
    status_filter: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100

    @property
    def query_type(self) -> str:
        return "GetBrokerOrders"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'account_id': self.account_id,
            'symbol_filter': self.symbol_filter,
            'status_filter': self.status_filter,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'limit': self.limit
        }


@dataclass
class GetBrokerOrderByIdQuery(Query):
    """
    Query to get broker order by ID

    Retrieves specific order details from broker.
    """

    broker_order_id: str
    connection_id: Optional[str] = None

    @property
    def query_type(self) -> str:
        return "GetBrokerOrderById"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'broker_order_id': self.broker_order_id,
            'connection_id': self.connection_id
        }


@dataclass
class GetBrokerPositionsQuery(Query):
    """
    Query to get broker positions

    Retrieves current positions from broker accounts.
    """

    connection_id: Optional[str] = None
    account_id: Optional[str] = None
    symbol_filter: Optional[str] = None

    @property
    def query_type(self) -> str:
        return "GetBrokerPositions"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'account_id': self.account_id,
            'symbol_filter': self.symbol_filter
        }


@dataclass
class GetBrokerExecutionsQuery(Query):
    """
    Query to get broker executions

    Retrieves trade executions from broker with filtering.
    """

    connection_id: Optional[str] = None
    account_id: Optional[str] = None
    symbol_filter: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 500

    @property
    def query_type(self) -> str:
        return "GetBrokerExecutions"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'account_id': self.account_id,
            'symbol_filter': self.symbol_filter,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'limit': self.limit
        }


@dataclass
class GetBrokerCapabilitiesQuery(Query):
    """
    Query to get broker capabilities

    Retrieves supported features and limitations for a broker.
    """

    connection_id: str

    @property
    def query_type(self) -> str:
        return "GetBrokerCapabilities"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id
        }


@dataclass
class GetConnectionStatusQuery(Query):
    """
    Query to get connection status

    Retrieves detailed status information for broker connections.
    """

    connection_id: str

    @property
    def query_type(self) -> str:
        return "GetConnectionStatus"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id
        }


@dataclass
class GetAccountBalanceQuery(Query):
    """
    Query to get account balance

    Retrieves current account balance and margin information.
    """

    account_id: str

    @property
    def query_type(self) -> str:
        return "GetAccountBalance"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'account_id': self.account_id
        }


@dataclass
class GetAccountSummaryQuery(Query):
    """
    Query to get account summary

    Retrieves comprehensive account information including P&L and positions.
    """

    account_id: str
    include_positions: bool = True
    include_orders: bool = True

    @property
    def query_type(self) -> str:
        return "GetAccountSummary"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'account_id': self.account_id,
            'include_positions': self.include_positions,
            'include_orders': self.include_orders
        }


@dataclass
class GetBrokerActivityLogQuery(Query):
    """
    Query to get broker activity log

    Retrieves activity log for broker connections and operations.
    """

    connection_id: Optional[str] = None
    account_id: Optional[str] = None
    activity_types: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 1000

    @property
    def query_type(self) -> str:
        return "GetBrokerActivityLog"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'account_id': self.account_id,
            'activity_types': self.activity_types,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'limit': self.limit
        }


@dataclass
class GetBrokerPerformanceMetricsQuery(Query):
    """
    Query to get broker performance metrics

    Retrieves performance statistics for broker operations.
    """

    connection_id: str
    metrics: List[str]  # e.g., ["execution_speed", "slippage", "commission_cost"]
    start_date: datetime
    end_date: datetime

    @property
    def query_type(self) -> str:
        return "GetBrokerPerformanceMetrics"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'metrics': self.metrics,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }


@dataclass
class GetSupportedAssetsQuery(Query):
    """
    Query to get supported assets

    Retrieves list of supported assets and trading pairs for a broker.
    """

    connection_id: str
    asset_class_filter: Optional[str] = None

    @property
    def query_type(self) -> str:
        return "GetSupportedAssets"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'asset_class_filter': self.asset_class_filter
        }


@dataclass
class GetBrokerOrderBookQuery(Query):
    """
    Query to get broker order book

    Retrieves order book information from broker for a symbol.
    """

    connection_id: str
    symbol: str
    depth: int = 10

    @property
    def query_type(self) -> str:
        return "GetBrokerOrderBook"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'symbol': self.symbol,
            'depth': self.depth
        }


@dataclass
class GetBrokerMarketDataQuery(Query):
    """
    Query to get broker market data

    Retrieves market data from broker sources.
    """

    connection_id: str
    symbol: str
    data_type: str  # "quote", "time_and_sales", "level2"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def query_type(self) -> str:
        return "GetBrokerMarketData"

    def _get_query_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'symbol': self.symbol,
            'data_type': self.data_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }
