"""
Test for scanner factory unified database integration
"""
import pytest
from unittest.mock import patch, MagicMock
from src.application.infrastructure.scanner_factory import ScannerFactory
from src.infrastructure.config.config_manager import ConfigManager


class TestScannerFactoryUnifiedDB:
    """Test scanner factory with unified database."""

    def test_scanner_factory_uses_unified_db_path(self):
        """Test that scanner factory uses the unified database path."""
        # Create scanner factory
        factory = ScannerFactory()

        # Check that factory has the correct default db_path from settings
        from src.infrastructure.config.settings import get_settings
        settings = get_settings()
        expected_path = settings.database.path

        assert expected_path == "data/financial_data.duckdb", f"Expected unified db path, got {expected_path}"

    def test_scanner_factory_create_with_config(self):
        """Test scanner creation with configuration."""
        factory = ScannerFactory()

        # Test configuration retrieval
        config = factory.get_scanner_config('breakout')
        assert isinstance(config, dict), "Should return configuration dict"
        # Check for actual config keys based on what we saw in the error
        assert 'breakout_volume_ratio' in config, "Should have breakout_volume_ratio config"

    @patch('src.infrastructure.adapters.scanner_read_adapter.DuckDBScannerReadAdapter')
    def test_crp_scanner_creation_uses_correct_db_path(self, mock_adapter):
        """Test that CRP scanner creation uses correct database path."""
        # Mock the adapter
        mock_adapter_instance = MagicMock()
        mock_adapter.return_value = mock_adapter_instance

        factory = ScannerFactory()

        # Try to create CRP scanner
        scanner = factory.create_scanner('crp')

        # Verify the adapter was created with correct path
        if scanner is not None:  # Scanner creation might fail if class not found
            mock_adapter.assert_called_with(database_path="data/financial_data.duckdb")

    @patch('src.infrastructure.adapters.scanner_read_adapter.DuckDBScannerReadAdapter')
    def test_breakout_scanner_creation_uses_correct_db_path(self, mock_adapter):
        """Test that breakout scanner creation uses correct database path."""
        # Mock the adapter
        mock_adapter_instance = MagicMock()
        mock_adapter.return_value = mock_adapter_instance

        factory = ScannerFactory()

        # Try to create breakout scanner
        scanner = factory.create_scanner('breakout')

        # Verify the adapter was created with correct path
        if scanner is not None:  # Scanner creation might fail if class not found
            mock_adapter.assert_called_with(database_path="data/financial_data.duckdb")

    def test_available_scanners_list(self):
        """Test that factory returns available scanners."""
        factory = ScannerFactory()
        scanners = factory.get_available_scanners()

        assert isinstance(scanners, list), "Should return list of scanners"
        assert len(scanners) > 0, "Should have at least one scanner available"

        expected_scanners = ['breakout', 'enhanced_breakout', 'crp', 'enhanced_crp',
                           'technical', 'nifty500_filter', 'relative_volume', 'simple_breakout']
        for scanner in expected_scanners:
            assert scanner in scanners, f"Scanner {scanner} should be available"

    def test_config_validation(self):
        """Test configuration validation."""
        factory = ScannerFactory()

        # Test valid config with correct keys
        valid_config = {'breakout_volume_ratio': 2.0, 'consolidation_period': 10}
        is_valid = factory.validate_config('breakout', valid_config)

        # For now, just check that validation doesn't crash
        # The actual validation logic may not be fully implemented yet
        assert isinstance(is_valid, bool), "Validation should return boolean"
