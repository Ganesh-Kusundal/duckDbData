"""
Unit tests for retry utilities and decorators.
Tests ConfigManager integration, tenacity configuration, and retry behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tenacity

from src.domain.exceptions import DatabaseConnectionError, BrokerAPIError
from src.infrastructure.config.config_manager import ConfigManager
from src.infrastructure.utils.retry import (
    get_retry_config,
    retry_on_transient_errors,
    retry_db_operation,
    retry_api_call
)


class TestGetRetryConfig:
    """Tests for get_retry_config function."""
    
    def test_default_configuration_without_config_manager(self):
        """Test default config when no ConfigManager provided."""
        config = get_retry_config(None)
        assert config == {
            "max_retries": 3,
            "initial_backoff": 1.0,
            "max_backoff": 10.0,
            "backoff_multiplier": 2.0,
            "retry_on_exceptions": [DatabaseConnectionError, BrokerAPIError]
        }
    
    def test_with_config_manager_defaults(self, mock_config_manager):
        """Test with ConfigManager returning empty config."""
        config = get_retry_config(mock_config_manager)
        assert config["max_retries"] == 3
        assert config["initial_backoff"] == 1.0
    
    def test_with_custom_retry_config(self, mock_config_manager):
        """Test with custom retry configuration from ConfigManager."""
        mock_config_manager.get_config.return_value = {
            "max_retries": 5,
            "initial_backoff": 0.5,
            "max_backoff": 5.0,
            "backoff_multiplier": 1.5
        }
        
        config = get_retry_config(mock_config_manager)
        assert config["max_retries"] == 5
        assert config["initial_backoff"] == 0.5
        assert config["max_backoff"] == 5.0
        assert config["backoff_multiplier"] == 1.5
    
    def test_with_scanners_retry_config(self, mock_config_manager):
        """Test with scanners-specific retry configuration."""
        mock_config_manager.get_value.return_value = {
            "max_retries": 4,
            "initial_backoff": 2.0
        }
        mock_config_manager.get_config.side_effect = lambda x: {"retry": {"max_retries": 4, "initial_backoff": 2.0}} if x == "scanners" else {}
        
        config = get_retry_config(mock_config_manager, "retry")
        assert config["max_retries"] == 4
        assert config["initial_backoff"] == 2.0
    
    def test_with_exception_classes_from_config(self, mock_config_manager):
        """Test loading exception classes from config."""
        mock_config_manager.get_config.return_value = {
            "retry_exceptions": ["DatabaseConnectionError", "BrokerAPIError"]
        }
        
        config = get_retry_config(mock_config_manager)
        assert DatabaseConnectionError in config["retry_on_exceptions"]
        assert BrokerAPIError in config["retry_on_exceptions"]
    
    def test_fallback_on_config_error(self, mock_config_manager):
        """Test fallback to defaults when config loading fails."""
        mock_config_manager.get_config.side_effect = Exception("Config error")
        
        config = get_retry_config(mock_config_manager)
        assert config["max_retries"] == 3
        assert len(config["retry_on_exceptions"]) == 2


class TestRetryOnTransientErrorsDecorator:
    """Tests for retry_on_transient_errors decorator."""
    
    def test_decorator_application(self):
        """Test that decorator can be applied to a function."""
        @retry_on_transient_errors()
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    def test_retry_configuration_with_overrides(self):
        """Test retry configuration with decorator parameter overrides."""
        config_manager = Mock()
        config_manager.get_config.return_value = {"max_retries": 2}
        
        @retry_on_transient_errors(config_manager=config_manager, max_retries=1)
        def test_function():
            return "success"
        
        # Verify the override works (this is harder to test directly, but decorator should apply)
        result = test_function()
        assert result == "success"
    
    def test_retry_on_configurable_exceptions(self):
        """Test retry with custom exception list."""
        call_count = [0]
        
        def failing_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Test failure")
            return "success"
        
        decorated_function = retry_on_transient_errors(
            retry_exceptions=[ValueError]
        )(failing_function)
        
        result = decorated_function()
        assert result == "success"
        assert call_count[0] == 2  # Should retry once
    
    def test_no_retry_on_non_configured_exception(self):
        """Test that non-configured exceptions are not retried."""
        call_count = [0]
        
        def failing_function():
            call_count[0] += 1
            raise TypeError("Non-retryable error")
        
        decorated_function = retry_on_transient_errors(
            retry_exceptions=[ValueError]
        )(failing_function)
        
        with pytest.raises(TypeError):
            decorated_function()
        
        assert call_count[0] == 1  # Should not retry


class TestRetryDBOperationDecorator:
    """Tests for retry_db_operation decorator."""
    
    def test_decorator_config_from_config_manager(self, mock_config_manager):
        """Test DB operation retry config loading."""
        mock_config_manager.get_config.return_value = {
            "max_retries": 4,
            "initial_backoff": 0.5
        }
        
        @retry_db_operation(mock_config_manager)
        def test_db_function():
            return "db success"
        
        result = test_db_function()
        assert result == "db success"
    
    def test_retry_only_on_database_exceptions(self):
        """Test retry only on DatabaseConnectionError."""
        call_count = [0]
        
        def failing_db_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise DatabaseConnectionError("DB connection failed", "connect")
            return "db success"
        
        decorated_function = retry_db_operation()(failing_db_function)
        
        result = decorated_function()
        assert result == "db success"
        assert call_count[0] == 2
    
    def test_no_retry_on_non_db_exception(self):
        """Test no retry on non-database exceptions."""
        call_count = [0]
        
        def failing_function():
            call_count[0] += 1
            raise ValueError("Not a DB error")
        
        decorated_function = retry_db_operation()(failing_function)
        
        with pytest.raises(ValueError):
            decorated_function()
        
        assert call_count[0] == 1


class TestRetryAPICallDecorator:
    """Tests for retry_api_call decorator."""
    
    def test_api_retry_config_loading(self, mock_config_manager):
        """Test API retry configuration loading."""
        mock_config_manager.get_config.return_value = {
            "max_retries": 3,
            "initial_backoff": 1.0
        }
        
        @retry_api_call(mock_config_manager)
        def test_api_function():
            return "api success"
        
        result = test_api_function()
        assert result == "api success"
    
    def test_retry_only_on_broker_exceptions(self):
        """Test retry only on BrokerAPIError."""
        call_count = [0]
        
        def failing_api_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise BrokerAPIError("API failed", "test_broker", "endpoint")
            return "api success"
        
        decorated_function = retry_api_call()(failing_api_function)
        
        result = decorated_function()
        assert result == "api success"
        assert call_count[0] == 2
    
    def test_no_retry_on_non_api_exception(self):
        """Test no retry on non-API exceptions."""
        call_count = [0]
        
        def failing_function():
            call_count[0] += 1
            raise ValueError("Not an API error")
        
        decorated_function = retry_api_call()(failing_function)
        
        with pytest.raises(ValueError):
            decorated_function()
        
        assert call_count[0] == 1


class TestRetryIntegration:
    """Integration tests for retry decorators with ConfigManager."""
    
    @patch('src.infrastructure.utils.retry.ConfigManager')
    def test_full_retry_integration(self, MockConfigManager):
        """Test complete retry flow with mocked ConfigManager."""
        mock_config = MockConfigManager()
        mock_config.get_config.return_value = {
            "max_retries": 2,
            "initial_backoff": 0.1,
            "max_backoff": 1.0,
            "backoff_multiplier": 2.0
        }
        
        # Test function that fails once then succeeds
        call_count = [0]
        
        @retry_on_transient_errors(mock_config)
        def integrated_test_function():
            call_count[0] += 1
            if call_count[0] == 1:
                raise DatabaseConnectionError("First attempt failed", "connect")
            return f"Success on attempt {call_count[0]}"
        
        result = integrated_test_function()
        assert "Success on attempt 2" in result
        assert call_count[0] == 2
        # Verify config was called
        mock_config.get_config.assert_called()


class TestRetryEdgeCases:
    """Tests for edge cases in retry logic."""
    
    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        call_count = [0]
        
        def always_failing_function():
            call_count[0] += 1
            raise DatabaseConnectionError("Always fails", "connect")
        
        decorated_function = retry_db_operation(max_retries=2)(always_failing_function)
        
        with pytest.raises(DatabaseConnectionError):
            decorated_function()
        
        assert call_count[0] == 2  # 2 attempts: initial + 1 retry for max_retries=2 (stop_after_attempt(2))
    
    def test_immediate_success(self):
        """Test when function succeeds on first attempt."""
        call_count = [0]
        
        @retry_on_transient_errors()
        def successful_function():
            call_count[0] += 1
            return "immediate success"
        
        result = successful_function()
        assert result == "immediate success"
        assert call_count[0] == 1
    
    def test_retry_with_side_effects(self):
        """Test retry preserves function side effects."""
        side_effect_tracker = []
        
        def function_with_side_effects(arg):
            side_effect_tracker.append(arg)
            if len(side_effect_tracker) == 1:
                raise ValueError("First failure")
            return f"Processed {arg}"
        
        decorated_function = retry_on_transient_errors(retry_exceptions=[ValueError])(function_with_side_effects)
        
        result = decorated_function("test_arg")
        assert result == "Processed test_arg"
        assert side_effect_tracker == ["test_arg", "test_arg"]  # Called twice


# Fixtures for testing
@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager for testing."""
    mock = Mock(spec=ConfigManager)
    mock.get_config.return_value = {}
    mock.get_value.return_value = {}
    return mock


if __name__ == "__main__":
    pytest.main([__file__])