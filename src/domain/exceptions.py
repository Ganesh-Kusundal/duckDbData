"""
Custom domain exceptions for the trading platform.
These exceptions follow clean architecture principles:
- Domain exceptions for business logic errors
- Infrastructure exceptions for technical failures
"""

from datetime import datetime
from typing import Optional, Dict, Any


class TradingError(Exception):
    """Base exception for all trading platform errors."""
    
    def __init__(self, message: str, symbol: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None, timestamp: Optional[datetime] = None):
        """
        Initialize TradingError with structured data.
        
        Args:
            message: Error message
            symbol: Affected symbol (if applicable)
            context: Additional context data
            timestamp: Error timestamp
        """
        self.message = message
        self.symbol = symbol
        self.context = context or {}
        self.timestamp = timestamp or datetime.now()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to structured dictionary for logging."""
        return {
            'error_type': self.__class__.__name__,
            'error_message': self.message,
            'symbol': self.symbol,
            'context': self.context,
            'timestamp': self.timestamp.isoformat()
        }


class DataSyncError(TradingError):
    """Exception for data synchronization failures."""


class ScannerError(TradingError):
    """Exception for scanner execution failures."""
    
    def __init__(self, message: str, scanner_name: str, symbol: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None, timestamp: Optional[datetime] = None):
        """
        Initialize ScannerError with scanner-specific details.
        
        Args:
            message: Error message
            scanner_name: Name of the failed scanner
            symbol: Affected symbol
            context: Additional context
            timestamp: Error timestamp
        """
        self.scanner_name = scanner_name
        context = context or {}
        context['scanner_name'] = scanner_name
        super().__init__(message, symbol, context, timestamp)


class DatabaseConnectionError(TradingError):
    """Exception for database connection and query failures."""
    
    def __init__(self, message: str, operation: str, symbol: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None, timestamp: Optional[datetime] = None):
        """
        Initialize DatabaseConnectionError with operation details.
        
        Args:
            message: Error message
            operation: Database operation that failed (e.g., 'connect', 'query')
            symbol: Affected symbol
            context: Additional context
            timestamp: Error timestamp
        """
        self.operation = operation
        context = context or {}
        context['operation'] = operation
        super().__init__(message, symbol, context, timestamp)


class BrokerAPIError(TradingError):
    """Exception for broker API communication failures."""
    
    def __init__(self, message: str, broker_name: str, endpoint: str, 
                 symbol: Optional[str] = None, context: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[datetime] = None):
        """
        Initialize BrokerAPIError with broker details.
        
        Args:
            message: Error message
            broker_name: Name of the broker
            endpoint: API endpoint that failed
            symbol: Affected symbol
            context: Additional context
            timestamp: Error timestamp
        """
        self.broker_name = broker_name
        self.endpoint = endpoint
        context = context or {}
        context.update({
            'broker_name': broker_name,
            'endpoint': endpoint
        })
        super().__init__(message, symbol, context, timestamp)


class ValidationError(TradingError):
    """Exception for data validation failures."""
    
    def __init__(self, message: str, field: str, value: Any, 
                 symbol: Optional[str] = None, context: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[datetime] = None):
        """
        Initialize ValidationError with field validation details.
        
        Args:
            message: Error message
            field: Invalid field name
            value: Invalid value
            symbol: Affected symbol
            context: Additional context
            timestamp: Error timestamp
        """
        self.field = field
        self.value = value
        context = context or {}
        context.update({
            'field': field,
            'invalid_value': str(value)
        })
        super().__init__(message, symbol, context, timestamp)