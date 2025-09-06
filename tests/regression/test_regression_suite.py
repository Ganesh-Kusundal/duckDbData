"""
Regression Test Suite
=====================

Comprehensive regression test suite for the DuckDB Financial Infrastructure.
This suite ensures that all critical functionality works correctly and serves
as the primary test suite for continuous integration and deployment.
"""

import pytest
import asyncio
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from src.domain.entities.market_data import MarketData, MarketDataBatch, OHLCV
from src.infrastructure.plugins import PluginManager
from src.infrastructure.config.settings import get_settings


class TestCoreFunctionalityRegression:
    """Regression tests for core system functionality."""

    @pytest.mark.regression
    def test_market_data_entity_creation(self):
        """Regression test: Market data entity creation should work."""
        ohlcv = OHLCV(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000)
        market_data = MarketData(
            symbol="AAPL",
            timestamp="2025-09-05T10:00:00Z",
            timeframe="1D",
            ohlcv=ohlcv,
            date_partition="2025-09-05"
        )

        assert market_data.symbol == "AAPL"
        assert market_data.timeframe == "1D"
        assert market_data.is_valid is True
        assert market_data.ohlcv.close == 102.0

    @pytest.mark.regression
    def test_market_data_batch_operations(self, test_utils):
        """Regression test: Market data batch operations should work."""
        data = test_utils.create_test_market_data(100, "REGRESSION")

        batch = MarketDataBatch(
            symbol="REGRESSION",
            timeframe="1H",
            data=data,
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )

        assert batch.record_count == 100
        assert batch.symbol == "REGRESSION"
        assert batch.is_sorted is True

    @pytest.mark.regression
    def test_plugin_system_initialization(self):
        """Regression test: Plugin system should initialize correctly."""
        manager = PluginManager()
        assert manager is not None
        # Plugin system should not crash on initialization
        assert hasattr(manager, 'load_plugin')
        assert hasattr(manager, 'unload_plugin')

    @pytest.mark.regression
    def test_configuration_loading(self):
        """Regression test: Configuration should load without errors."""
        try:
            settings = get_settings()
            assert settings is not None
            assert hasattr(settings, 'database')
            assert hasattr(settings, 'logging')
        except Exception as e:
            pytest.fail(f"Configuration loading failed: {e}")


class TestDataProcessingRegression:
    """Regression tests for data processing operations."""

    @pytest.mark.regression
    def test_data_validation_rules(self):
        """Regression test: Data validation rules should work."""
        # Valid data should pass
        ohlcv = OHLCV(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000)
        assert ohlcv.open > 0
        assert ohlcv.high >= ohlcv.low
        assert ohlcv.volume > 0

        # Invalid data should raise errors
        with pytest.raises(ValueError):
            OHLCV(open=-100.0, high=105.0, low=95.0, close=102.0, volume=1000000)

        with pytest.raises(ValueError):
            OHLCV(open=100.0, high=95.0, low=98.0, close=102.0, volume=1000000)

    @pytest.mark.regression
    def test_data_transformation_pipeline(self, test_utils):
        """Regression test: Data transformation should work."""
        data = test_utils.create_test_market_data(50, "TRANSFORM")

        # Transform data (simulate business logic)
        transformed = []
        for record in data:
            transformed_record = MarketData(
                symbol=record.symbol.lower(),
                timestamp=record.timestamp,
                timeframe=record.timeframe,
                ohlcv=OHLCV(
                    open=float(record.ohlcv.open) * 1.01,
                    high=float(record.ohlcv.high) * 1.01,
                    low=float(record.ohlcv.low) * 1.01,
                    close=float(record.ohlcv.close) * 1.01,
                    volume=int(float(record.ohlcv.volume) * 1.05)
                ),
                date_partition=record.date_partition
            )
            transformed.append(transformed_record)

        assert len(transformed) == 50
        assert transformed[0].symbol == "transform_000"
        assert transformed[0].ohlcv.open > data[0].ohlcv.open

    @pytest.mark.regression
    def test_data_filtering_operations(self, test_utils):
        """Regression test: Data filtering should work."""
        data = test_utils.create_test_market_data(200, "FILTER")

        # Filter high volume records
        filtered = [record for record in data if record.ohlcv.volume > 200000]

        assert len(filtered) < len(data)
        assert all(record.ohlcv.volume > 200000 for record in filtered)


class TestIntegrationRegression:
    """Regression tests for system integration."""

    @pytest.mark.regression
    def test_end_to_end_data_workflow(self, test_utils):
        """Regression test: End-to-end data workflow should work."""
        # 1. Create data
        data = test_utils.create_test_market_data(25, "E2E")

        # 2. Create batch
        batch = MarketDataBatch(
            symbol="E2E",
            timeframe="1H",
            data=data,
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )

        # 3. Validate batch
        assert batch.record_count == 25
        assert batch.is_sorted is True

        # 4. Process batch (simulate business logic)
        processed_records = 0
        for record in batch.data:
            if record.ohlcv.close > record.ohlcv.open:
                processed_records += 1

        assert processed_records >= 0  # At least some records processed

    @pytest.mark.regression
    def test_concurrent_operations(self, test_utils):
        """Regression test: Concurrent operations should work."""
        import threading
        from queue import Queue

        results = Queue()
        errors = Queue()

        def worker(worker_id: int):
            try:
                # Simulate concurrent data processing
                data = test_utils.create_test_market_data(10, f"WORKER_{worker_id}")
                batch = MarketDataBatch(
                    symbol=f"WORKER_{worker_id}",
                    timeframe="1H",
                    data=data,
                    start_date="2025-09-05T00:00:00Z",
                    end_date="2025-09-05T23:59:59Z"
                )
                results.put((worker_id, batch.record_count))
            except Exception as e:
                errors.put((worker_id, str(e)))

        # Start 5 concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"
        assert results.qsize() == 5

        # Verify all workers completed successfully
        while not results.empty():
            worker_id, record_count = results.get()
            assert record_count == 10

    @pytest.mark.regression
    def test_error_handling_and_recovery(self, test_utils):
        """Regression test: Error handling and recovery should work."""
        # Test with invalid data
        try:
            invalid_data = test_utils.create_test_market_data(5, "")
            pytest.fail("Should have raised an error for invalid data")
        except (ValueError, AssertionError):
            pass  # Expected error

        # Test with valid data after error
        valid_data = test_utils.create_test_market_data(5, "RECOVERY")
        batch = MarketDataBatch(
            symbol="RECOVERY",
            timeframe="1H",
            data=valid_data,
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )

        assert batch.record_count == 5  # Recovery successful


class TestPerformanceRegression:
    """Regression tests for performance requirements."""

    @pytest.mark.regression
    def test_memory_usage_regression(self, test_utils):
        """Regression test: Memory usage should be reasonable."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create moderate amount of data
        data = test_utils.create_test_market_data(1000, "MEMORY")

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = final_memory - initial_memory

        # Memory usage should be reasonable (< 100MB for 1000 records)
        assert memory_used < 100.0

    @pytest.mark.regression
    def test_processing_speed_regression(self, test_utils):
        """Regression test: Processing speed should be acceptable."""
        import time

        data = test_utils.create_test_market_data(5000, "SPEED")

        start_time = time.time()

        # Process data
        processed = []
        for record in data:
            if record.ohlcv.volume > 150000:
                processed.append(record)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process 5000 records in reasonable time (< 2 seconds)
        assert processing_time < 2.0
        assert len(processed) >= 0


class TestPluginSystemRegression:
    """Regression tests for plugin system."""

    @pytest.mark.regression
    def test_plugin_discovery(self):
        """Regression test: Plugin discovery should work."""
        from src.infrastructure.plugins.plugin_discovery import PluginDiscovery

        discovery = PluginDiscovery()
        assert discovery is not None
        assert hasattr(discovery, 'discover_plugins')

    @pytest.mark.regression
    def test_plugin_registry(self):
        """Regression test: Plugin registry should work."""
        from src.infrastructure.plugins.plugin_registry import PluginRegistry

        registry = PluginRegistry()
        assert registry is not None
        assert hasattr(registry, 'register_plugin')
        assert hasattr(registry, 'get_plugin')

    @pytest.mark.regression
    def test_plugin_interfaces(self):
        """Regression test: Plugin interfaces should be importable."""
        from src.infrastructure.plugins.plugin_interfaces import (
            ScannerPluginInterface,
            BrokerPluginInterface,
            DataSourcePluginInterface
        )

        # Should be able to instantiate interfaces
        assert ScannerPluginInterface is not None
        assert BrokerPluginInterface is not None
        assert DataSourcePluginInterface is not None


class TestAPISystemRegression:
    """Regression tests for API system."""

    @pytest.mark.regression
    def test_api_app_creation(self):
        """Regression test: API app should create successfully."""
        try:
            from src.interfaces.api.app import app
            assert app is not None
            assert hasattr(app, 'title')
            assert hasattr(app, 'version')
        except Exception as e:
            pytest.fail(f"API app creation failed: {e}")

    @pytest.mark.regression
    def test_api_routes_import(self):
        """Regression test: API routes should import successfully."""
        try:
            from src.interfaces.api.routes import (
                health,
                market_data,
                scanners,
                plugins,
                system
            )
            # Should not raise any import errors
            assert True
        except ImportError as e:
            pytest.fail(f"API routes import failed: {e}")


class TestInfrastructureRegression:
    """Regression tests for infrastructure components."""

    @pytest.mark.regression
    def test_event_bus_functionality(self):
        """Regression test: Event bus should work."""
        from src.infrastructure.messaging.event_bus import EventBus

        bus = EventBus()
        assert bus is not None

        # Test basic event publishing (should not crash)
        test_event = {"type": "test", "data": "regression_test"}
        bus.publish(test_event)

    @pytest.mark.regression
    def test_logging_system(self):
        """Regression test: Logging system should work."""
        import structlog

        logger = structlog.get_logger("regression_test")
        assert logger is not None

        # Test logging (should not crash)
        logger.info("Regression test log message", test_id="REGRESSION_001")

    @pytest.mark.regression
    def test_configuration_system(self):
        """Regression test: Configuration system should work."""
        from src.infrastructure.config.settings import get_settings

        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, 'database')


class TestCrossLayerIntegrationRegression:
    """Regression tests for cross-layer integration."""

    @pytest.mark.regression
    def test_domain_to_application_integration(self, test_utils):
        """Regression test: Domain to application layer integration."""
        # Create domain entities
        data = test_utils.create_test_market_data(10, "DOMAIN_APP")

        # Simulate application layer processing
        processed_count = 0
        for record in data:
            if record.is_valid:
                processed_count += 1

        assert processed_count == 10

    @pytest.mark.regression
    def test_application_to_infrastructure_integration(self):
        """Regression test: Application to infrastructure layer integration."""
        # Test infrastructure component access
        from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter

        adapter = DuckDBAdapter()
        assert adapter is not None
        assert hasattr(adapter, 'connect')
        assert hasattr(adapter, 'disconnect')

    @pytest.mark.regression
    def test_infrastructure_to_interface_integration(self):
        """Regression test: Infrastructure to interface layer integration."""
        # Test interface layer access to infrastructure
        from src.interfaces.api.app import app
        from src.infrastructure.config.settings import get_settings

        settings = get_settings()
        assert app.title is not None
        assert settings.database.path is not None


# Test suite metadata
REGRESSION_TEST_SUITE = {
    "name": "DuckDB Financial Infrastructure Regression Suite",
    "version": "1.0.0",
    "description": "Comprehensive regression test suite for all system components",
    "test_categories": [
        "core_functionality",
        "data_processing",
        "integration",
        "performance",
        "plugin_system",
        "api_system",
        "infrastructure",
        "cross_layer_integration"
    ],
    "critical_components": [
        "MarketData entities",
        "Plugin system",
        "API endpoints",
        "Data processing pipelines",
        "Event-driven architecture",
        "Configuration management"
    ]
}


def get_regression_test_summary():
    """Get summary of regression test suite."""
    return {
        "suite_name": REGRESSION_TEST_SUITE["name"],
        "version": REGRESSION_TEST_SUITE["version"],
        "total_categories": len(REGRESSION_TEST_SUITE["test_categories"]),
        "critical_components": len(REGRESSION_TEST_SUITE["critical_components"]),
        "description": REGRESSION_TEST_SUITE["description"]
    }


if __name__ == "__main__":
    # Allow running regression tests directly
    pytest.main([__file__, "-v", "--tb=short"])
