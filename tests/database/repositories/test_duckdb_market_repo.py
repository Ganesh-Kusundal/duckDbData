"""Integration tests for DuckDBMarketDataRepository using real database connections."""
import pytest
import tempfile
import os
from datetime import datetime, date
from decimal import Decimal
import pandas as pd

from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from src.infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository
from src.domain.entities.market_data import (
    OHLCV,
    MarketData,
    MarketDataBatch
)


class TestDuckDBMarketDataRepository:
    """Integration test cases for DuckDBMarketDataRepository."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def adapter(self, temp_db_path):
        """Create DuckDBAdapter with temp database."""
        adapter = DuckDBAdapter(database_path=temp_db_path)
        yield adapter
        adapter.close()

    @pytest.fixture
    def repo(self, adapter):
        """Create repository instance."""
        return DuckDBMarketDataRepository(adapter=adapter)

    @pytest.fixture
    def sample_market_data(self):
        """Sample MarketData instance."""
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
    def sample_market_data_batch(self, sample_market_data):
        """Sample MarketDataBatch."""
        # Create batch with multiple entries
        data_list = [
            sample_market_data,
            MarketData(
                symbol="AAPL",
                timestamp=datetime(2025, 1, 15, 11, 30, 0),
                timeframe="1H",
                ohlcv=OHLCV(
                    open=Decimal("104.00"),
                    high=Decimal("106.00"),
                    low=Decimal("103.00"),
                    close=Decimal("105.50"),
                    volume=1200
                ),
                date_partition="2025-01-15"
            )
        ]
        return MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=data_list,
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15)
        )

    def test_repository_initialization(self, repo):
        """Test repository initialization."""
        assert repo is not None
        assert hasattr(repo, 'adapter')
        assert repo.adapter is not None

    def test_save_single_market_data(self, repo, sample_market_data):
        """Test saving a single market data record."""
        repo.save(sample_market_data)

        # Verify by querying
        results = repo.find_by_symbol_and_date_range(
            "AAPL", date(2025, 1, 15), date(2025, 1, 15), "1H"
        )
        assert len(results) == 1
        saved_data = results[0]
        assert saved_data.symbol == "AAPL"
        assert saved_data.ohlcv.close == Decimal("104.00")

    def test_save_batch_market_data(self, repo, sample_market_data_batch):
        """Test saving a batch of market data."""
        repo.save_batch(sample_market_data_batch)

        results = repo.find_by_symbol_and_date_range(
            "AAPL", date(2025, 1, 15), date(2025, 1, 15), "1H"
        )
        assert len(results) == 2
        assert all(d.symbol == "AAPL" for d in results)

    def test_find_by_symbol_and_date_range(self, repo, sample_market_data_batch):
        """Test finding market data by symbol and date range."""
        repo.save_batch(sample_market_data_batch)

        results = repo.find_by_symbol_and_date_range(
            "AAPL", date(2025, 1, 15), date(2025, 1, 15), "1H"
        )
        assert len(results) == 2
        timestamps = [d.timestamp for d in results]
        assert timestamps == sorted(timestamps)
        assert results[0].ohlcv.volume == 1000
        assert results[1].ohlcv.volume == 1200

    def test_find_by_symbol_and_date_range_no_results(self, repo):
        """Test finding with no results."""
        results = repo.find_by_symbol_and_date_range(
            "NONEXISTENT", date(2025, 1, 15), date(2025, 1, 15), "1H"
        )
        assert results == []

    def test_find_latest_by_symbol(self, repo, sample_market_data_batch):
        """Test finding latest records."""
        repo.save_batch(sample_market_data_batch)

        results = repo.find_latest_by_symbol("AAPL", limit=1)
        assert len(results) == 1
        # Latest should be the second one
        assert results[0].timestamp == datetime(2025, 1, 15, 11, 30, 0)

    def test_exists_positive(self, repo, sample_market_data):
        """Test exists method positive case."""
        repo.save(sample_market_data)
        exists = repo.exists("AAPL", sample_market_data.timestamp.isoformat())
        assert exists is True

    def test_exists_negative(self, repo):
        """Test exists method negative case."""
        exists = repo.exists("AAPL", "2025-01-15T00:00:00")
        assert exists is False

    def test_count_by_symbol(self, repo, sample_market_data_batch):
        """Test counting records by symbol."""
        repo.save_batch(sample_market_data_batch)
        count = repo.count_by_symbol("AAPL")
        assert count == 2

    def test_get_date_range(self, repo, sample_market_data_batch):
        """Test getting date range."""
        repo.save_batch(sample_market_data_batch)
        date_range = repo.get_date_range("AAPL")
        assert date_range == (date(2025, 1, 15), date(2025, 1, 15))
def test_data_validation_from_db(self, repo, sample_market_data_batch):
    """Test data validation for data retrieved from DB."""
    repo.save_batch(sample_market_data_batch)
    
    results = repo.find_by_symbol_and_date_range(
        "AAPL", date(2025, 1, 15), date(2025, 1, 15), "1H"
    )
    
    # Validate data integrity
    for data in results:
        # Check required fields are present
        assert data.symbol is not None
        assert data.timestamp is not None
        assert data.timeframe is not None
        assert data.date_partition is not None
        
        # Validate OHLCV values are positive and make sense
        assert data.ohlcv.open > 0
        assert data.ohlcv.high > 0
        assert data.ohlcv.low > 0
        assert data.ohlcv.close > 0
        assert data.ohlcv.volume >= 0
        
        # Check high >= low
        assert data.ohlcv.high >= data.ohlcv.low
        
        # Check high >= open, close >= low
        assert data.ohlcv.high >= data.ohlcv.open
        assert data.ohlcv.high >= data.ohlcv.close
        assert data.ohlcv.open >= data.ohlcv.low
        assert data.ohlcv.close >= data.ohlcv.low
        
        # Validate date_partition matches timestamp
        expected_date = data.timestamp.date().strftime('%Y-%m-%d')
        assert data.date_partition == expected_date
        
        # Check Decimal precision (if applicable)
        assert isinstance(data.ohlcv.open, Decimal)
        assert len(str(data.ohlcv.open).split('.')[-1]) <= 2  # 2 decimal places

    print(f"Validated {len(results)} records from DB")