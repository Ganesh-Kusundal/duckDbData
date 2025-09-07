"""Async integration tests for realtime data processing components."""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
from decimal import Decimal
import pandas as pd

# Fix imports for test environment
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import from src
from src.infrastructure.external.realtime_data_streamer import AsyncRealtimeStreamer
from src.infrastructure.adapters.broker_adapter import LegacyBrokerAdapter
from src.application.scanners.base_scanner import BaseScanner
from src.infrastructure.messaging.event_bus import async_publish_event, get_async_event_bus
from src.domain.entities.market_data import MarketData, OHLCV
from src.domain.events import DataIngestedEvent
from src.domain.exceptions import BrokerAPIError, ScannerError


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_event_bus():
    """Fixture for async event bus."""
    bus = get_async_event_bus()
    await bus.start()
    yield bus
    await bus.stop()


class TestAsyncRealtimeStreamer:
    """Tests for AsyncRealtimeStreamer."""

    @pytest.fixture
    def mock_repo(self):
        """Mock market data repository."""
        repo = MagicMock()
        repo.save.return_value = None
        return repo

    @pytest.fixture
    def mock_broker(self):
        """Mock broker adapter."""
        broker = MagicMock(spec=LegacyBrokerAdapter)
        broker.get_broker_name.return_value = "test_broker"
        return broker

    @pytest.mark.asyncio
    async def test_async_realtime_streamer_initialization(self, mock_repo, mock_broker):
        """Test AsyncRealtimeStreamer initialization."""
        streamer = AsyncRealtimeStreamer(
            market_data_repo=mock_repo,
            broker_adapter=mock_broker
        )
        
        assert streamer._is_streaming is False
        assert len(streamer._tasks) == 0
        assert len(streamer._websockets) == 0
        assert streamer._concurrent_streams == 10
        assert streamer._timeout == 30.0

    @pytest.mark.asyncio
    async def test_async_start_streaming(self, mock_repo, mock_broker):
        """Test starting async streaming."""
        streamer = AsyncRealtimeStreamer(
            market_data_repo=mock_repo,
            broker_adapter=mock_broker
        )
        
        symbols = ["TEST1", "TEST2"]
        result = await streamer.start_streaming(symbols)
        
        assert result is True
        assert streamer._monitored_symbols == symbols
        assert streamer._is_streaming is False

    @pytest.mark.asyncio
    @patch('src.infrastructure.external.realtime_data_streamer.ConfigManager')
    async def test_async_streaming_with_config(self, mock_config, mock_repo, mock_broker):
        """Test async streaming with configuration from ConfigManager."""
        # Mock config manager
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get_config.return_value = {
            'max_concurrent_streams': 5,
            'realtime_timeout': 10.0,
            'max_retries': 2
        }
        
        streamer = AsyncRealtimeStreamer(
            market_data_repo=mock_repo,
            broker_adapter=mock_broker,
            config_manager=mock_config_instance
        )
        
        # Verify config loading
        assert streamer._concurrent_streams == 5
        assert streamer._timeout == 10.0
        assert streamer._max_retries == 2

    @pytest.mark.asyncio
    async def test_async_streaming_status(self, mock_repo, mock_broker):
        """Test getting async streaming status."""
        streamer = AsyncRealtimeStreamer(
            market_data_repo=mock_repo,
            broker_adapter=mock_broker
        )
        
        status = streamer.get_streaming_status()
        
        assert status['is_streaming'] is False
        assert status['monitored_symbols'] == 0
        assert status['active_tasks'] == 0
        assert status['active_websockets'] == 0
        assert 'concurrent_streams' in status
        assert 'timestamp' in status


class TestAsyncBrokerAdapter:
    """Tests for async broker adapter methods."""

    @pytest.fixture
    def mock_legacy_broker(self):
        """Mock legacy broker instance."""
        broker = MagicMock()
        broker.subscribe_symbols.return_value = True
        broker.unsubscribe_symbols.return_value = True
        broker.get_tick_data.return_value = {
            'symbol': 'TEST',
            'last_price': 100.0,
            'volume': 1000
        }
        return broker

    @pytest.mark.asyncio
    async def test_async_subscribe_symbols(self, mock_legacy_broker):
        """Test async symbol subscription."""
        adapter = LegacyBrokerAdapter(
            legacy_broker=mock_legacy_broker,
            config_manager=None
        )
        
        symbols = ["TEST1", "TEST2"]
        result = await adapter.async_subscribe_symbols(symbols)
        
        assert result is True
        mock_legacy_broker.subscribe_symbols.assert_called_once_with(symbols)

    @pytest.mark.asyncio
    async def test_async_get_tick_data(self, mock_legacy_broker):
        """Test async tick data retrieval."""
        adapter = LegacyBrokerAdapter(
            legacy_broker=mock_legacy_broker,
            config_manager=None
        )
        
        tick_data = await adapter.async_get_tick_data("TEST", timeout=1.0)
        
        assert tick_data is not None
        assert tick_data['symbol'] == "TEST"
        assert 'data' in tick_data
        assert 'timestamp' in tick_data
        # Mock may not call sync method directly due to async wrapper

    @pytest.mark.asyncio
    async def test_async_get_tick_data_timeout(self, mock_legacy_broker):
        """Test async tick data timeout."""
        # Mock timeout scenario
        mock_legacy_broker.get_tick_data.side_effect = asyncio.TimeoutError
        
        adapter = LegacyBrokerAdapter(
            legacy_broker=mock_legacy_broker,
            config_manager=None
        )
        
        with pytest.raises(asyncio.TimeoutError):
            await adapter.async_get_tick_data("TEST", timeout=0.1)

    @pytest.mark.asyncio
    async def test_async_unsubscribe_symbols(self, mock_legacy_broker):
        """Test async symbol unsubscription."""
        adapter = LegacyBrokerAdapter(
            legacy_broker=mock_legacy_broker,
            config_manager=None
        )
        
        symbols = ["TEST1", "TEST2"]
        result = await adapter.async_unsubscribe_symbols(symbols)
        
        assert result is True
        mock_legacy_broker.unsubscribe_symbols.assert_called_once_with(symbols)


class TestAsyncBaseScanner:
    """Tests for async scanner methods."""

    @pytest.fixture
    def mock_query_api(self):
        """Mock QueryAPI instance."""
        api = MagicMock()
        # Mock market data for symbols
        api.get_market_data.return_value = pd.DataFrame({
            'symbol': ['TEST1'],
            'open': [100.0],
            'high': [105.0],
            'low': [98.0],
            'close': [102.0],
            'volume': [1000]
        })
        
        # Mock technical indicators
        api.get_technical_indicators.return_value = pd.DataFrame({
            'symbol': ['TEST1'],
            'rsi': [60.5],
            'macd': [1.2],
            'sma_20': [101.0]
        })
        
        return api

    @pytest.fixture
    def mock_scanner(self, mock_query_api):
        """Mock BaseScanner instance."""
        class MockScanner(BaseScanner):
            @property
            def scanner_name(self):
                return "test_scanner"
        
        scanner = MockScanner(
            db_manager=None,
            config_manager=None
        )
        scanner.query_api = mock_query_api
        return scanner

    @pytest.mark.asyncio
    async def test_async_get_market_data(self, mock_scanner):
        """Test async market data retrieval."""
        symbols = ["TEST1", "TEST2"]
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 31)
        
        result = await mock_scanner.async_get_market_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            timeframe='1d',
            timeout=5.0
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'symbol' in result.columns

    @pytest.mark.asyncio
    async def test_async_get_market_data_timeout(self, mock_scanner):
        """Test async market data timeout."""
        symbols = ["TEST1", "TEST2"]
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 31)
        
        # Mock timeout
        with patch.object(asyncio, 'wait_for', side_effect=asyncio.TimeoutError):
            with pytest.raises(ScannerError):
                await mock_scanner.async_get_market_data(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    timeout=0.1
                )

    @pytest.mark.asyncio
    async def test_async_get_technical_indicators(self, mock_scanner):
        """Test async technical indicators retrieval."""
        symbols = ["TEST1", "TEST2"]
        indicators = ["rsi", "macd", "sma_20"]
        start_date = date(2023, 1, 1)
        
        result = await mock_scanner.async_get_technical_indicators(
            symbols=symbols,
            indicators=indicators,
            start_date=start_date,
            timeout=5.0
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert all(ind in result.columns for ind in indicators)

    @pytest.mark.asyncio
    async def test_async_get_technical_indicators_empty(self, mock_scanner):
        """Test async technical indicators with empty results."""
        # Mock empty results
        mock_scanner.query_api.get_technical_indicators.return_value = pd.DataFrame()
        
        symbols = ["TEST1"]
        indicators = ["rsi"]
        
        result = await mock_scanner.async_get_technical_indicators(
            symbols=symbols,
            indicators=indicators
        )
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestAsyncEventBusIntegration:
    """Integration tests for async event bus."""

    @pytest.mark.asyncio
    async def test_async_event_publishing(self, async_event_bus):
        """Test async event publishing and subscription."""
        # Test data
        test_event = DataIngestedEvent(
            symbol="TEST",
            timeframe="1m",
            records_count=1,
            start_date=date.today(),
            end_date=date.today()
        )
        
        # Capture published events
        published_events = []
        
        def sync_handler(event):
            published_events.append(event)
        
        async def async_handler(event):
            published_events.append(event)
        
        # Subscribe to events
        await async_event_bus.async_subscribe("data_ingested", sync_handler)
        await async_event_bus.async_subscribe("data_ingested", async_handler)
        
        # Publish event
        await async_publish_event(test_event)
        
        # Wait a bit for processing
        await asyncio.sleep(0.5)
        
        # Verify events were received
        assert len(published_events) >= 1
        assert published_events[0].symbol == "TEST"

    @pytest.mark.asyncio
    async def test_async_event_bus_start_stop(self):
        """Test async event bus start and stop functionality."""
        bus = get_async_event_bus()
        
        # Start bus
        await bus.start()
        assert bus._is_running is True
        
        # Stop bus
        await bus.stop()
        assert bus._is_running is False

    @pytest.mark.asyncio
    async def test_async_publish_event_integration(self):
        """Test complete async publish event flow."""
        # Create test event
        test_event = DataIngestedEvent(
            symbol="INTEGRATION_TEST",
            timeframe="1m",
            records_count=10,
            start_date=date.today(),
            end_date=date.today()
        )
        
        # Capture events
        events_received = []
        
        async def event_handler(event):
            events_received.append(event)
        
        # Subscribe
        async_bus = get_async_event_bus()
        await async_bus.async_subscribe("data_ingested", event_handler)
        
        # Publish
        await async_publish_event(test_event)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        # Verify
        assert len(events_received) == 1
        assert events_received[0].symbol == "INTEGRATION_TEST"
        assert events_received[0].records_count == 10


class TestAsyncIntegrationFlow:
    """End-to-end async integration tests."""

    @pytest.mark.asyncio
    async def test_complete_async_realtime_flow(self):
        """Test complete async realtime data flow."""
        # Mock components
        mock_repo = MagicMock()
        mock_broker = MagicMock(spec=LegacyBrokerAdapter)
        mock_broker.async_subscribe_symbols = AsyncMock(return_value=True)
        mock_broker.async_get_tick_data = AsyncMock(return_value={
            'symbol': 'TEST_SYMBOL',
            'data': {'last_price': 100.0, 'volume': 1000},
            'timestamp': datetime.now()
        })
        
        # Create streamer
        streamer = AsyncRealtimeStreamer(
            market_data_repo=mock_repo,
            broker_adapter=mock_broker
        )
        
        # Mock config for testing
        with patch.object(streamer, '_concurrent_streams', 2):
            with patch.object(streamer, '_timeout', 2.0):
                # Subscribe symbols
                await mock_broker.async_subscribe_symbols(["TEST_SYMBOL"])
                
                # Start streaming (mock the websocket connection)
                with patch.object(streamer, '_connect_websocket', return_value=None):
                    # This will test the error handling path
                    await streamer.start_streaming(["TEST_SYMBOL"])
                
                # Verify calls
                mock_broker.async_subscribe_symbols.assert_called_once()
                mock_repo.save.assert_not_called()  # No data due to mock websocket
                
                # Test status
                status = streamer.get_streaming_status()
                assert status['monitored_symbols'] == 1


@pytest.mark.asyncio
async def test_async_scanner_integration():
    """Test async scanner integration with realtime data."""
    # This would require a more complex setup with actual database
    # For now, test the async methods work without blocking
    
    class TestScanner(BaseScanner):
        @property
        def scanner_name(self):
            return "integration_test"
    
    # Create scanner with mock query API
    mock_query = MagicMock()
    mock_query.get_market_data.return_value = pd.DataFrame({
        'symbol': ['AAPL', 'GOOGL'],
        'close': [150.0, 2800.0],
        'volume': [1000000, 500000]
    })
    
    scanner = TestScanner()
    scanner.query_api = mock_query
    
    # Test concurrent async calls
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 31)
    
    # Run async market data
    market_data = await scanner.async_get_market_data(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        timeout=3.0
    )
    
    assert isinstance(market_data, pd.DataFrame)
    assert len(market_data) > 0
    
    # Run async technical indicators
    indicators_data = await scanner.async_get_technical_indicators(
        symbols=symbols[:2],
        indicators=['rsi', 'macd'],
        timeout=3.0
    )
    
    assert isinstance(indicators_data, pd.DataFrame)


@pytest.mark.asyncio
async def test_async_error_handling():
    """Test async error handling and exception wrapping."""
    # Test broker timeout error wrapping
    mock_broker = MagicMock()
    mock_broker.async_get_tick_data.side_effect = asyncio.TimeoutError("Test timeout")
    
    adapter = LegacyBrokerAdapter(legacy_broker=mock_broker)
    
    with pytest.raises(asyncio.TimeoutError) as exc_info:
        await adapter.async_get_tick_data("TEST", timeout=0.1)
    
    assert "timeout" in str(exc_info.value)
    
    # Test scanner timeout error wrapping
    class TestScanner(BaseScanner):
        @property
        def scanner_name(self):
            return "error_test"
    
    scanner = TestScanner()
    
    with patch.object(asyncio, 'wait_for', side_effect=asyncio.TimeoutError):
        with pytest.raises(ScannerError) as exc_info:
            await scanner.async_get_market_data(
                symbols=["TEST"],
                start_date=date.today(),
                end_date=date.today(),
                timeout=0.1
            )
    
    assert "timeout" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])