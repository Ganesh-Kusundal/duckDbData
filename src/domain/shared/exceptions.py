"""
Domain-specific exceptions for the trading system.
Provides structured error handling with context information.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ErrorContext:
    """Structured context information for errors"""
    operation: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


class DomainException(Exception):
    """
    Base exception for all domain-related errors.
    Provides structured error information for domain logic violations.
    """

    def __init__(self,
                 message: str,
                 entity_type: Optional[str] = None,
                 entity_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.context = context or {}
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        entity_info = f" [{self.entity_type}:{self.entity_id}]" if self.entity_type and self.entity_id else ""
        return f"{self.__class__.__name__}: {self.message}{entity_info}"


class TradingError(Exception):
    """
    Base exception for all trading-related errors.
    Provides structured error information for better debugging and monitoring.
    """

    def __init__(self,
                 message: str,
                 symbol: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.symbol = symbol
        self.context = context or {}
        self.timestamp = datetime.now()
        self.cause = cause

    def __str__(self) -> str:
        symbol_info = f" [{self.symbol}]" if self.symbol else ""
        return f"{self.__class__.__name__}: {self.message}{symbol_info}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'symbol': self.symbol,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'cause': str(self.cause) if self.cause else None
        }


class DataSyncError(TradingError):
    """
    Exception raised when data synchronization fails.
    Includes information about sync operation and data source.
    """

    def __init__(self,
                 message: str,
                 data_source: Optional[str] = None,
                 sync_type: Optional[str] = None,
                 record_count: Optional[int] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.data_source = data_source
        self.sync_type = sync_type
        self.record_count = record_count


class ScannerError(TradingError):
    """
    Exception raised when scanner operations fail.
    Includes information about scanning criteria and execution.
    """

    def __init__(self,
                 message: str,
                 scanner_type: Optional[str] = None,
                 criteria: Optional[Dict[str, Any]] = None,
                 execution_time: Optional[float] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.scanner_type = scanner_type
        self.criteria = criteria or {}
        self.execution_time = execution_time


class DatabaseConnectionError(TradingError):
    """
    Exception raised when database connection or operations fail.
    Includes information about database operations and connection details.
    """

    def __init__(self,
                 message: str,
                 operation: Optional[str] = None,
                 connection_string: Optional[str] = None,
                 query: Optional[str] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.operation = operation
        self.connection_string = connection_string
        self.query = query


class BrokerAPIError(TradingError):
    """
    Exception raised when broker API operations fail.
    Includes information about API calls and broker responses.
    """

    def __init__(self,
                 message: str,
                 broker_name: Optional[str] = None,
                 api_endpoint: Optional[str] = None,
                 http_status: Optional[int] = None,
                 api_response: Optional[Dict[str, Any]] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.broker_name = broker_name
        self.api_endpoint = api_endpoint
        self.http_status = http_status
        self.api_response = api_response or {}


class ValidationError(TradingError):
    """
    Exception raised when business rule validation fails.
    Includes information about validation rules and field values.
    """

    def __init__(self,
                 message: str,
                 field_name: Optional[str] = None,
                 field_value: Optional[Any] = None,
                 validation_rule: Optional[str] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule


class MarketDataError(TradingError):
    """
    Exception raised when market data operations fail.
    Includes information about data sources and timeframes.
    """

    def __init__(self,
                 message: str,
                 data_source: Optional[str] = None,
                 timeframe: Optional[str] = None,
                 date_range: Optional[tuple] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.data_source = data_source
        self.timeframe = timeframe
        self.date_range = date_range


class OrderError(TradingError):
    """
    Exception raised when order operations fail.
    Includes information about order details and execution.
    """

    def __init__(self,
                 message: str,
                 order_id: Optional[str] = None,
                 order_type: Optional[str] = None,
                 quantity: Optional[int] = None,
                 price: Optional[float] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.order_id = order_id
        self.order_type = order_type
        self.quantity = quantity
        self.price = price


class RiskManagementError(TradingError):
    """
    Exception raised when risk management operations fail.
    Includes information about risk rules and thresholds.
    """

    def __init__(self,
                 message: str,
                 risk_type: Optional[str] = None,
                 threshold_value: Optional[float] = None,
                 current_value: Optional[float] = None,
                 portfolio_id: Optional[str] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.risk_type = risk_type
        self.threshold_value = threshold_value
        self.current_value = current_value
        self.portfolio_id = portfolio_id


class AnalyticsError(TradingError):
    """
    Exception raised when analytics operations fail.
    Includes information about calculations and data quality.
    """

    def __init__(self,
                 message: str,
                 indicator_name: Optional[str] = None,
                 calculation_period: Optional[int] = None,
                 data_quality_score: Optional[float] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.indicator_name = indicator_name
        self.calculation_period = calculation_period
        self.data_quality_score = data_quality_score


class ConfigurationError(TradingError):
    """
    Exception raised when configuration issues occur.
    Includes information about configuration validation.
    """

    def __init__(self,
                 message: str,
                 config_key: Optional[str] = None,
                 config_value: Optional[Any] = None,
                 expected_type: Optional[str] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_value = config_value
        self.expected_type = expected_type


# Exception hierarchy for error classification
BUSINESS_ERRORS = (
    ValidationError,
    OrderError,
    RiskManagementError,
    AnalyticsError
)

INFRASTRUCTURE_ERRORS = (
    DatabaseConnectionError,
    BrokerAPIError,
    DataSyncError
)

SYSTEM_ERRORS = (
    ConfigurationError,
    TradingError  # Base class for uncategorized errors
)

ALL_TRADING_ERRORS = BUSINESS_ERRORS + INFRASTRUCTURE_ERRORS + SYSTEM_ERRORS
