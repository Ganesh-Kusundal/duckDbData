"""Performance benchmarks for bulk operations in database layer."""
import pytest
import time
from decimal import Decimal
from datetime import datetime
import pandas as pd

from database.adapters.duckdb_adapter import DuckDBAdapter
from src.domain.entities.market_data import (
    OHLCV,
    MarketData,
    MarketDataBatch
)
from database.repositories.duckdb_market_repo import DuckDBMarketDataRepository


@pytest.fixture
def temp_db_path():
    """Temporary DB path for performance tests."""
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def adapter(temp_db_path):
    """Adapter for performance tests."""
    adapter = DuckDBAdapter(database_path=temp_db_path)
    yield adapter
    adapter.close()


@pytest.fixture
def repo(adapter):
    """Repository for performance tests."""
    return DuckDBMarketDataRepository(adapter=adapter)


def generate_large_batch(symbol="AAPL", num_records=10000):
    """Generate a large batch of market data for testing."""
    data_list = []
    base_time = datetime(2025, 1, 1)
    for i in range(num_records):
        timestamp = base_time.replace(hour=i % 24, minute=0)
        ohlcv = OHLCV(
            open=Decimal(f"100.{i}"),
            high=Decimal(f"105.{i}"),
            low=Decimal(f"99.{i}"),
            close=Decimal(f"104.{i}"),
            volume=i * 1000
        )
        data = MarketData(
            symbol=symbol,
            timestamp=timestamp,
            timeframe="1H",
            ohlcv=ohlcv,
            date_partition=timestamp.strftime("%Y-%m-%d")
        )
        data_list.append(data)
    return MarketDataBatch(
        symbol=symbol,
        timeframe="1H",
        data=data_list,
        start_date=data_list[0].timestamp.date(),
        end_date=data_list[-1].timestamp.date()
    )


def test_bulk_insert_performance(repo, temp_db_path):
    """Benchmark bulk insert performance."""
    batch = generate_large_batch(num_records=5000)
    
    start_time = time.time()
    repo.save_batch(batch)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"Bulk insert of 5000 records took {duration:.4f} seconds")
    
    # Verify data was inserted
    results = repo.find_by_symbol_and_date_range("AAPL", repo.get_date_range("AAPL")[0], repo.get_date_range("AAPL")[1], "1H")
    assert len(results) == 5000
    
    # Assert reasonable performance (e.g., under 2 seconds for 5000 records)
    assert duration < 2.0, f"Bulk insert too slow: {duration} seconds"


def test_large_query_performance(adapter, temp_db_path):
    """Benchmark large query performance."""
    # Insert large dataset
    batch = generate_large_batch(num_records=10000)
    repo = DuckDBMarketDataRepository(adapter)
    repo.save_batch(batch)
    
    # Query the entire dataset
    start_time = time.time()
    df = adapter.execute_query("SELECT * FROM market_data WHERE symbol = 'AAPL'")
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"Query of 10000 records took {duration:.4f} seconds")
    
    assert len(df) == 10000
    assert duration < 0.5, f"Query too slow: {duration} seconds"


def test_indexed_query_performance(adapter, temp_db_path):
    """Benchmark query with indexes."""
    # The schema already has indexes, test date range query
    batch = generate_large_batch(num_records=10000)
    repo = DuckDBMarketDataRepository(adapter)
    repo.save_batch(batch)
    
    start_date = datetime(2025, 1, 1).date()
    end_date = datetime(2025, 1, 2).date()
    
    start_time = time.time()
    results = repo.find_by_symbol_and_date_range("AAPL", start_date, end_date, "1H")
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"Indexed date range query took {duration:.4f} seconds")
    
    # Expect fewer records for small range
    assert len(results) <= 24  # 1 day, 1H timeframe
    assert duration < 0.1, f"Indexed query too slow: {duration} seconds"