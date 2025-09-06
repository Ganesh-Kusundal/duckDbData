"""
Test Suite for ScannerService
=============================

Comprehensive tests for the ScannerService application service.
"""

import pytest
from datetime import date, time, datetime
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd
import asyncio

from src.application.services.scanner_service import (
    ScannerService,
    ScannerConfig,
    ScannerResult
)
from src.domain.repositories.market_data_repo import MarketDataRepository
from src.domain.services.data_sync_service import DataSyncService
from src.infrastructure.messaging.event_bus import EventBus


class TestScannerService:
    """Test cases for ScannerService."""

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
    def scanner_service(self, mock_market_data_repo, mock_data_sync_service, mock_event_bus):
        """Create ScannerService instance with mocks."""
        return ScannerService(
            market_data_repo=mock_market_data_repo,
            data_sync_service=mock_data_sync_service,
            event_bus=mock_event_bus
        )

    @pytest.fixture
    def sample_scanner_config(self):
        """Create sample scanner configuration."""
        return ScannerConfig(
            scanner_types=['relative_volume'],  # Only use available scanner
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            parallel_execution=True,
            max_concurrent_scanners=3
        )

    @pytest.fixture
    def mock_scanner_class(self):
        """Create mock scanner class."""
        mock_scanner = Mock()
        mock_scanner.scan.return_value = pd.DataFrame({
            'symbol': ['AAPL', 'GOOGL'],
            'relative_volume': [2.1, 1.8]
        })
        return Mock(return_value=mock_scanner)

    def test_service_initialization(self, scanner_service):
        """Test that ScannerService initializes correctly."""
        assert scanner_service.market_data_repo is not None
        assert scanner_service.data_sync_service is not None
        assert scanner_service.event_bus is not None
        assert scanner_service.scanner_strategies == {}

    def test_register_scanner_strategy(self, scanner_service, mock_scanner_class):
        """Test registering a scanner strategy."""
        scanner_service.register_scanner_strategy('test_scanner', mock_scanner_class)

        assert 'test_scanner' in scanner_service.scanner_strategies
        assert scanner_service.scanner_strategies['test_scanner'] == mock_scanner_class

    @pytest.mark.asyncio
    async def test_execute_scanner_workflow_parallel(self, scanner_service, sample_scanner_config, mock_scanner_class):
        """Test executing scanner workflow in parallel mode."""
        # Register mock scanners
        scanner_service.register_scanner_strategy('relative_volume', mock_scanner_class)
        scanner_service.register_scanner_strategy('technical', mock_scanner_class)

        # Mock event publishing
        scanner_service.event_bus.publish = AsyncMock()

        # Execute workflow
        result = await scanner_service.execute_scanner_workflow(sample_scanner_config)

        # Verify result
        assert isinstance(result, ScannerResult)
        assert result.execution_stats['scanners_executed'] == 2
        assert result.scanner_results['summary']['total_scanners'] == 2
        assert result.scanner_results['summary']['successful_scanners'] == 2

    @pytest.mark.asyncio
    async def test_execute_scanner_workflow_sequential(self, scanner_service, mock_scanner_class):
        """Test executing scanner workflow in sequential mode."""
        config = ScannerConfig(
            scanner_types=['relative_volume'],
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            parallel_execution=False
        )

        scanner_service.register_scanner_strategy('relative_volume', mock_scanner_class)

        result = await scanner_service.execute_scanner_workflow(config)

        assert isinstance(result, ScannerResult)
        assert result.execution_stats['scanners_executed'] == 1

    def test_execute_daily_scan(self, scanner_service, mock_scanner_class):
        """Test executing daily scanner workflow."""
        scanner_service.register_scanner_strategy('relative_volume', mock_scanner_class)
        scanner_service.register_scanner_strategy('technical', mock_scanner_class)

        with patch.object(scanner_service, 'execute_scanner_workflow', new_callable=AsyncMock) as mock_workflow:
            mock_workflow.return_value = ScannerResult(
                scanner_results={},
                execution_stats={},
                timestamp=datetime.now(),
                duration_seconds=1.0
            )

            result = scanner_service.execute_daily_scan()

            # Verify workflow was called with correct config
            mock_workflow.assert_called_once()
            call_args = mock_workflow.call_args[0][0]

            assert call_args.scan_date == date.today()
            assert call_args.cutoff_time == time(9, 50)
            assert 'relative_volume' in call_args.scanner_types
            assert 'technical' in call_args.scanner_types
            assert call_args.parallel_execution is True

    def test_execute_custom_scan(self, scanner_service, mock_scanner_class):
        """Test executing custom scanner configuration."""
        scanner_service.register_scanner_strategy('relative_volume', mock_scanner_class)

        with patch.object(scanner_service, 'execute_scanner_workflow', new_callable=AsyncMock) as mock_workflow:
            mock_workflow.return_value = ScannerResult(
                scanner_results={},
                execution_stats={},
                timestamp=datetime.now(),
                duration_seconds=1.0
            )

            result = scanner_service.execute_custom_scan(
                scanner_types=['relative_volume'],
                symbols=['AAPL', 'GOOGL']
            )

            mock_workflow.assert_called_once()
            call_args = mock_workflow.call_args[0][0]

            assert call_args.scanner_types == ['relative_volume']
            assert call_args.symbols == ['AAPL', 'GOOGL']
            assert call_args.parallel_execution is True  # Since only one scanner

    def test_get_scanner_status(self, scanner_service, mock_scanner_class):
        """Test getting scanner service status."""
        # Initially empty
        status = scanner_service.get_scanner_status()
        assert status['total_scanners'] == 0
        assert status['registered_scanners'] == []

        # Register scanner
        scanner_service.register_scanner_strategy('test_scanner', mock_scanner_class)

        status = scanner_service.get_scanner_status()
        assert status['total_scanners'] == 1
        assert status['registered_scanners'] == ['test_scanner']

    def test_get_scanner_performance_metrics(self, scanner_service):
        """Test getting scanner performance metrics."""
        metrics = scanner_service.get_scanner_performance_metrics()

        # Should return default values since no actual metrics are tracked
        assert 'avg_execution_time' in metrics
        assert 'total_scans_executed' in metrics
        assert 'success_rate' in metrics

    @pytest.mark.asyncio
    async def test_workflow_with_config_validation_error(self, scanner_service):
        """Test workflow execution with configuration validation error."""
        # Empty scanner types should raise error
        config = ScannerConfig(
            scanner_types=[],
            scan_date=date.today(),
            cutoff_time=time(9, 50)
        )

        with pytest.raises(ValueError, match="At least one scanner type must be specified"):
            await scanner_service.execute_scanner_workflow(config)

    @pytest.mark.asyncio
    async def test_workflow_with_future_scan_date(self, scanner_service):
        """Test workflow execution with future scan date."""
        future_date = date.today().replace(day=date.today().day + 1)
        config = ScannerConfig(
            scanner_types=['relative_volume'],
            scan_date=future_date,
            cutoff_time=time(9, 50)
        )

        with pytest.raises(ValueError, match="Scan date cannot be in the future"):
            await scanner_service.execute_scanner_workflow(config)

    @pytest.mark.asyncio
    async def test_workflow_with_unavailable_scanner(self, scanner_service):
        """Test workflow execution with unavailable scanner."""
        config = ScannerConfig(
            scanner_types=['nonexistent_scanner'],
            scan_date=date.today(),
            cutoff_time=time(9, 50)
        )

        with pytest.raises(ValueError, match="Requested scanners not available"):
            await scanner_service.execute_scanner_workflow(config)

    @pytest.mark.asyncio
    async def test_parallel_execution_with_semaphore(self, scanner_service, mock_scanner_class):
        """Test parallel execution respects semaphore limits."""
        # Register multiple scanners
        for i in range(5):
            scanner_service.register_scanner_strategy(f'scanner_{i}', mock_scanner_class)

        config = ScannerConfig(
            scanner_types=[f'scanner_{i}' for i in range(5)],
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            parallel_execution=True,
            max_concurrent_scanners=2  # Limit concurrency
        )

        result = await scanner_service.execute_scanner_workflow(config)

        assert result.execution_stats['scanners_executed'] == 5
        assert result.scanner_results['summary']['total_scanners'] == 5

    @pytest.mark.asyncio
    async def test_error_handling_in_parallel_execution(self, scanner_service, mock_scanner_class):
        """Test error handling in parallel execution."""
        # Create a failing scanner
        failing_scanner = Mock()
        failing_scanner.scan.side_effect = Exception("Scanner failed")

        scanner_service.register_scanner_strategy('good_scanner', mock_scanner_class)
        scanner_service.register_scanner_strategy('bad_scanner', Mock(return_value=failing_scanner))

        config = ScannerConfig(
            scanner_types=['good_scanner', 'bad_scanner'],
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            parallel_execution=True
        )

        result = await scanner_service.execute_scanner_workflow(config)

        # Should handle errors gracefully
        assert result.scanner_results['summary']['total_scanners'] == 2
        assert result.scanner_results['summary']['successful_scanners'] == 1
        assert result.scanner_results['summary']['failed_scanners'] == 1

    def test_scanner_preparation_with_config_overrides(self, scanner_service, mock_scanner_class):
        """Test scanner preparation with configuration overrides."""
        scanner_service.register_scanner_strategy('test_scanner', mock_scanner_class)

        config = ScannerConfig(
            scanner_types=['test_scanner'],
            scan_date=date.today(),
            cutoff_time=time(9, 50),
            config_overrides={'test_scanner': {'custom_param': 'value'}}
        )

        # This would normally be called internally during workflow execution
        scanners = scanner_service._prepare_scanners(config)

        assert 'test_scanner' in scanners
        # Verify config override was applied
        scanners['test_scanner'].config.update.assert_called_with({'custom_param': 'value'})

    def test_result_aggregation(self, scanner_service):
        """Test result aggregation functionality."""
        # Mock scanner results
        results = {
            'scanner1': {'success': True, 'records_found': 10, 'execution_time': 1.0},
            'scanner2': {'success': True, 'records_found': 15, 'execution_time': 1.2},
            'scanner3': {'success': False, 'records_found': 0, 'execution_time': 0.5}
        }

        aggregated = scanner_service._aggregate_results(results)

        assert aggregated['summary']['total_scanners'] == 3
        assert aggregated['summary']['successful_scanners'] == 2
        assert aggregated['summary']['failed_scanners'] == 1
        assert aggregated['summary']['total_records'] == 25

    def test_execution_stats_calculation(self, scanner_service):
        """Test execution statistics calculation."""
        start_time = datetime.now()
        results = {
            'scanner1': {'execution_time': 1.0},
            'scanner2': {'execution_time': 1.5}
        }

        stats = scanner_service._calculate_execution_stats(results, start_time)

        assert stats['scanners_executed'] == 2
        assert stats['avg_scanner_time'] == 1.25
        assert stats['min_scanner_time'] == 1.0
        assert stats['max_scanner_time'] == 1.5
        assert 'total_execution_time' in stats

    def test_optimize_scanner_config(self, scanner_service):
        """Test scanner configuration optimization."""
        optimization = scanner_service.optimize_scanner_config('test_scanner')

        assert 'batch_size' in optimization
        assert 'parallel_processing' in optimization
        assert 'memory_limit' in optimization

    @pytest.mark.asyncio
    async def test_workflow_event_publishing(self, scanner_service, sample_scanner_config, mock_scanner_class):
        """Test that workflow events are published."""
        scanner_service.register_scanner_strategy('relative_volume', mock_scanner_class)

        # Mock event publishing
        publish_mock = AsyncMock()
        scanner_service.event_bus.publish = publish_mock

        await scanner_service.execute_scanner_workflow(sample_scanner_config)

        # Verify event was published
        assert publish_mock.called
        call_args = publish_mock.call_args[0][0]

        assert call_args['event_type'] == 'scanner_workflow_completed'
        assert 'data' in call_args
        assert 'summary' in call_args['data']
        assert 'execution_stats' in call_args['data']

    def test_workflow_with_empty_results(self, scanner_service):
        """Test workflow execution with no scanner results."""
        config = ScannerConfig(
            scanner_types=['nonexistent'],
            scan_date=date.today(),
            cutoff_time=time(9, 50)
        )

        # This should raise an error during validation
        with pytest.raises(ValueError):
            asyncio.run(scanner_service.execute_scanner_workflow(config))
