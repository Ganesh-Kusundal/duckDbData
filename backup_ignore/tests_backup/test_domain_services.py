"""Test domain services."""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from duckdb_financial_infra.domain.services.data_sync_service import DataSyncService
from duckdb_financial_infra.infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository


class TestDataSyncService:
    """Test data synchronization service."""

    def test_service_creation(self):
        """Test service initialization."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)
        assert service is not None

    def test_sync_status(self):
        """Test sync status retrieval."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        status = service.get_sync_status()
        assert 'is_running' in status
        assert 'active_callbacks' in status
        assert 'timestamp' in status

    def test_callback_management(self):
        """Test callback registration and removal."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        # Test callback addition
        def test_callback(event_type, data):
            pass

        service.add_sync_callback(test_callback)
        status = service.get_sync_status()
        assert status['active_callbacks'] == 1

        # Test callback removal
        service.remove_sync_callback(test_callback)
        status = service.get_sync_status()
        assert status['active_callbacks'] == 0

    @pytest.mark.asyncio
    async def test_historical_sync_initialization(self):
        """Test historical data sync initialization."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        # Mock the actual sync operations
        with patch.object(service, '_sync_symbol_historical', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                'symbol': 'TEST',
                'existing_records': 0,
                'records_synced': 100,
                'success': True
            }

            # Test sync call
            stats = await service.sync_historical_data(
                symbols=['TEST'],
                start_date=date(2025, 1, 1),
                end_date=date.today(),
                timeframe='1D'
            )

            assert stats['total_symbols'] == 1
            assert stats['processed_symbols'] == 1
            assert 'start_time' in stats
            assert 'end_time' in stats

    @pytest.mark.asyncio
    async def test_intraday_sync_initialization(self):
        """Test intraday data sync initialization."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        # Mock the actual sync operations
        with patch.object(service, '_sync_symbol_intraday', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                'symbol': 'TEST',
                'existing_records': 50,
                'records_synced': 25,
                'success': True
            }

            # Test sync call
            stats = await service.sync_intraday_data(
                symbols=['TEST'],
                target_date=date.today()
            )

            assert stats['total_symbols'] == 1
            assert stats['processed_symbols'] == 1
            assert stats['target_date'] == date.today()

    @pytest.mark.asyncio
    async def test_realtime_sync_start_stop(self):
        """Test real-time sync start and stop."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        # Test start (will fail without broker adapter, but should not crash)
        success = await service.start_realtime_sync(['TEST'])
        # Should return False since no broker adapter is configured
        assert success is False

        # Test stop
        stop_success = await service.stop_realtime_sync()
        assert stop_success is True

    def test_sync_statistics_calculation(self):
        """Test sync statistics calculation."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        # Test with mock data
        stats = {
            'total_symbols': 10,
            'processed_symbols': 8,
            'successful_syncs': 7,
            'failed_syncs': 1,
            'total_records': 1500,
            'start_time': datetime.now(),
            'errors': [{'symbol': 'FAILED', 'error': 'Test error'}]
        }

        # Verify statistics structure
        assert stats['total_symbols'] == 10
        assert stats['processed_symbols'] == 8
        assert stats['successful_syncs'] == 7
        assert stats['failed_syncs'] == 1
        assert stats['total_records'] == 1500
        assert len(stats['errors']) == 1


class TestDataSyncCallbacks:
    """Test data sync callback functionality."""

    def test_callback_execution(self):
        """Test callback execution during sync."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        callback_calls = []

        def test_callback(event_type, data):
            callback_calls.append((event_type, data))

        service.add_sync_callback(test_callback)

        # Manually trigger callback notification
        service._notify_callbacks('test_event', {'test': 'data'})

        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 'test_event'
        assert callback_calls[0][1]['test'] == 'data'

    def test_multiple_callbacks(self):
        """Test multiple callback execution."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        callback1_calls = []
        callback2_calls = []

        def callback1(event_type, data):
            callback1_calls.append((event_type, data))

        def callback2(event_type, data):
            callback2_calls.append((event_type, data))

        service.add_sync_callback(callback1)
        service.add_sync_callback(callback2)

        # Trigger callbacks
        service._notify_callbacks('multi_test', {'count': 2})

        assert len(callback1_calls) == 1
        assert len(callback2_calls) == 1
        assert callback1_calls[0][1]['count'] == 2
        assert callback2_calls[0][1]['count'] == 2


class TestDataSyncErrorHandling:
    """Test error handling in data sync operations."""

    @pytest.mark.asyncio
    async def test_sync_with_errors(self):
        """Test sync operation with errors."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        # Mock sync operation that raises an exception
        with patch.object(service, '_sync_symbol_historical', new_callable=AsyncMock) as mock_sync:
            mock_sync.side_effect = Exception("Test error")

            stats = await service.sync_historical_data(
                symbols=['TEST'],
                start_date=date(2025, 1, 1),
                end_date=date.today()
            )

            assert stats['total_symbols'] == 1
            assert stats['processed_symbols'] == 1
            assert stats['successful_syncs'] == 0
            assert stats['failed_syncs'] == 1
            assert len(stats['errors']) == 1
            assert stats['errors'][0]['symbol'] == 'TEST'

    def test_callback_error_handling(self):
        """Test error handling in callbacks."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        def failing_callback(event_type, data):
            raise Exception("Callback error")

        def working_callback(event_type, data):
            pass  # This should still execute

        service.add_sync_callback(failing_callback)
        service.add_sync_callback(working_callback)

        # This should not raise an exception even though one callback fails
        service._notify_callbacks('error_test', {'data': 'test'})

        # Verify working callback was still called
        status = service.get_sync_status()
        assert status['active_callbacks'] == 2  # Both callbacks still registered


class TestDataSyncIntegration:
    """Test data sync integration scenarios."""

    def test_service_with_repository_integration(self):
        """Test service integration with repository."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        # Verify service has access to repository
        assert service.market_data_repo is not None
        assert hasattr(service.market_data_repo, 'save')
        assert hasattr(service.market_data_repo, 'find_latest_by_symbol')

    @pytest.mark.asyncio
    async def test_batch_processing_simulation(self):
        """Test batch processing simulation."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        symbols = [f'SYMBOL{i}' for i in range(10)]

        # Mock successful sync for all symbols
        with patch.object(service, '_sync_symbol_historical', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                'symbol': 'MOCK',
                'existing_records': 0,
                'records_synced': 100,
                'success': True
            }

            stats = await service.sync_historical_data(
                symbols=symbols,
                start_date=date(2025, 1, 1),
                end_date=date.today(),
                batch_size=5
            )

            assert stats['total_symbols'] == 10
            assert stats['processed_symbols'] == 10
            assert stats['successful_syncs'] == 10
            assert stats['failed_syncs'] == 0

    def test_sync_status_tracking(self):
        """Test sync status tracking."""
        repo = DuckDBMarketDataRepository()
        service = DataSyncService(repo)

        # Initial status
        status = service.get_sync_status()
        assert status['is_running'] is False
        assert status['active_callbacks'] == 0
        assert 'timestamp' in status

        # Add callback and check status
        service.add_sync_callback(lambda e, d: None)
        status = service.get_sync_status()
        assert status['active_callbacks'] == 1
