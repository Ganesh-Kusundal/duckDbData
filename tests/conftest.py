"""
Test Configuration and Fixtures
===============================

Pytest configuration and shared fixtures for the DuckDB Financial Infrastructure test suite.
"""

import pytest
import asyncio
from typing import Dict, List, Any, Generator
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, MagicMock

from src.domain.entities.market_data import MarketData, MarketDataBatch, OHLCV
from src.infrastructure.plugins import PluginManager
from src.infrastructure.config.settings import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data for testing."""
    return OHLCV(
        open=150.0,
        high=155.0,
        low=148.0,
        close=152.0,
        volume=1000000
    )

@pytest.fixture
def sample_market_data(sample_ohlcv):
    """Create sample market data for testing."""
    return MarketData(
        symbol="AAPL",
        timestamp="2025-09-05T10:00:00Z",
        timeframe="1D",
        ohlcv=sample_ohlcv,
        date_partition="2025-09-05"
    )


@pytest.fixture
def sample_market_data_batch(sample_market_data):
    """Create a batch of sample market data."""
    return MarketDataBatch(
        symbol="AAPL",
        timeframe="1D",
        data=[sample_market_data],
        start_date="2025-09-05T00:00:00Z",
        end_date="2025-09-05T23:59:59Z"
    )


@pytest.fixture
def mock_plugin_manager():
    """Create a mock plugin manager for testing."""
    manager = Mock(spec=PluginManager)
    manager.load_plugin.return_value = True
    manager.unload_plugin.return_value = True
    manager.get_plugin.return_value = Mock()
    return manager


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock()
    settings.database.path = ":memory:"
    settings.database.memory_limit = "1GB"
    settings.database.threads = 2
    settings.debug = True
    return settings


@pytest.fixture
def test_config():
    """Test configuration dictionary."""
    return {
        "database": {
            "path": ":memory:",
            "memory_limit": "1GB",
            "threads": 2
        },
        "logging": {
            "level": "DEBUG",
            "format": "json"
        },
        "plugins": {
            "scan_directory": "plugins",
            "auto_discover": True
        }
    }


@pytest.fixture
def performance_test_data():
    """Generate performance test data."""
    data = []
    for i in range(1000):
        data.append(MarketData(
            symbol="PERF_TEST",  # Same symbol for all data
            timestamp=f"2025-09-05T{i%24:02d}:{i%60:02d}:00Z",
            timeframe="1H",
            ohlcv=OHLCV(
                open=100.0 + i * 0.1,
                high=105.0 + i * 0.1,
                low=95.0 + i * 0.1,
                close=102.0 + i * 0.1,
                volume=100000 + i * 100
            ),
            date_partition="2025-09-05"
        ))
    return data


@pytest.fixture
def load_test_symbols():
    """Generate symbols for load testing."""
    return [f"SYMBOL_{i:04d}" for i in range(500)]


@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    connection = Mock()
    connection.execute.return_value = Mock()
    connection.fetchall.return_value = []
    connection.fetchone.return_value = None
    connection.commit.return_value = None
    connection.close.return_value = None
    return connection


@pytest.fixture
def mock_api_client():
    """Mock API client for testing."""
    client = Mock()
    client.get.return_value = Mock(status_code=200, json=lambda: {"status": "success"})
    client.post.return_value = Mock(status_code=201, json=lambda: {"id": 1})
    client.put.return_value = Mock(status_code=200, json=lambda: {"status": "updated"})
    client.delete.return_value = Mock(status_code=204)
    return client


@pytest.fixture
def test_logger():
    """Test logger fixture."""
    logger = Mock()
    logger.info.return_value = None
    logger.error.return_value = None
    logger.warning.return_value = None
    logger.debug.return_value = None
    return logger


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test."""
    # This fixture runs automatically before each test
    pass


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "functional: Functional tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "load: Load tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "regression: Regression tests")


# Test utilities
class TestUtils:
    """Utility functions for tests."""

    @staticmethod
    def create_test_market_data(count: int = 10, symbol: str = "TEST") -> List[MarketData]:
        """Create test market data."""
        data = []
        for i in range(count):
            data.append(MarketData(
                symbol=symbol,  # Use consistent symbol for all records
                timestamp=f"2025-09-05T{i%24:02d}:00:00Z",
                timeframe="1H",
                ohlcv=OHLCV(
                    open=100.0 + i,
                    high=105.0 + i,
                    low=95.0 + i,
                    close=102.0 + i,
                    volume=100000 + i * 1000
                ),
                date_partition="2025-09-05"
            ))
        return data

    @staticmethod
    def mock_successful_response(data: Any = None) -> Dict[str, Any]:
        """Create a mock successful response."""
        return {
            "status": "success",
            "data": data or {},
            "timestamp": "2025-09-05T10:00:00Z"
        }

    @staticmethod
    def mock_error_response(message: str = "Test error") -> Dict[str, Any]:
        """Create a mock error response."""
        return {
            "status": "error",
            "message": message,
            "timestamp": "2025-09-05T10:00:00Z"
        }


# Make TestUtils available to all tests
@pytest.fixture
def test_utils():
    """Test utilities fixture."""
    return TestUtils()
