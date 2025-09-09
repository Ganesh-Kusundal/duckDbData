"""Tests for performance mode configuration."""

import pytest
from unittest.mock import patch, mock_open
import tempfile
import os
from pathlib import Path

from src.infrastructure.config.settings import (
    PerformanceSettings,
    AppSettings,
    get_settings,
    reload_settings
)


class TestPerformanceSettings:
    """Test cases for PerformanceSettings class."""

    def test_default_values(self):
        """Test default values for PerformanceSettings."""
        settings = PerformanceSettings()
        assert settings.fast_mode is False
        assert settings.connection_pool_enabled is True
        assert settings.connection_pool_size == 10
        assert settings.connection_pool_timeout == 30.0
        assert settings.skip_complex_verification is False
        assert settings.verification_timeout == 5.0
        assert settings.essential_checks_only is False
        assert settings.query_cache_enabled is True
        assert settings.query_cache_ttl == 300
        assert settings.prepared_statements_enabled is True
        assert settings.performance_monitoring is False
        assert settings.metrics_collection is False

    def test_is_fast_mode_property(self):
        """Test is_fast_mode property."""
        settings = PerformanceSettings(fast_mode=True)
        assert settings.is_fast_mode is True
        assert settings.is_development_mode is True

        settings = PerformanceSettings(fast_mode=False)
        assert settings.is_fast_mode is False
        assert settings.is_development_mode is False

    @patch.dict(os.environ, {"PERF_FAST_MODE": "true"})
    def test_environment_variables(self):
        """Test loading settings from environment variables."""
        settings = PerformanceSettings()
        assert settings.fast_mode is True

    @patch.dict(os.environ, {"PERF_CONNECTION_POOL_SIZE": "20"})
    def test_connection_pool_env_var(self):
        """Test connection pool size from environment."""
        settings = PerformanceSettings()
        assert settings.connection_pool_size == 20

    def test_validation_bounds(self):
        """Test validation of configuration bounds."""
        # Test valid values
        settings = PerformanceSettings(
            connection_pool_size=50,
            connection_pool_timeout=10.0,
            verification_timeout=2.0,
            query_cache_ttl=600
        )
        assert settings.connection_pool_size == 50

        # Test invalid values should raise validation errors
        with pytest.raises(ValueError):
            PerformanceSettings(connection_pool_size=0)

        with pytest.raises(ValueError):
            PerformanceSettings(connection_pool_timeout=0.0)


class TestAppSettingsPerformance:
    """Test cases for performance settings in AppSettings."""

    def test_performance_settings_in_app_settings(self):
        """Test that PerformanceSettings is included in AppSettings."""
        settings = AppSettings()
        assert hasattr(settings, 'performance')
        assert isinstance(settings.performance, PerformanceSettings)

    def test_performance_mode_detection(self):
        """Test performance mode detection in AppSettings."""
        # Test default (fast mode disabled)
        settings = AppSettings()
        assert settings.performance.is_fast_mode is False

        # Test with fast mode enabled
        settings = AppSettings(performance=PerformanceSettings(fast_mode=True))
        assert settings.performance.is_fast_mode is True


class TestConfigurationLoading:
    """Test cases for loading performance configuration from YAML."""

    def test_yaml_performance_config_loading(self):
        """Test loading performance settings from YAML config."""
        yaml_content = """
performance:
  fast_mode: true
  connection_pool_size: 15
  verification_timeout: 3.0
  skip_complex_verification: true
"""
        with patch('src.infrastructure.config.settings.yaml_settings_source') as mock_yaml:
            mock_yaml.return_value = {
                'performance': {
                    'fast_mode': True,
                    'connection_pool_size': 15,
                    'verification_timeout': 3.0,
                    'skip_complex_verification': True
                }
            }

            settings = AppSettings()
            assert settings.performance.fast_mode is True
            assert settings.performance.connection_pool_size == 15
            assert settings.performance.verification_timeout == 3.0
            assert settings.performance.skip_complex_verification is True

    def test_partial_yaml_config(self):
        """Test loading partial performance settings from YAML."""
        with patch('src.infrastructure.config.settings.yaml_settings_source') as mock_yaml:
            mock_yaml.return_value = {
                'performance': {
                    'fast_mode': True
                }
            }

            settings = AppSettings()
            # Only fast_mode should be overridden, others should be defaults
            assert settings.performance.fast_mode is True
            assert settings.performance.connection_pool_size == 10  # default
            assert settings.performance.verification_timeout == 5.0  # default


class TestGlobalSettings:
    """Test cases for global settings functions."""

    def test_get_settings_returns_app_settings(self):
        """Test that get_settings returns AppSettings instance."""
        settings = get_settings()
        assert isinstance(settings, AppSettings)
        assert hasattr(settings, 'performance')

    def test_reload_settings(self):
        """Test that reload_settings creates new instance."""
        settings1 = get_settings()
        reloaded_settings = reload_settings()
        # Should be different instances
        assert settings1 is not reloaded_settings
        assert isinstance(reloaded_settings, AppSettings)


class TestPerformanceModeIntegration:
    """Integration tests for performance mode functionality."""

    def test_fast_mode_configuration_workflow(self):
        """Test complete workflow for enabling fast mode."""
        # Create settings with fast mode enabled
        fast_settings = PerformanceSettings(
            fast_mode=True,
            connection_pool_enabled=True,
            skip_complex_verification=True,
            essential_checks_only=True,
            performance_monitoring=True
        )

        # Verify all fast mode optimizations are enabled
        assert fast_settings.is_fast_mode is True
        assert fast_settings.connection_pool_enabled is True
        assert fast_settings.skip_complex_verification is True
        assert fast_settings.essential_checks_only is True
        assert fast_settings.performance_monitoring is True

    def test_standard_mode_configuration_workflow(self):
        """Test complete workflow for standard mode."""
        # Create settings with standard mode (defaults)
        standard_settings = PerformanceSettings()

        # Verify standard mode settings
        assert standard_settings.is_fast_mode is False
        assert standard_settings.connection_pool_enabled is True  # Still enabled
        assert standard_settings.skip_complex_verification is False
        assert standard_settings.essential_checks_only is False
        assert standard_settings.performance_monitoring is False

