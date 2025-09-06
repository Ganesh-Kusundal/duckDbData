"""Test-Driven Development tests for Market Data Repository in Domain Layer."""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, MagicMock
from typing import List, Optional, Tuple

# Mock complex dependencies
import sys
from unittest.mock import MagicMock

# Create more complete mocks
mock_structlog = MagicMock()
mock_structlog.BoundLogger = MagicMock
sys.modules['structlog'] = mock_structlog

sys.modules['pythonjsonlogger'] = MagicMock()
sys.modules['opentelemetry'] = MagicMock()
sys.modules['prometheus_client'] = MagicMock()

try:
    from src.domain.repositories.market_data_repo import MarketDataRepository
    from src.domain.entities.market_data import MarketData, MarketDataBatch, OHLCV
except ImportError:
    # Create mock classes if imports fail
    class MockMarketDataRepository:
        pass
    class MockMarketData:
        pass
    class MockMarketDataBatch:
        pass
    class MockOHLCV:
        pass

    MarketDataRepository = MockMarketDataRepository
    MarketData = MockMarketData
    MarketDataBatch = MockMarketDataBatch
    OHLCV = MockOHLCV


class ConcreteMarketDataRepository(MarketDataRepository):
    """Concrete implementation of MarketDataRepository for testing."""

    def __init__(self):
        self._data_store = {}

    def save(self, data: MarketData) -> None:
        """Save a single market data record."""
        key = f"{data.symbol}_{data.timestamp.isoformat()}"
        self._data_store[key] = data

    def save_batch(self, batch: MarketDataBatch) -> None:
        """Save a batch of market data records."""
        for data in batch.data:
            self.save(data)

    def find_by_symbol_and_date_range(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        timeframe: str = "1D"
    ) -> List[MarketData]:
        """Find market data by symbol and date range."""
        results = []
        for key, data in self._data_store.items():
            if (data.symbol == symbol and
                data.timeframe == timeframe and
                start_date <= data.timestamp.date() <= end_date):
                results.append(data)
        return sorted(results, key=lambda x: x.timestamp)

    def find_latest_by_symbol(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[MarketData]:
        """Find the latest market data records for a symbol."""
        symbol_data = [data for data in self._data_store.values() if data.symbol == symbol]
        return sorted(symbol_data, key=lambda x: x.timestamp, reverse=True)[:limit]

    def exists(self, symbol: str, timestamp: str) -> bool:
        """Check if market data exists for the given symbol and timestamp."""
        key = f"{symbol}_{timestamp}"
        return key in self._data_store

    def count_by_symbol(self, symbol: str) -> int:
        """Count total records for a symbol."""
        return len([data for data in self._data_store.values() if data.symbol == symbol])

    def get_date_range(self, symbol: str) -> Optional[Tuple[date, date]]:
        """Get the date range for a symbol's data."""
        symbol_data = [data for data in self._data_store.values() if data.symbol == symbol]
        if not symbol_data:
            return None

        dates = [data.timestamp.date() for data in symbol_data]
        return min(dates), max(dates)


class TestMarketDataRepository:
    """Test cases for MarketDataRepository abstract class and concrete implementation."""

    @pytest.fixture
    def repository(self):
        """Create a concrete repository instance for testing."""
        return ConcreteMarketDataRepository()

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        return MarketData(
            symbol="AAPL",
            timestamp=datetime(2025, 1, 15, 10, 30, 0),
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

    @pytest.fixture
    def sample_market_data_batch(self):
        """Create a batch of sample market data."""
        data_list = []
        base_time = datetime(2025, 1, 15, 9, 30, 0)

        for i in range(5):
            timestamp = base_time.replace(hour=9 + i)
            data = MarketData(
                symbol="AAPL",
                timestamp=timestamp,
                timeframe="1H",
                ohlcv=OHLCV(
                    open=Decimal("150.00") + Decimal(str(i)),
                    high=Decimal("155.00") + Decimal(str(i)),
                    low=Decimal("149.00") + Decimal(str(i)),
                    close=Decimal("154.00") + Decimal(str(i)),
                    volume=1000000 + (i * 100000)
                ),
                date_partition="2025-01-15"
            )
            data_list.append(data)

        return MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=data_list,
            start_date=data_list[0].timestamp.date(),
            end_date=data_list[-1].timestamp.date()
        )

    def test_repository_initialization(self, repository):
        """Test repository initialization."""
        assert repository is not None
        assert isinstance(repository, MarketDataRepository)
        assert len(repository._data_store) == 0

    def test_save_single_market_data(self, repository, sample_market_data):
        """Test saving a single market data record."""
        repository.save(sample_market_data)

        # Verify data was saved
        assert len(repository._data_store) == 1
        key = f"{sample_market_data.symbol}_{sample_market_data.timestamp.isoformat()}"
        assert key in repository._data_store
        assert repository._data_store[key] == sample_market_data

    def test_save_batch_market_data(self, repository, sample_market_data_batch):
        """Test saving a batch of market data records."""
        repository.save_batch(sample_market_data_batch)

        # Verify all data was saved
        assert len(repository._data_store) == 5

        # Verify each record
        for data in sample_market_data_batch.data:
            key = f"{data.symbol}_{data.timestamp.isoformat()}"
            assert key in repository._data_store
            assert repository._data_store[key] == data

    def test_find_by_symbol_and_date_range(self, repository, sample_market_data_batch):
        """Test finding market data by symbol and date range."""
        # Save batch first
        repository.save_batch(sample_market_data_batch)

        # Test finding within date range
        start_date = date(2025, 1, 15)
        end_date = date(2025, 1, 15)

        results = repository.find_by_symbol_and_date_range(
            symbol="AAPL",
            start_date=start_date,
            end_date=end_date,
            timeframe="1H"
        )

        assert len(results) == 5
        assert all(data.symbol == "AAPL" for data in results)
        assert all(data.timeframe == "1H" for data in results)

        # Verify results are sorted by timestamp
        timestamps = [data.timestamp for data in results]
        assert timestamps == sorted(timestamps)

    def test_find_by_symbol_and_date_range_no_results(self, repository):
        """Test finding market data when no results exist."""
        results = repository.find_by_symbol_and_date_range(
            symbol="AAPL",
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15)
        )

        assert results == []

    def test_find_by_symbol_and_date_range_wrong_symbol(self, repository, sample_market_data_batch):
        """Test finding market data with wrong symbol."""
        repository.save_batch(sample_market_data_batch)

        results = repository.find_by_symbol_and_date_range(
            symbol="GOOGL",  # Wrong symbol
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15)
        )

        assert results == []

    def test_find_latest_by_symbol(self, repository, sample_market_data_batch):
        """Test finding latest market data records for a symbol."""
        repository.save_batch(sample_market_data_batch)

        results = repository.find_latest_by_symbol("AAPL", limit=3)

        assert len(results) == 3
        # Should be sorted in descending order (latest first)
        timestamps = [data.timestamp for data in results]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_find_latest_by_symbol_limit_exceeded(self, repository, sample_market_data_batch):
        """Test finding latest records when limit exceeds available data."""
        repository.save_batch(sample_market_data_batch)

        results = repository.find_latest_by_symbol("AAPL", limit=10)

        assert len(results) == 5  # Should return all available data

    def test_exists_positive_case(self, repository, sample_market_data):
        """Test exists method with existing data."""
        repository.save(sample_market_data)

        exists = repository.exists(
            sample_market_data.symbol,
            sample_market_data.timestamp.isoformat()
        )

        assert exists is True

    def test_exists_negative_case(self, repository):
        """Test exists method with non-existing data."""
        exists = repository.exists("AAPL", "2025-01-15T10:30:00")

        assert exists is False

    def test_count_by_symbol(self, repository, sample_market_data_batch):
        """Test counting records by symbol."""
        repository.save_batch(sample_market_data_batch)

        count = repository.count_by_symbol("AAPL")

        assert count == 5

    def test_count_by_symbol_no_data(self, repository):
        """Test counting records for symbol with no data."""
        count = repository.count_by_symbol("AAPL")

        assert count == 0

    def test_get_date_range(self, repository, sample_market_data_batch):
        """Test getting date range for a symbol."""
        repository.save_batch(sample_market_data_batch)

        date_range = repository.get_date_range("AAPL")

        assert date_range is not None
        start_date, end_date = date_range
        assert start_date == date(2025, 1, 15)
        assert end_date == date(2025, 1, 15)

    def test_get_date_range_no_data(self, repository):
        """Test getting date range for symbol with no data."""
        date_range = repository.get_date_range("AAPL")

        assert date_range is None

    def test_multiple_symbols_isolation(self, repository):
        """Test that data for different symbols is properly isolated."""
        # Create data for two different symbols
        aapl_data = MarketData(
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

        googl_data = MarketData(
            symbol="GOOGL",
            timestamp=datetime(2025, 1, 15, 10, 0, 0),
            timeframe="1D",
            ohlcv=OHLCV(
                open=Decimal("2500.00"),
                high=Decimal("2550.00"),
                low=Decimal("2490.00"),
                close=Decimal("2540.00"),
                volume=500000
            ),
            date_partition="2025-01-15"
        )

        repository.save(aapl_data)
        repository.save(googl_data)

        # Test AAPL data
        aapl_results = repository.find_by_symbol_and_date_range(
            "AAPL", date(2025, 1, 15), date(2025, 1, 15)
        )
        assert len(aapl_results) == 1
        assert aapl_results[0].symbol == "AAPL"

        # Test GOOGL data
        googl_results = repository.find_by_symbol_and_date_range(
            "GOOGL", date(2025, 1, 15), date(2025, 1, 15)
        )
        assert len(googl_results) == 1
        assert googl_results[0].symbol == "GOOGL"

        # Test counts
        assert repository.count_by_symbol("AAPL") == 1
        assert repository.count_by_symbol("GOOGL") == 1

    def test_timeframe_filtering(self, repository):
        """Test that timeframe filtering works correctly."""
        # Create data with different timeframes
        daily_data = MarketData(
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

        hourly_data = MarketData(
            symbol="AAPL",
            timestamp=datetime(2025, 1, 15, 11, 0, 0),  # Different timestamp
            timeframe="1H",
            ohlcv=OHLCV(
                open=Decimal("150.00"),
                high=Decimal("155.00"),
                low=Decimal("149.00"),
                close=Decimal("154.00"),
                volume=1000000
            ),
            date_partition="2025-01-15"
        )

        repository.save(daily_data)
        repository.save(hourly_data)

        # Test daily timeframe
        daily_results = repository.find_by_symbol_and_date_range(
            "AAPL", date(2025, 1, 15), date(2025, 1, 15), timeframe="1D"
        )
        assert len(daily_results) == 1
        assert daily_results[0].timeframe == "1D"

        # Test hourly timeframe
        hourly_results = repository.find_by_symbol_and_date_range(
            "AAPL", date(2025, 1, 15), date(2025, 1, 15), timeframe="1H"
        )
        assert len(hourly_results) == 1
        assert hourly_results[0].timeframe == "1H"

    def test_repository_abstract_methods(self):
        """Test that MarketDataRepository defines all required abstract methods."""
        # This test ensures the abstract class has all expected methods
        expected_methods = [
            'save',
            'save_batch',
            'find_by_symbol_and_date_range',
            'find_latest_by_symbol',
            'exists',
            'count_by_symbol',
            'get_date_range'
        ]

        for method_name in expected_methods:
            assert hasattr(MarketDataRepository, method_name), f"Missing method: {method_name}"

    def test_concrete_implementation_instantiation(self):
        """Test that concrete implementation can be instantiated."""
        repo = ConcreteMarketDataRepository()
        assert repo is not None
        assert isinstance(repo, MarketDataRepository)
