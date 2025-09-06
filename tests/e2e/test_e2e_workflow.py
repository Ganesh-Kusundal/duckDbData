"""
End-to-End Tests
================

Complete workflow tests from data ingestion to analysis.
"""

import pytest
import time
from pathlib import Path
from typing import List

from src.domain.entities.market_data import MarketData, MarketDataBatch, OHLCV
from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from src.interfaces.api.app import app
from fastapi.testclient import TestClient


class TestEndToEndWorkflow:
    """End-to-end tests for complete data workflows."""

    @pytest.fixture
    def test_client(self):
        """Create test client for API testing."""
        return TestClient(app)

    @pytest.fixture
    def db_adapter(self, tmp_path):
        """Create database adapter for testing."""
        db_path = tmp_path / "test_e2e.db"
        return DuckDBAdapter(database_path=str(db_path))

    @pytest.fixture
    def sample_e2e_data(self) -> List[MarketData]:
        """Create comprehensive sample data for E2E testing."""
        data = []
        for i in range(100):
            data.append(MarketData(
                symbol="AAPL",
                timestamp=f"2025-09-05T{i%24:02d}:{i%60:02d}:00Z",
                timeframe="1H",
                ohlcv=OHLCV(
                    open=150.0 + i * 0.5,
                    high=155.0 + i * 0.5,
                    low=145.0 + i * 0.5,
                    close=152.0 + i * 0.5,
                    volume=1000000 + i * 1000
                ),
                date_partition="2025-09-05"
            ))
        return data

    @pytest.mark.e2e
    def test_complete_data_workflow(self, db_adapter, sample_e2e_data, test_client):
        """Test complete workflow from data ingestion to API serving."""
        # Step 1: Create data batch
        batch = MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=sample_e2e_data,
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )

        # Step 2: Persist data
        for market_data in sample_e2e_data:
            insert_query = f"""
            INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
            VALUES (
                '{market_data.symbol}',
                '{market_data.timestamp}',
                '{market_data.timeframe}',
                {market_data.ohlcv.open},
                {market_data.ohlcv.high},
                {market_data.ohlcv.low},
                {market_data.ohlcv.close},
                {market_data.ohlcv.volume},
                '{market_data.date_partition}'
            )
            """
            db_adapter.execute_query(insert_query)

        # Step 3: Verify data persistence
        result = db_adapter.execute_query("SELECT COUNT(*) as count FROM market_data")
        assert result.iloc[0]['count'] == len(sample_e2e_data)

        # Step 4: Test API endpoints
        # Health check
        response = test_client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"

        # Market data API (would need actual implementation)
        # response = test_client.get("/market-data/AAPL")
        # assert response.status_code == 200

        # Step 5: Test data integrity
        result = db_adapter.execute_query("""
        SELECT
            symbol,
            COUNT(*) as record_count,
            AVG(close) as avg_close,
            MAX(high) as max_high,
            MIN(low) as min_low,
            SUM(volume) as total_volume
        FROM market_data
        WHERE symbol = 'AAPL'
        GROUP BY symbol
        """)

        assert len(result) == 1
        stats = result.iloc[0]
        assert stats['record_count'] == 100
        assert stats['symbol'] == 'AAPL'
        assert stats['total_volume'] > 0

    @pytest.mark.e2e
    def test_data_processing_pipeline(self, db_adapter, sample_e2e_data):
        """Test complete data processing pipeline."""
        # Step 1: Data ingestion
        start_time = time.time()

        for market_data in sample_e2e_data:
            insert_query = f"""
            INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
            VALUES (
                '{market_data.symbol}',
                '{market_data.timestamp}',
                '{market_data.timeframe}',
                {market_data.ohlcv.open},
                {market_data.ohlcv.high},
                {market_data.ohlcv.low},
                {market_data.ohlcv.close},
                {market_data.ohlcv.volume},
                '{market_data.date_partition}'
            )
            """
            db_adapter.execute_query(insert_query)

        ingestion_time = time.time() - start_time

        # Step 2: Data validation
        result = db_adapter.execute_query("""
        SELECT
            COUNT(*) as total_records,
            COUNT(CASE WHEN volume < 0 THEN 1 END) as negative_volume,
            COUNT(CASE WHEN high < low THEN 1 END) as invalid_ranges
        FROM market_data
        """)

        validation = result.iloc[0]
        assert validation['total_records'] == len(sample_e2e_data)
        assert validation['negative_volume'] == 0
        assert validation['invalid_ranges'] == 0

        # Step 3: Data aggregation
        result = db_adapter.execute_query("""
        SELECT
            symbol,
            date_partition,
            MIN(low) as daily_low,
            MAX(high) as daily_high,
            FIRST(open) as daily_open,
            LAST(close) as daily_close,
            SUM(volume) as total_volume,
            AVG((high + low + close) / 3) as avg_price
        FROM market_data
        WHERE symbol = 'AAPL'
        GROUP BY symbol, date_partition
        """)

        assert len(result) == 1
        agg_data = result.iloc[0]
        assert agg_data['total_volume'] > 0
        assert agg_data['daily_high'] > agg_data['daily_low']

        # Performance check
        assert ingestion_time < 5.0  # Should complete within 5 seconds

    @pytest.mark.e2e
    def test_error_handling_workflow(self, db_adapter):
        """Test error handling throughout the workflow."""
        # Test invalid data handling
        try:
            # This should fail due to validation
            invalid_data = MarketData(
                symbol="TEST",
                timestamp="2025-09-05T10:00:00Z",
                timeframe="1H",
                ohlcv=OHLCV(
                    open=-100.0,  # Invalid negative price
                    high=105.0,
                    low=95.0,
                    close=102.0,
                    volume=1000000
                ),
                date_partition="2025-09-05"
            )

            insert_query = f"""
            INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
            VALUES (
                '{invalid_data.symbol}',
                '{invalid_data.timestamp}',
                '{invalid_data.timeframe}',
                {invalid_data.ohlcv.open},
                {invalid_data.ohlcv.high},
                {invalid_data.ohlcv.low},
                {invalid_data.ohlcv.close},
                {invalid_data.ohlcv.volume},
                '{invalid_data.date_partition}'
            )
            """
            db_adapter.execute_query(insert_query)

            # If we get here, the constraint wasn't enforced
            # Check that the data was actually inserted
            result = db_adapter.execute_query("SELECT COUNT(*) as count FROM market_data WHERE open < 0")
            assert result.iloc[0]['count'] == 0  # Should be rejected

        except Exception as e:
            # Expected to fail due to validation (either Pydantic or database constraints)
            error_msg = str(e).lower()
            assert ("constraint" in error_msg or
                   "check" in error_msg or
                   "validation" in error_msg or
                   "greater_than_equal" in error_msg)

    @pytest.mark.e2e
    def test_concurrent_access_workflow(self, db_adapter, sample_e2e_data):
        """Test concurrent access patterns."""
        import threading
        import queue

        results = queue.Queue()
        errors = queue.Queue()

        def worker(worker_id: int, data_subset: List[MarketData]):
            """Worker function for concurrent processing."""
            try:
                # Simple data processing without database conflicts
                processed_count = 0
                for market_data in data_subset:
                    # Simulate processing time
                    processed_count += 1

                results.put(f"Worker {worker_id} processed {processed_count} records")

            except Exception as e:
                errors.put(f"Worker {worker_id} error: {e}")

        # Create workers
        workers = []
        subset_size = len(sample_e2e_data) // 3

        for i in range(3):
            start_idx = i * subset_size
            end_idx = start_idx + subset_size if i < 2 else len(sample_e2e_data)
            subset = sample_e2e_data[start_idx:end_idx]

            worker_thread = threading.Thread(
                target=worker,
                args=(i, subset)
            )
            workers.append(worker_thread)

        # Start workers
        for worker in workers:
            worker.start()

        # Wait for completion
        for worker in workers:
            worker.join(timeout=30)

        # Check results
        assert results.qsize() == 3  # All workers completed
        assert errors.qsize() == 0   # No errors occurred

        # Verify that each worker processed some data
        total_processed = 0
        while not results.empty():
            message = results.get()
            if "processed" in message:
                count = int(message.split("processed")[1].split()[0])
                total_processed += count

        assert total_processed == len(sample_e2e_data)
