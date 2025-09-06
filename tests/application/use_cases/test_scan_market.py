"""
Test Suite for ScanMarketUseCase
=================================

Comprehensive tests for the ScanMarketUseCase application use case.
"""

import pytest
from datetime import date, time, datetime
from unittest.mock import Mock, AsyncMock, MagicMock
import pandas as pd

from src.application.use_cases.scan_market import (
    ScanMarketUseCase,
    ScanRequest,
    ScanResult
)
from src.domain.repositories.market_data_repo import MarketDataRepository
from src.domain.services.data_sync_service import DataSyncService
from src.infrastructure.messaging.event_bus import EventBus


class TestScanMarketUseCase:
    """Test cases for ScanMarketUseCase."""

    @pytest.fixture
    def mock_market_data_repo(self):
        """Create mock market data repository."""
        return Mock(spec=MarketDataRepository)

    @pytest.fixture
    def mock_data_sync_service(self):
        """Create mock data sync service."""
        return Mock(spec=DataSyncService)

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return Mock(spec=EventBus)

    @pytest.fixture
    def scan_market_use_case(self, mock_market_data_repo, mock_data_sync_service, mock_event_bus):
        """Create ScanMarketUseCase instance with mocks."""
        return ScanMarketUseCase(
            market_data_repo=mock_market_data_repo,
            data_sync_service=mock_data_sync_service,
            event_bus=mock_event_bus
        )

    @pytest.fixture
    def sample_scan_request(self):
        """Create sample scan request."""
        return ScanRequest(
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            scanner_types=['relative_volume', 'technical'],
            config_overrides={
                'relative_volume': {'min_volume_ratio': 1.5}
            }
        )

    @pytest.fixture
    def mock_scanner_class(self):
        """Create mock scanner class."""
        mock_scanner = Mock()
        mock_scanner.scan.return_value = pd.DataFrame({
            'symbol': ['AAPL', 'GOOGL'],
            'relative_volume': [2.1, 1.8],
            'price_change_pct': [1.5, -0.8]
        })
        return Mock(return_value=mock_scanner)

    def test_use_case_initialization(self, scan_market_use_case):
        """Test that ScanMarketUseCase initializes correctly."""
        assert scan_market_use_case.market_data_repo is not None
        assert scan_market_use_case.data_sync_service is not None
        assert scan_market_use_case.event_bus is not None
        assert scan_market_use_case.scanner_strategies == {}

    def test_register_scanner_strategy(self, scan_market_use_case, mock_scanner_class):
        """Test registering a scanner strategy."""
        scan_market_use_case.register_scanner_strategy('test_scanner', mock_scanner_class)

        assert 'test_scanner' in scan_market_use_case.scanner_strategies
        assert scan_market_use_case.scanner_strategies['test_scanner'] == mock_scanner_class

    def test_execute_with_valid_request(self, scan_market_use_case, sample_scan_request, mock_scanner_class):
        """Test executing scan with valid request."""
        # Register mock scanner
        scan_market_use_case.register_scanner_strategy('relative_volume', mock_scanner_class)
        scan_market_use_case.register_scanner_strategy('technical', mock_scanner_class)

        # Mock event bus publish
        scan_market_use_case.event_bus.publish = Mock()

        # Execute use case
        result = scan_market_use_case.execute(sample_scan_request)

        # Verify result structure
        assert isinstance(result, ScanResult)
        assert result.scan_timestamp is not None
        assert result.execution_time_seconds >= 0
        assert 'relative_volume' in result.scanner_results
        assert 'technical' in result.scanner_results

        # Verify event was published
        scan_market_use_case.event_bus.publish.assert_called_once()

    def test_execute_with_empty_scanner_types(self, scan_market_use_case):
        """Test executing scan with empty scanner types raises error."""
        request = ScanRequest(
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            scanner_types=[]
        )

        with pytest.raises(ValueError, match="At least one scanner type must be specified"):
            scan_market_use_case.execute(request)

    def test_execute_with_future_scan_date(self, scan_market_use_case):
        """Test executing scan with future date raises error."""
        future_date = date.today().replace(day=date.today().day + 1)
        request = ScanRequest(
            scan_date=future_date,
            cutoff_time=time(9, 50),
            scanner_types=['relative_volume']
        )

        with pytest.raises(ValueError, match="Scan date cannot be in the future"):
            scan_market_use_case.execute(request)

    def test_execute_with_unavailable_scanner(self, scan_market_use_case, sample_scan_request):
        """Test executing scan with unavailable scanner."""
        # Don't register any scanners but request them
        result = scan_market_use_case.execute(sample_scan_request)

        # Should still return result but with empty dataframes
        assert isinstance(result, ScanResult)
        assert len(result.scanner_results) == 2  # Both scanners should be present
        assert result.scanner_results['relative_volume'].empty
        assert result.scanner_results['technical'].empty

    def test_get_available_scanners(self, scan_market_use_case, mock_scanner_class):
        """Test getting available scanners."""
        # Initially empty
        assert scan_market_use_case.get_available_scanners() == []

        # Register scanner
        scan_market_use_case.register_scanner_strategy('test_scanner', mock_scanner_class)

        # Should return registered scanner
        assert scan_market_use_case.get_available_scanners() == ['test_scanner']

    def test_get_scanner_config_schema_with_valid_scanner(self, scan_market_use_case, mock_scanner_class):
        """Test getting config schema for valid scanner."""
        # Mock scanner class with get_config_schema method
        mock_scanner_class.get_config_schema = Mock(return_value={'min_volume': 1.0})

        scan_market_use_case.register_scanner_strategy('test_scanner', mock_scanner_class)

        schema = scan_market_use_case.get_scanner_config_schema('test_scanner')
        assert schema == {'min_volume': 1.0}

    def test_get_scanner_config_schema_with_invalid_scanner(self, scan_market_use_case):
        """Test getting config schema for invalid scanner."""
        schema = scan_market_use_case.get_scanner_config_schema('nonexistent')
        assert schema is None

    def test_get_scanner_config_schema_without_method(self, scan_market_use_case, mock_scanner_class):
        """Test getting config schema when scanner doesn't have the method."""
        scan_market_use_case.register_scanner_strategy('test_scanner', mock_scanner_class)

        schema = scan_market_use_case.get_scanner_config_schema('test_scanner')
        assert schema is None

    def test_event_publishing_on_scan_completion(self, scan_market_use_case, sample_scan_request, mock_scanner_class):
        """Test that events are published on scan completion."""
        # Register mock scanner
        scan_market_use_case.register_scanner_strategy('relative_volume', mock_scanner_class)

        # Mock event bus
        mock_publish = Mock()
        scan_market_use_case.event_bus.publish = mock_publish

        # Execute
        result = scan_market_use_case.execute(sample_scan_request)

        # Verify event was published
        assert mock_publish.called
        call_args = mock_publish.call_args[0][0]

        assert call_args['event_type'] == 'scan_completed'
        assert 'data' in call_args
        assert call_args['data']['total_stocks_found'] == 4  # 2 symbols * 2 scanners
        assert call_args['data']['successful_scanners'] == 2

    def test_error_handling_in_scanner_execution(self, scan_market_use_case, sample_scan_request, mock_scanner_class):
        """Test error handling when scanner execution fails."""
        # Create scanner that raises exception
        failing_scanner = Mock()
        failing_scanner.scan.side_effect = Exception("Scanner failed")

        scan_market_use_case.register_scanner_strategy('failing_scanner', Mock(return_value=failing_scanner))

        request = ScanRequest(
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            scanner_types=['failing_scanner']
        )

        result = scan_market_use_case.execute(request)

        # Should handle error gracefully
        assert isinstance(result, ScanResult)
        assert result.scanner_results['failing_scanner'].empty
        assert result.total_stocks_found == 0
        assert result.successful_scanners == 0
        assert result.failed_checks == 1

    def test_execution_time_tracking(self, scan_market_use_case, sample_scan_request, mock_scanner_class):
        """Test that execution time is properly tracked."""
        scan_market_use_case.register_scanner_strategy('relative_volume', mock_scanner_class)

        result = scan_market_use_case.execute(sample_scan_request)

        assert result.execution_time_seconds >= 0
        assert isinstance(result.execution_time_seconds, float)

    def test_result_aggregation(self, scan_market_use_case, sample_scan_request, mock_scanner_class):
        """Test that results are properly aggregated."""
        # Register two scanners
        scan_market_use_case.register_scanner_strategy('scanner1', mock_scanner_class)
        scan_market_use_case.register_scanner_strategy('scanner2', mock_scanner_class)

        request = ScanRequest(
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            scanner_types=['scanner1', 'scanner2']
        )

        result = scan_market_use_case.execute(request)

        # Should aggregate results from both scanners
        assert result.total_stocks_found == 4  # 2 symbols * 2 scanners
        assert result.successful_scanners == 2
        assert len(result.scanner_results) == 2
