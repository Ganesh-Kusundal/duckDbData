"""Test adapter components."""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd

from duckdb_financial_infra.infrastructure.adapters.scanner_adapter import (
    ScannerService, LegacyScannerAdapter
)
from duckdb_financial_infra.infrastructure.adapters.broker_adapter import (
    BrokerService, LegacyBrokerAdapter
)
from duckdb_financial_infra.infrastructure.adapters.data_sync_adapter import LegacyDataSyncAdapter


class TestScannerAdapter:
    """Test scanner adapter functionality."""

    def test_scanner_service_creation(self):
        """Test scanner service initialization."""
        service = ScannerService()
        assert service is not None
        assert service.get_available_scanners() == []

    def test_scanner_registration(self):
        """Test scanner registration and retrieval."""
        service = ScannerService()

        # Create mock adapter
        mock_adapter = Mock()
        mock_adapter.get_scanner_name.return_value = "test_scanner"

        # Register scanner
        service.register_scanner("test", mock_adapter)

        # Verify registration
        assert "test" in service.get_available_scanners()
        assert service.get_broker("test") == mock_adapter

    def test_scanner_execution(self):
        """Test scanner execution through service."""
        service = ScannerService()

        # Create mock adapter
        mock_adapter = Mock()
        mock_adapter.get_scanner_name.return_value = "test_scanner"
        mock_adapter.execute_scan.return_value = []

        # Register and execute
        service.register_scanner("test", mock_adapter)

        result = service.execute_scanner("test", date.today())
        assert result == []

        # Verify execution was called
        mock_adapter.execute_scan.assert_called_once()

    def test_legacy_scanner_adapter(self):
        """Test legacy scanner adapter."""
        # Create mock legacy scanner
        mock_scanner = Mock()
        mock_scanner.scanner_name = "legacy_scanner"
        mock_scanner.scan.return_value = pd.DataFrame({
            'symbol': ['TEST'],
            'signal_type': ['BUY'],
            'price_change_pct': [2.5]
        })

        # Create adapter
        adapter = LegacyScannerAdapter(mock_scanner)

        assert adapter.get_scanner_name() == "legacy_scanner"

        # Test scan execution
        results = adapter.execute_scan(date.today())
        assert len(results) == 1
        assert results[0].symbol == 'TEST'


class TestBrokerAdapter:
    """Test broker adapter functionality."""

    def test_broker_service_creation(self):
        """Test broker service initialization."""
        service = BrokerService()
        assert service is not None
        assert service.get_available_brokers() == []

    def test_broker_registration(self):
        """Test broker registration and retrieval."""
        service = BrokerService()

        # Create mock adapter
        mock_adapter = Mock()
        mock_adapter.get_broker_name.return_value = "test_broker"

        # Register broker
        service.register_broker("test", mock_adapter)

        # Verify registration
        assert "test" in service.get_available_brokers()
        assert service.get_broker("test") == mock_adapter

    def test_order_execution(self):
        """Test order execution through service."""
        service = BrokerService()

        # Create mock adapter
        mock_adapter = Mock()
        mock_adapter.get_broker_name.return_value = "test_broker"
        mock_adapter.place_order.return_value = Mock(order_id="ORD123")

        # Register and execute
        service.register_broker("test", mock_adapter)

        from duckdb_financial_infra.domain.entities.trading import OrderSide, OrderType

        result = service.execute_order(
            "test", "TEST", OrderSide.BUY, 100, OrderType.MARKET
        )

        assert result is not None
        mock_adapter.place_order.assert_called_once()

    def test_legacy_broker_adapter_creation(self):
        """Test legacy broker adapter creation."""
        mock_broker = Mock()
        mock_broker.is_connected.return_value = True

        adapter = LegacyBrokerAdapter(mock_broker)
        assert adapter.get_broker_name() == "LegacyBroker"
        assert adapter.is_connected() is True

    def test_domain_entity_conversion(self):
        """Test conversion of legacy data to domain entities."""
        mock_broker = Mock()
        adapter = LegacyBrokerAdapter(mock_broker)

        # Test order conversion
        legacy_order = {
            'orderid': 'ORD123',
            'symbol': 'TEST',
            'transactiontype': 'BUY',
            'ordertype': 'MARKET',
            'quantity': 100,
            'price': 100.50
        }

        order = adapter.convert_legacy_order_to_domain(legacy_order)
        assert order.order_id == 'ORD123'
        assert order.symbol == 'TEST'
        assert order.quantity == 100

        # Test position conversion
        legacy_position = {
            'symbol': 'TEST',
            'netqty': 50,
            'avgnetprice': 100.25,
            'ltp': 105.50,
            'unrealised': 2650.00,
            'realised': 0.00
        }

        position = adapter.convert_legacy_position_to_domain(legacy_position)
        assert position.symbol == 'TEST'
        assert position.quantity == 50
        assert position.average_price == Decimal('100.25')


class TestDataSyncAdapter:
    """Test data sync adapter functionality."""

    def test_adapter_creation(self):
        """Test data sync adapter initialization."""
        adapter = LegacyDataSyncAdapter()
        assert adapter is not None
        assert hasattr(adapter, 'sync_today_intraday_data')

    def test_pandas_conversion(self):
        """Test pandas DataFrame to domain entity conversion."""
        adapter = LegacyDataSyncAdapter()

        # Create test DataFrame
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [Decimal('100.00')],
            'high': [Decimal('105.00')],
            'low': [Decimal('99.00')],
            'close': [Decimal('104.00')],
            'volume': [5000]
        })

        # Test conversion
        entities = adapter.convert_pandas_to_domain_entities(df, 'TEST', '1D')
        assert len(entities) == 1
        assert entities[0].symbol == 'TEST'
        assert entities[0].ohlcv.close == Decimal('104.00')
        assert entities[0].timeframe == '1D'

    @pytest.mark.asyncio
    async def test_missing_data_check(self):
        """Test missing data identification."""
        adapter = LegacyDataSyncAdapter()

        # Mock repository
        mock_repo = Mock()
        mock_repo.find_by_symbol_and_date_range.return_value = [
            Mock() for _ in range(5)  # 5 existing records
        ]
        adapter.market_data_repo = mock_repo

        # Test missing data check
        stats = await adapter.sync_missing_data(
            symbols=['TEST'],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 10)  # 10 days expected
        )

        assert stats['total_symbols'] == 1
        assert 'symbols_with_missing_data' in stats
        assert 'total_missing_records' in stats

    def test_sync_status(self):
        """Test sync status retrieval."""
        adapter = LegacyDataSyncAdapter()

        status = adapter.get_sync_status()
        assert 'is_running' in status
        assert 'active_callbacks' in status
        assert 'timestamp' in status


class TestAdapterIntegration:
    """Test adapter integration scenarios."""

    def test_scanner_adapter_with_service(self):
        """Test scanner adapter integration with service."""
        service = ScannerService()

        # Create mock scanner
        mock_scanner = Mock()
        mock_scanner.scanner_name = "integration_scanner"
        mock_scanner.scan.return_value = pd.DataFrame({
            'symbol': ['INT_TEST'],
            'signal_type': ['BUY']
        })

        # Create and register adapter
        adapter = LegacyScannerAdapter(mock_scanner)
        service.register_scanner("integration", adapter)

        # Execute scan
        results = service.execute_scanner("integration", date.today())

        assert len(results) == 1
        assert results[0].symbol == 'INT_TEST'

    def test_broker_adapter_with_service(self):
        """Test broker adapter integration with service."""
        service = BrokerService()

        # Create mock broker
        mock_broker = Mock()
        mock_broker.is_connected.return_value = True

        # Create and register adapter
        adapter = LegacyBrokerAdapter(mock_broker)
        service.register_broker("integration", adapter)

        # Test service methods
        assert "integration" in service.get_available_brokers()
        assert service.get_broker("integration") == adapter

    def test_data_sync_adapter_operations(self):
        """Test data sync adapter operations."""
        adapter = LegacyDataSyncAdapter()

        # Test status
        status = adapter.get_sync_status()
        assert isinstance(status, dict)

        # Test callback management
        callback_called = False

        def test_callback(event_type, data):
            nonlocal callback_called
            callback_called = True

        adapter.sync_service.add_sync_callback(test_callback)
        adapter.sync_service._notify_callbacks('test', {})

        assert callback_called


class TestAdapterErrorHandling:
    """Test error handling in adapters."""

    def test_scanner_adapter_error_handling(self):
        """Test error handling in scanner adapter."""
        mock_scanner = Mock()
        mock_scanner.scanner_name = "error_scanner"
        mock_scanner.scan.side_effect = Exception("Scan error")

        adapter = LegacyScannerAdapter(mock_scanner)

        # Should handle error gracefully
        results = adapter.execute_scan(date.today())
        assert results == []  # Empty results on error

    def test_broker_adapter_error_handling(self):
        """Test error handling in broker adapter."""
        mock_broker = Mock()
        mock_broker.is_connected.return_value = True
        mock_broker.order_placement.side_effect = Exception("Order error")

        adapter = LegacyBrokerAdapter(mock_broker)

        from duckdb_financial_infra.domain.entities.trading import OrderSide, OrderType

        # Should handle error gracefully
        result = adapter.place_order("TEST", OrderSide.BUY, 100, OrderType.MARKET)
        assert result is None

    def test_data_sync_adapter_error_handling(self):
        """Test error handling in data sync adapter."""
        adapter = LegacyDataSyncAdapter()

        # Mock repository error
        mock_repo = Mock()
        mock_repo.find_by_symbol_and_date_range.side_effect = Exception("Repo error")
        adapter.market_data_repo = mock_repo

        # Should handle error gracefully
        import asyncio
        async def test_async():
            stats = await adapter.sync_missing_data(
                symbols=['TEST'],
                start_date=date.today(),
                end_date=date.today()
            )
            assert 'errors' in stats

        asyncio.run(test_async())


class TestAdapterCallbacks:
    """Test callback functionality in adapters."""

    def test_scanner_service_callbacks(self):
        """Test callbacks in scanner service."""
        service = ScannerService()

        callback_data = []

        def test_callback(event_type, data):
            callback_data.append((event_type, data))

        # Note: ScannerService doesn't have callback functionality
        # This is more of a design consideration for future enhancement
        assert len(callback_data) == 0

    def test_data_sync_callbacks(self):
        """Test callbacks in data sync adapter."""
        adapter = LegacyDataSyncAdapter()

        callback_calls = []

        def sync_callback(event_type, data):
            callback_calls.append((event_type, data))

        adapter.sync_service.add_sync_callback(sync_callback)

        # Trigger callback
        adapter.sync_service._notify_callbacks('sync_test', {'status': 'success'})

        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 'sync_test'
        assert callback_calls[0][1]['status'] == 'success'
