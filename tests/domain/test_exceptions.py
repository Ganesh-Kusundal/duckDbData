"""
Unit tests for custom domain exceptions.
Tests exception instantiation, inheritance, and structured data handling.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.domain.exceptions import (
    TradingError,
    DataSyncError,
    ScannerError,
    DatabaseConnectionError,
    BrokerAPIError,
    ValidationError
)


class TestTradingError:
    """Tests for the base TradingError exception."""
    
    def test_instantiation(self):
        """Test basic instantiation of TradingError."""
        exc = TradingError("Test error message")
        assert str(exc) == "Test error message"
        assert exc.message == "Test error message"
        assert exc.symbol is None
        assert exc.context == {}
        assert isinstance(exc.timestamp, datetime)
    
    def test_with_symbol_and_context(self):
        """Test instantiation with symbol and context."""
        context = {"key": "value"}
        timestamp = datetime(2023, 1, 1)
        exc = TradingError(
            "Test message", 
            symbol="TEST", 
            context=context, 
            timestamp=timestamp
        )
        assert exc.message == "Test message"
        assert exc.symbol == "TEST"
        assert exc.context == context
        assert exc.timestamp == timestamp
    
    def test_to_dict_structure(self):
        """Test the to_dict method produces correct structure."""
        exc = TradingError("Test error", symbol="TEST")
        exc_dict = exc.to_dict()
        expected = {
            'error_type': 'TradingError',
            'message': 'Test error',
            'symbol': 'TEST',
            'context': {},
            'timestamp': exc.timestamp.isoformat()
        }
        assert exc_dict == expected
    
    def test_inheritance_from_exception(self):
        """Test that TradingError inherits from Exception."""
        exc = TradingError("Test")
        assert isinstance(exc, Exception)


class TestDataSyncError:
    """Tests for DataSyncError exception."""
    
    def test_inheritance(self):
        """Test inheritance from TradingError."""
        exc = DataSyncError("Sync failed")
        assert isinstance(exc, TradingError)
        assert isinstance(exc, Exception)
    
    def test_basic_instantiation(self):
        """Test basic instantiation."""
        exc = DataSyncError("Sync failed", symbol="TEST")
        assert exc.message == "Sync failed"
        assert exc.symbol == "TEST"


class TestScannerError:
    """Tests for ScannerError exception."""
    
    def test_inheritance(self):
        """Test inheritance from TradingError."""
        exc = ScannerError("Scan failed", "test_scanner")
        assert isinstance(exc, TradingError)
        assert isinstance(exc, Exception)
    
    def test_scanner_name_in_context(self):
        """Test that scanner_name is added to context."""
        exc = ScannerError("Scan failed", "test_scanner")
        assert exc.scanner_name == "test_scanner"
        assert exc.context.get('scanner_name') == "test_scanner"
    
    def test_with_symbol_and_context(self):
        """Test instantiation with additional parameters."""
        context = {"extra": "data"}
        exc = ScannerError(
            "Scan failed", 
            "test_scanner", 
            symbol="TEST", 
            context=context
        )
        assert exc.scanner_name == "test_scanner"
        assert exc.symbol == "TEST"
        assert exc.context == {'scanner_name': 'test_scanner', 'extra': 'data'}


class TestDatabaseConnectionError:
    """Tests for DatabaseConnectionError exception."""
    
    def test_inheritance(self):
        """Test inheritance from TradingError."""
        exc = DatabaseConnectionError("Connection failed", "connect")
        assert isinstance(exc, TradingError)
        assert isinstance(exc, Exception)
    
    def test_operation_in_context(self):
        """Test that operation is added to context."""
        exc = DatabaseConnectionError("Connection failed", "connect")
        assert exc.operation == "connect"
        assert exc.context.get('operation') == "connect"
    
    def test_with_symbol_and_context(self):
        """Test instantiation with additional parameters."""
        context = {"database": "test_db"}
        exc = DatabaseConnectionError(
            "Connection failed", 
            "connect", 
            symbol="TEST", 
            context=context
        )
        assert exc.operation == "connect"
        assert exc.symbol == "TEST"
        assert exc.context == {'operation': 'connect', 'database': 'test_db'}


class TestBrokerAPIError:
    """Tests for BrokerAPIError exception."""
    
    def test_inheritance(self):
        """Test inheritance from TradingError."""
        exc = BrokerAPIError("API failed", "test_broker", "endpoint")
        assert isinstance(exc, TradingError)
        assert isinstance(exc, Exception)
    
    def test_broker_details_in_context(self):
        """Test that broker details are added to context."""
        exc = BrokerAPIError("API failed", "test_broker", "endpoint")
        assert exc.broker_name == "test_broker"
        assert exc.endpoint == "endpoint"
        assert exc.context.get('broker_name') == "test_broker"
        assert exc.context.get('endpoint') == "endpoint"
    
    def test_with_symbol_and_context(self):
        """Test instantiation with additional parameters."""
        context = {"status_code": 500}
        exc = BrokerAPIError(
            "API failed", 
            "test_broker", 
            "endpoint", 
            symbol="TEST", 
            context=context
        )
        assert exc.broker_name == "test_broker"
        assert exc.endpoint == "endpoint"
        assert exc.symbol == "TEST"
        expected_context = {
            'broker_name': 'test_broker',
            'endpoint': 'endpoint',
            'status_code': 500
        }
        assert exc.context == expected_context


class TestValidationError:
    """Tests for ValidationError exception."""
    
    def test_inheritance(self):
        """Test inheritance from TradingError."""
        exc = ValidationError("Invalid value", "field", "value")
        assert isinstance(exc, TradingError)
        assert isinstance(exc, Exception)
    
    def test_validation_details_in_context(self):
        """Test that validation details are added to context."""
        exc = ValidationError("Invalid value", "field", "value")
        assert exc.field == "field"
        assert exc.value == "value"
        assert exc.context.get('field') == "field"
        assert exc.context.get('invalid_value') == "value"
    
    def test_with_symbol_and_context(self):
        """Test instantiation with additional parameters."""
        context = {"rule": "required"}
        exc = ValidationError(
            "Invalid value", 
            "field", 
            "value", 
            symbol="TEST", 
            context=context
        )
        assert exc.field == "field"
        assert exc.value == "value"
        assert exc.symbol == "TEST"
        expected_context = {
            'field': 'field',
            'invalid_value': 'value',
            'rule': 'required'
        }
        assert exc.context == expected_context


class TestExceptionStructuredLogging:
    """Tests for structured logging compatibility."""
    
    def test_all_exceptions_have_to_dict(self):
        """Test that all custom exceptions have to_dict method."""
        test_cases = [
            (TradingError("test", symbol="TEST"), {'symbol': 'TEST'}),
            (DataSyncError("sync test"), {}),
            (ScannerError("scan test", "scanner_name"), {'scanner_name': 'scanner_name'}),
            (DatabaseConnectionError("db test", "connect"), {'operation': 'connect'}),
            (BrokerAPIError("api test", "broker", "endpoint"),
             {'broker_name': 'broker', 'endpoint': 'endpoint'}),
            (ValidationError("validation test", "field", "value"),
             {'field': 'field', 'invalid_value': 'value'})
        ]
        
        for exc, expected_keys in test_cases:
            exc_dict = exc.to_dict()
            assert 'error_type' in exc_dict
            assert 'message' in exc_dict
            assert 'timestamp' in exc_dict
            for key in expected_keys:
                assert key in exc_dict['context']
    
    def test_exception_str_representation(self):
        """Test string representation for logging."""
        exc = TradingError("Test error message")
        assert str(exc) == "Test error message"
        
        exc = ScannerError("Scan failed", "test_scanner")
        assert str(exc) == "Scan failed"


if __name__ == "__main__":
    pytest.main([__file__])