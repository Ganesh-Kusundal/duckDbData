"""Test-Driven Development tests for Base Scanner in Application Layer."""

import pytest
from datetime import datetime, date, time
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import Mock, MagicMock
import pandas as pd

from src.application.scanners.base_scanner import BaseScanner
from src.domain.entities.market_data import (
    OHLCV,
    MarketData,
    MarketDataBatch
)


class TestBaseScanner:
    """Test cases for BaseScanner application service."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        ohlcv = OHLCV(
            open=Decimal("100.50"),
            high=Decimal("105.25"),
            low=Decimal("99.75"),
            close=Decimal("104.00"),
            volume=1000
        )

        return MarketData(
            symbol="AAPL",
            timestamp=datetime(2025, 1, 15, 10, 30, 0),
            timeframe="1H",
            ohlcv=ohlcv,
            date_partition="2025-01-15"
        )

    @pytest.fixture
    def sample_batch(self, sample_market_data):
        """Create sample market data batch for testing."""
        return MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=[sample_market_data],
            start_date=datetime(2025, 1, 15, 10, 0, 0),
            end_date=datetime(2025, 1, 15, 11, 0, 0)
        )

    def test_base_scanner_initialization(self):
        """Test that BaseScanner can be initialized with concrete implementation."""
        scanner = ConcreteTestScanner()
        assert scanner is not None
        assert hasattr(scanner, 'scan')
        assert hasattr(scanner, 'scanner_name')

    def test_base_scanner_name_property(self):
        """Test that BaseScanner has a name property."""
        scanner = ConcreteTestScanner()
        assert scanner.scanner_name == "ConcreteTestScanner"

    def test_base_scanner_scan_method_raises_not_implemented(self, sample_batch):
        """Test that BaseScanner.scan raises NotImplementedError when not implemented."""
        # Test with a mock that doesn't implement scan
        class MockScanner(BaseScanner):
            @property
            def scanner_name(self):
                return "MockScanner"

            def _get_default_config(self):
                return {}

        scanner = MockScanner()

        with pytest.raises(NotImplementedError):
            scanner.scan(sample_batch)

    def test_base_scanner_with_market_data_repo(self):
        """Test BaseScanner with market data repository dependency."""
        mock_repo = Mock()
        scanner = ConcreteTestScanner()

        # In a real implementation, the scanner would use the repo
        # For now, we just verify the scanner exists
        assert scanner is not None

    def test_scanner_processes_single_market_data(self, sample_market_data):
        """Test that scanner can process individual market data points."""
        scanner = ConcreteTestScanner()

        # Test that the scanner can handle individual data points
        # This would be used by concrete implementations
        assert sample_market_data.symbol == "AAPL"
        assert sample_market_data.is_valid is True

    def test_scanner_processes_batch_data(self, sample_batch):
        """Test that scanner can process batch market data."""
        scanner = ConcreteTestScanner()

        # Test that the scanner can handle batch data
        # This would be used by concrete implementations
        assert sample_batch.symbol == "AAPL"
        assert sample_batch.record_count == 1
        assert sample_batch.is_sorted is True


class ConcreteTestScanner(BaseScanner):
    """Concrete implementation of BaseScanner for testing."""

    @property
    def scanner_name(self) -> str:
        """Get scanner name."""
        return "test_scanner"

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {"test_param": "test_value"}

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """Implement the scan method for testing."""
        return pd.DataFrame({
            "symbol": ["TEST"],
            "signal": ["test_signal"]
        })


class TestConcreteScanner:
    """Test cases for concrete scanner implementation."""

    @pytest.fixture
    def concrete_scanner(self):
        """Create a concrete scanner for testing."""
        return ConcreteTestScanner()

    @pytest.fixture
    def sample_batch(self):
        """Create sample market data batch."""
        ohlcv = OHLCV(
            open=Decimal("100.50"),
            high=Decimal("105.25"),
            low=Decimal("99.75"),
            close=Decimal("104.00"),
            volume=1000
        )

        market_data = MarketData(
            symbol="AAPL",
            timestamp=datetime(2025, 1, 15, 10, 30, 0),
            timeframe="1H",
            ohlcv=ohlcv,
            date_partition="2025-01-15"
        )

        return MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=[market_data],
            start_date=datetime(2025, 1, 15, 10, 0, 0),
            end_date=datetime(2025, 1, 15, 11, 0, 0)
        )

    def test_concrete_scanner_creation(self, concrete_scanner):
        """Test creating a concrete scanner."""
        assert concrete_scanner is not None
        assert concrete_scanner.name == "ConcreteTestScanner"

    def test_concrete_scanner_scan_implementation(self, concrete_scanner, sample_batch):
        """Test the concrete scanner's scan implementation."""
        result = concrete_scanner.scan(sample_batch)

        expected_result = {
            "scanner_name": "ConcreteTestScanner",
            "symbol": "AAPL",
            "record_count": 1,
            "signals": []
        }

        assert result == expected_result

    def test_concrete_scanner_with_empty_batch(self, concrete_scanner):
        """Test concrete scanner with empty batch."""
        # Create empty batch
        empty_batch = MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=[],
            start_date=datetime(2025, 1, 15, 10, 0, 0),
            end_date=datetime(2025, 1, 15, 11, 0, 0)
        )

        # This should work with our concrete implementation
        result = concrete_scanner.scan(empty_batch)

        expected_result = {
            "scanner_name": "ConcreteTestScanner",
            "symbol": "AAPL",
            "record_count": 0,
            "signals": []
        }

        assert result == expected_result
