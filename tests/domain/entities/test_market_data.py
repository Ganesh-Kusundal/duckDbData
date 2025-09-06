"""Test-Driven Development tests for Market Data domain entities."""

import pytest
from datetime import datetime
from decimal import Decimal

from src.domain.entities.market_data import (
    OHLCV,
    MarketData,
    MarketDataBatch
)


class TestOHLCV:
    """Test cases for OHLCV data structure."""

    def test_valid_ohlcv_creation(self):
        """Test creating valid OHLCV data."""
        ohlcv = OHLCV(
            open=Decimal("100.50"),
            high=Decimal("105.25"),
            low=Decimal("99.75"),
            close=Decimal("104.00"),
            volume=1000
        )

        assert ohlcv.open == Decimal("100.50")
        assert ohlcv.high == Decimal("105.25")
        assert ohlcv.low == Decimal("99.75")
        assert ohlcv.close == Decimal("104.00")
        assert ohlcv.volume == 1000

    def test_invalid_high_lower_than_low(self):
        """Test that high cannot be lower than low."""
        with pytest.raises(ValueError, match="low cannot be higher than high"):
            OHLCV(
                open=Decimal("100.00"),
                high=Decimal("99.00"),  # High lower than low
                low=Decimal("100.00"),
                close=Decimal("99.50"),
                volume=1000
            )

    def test_negative_prices_not_allowed(self):
        """Test that negative prices are not allowed."""
        with pytest.raises(ValueError):
            OHLCV(
                open=Decimal("-100.00"),
                high=Decimal("105.00"),
                low=Decimal("99.00"),
                close=Decimal("104.00"),
                volume=1000
            )

    def test_negative_volume_not_allowed(self):
        """Test that negative volume is not allowed."""
        with pytest.raises(ValueError):
            OHLCV(
                open=Decimal("100.00"),
                high=Decimal("105.00"),
                low=Decimal("99.00"),
                close=Decimal("104.00"),
                volume=-1000
            )


class TestMarketData:
    """Test cases for MarketData entity."""

    @pytest.fixture
    def sample_ohlcv(self):
        """Create a sample OHLCV for testing."""
        return OHLCV(
            open=Decimal("100.50"),
            high=Decimal("105.25"),
            low=Decimal("99.75"),
            close=Decimal("104.00"),
            volume=1000
        )

    @pytest.fixture
    def sample_timestamp(self):
        """Create a sample timestamp for testing."""
        return datetime(2025, 1, 15, 10, 30, 0)

    def test_valid_market_data_creation(self, sample_ohlcv, sample_timestamp):
        """Test creating valid MarketData entity."""
        market_data = MarketData(
            symbol="AAPL",
            timestamp=sample_timestamp,
            timeframe="1H",
            ohlcv=sample_ohlcv,
            date_partition="2025-01-15"
        )

        assert market_data.symbol == "AAPL"
        assert market_data.timestamp == sample_timestamp
        assert market_data.timeframe == "1H"
        assert market_data.ohlcv == sample_ohlcv
        assert market_data.date_partition == "2025-01-15"
        assert market_data.is_valid is True

    def test_empty_symbol_not_allowed(self, sample_ohlcv, sample_timestamp):
        """Test that empty symbol is not allowed."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            MarketData(
                symbol="",  # Empty symbol
                timestamp=sample_timestamp,
                timeframe="1H",
                ohlcv=sample_ohlcv,
                date_partition="2025-01-15"
            )

    def test_empty_timeframe_not_allowed(self, sample_ohlcv, sample_timestamp):
        """Test that empty timeframe is not allowed."""
        with pytest.raises(ValueError, match="Timeframe cannot be empty"):
            MarketData(
                symbol="AAPL",
                timestamp=sample_timestamp,
                timeframe="",  # Empty timeframe
                ohlcv=sample_ohlcv,
                date_partition="2025-01-15"
            )

    def test_empty_date_partition_not_allowed(self, sample_ohlcv, sample_timestamp):
        """Test that empty date partition is not allowed."""
        with pytest.raises(ValueError, match="Date partition cannot be empty"):
            MarketData(
                symbol="AAPL",
                timestamp=sample_timestamp,
                timeframe="1H",
                ohlcv=sample_ohlcv,
                date_partition=""  # Empty date partition
            )

    def test_market_data_immutability(self, sample_ohlcv, sample_timestamp):
        """Test that MarketData is immutable (frozen dataclass)."""
        market_data = MarketData(
            symbol="AAPL",
            timestamp=sample_timestamp,
            timeframe="1H",
            ohlcv=sample_ohlcv,
            date_partition="2025-01-15"
        )

        # Attempting to modify should raise an error
        with pytest.raises(AttributeError):
            market_data.symbol = "GOOGL"


class TestMarketDataBatch:
    """Test cases for MarketDataBatch entity."""

    @pytest.fixture
    def sample_market_data_list(self, sample_ohlcv):
        """Create a list of sample MarketData for testing."""
        timestamps = [
            datetime(2025, 1, 15, 10, 0, 0),
            datetime(2025, 1, 15, 11, 0, 0),
            datetime(2025, 1, 15, 12, 0, 0)
        ]

        return [
            MarketData(
                symbol="AAPL",
                timestamp=ts,
                timeframe="1H",
                ohlcv=sample_ohlcv,
                date_partition="2025-01-15"
            )
            for ts in timestamps
        ]

    def test_valid_batch_creation(self, sample_market_data_list):
        """Test creating valid MarketDataBatch."""
        batch = MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=sample_market_data_list,
            start_date=datetime(2025, 1, 15, 10, 0, 0),
            end_date=datetime(2025, 1, 15, 12, 0, 0)
        )

        assert batch.symbol == "AAPL"
        assert batch.timeframe == "1H"
        assert len(batch.data) == 3
        assert batch.record_count == 3
        assert batch.start_date == datetime(2025, 1, 15, 10, 0, 0)
        assert batch.end_date == datetime(2025, 1, 15, 12, 0, 0)

    def test_empty_symbol_not_allowed(self, sample_market_data_list):
        """Test that empty symbol is not allowed in batch."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            MarketDataBatch(
                symbol="",  # Empty symbol
                timeframe="1H",
                data=sample_market_data_list,
                start_date=datetime(2025, 1, 15, 10, 0, 0),
                end_date=datetime(2025, 1, 15, 12, 0, 0)
            )

    def test_empty_data_not_allowed(self):
        """Test that empty data list is not allowed."""
        with pytest.raises(ValueError, match="Data cannot be empty"):
            MarketDataBatch(
                symbol="AAPL",
                timeframe="1H",
                data=[],  # Empty data
                start_date=datetime(2025, 1, 15, 10, 0, 0),
                end_date=datetime(2025, 1, 15, 12, 0, 0)
            )

    def test_start_date_after_end_date_not_allowed(self, sample_market_data_list):
        """Test that start date after end date is not allowed."""
        with pytest.raises(ValueError, match="Start date cannot be after end date"):
            MarketDataBatch(
                symbol="AAPL",
                timeframe="1H",
                data=sample_market_data_list,
                start_date=datetime(2025, 1, 15, 12, 0, 0),  # After end date
                end_date=datetime(2025, 1, 15, 10, 0, 0)
            )

    def test_sorted_data_check(self, sample_market_data_list):
        """Test the is_sorted property."""
        # Data is already sorted by timestamp
        batch = MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=sample_market_data_list,
            start_date=datetime(2025, 1, 15, 10, 0, 0),
            end_date=datetime(2025, 1, 15, 12, 0, 0)
        )

        assert batch.is_sorted is True

    def test_unsorted_data_check(self, sample_market_data_list):
        """Test the is_sorted property with unsorted data."""
        # Reverse the data to make it unsorted
        unsorted_data = list(reversed(sample_market_data_list))

        batch = MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=unsorted_data,
            start_date=datetime(2025, 1, 15, 10, 0, 0),
            end_date=datetime(2025, 1, 15, 12, 0, 0)
        )

        assert batch.is_sorted is False
