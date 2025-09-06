"""Test-Driven Development tests for Data Sync Service in Domain Layer."""

import pytest
import asyncio
from datetime import datetime, date, time
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# Mock the complex dependencies to avoid import issues
import sys
from unittest.mock import MagicMock

# Mock modules that have complex dependencies
sys.modules['structlog'] = MagicMock()
sys.modules['pythonjsonlogger'] = MagicMock()
sys.modules['opentelemetry'] = MagicMock()
sys.modules['prometheus_client'] = MagicMock()

# Now import the actual modules
try:
    from src.domain.services.data_sync_service import DataSyncService
    from src.domain.entities.market_data import MarketData, OHLCV
    from src.domain.repositories.market_data_repo import MarketDataRepository
except ImportError as e:
    print(f"Import error: {e}")
    # Create mock classes for testing
    class MockDataSyncService:
        def __init__(self, repo): pass
        def sync_historical_data(self, *args, **kwargs): return {"success": True}
        def sync_intraday_data(self, *args, **kwargs): return {"success": True}
        def start_realtime_sync(self, *args, **kwargs): return True
        def stop_realtime_sync(self, *args, **kwargs): return True
        def get_sync_status(self): return {"is_running": False}

    class MockMarketDataRepository:
        pass

    DataSyncService = MockDataSyncService
    MarketDataRepository = MockMarketDataRepository
    MarketData = Mock
    OHLCV = Mock


class TestDataSyncService:
    """Test cases for DataSyncService domain service."""

    @pytest.fixture
    def mock_market_data_repo(self):
        """Create a mock market data repository."""
        repo = Mock(spec=MarketDataRepository)
        repo.find_by_symbol_and_date_range = Mock(return_value=[])
        return repo

    @pytest.fixture
    def data_sync_service(self, mock_market_data_repo):
        """Create a DataSyncService instance for testing."""
        return DataSyncService(mock_market_data_repo)

    @pytest.fixture
    def sample_symbols(self):
        """Create sample symbols for testing."""
        return ["AAPL", "GOOGL", "MSFT", "TSLA"]

    @pytest.fixture
    def sample_date_range(self):
        """Create sample date range for testing."""
        return date(2025, 1, 1), date(2025, 1, 31)

    def test_data_sync_service_initialization(self, mock_market_data_repo):
        """Test DataSyncService initialization."""
        service = DataSyncService(mock_market_data_repo)

        assert service.market_data_repo == mock_market_data_repo
        assert service._sync_callbacks == []
        assert service._is_running is False

    def test_add_sync_callback(self, data_sync_service):
        """Test adding sync callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        data_sync_service.add_sync_callback(callback1)
        data_sync_service.add_sync_callback(callback2)

        assert len(data_sync_service._sync_callbacks) == 2
        assert callback1 in data_sync_service._sync_callbacks
        assert callback2 in data_sync_service._sync_callbacks

    def test_remove_sync_callback(self, data_sync_service):
        """Test removing sync callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        data_sync_service.add_sync_callback(callback1)
        data_sync_service.add_sync_callback(callback2)

        data_sync_service.remove_sync_callback(callback1)

        assert len(data_sync_service._sync_callbacks) == 1
        assert callback1 not in data_sync_service._sync_callbacks
        assert callback2 in data_sync_service._sync_callbacks

    def test_remove_nonexistent_callback(self, data_sync_service):
        """Test removing a callback that doesn't exist."""
        callback1 = Mock()
        callback2 = Mock()

        data_sync_service.add_sync_callback(callback1)
        data_sync_service.remove_sync_callback(callback2)  # Should not raise error

        assert len(data_sync_service._sync_callbacks) == 1
        assert callback1 in data_sync_service._sync_callbacks

    @pytest.mark.asyncio
    async def test_sync_historical_data_success(self, data_sync_service, mock_market_data_repo, sample_symbols, sample_date_range):
        """Test successful historical data sync."""
        start_date, end_date = sample_date_range

        # Mock the repository to return some existing data
        existing_data = [
            MarketData(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 15, 10, 0, 0),
                timeframe="1D",
                ohlcv=OHLCV(
                    open=Decimal("150.00"),
                    high=Decimal("155.00"),
                    low=Decimal("149.00"),
                    close=Decimal("154.00"),
                    volume=1000000
                ),
                date_partition="2025-01-15"
            )
        ]
        mock_market_data_repo.find_by_symbol_and_date_range.return_value = existing_data

        # Mock the internal sync method
        with patch.object(data_sync_service, '_sync_symbol_historical', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                'symbol': 'AAPL',
                'existing_records': 1,
                'records_synced': 25,
                'success': True
            }

            with patch.object(data_sync_service, '_publish_sync_completed_event', new_callable=AsyncMock):
                result = await data_sync_service.sync_historical_data(
                    symbols=sample_symbols,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe='1D',
                    batch_size=2
                )

        # Verify results
        assert result['total_symbols'] == 4
        assert result['processed_symbols'] == 4
        assert result['successful_syncs'] == 4
        assert result['failed_syncs'] == 0
        assert 'start_time' in result
        assert 'end_time' in result
        assert 'duration_seconds' in result

    @pytest.mark.asyncio
    async def test_sync_historical_data_with_failures(self, data_sync_service, mock_market_data_repo, sample_symbols, sample_date_range):
        """Test historical data sync with some failures."""
        start_date, end_date = sample_date_range

        # Mock repository
        mock_market_data_repo.find_by_symbol_and_date_range.return_value = []

        # Mock sync method to fail for some symbols
        call_count = 0
        async def mock_sync_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:  # Fail every other call
                return {
                    'symbol': f'SYMBOL{call_count}',
                    'success': False,
                    'error': 'Mock failure',
                    'records_synced': 0
                }
            else:
                return {
                    'symbol': f'SYMBOL{call_count}',
                    'success': True,
                    'records_synced': 10
                }

        with patch.object(data_sync_service, '_sync_symbol_historical', side_effect=mock_sync_side_effect):
            with patch.object(data_sync_service, '_publish_sync_completed_event', new_callable=AsyncMock):
                result = await data_sync_service.sync_historical_data(
                    symbols=sample_symbols,
                    start_date=start_date,
                    end_date=end_date
                )

        # Verify results
        assert result['total_symbols'] == 4
        assert result['successful_syncs'] == 2  # Half should succeed
        assert result['failed_syncs'] == 2     # Half should fail
        assert len(result['errors']) == 2

    @pytest.mark.asyncio
    async def test_sync_historical_data_empty_symbols(self, data_sync_service):
        """Test historical data sync with empty symbol list."""
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        with patch.object(data_sync_service, '_publish_sync_completed_event', new_callable=AsyncMock):
            result = await data_sync_service.sync_historical_data(
                symbols=[],
                start_date=start_date,
                end_date=end_date
            )

        assert result['total_symbols'] == 0
        assert result['processed_symbols'] == 0
        assert result['successful_syncs'] == 0
        assert result['failed_syncs'] == 0

    @pytest.mark.asyncio
    async def test_sync_intraday_data_success(self, data_sync_service, mock_market_data_repo, sample_symbols):
        """Test successful intraday data sync."""
        target_date = date(2025, 1, 15)

        # Mock repository
        mock_market_data_repo.find_by_symbol_and_date_range.return_value = []

        # Mock the internal sync method
        with patch.object(data_sync_service, '_sync_symbol_intraday', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = {
                'symbol': 'AAPL',
                'existing_records': 0,
                'records_synced': 375,  # 6.5 hours * 60 minutes = 390, but some missing
                'success': True
            }

            result = await data_sync_service.sync_intraday_data(
                symbols=sample_symbols,
                target_date=target_date,
                batch_size=2
            )

        # Verify results
        assert result['total_symbols'] == 4
        assert result['processed_symbols'] == 4
        assert result['successful_syncs'] == 4
        assert result['failed_syncs'] == 0
        assert result['target_date'] == target_date

    @pytest.mark.asyncio
    async def test_sync_intraday_data_with_errors(self, data_sync_service, mock_market_data_repo, sample_symbols):
        """Test intraday data sync with errors."""
        target_date = date(2025, 1, 15)

        # Mock repository to raise exception
        mock_market_data_repo.find_by_symbol_and_date_range.side_effect = Exception("Database error")

        result = await data_sync_service.sync_intraday_data(
            symbols=sample_symbols[:2],  # Test with just 2 symbols
            target_date=target_date
        )

        # Should handle errors gracefully
        assert result['total_symbols'] == 2
        assert result['processed_symbols'] == 2
        assert result['failed_syncs'] == 2
        assert len(result['errors']) == 2

    @pytest.mark.asyncio
    async def test_start_realtime_sync_success(self, data_sync_service):
        """Test starting real-time sync successfully."""
        symbols = ["AAPL", "GOOGL"]

        with patch('asyncio.create_task') as mock_create_task:
            result = await data_sync_service.start_realtime_sync(symbols)

            assert result is True
            assert data_sync_service._is_running is True
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_realtime_sync_already_running(self, data_sync_service):
        """Test starting real-time sync when already running."""
        data_sync_service._is_running = True

        result = await data_sync_service.start_realtime_sync(["AAPL"])

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_realtime_sync_success(self, data_sync_service):
        """Test stopping real-time sync successfully."""
        data_sync_service._is_running = True
        data_sync_service._sync_callbacks = [Mock(), Mock()]

        result = await data_sync_service.stop_realtime_sync()

        assert result is True
        assert data_sync_service._is_running is False
        assert len(data_sync_service._sync_callbacks) == 0

    @pytest.mark.asyncio
    async def test_stop_realtime_sync_not_running(self, data_sync_service):
        """Test stopping real-time sync when not running."""
        data_sync_service._is_running = False

        result = await data_sync_service.stop_realtime_sync()

        assert result is True

    def test_get_sync_status(self, data_sync_service):
        """Test getting sync status."""
        data_sync_service._is_running = True
        data_sync_service._sync_callbacks = [Mock(), Mock(), Mock()]

        status = data_sync_service.get_sync_status()

        assert status['is_running'] is True
        assert status['active_callbacks'] == 3
        assert 'timestamp' in status

    def test_notify_callbacks_with_error(self, data_sync_service, caplog):
        """Test callback notification with error handling."""
        callback1 = Mock(side_effect=Exception("Callback error"))
        callback2 = Mock()

        data_sync_service.add_sync_callback(callback1)
        data_sync_service.add_sync_callback(callback2)

        with caplog.at_level('ERROR'):
            data_sync_service._notify_callbacks('test_event', {'data': 'test'})

        # Both callbacks should be called
        callback1.assert_called_once_with('test_event', {'data': 'test'})
        callback2.assert_called_once_with('test_event', {'data': 'test'})

        # Error should be logged
        assert "Error in sync callback" in caplog.text

    @pytest.mark.asyncio
    async def test_sync_symbol_historical_with_exception(self, data_sync_service, mock_market_data_repo):
        """Test _sync_symbol_historical with exception."""
        mock_market_data_repo.find_by_symbol_and_date_range.side_effect = Exception("Database error")

        result = await data_sync_service._sync_symbol_historical(
            symbol="AAPL",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            timeframe="1D"
        )

        assert result['symbol'] == "AAPL"
        assert result['success'] is False
        assert "Database error" in result['error']
        assert result['records_synced'] == 0

    @pytest.mark.asyncio
    async def test_sync_symbol_intraday_with_exception(self, data_sync_service, mock_market_data_repo):
        """Test _sync_symbol_intraday with exception."""
        mock_market_data_repo.find_by_symbol_and_date_range.side_effect = Exception("Database error")

        result = await data_sync_service._sync_symbol_intraday(
            symbol="AAPL",
            target_date=date(2025, 1, 15)
        )

        assert result['symbol'] == "AAPL"
        assert result['success'] is False
        assert "Database error" in result['error']
        assert result['records_synced'] == 0

    @pytest.mark.asyncio
    async def test_publish_sync_completed_event_error(self, data_sync_service, caplog):
        """Test error handling in _publish_sync_completed_event."""
        with patch('src.domain.services.data_sync_service.publish_event', side_effect=Exception("Publish error")):
            with caplog.at_level('ERROR'):
                await data_sync_service._publish_sync_completed_event({'test': 'data'})

        assert "Error publishing sync event" in caplog.text

    def test_sync_service_with_callbacks(self, data_sync_service):
        """Test sync service callback functionality."""
        callback = Mock()
        data_sync_service.add_sync_callback(callback)

        # Test callback notification
        data_sync_service._notify_callbacks('symbol_synced', {'symbol': 'AAPL'})

        callback.assert_called_once_with('symbol_synced', {'symbol': 'AAPL'})

    @pytest.mark.asyncio
    async def test_realtime_sync_loop_error_handling(self, data_sync_service, caplog):
        """Test error handling in real-time sync loop."""
        data_sync_service._is_running = True

        # Mock asyncio.sleep to raise exception to exit loop
        with patch('asyncio.sleep', side_effect=Exception("Sleep error")):
            with caplog.at_level('ERROR'):
                await data_sync_service._run_realtime_sync(['AAPL'])

        assert "Real-time sync loop failed" in caplog.text
        assert data_sync_service._is_running is False
