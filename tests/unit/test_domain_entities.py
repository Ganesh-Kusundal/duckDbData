"""
Unit Tests for Domain Entities
==============================

Comprehensive unit tests for domain entities including MarketData, OHLCV, and related classes.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.domain.entities.market_data import (
    MarketData, MarketDataBatch, OHLCV
)


class TestOHLCV:
    """Test cases for OHLCV entity."""

    def test_ohlcv_creation_valid(self):
        """Test creating valid OHLCV data."""
        ohlcv = OHLCV(
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000
        )

        assert ohlcv.open == Decimal('100.0')
        assert ohlcv.high == Decimal('105.0')
        assert ohlcv.low == Decimal('95.0')
        assert ohlcv.close == Decimal('102.0')
        assert ohlcv.volume == 1000000

    def test_ohlcv_validation_high_lower_than_low(self):
        """Test validation when high is lower than low."""
        with pytest.raises(ValueError, match="low cannot be higher than high"):
            OHLCV(
                open=100.0,
                high=95.0,  # Lower than low
                low=98.0,
                close=102.0,
                volume=1000000
            )

    def test_ohlcv_negative_values(self):
        """Test OHLCV with negative values."""
        with pytest.raises(ValueError):
            OHLCV(
                open=-100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000000
            )

    def test_ohlcv_zero_volume(self):
        """Test OHLCV with zero volume."""
        with pytest.raises(ValueError):
            OHLCV(
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=0
            )


class TestMarketData:
    """Test cases for MarketData entity."""

    def test_market_data_creation_valid(self, sample_market_data):
        """Test creating valid market data."""
        assert sample_market_data.symbol == "AAPL"
        assert sample_market_data.timeframe == "1D"
        assert sample_market_data.date_partition == "2025-09-05"
        assert sample_market_data.is_valid is True

    def test_market_data_empty_symbol(self):
        """Test market data with empty symbol."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            MarketData(
                symbol="",
                timestamp="2025-09-05T10:00:00Z",
                timeframe="1D",
                ohlcv=OHLCV(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000),
                date_partition="2025-09-05"
            )

    def test_market_data_empty_timeframe(self):
        """Test market data with empty timeframe."""
        with pytest.raises(ValueError, match="Timeframe cannot be empty"):
            MarketData(
                symbol="AAPL",
                timestamp="2025-09-05T10:00:00Z",
                timeframe="",
                ohlcv=OHLCV(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000),
                date_partition="2025-09-05"
            )

    def test_market_data_empty_partition(self):
        """Test market data with empty date partition."""
        with pytest.raises(ValueError, match="Date partition cannot be empty"):
            MarketData(
                symbol="AAPL",
                timestamp="2025-09-05T10:00:00Z",
                timeframe="1D",
                ohlcv=OHLCV(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000),
                date_partition=""
            )

    def test_market_data_immutability(self, sample_market_data):
        """Test that market data is immutable."""
        # This should work since it's a dataclass with frozen=True
        with pytest.raises(AttributeError):
            sample_market_data.symbol = "GOOGL"


class TestMarketDataBatch:
    """Test cases for MarketDataBatch entity."""

    def test_batch_creation_valid(self, sample_market_data_batch):
        """Test creating valid market data batch."""
        assert sample_market_data_batch.symbol == "AAPL"
        assert sample_market_data_batch.timeframe == "1D"
        assert len(sample_market_data_batch.data) == 1
        assert sample_market_data_batch.record_count == 1

    def test_batch_empty_symbol(self, sample_market_data):
        """Test batch with empty symbol."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            MarketDataBatch(
                symbol="",
                timeframe="1D",
                data=[sample_market_data],
                start_date="2025-09-05T00:00:00Z",
                end_date="2025-09-05T23:59:59Z"
            )

    def test_batch_empty_data(self):
        """Test batch with empty data."""
        with pytest.raises(ValueError, match="Data cannot be empty"):
            MarketDataBatch(
                symbol="AAPL",
                timeframe="1D",
                data=[],
                start_date="2025-09-05T00:00:00Z",
                end_date="2025-09-05T23:59:59Z"
            )

    def test_batch_invalid_date_range(self, sample_market_data):
        """Test batch with invalid date range."""
        with pytest.raises(ValueError, match="Start date cannot be after end date"):
            MarketDataBatch(
                symbol="AAPL",
                timeframe="1D",
                data=[sample_market_data],
                start_date="2025-09-05T23:59:59Z",
                end_date="2025-09-05T00:00:00Z"
            )

    def test_batch_is_sorted(self, sample_market_data_batch):
        """Test batch sorting check."""
        assert sample_market_data_batch.is_sorted is True

    def test_batch_unsorted_data(self, sample_market_data):
        """Test batch with unsorted data."""
        # Create data with timestamps out of order
        data1 = MarketData(
            symbol="AAPL",
            timestamp="2025-09-05T12:00:00Z",
            timeframe="1D",
            ohlcv=OHLCV(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000),
            date_partition="2025-09-05"
        )
        data2 = MarketData(
            symbol="AAPL",
            timestamp="2025-09-05T10:00:00Z",  # Earlier timestamp
            timeframe="1D",
            ohlcv=OHLCV(open=100.0, high=105.0, low=95.0, close=102.0, volume=1000000),
            date_partition="2025-09-05"
        )

        batch = MarketDataBatch(
            symbol="AAPL",
            timeframe="1D",
            data=[data1, data2],  # Unsorted order
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )

        assert batch.is_sorted is False


class TestDomainEntityIntegration:
    """Integration tests for domain entities."""

    def test_full_market_data_workflow(self):
        """Test complete market data workflow."""
        # Create OHLCV data
        ohlcv = OHLCV(
            open=150.0,
            high=155.0,
            low=148.0,
            close=152.0,
            volume=1000000
        )

        # Create market data
        market_data = MarketData(
            symbol="AAPL",
            timestamp="2025-09-05T10:00:00Z",
            timeframe="1D",
            ohlcv=ohlcv,
            date_partition="2025-09-05"
        )

        # Create batch
        batch = MarketDataBatch(
            symbol="AAPL",
            timeframe="1D",
            data=[market_data],
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )

        # Verify all components work together
        assert batch.symbol == market_data.symbol
        assert batch.timeframe == market_data.timeframe
        assert batch.record_count == 1
        assert batch.data[0].ohlcv.close == ohlcv.close

    def test_multiple_symbols_batch(self):
        """Test batch with multiple symbols."""
        data = []
        symbols = ["AAPL", "GOOGL", "MSFT"]

        for i, symbol in enumerate(symbols):
            market_data = MarketData(
                symbol=symbol,
                timestamp="2025-09-05T10:00:00Z",
                timeframe="1D",
                ohlcv=OHLCV(
                    open=100.0 + i * 10,
                    high=105.0 + i * 10,
                    low=95.0 + i * 10,
                    close=102.0 + i * 10,
                    volume=1000000 + i * 100000
                ),
                date_partition="2025-09-05"
            )
            data.append(market_data)

        # This should fail because all data must have the same symbol
        with pytest.raises(ValueError):
            MarketDataBatch(
                symbol="AAPL",  # Only AAPL allowed
                timeframe="1D",
                data=data,  # Contains multiple symbols
                start_date="2025-09-05T00:00:00Z",
                end_date="2025-09-05T23:59:59Z"
            )
