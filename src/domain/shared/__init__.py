"""
Domain Shared Module
Contains cross-cutting concerns used across bounded contexts
"""

from .exceptions import (
    TradingError,
    DataSyncError,
    ScannerError,
    DatabaseConnectionError,
    BrokerAPIError,
    ValidationError,
    MarketDataError,
    OrderError,
    RiskManagementError,
    AnalyticsError,
    ConfigurationError,
    BUSINESS_ERRORS,
    INFRASTRUCTURE_ERRORS,
    SYSTEM_ERRORS,
    ALL_TRADING_ERRORS
)

__all__ = [
    'TradingError',
    'DataSyncError',
    'ScannerError',
    'DatabaseConnectionError',
    'BrokerAPIError',
    'ValidationError',
    'MarketDataError',
    'OrderError',
    'RiskManagementError',
    'AnalyticsError',
    'ConfigurationError',
    'BUSINESS_ERRORS',
    'INFRASTRUCTURE_ERRORS',
    'SYSTEM_ERRORS',
    'ALL_TRADING_ERRORS'
]
