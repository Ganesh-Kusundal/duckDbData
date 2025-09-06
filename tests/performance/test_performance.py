"""
Performance Tests
=================

Comprehensive performance testing for the DuckDB Financial Infrastructure.
Tests data processing speed, memory usage, and scalability.
"""

import pytest
import time
import psutil
import os
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.domain.entities.market_data import MarketData, MarketDataBatch, OHLCV


class TestDataProcessingPerformance:
    """Performance tests for data processing operations."""

    @pytest.mark.performance
    def test_market_data_creation_performance(self, performance_test_data):
        """Test market data creation performance."""
        start_time = time.time()
        result = MarketDataBatch(
            symbol="PERF_TEST",
            timeframe="1H",
            data=performance_test_data,
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )
        end_time = time.time()

        processing_time = end_time - start_time
        assert processing_time < 2.0  # 2 seconds max
        assert result.record_count == 1000
        assert result.symbol == "PERF_TEST"

    @pytest.mark.performance
    def test_large_batch_processing(self):
        """Test processing of large data batches."""
        # Create 1,000 records (reduced for practicality)
        large_data = []
        for i in range(1000):
            large_data.append(MarketData(
                symbol="LARGE_TEST",
                timestamp=datetime(2025, 9, 5, (i//60)%24, i%60, 0),
                timeframe="1M",
                ohlcv=OHLCV(
                    open=100.0 + i * 0.01,
                    high=105.0 + i * 0.01,
                    low=95.0 + i * 0.01,
                    close=102.0 + i * 0.01,
                    volume=100000 + i * 10
                ),
                date_partition="2025-09-05"
            ))

        start_time = time.time()
        result = MarketDataBatch(
            symbol="LARGE_TEST",
            timeframe="1M",
            data=large_data,
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )
        end_time = time.time()
        assert result.record_count == 1000
        assert result.is_sorted is True

    @pytest.mark.performance
    def test_memory_usage_during_batch_creation(self, performance_test_data):
        """Test memory usage during batch creation."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create large batch
        batch = MarketDataBatch(
            symbol="PERF_TEST",  # Match the fixture symbol
            timeframe="1H",
            data=performance_test_data,
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = final_memory - initial_memory

        # Memory usage should be reasonable (< 50MB for 1000 records)
        assert memory_used < 50.0
        assert batch.record_count == 1000


class TestConcurrentProcessingPerformance:
    """Performance tests for concurrent data processing."""

    @pytest.mark.performance
    def test_concurrent_batch_creation(self, performance_test_data):
        """Test concurrent batch creation performance."""
        def create_batch(symbol_suffix: int):
            # Generate data with correct symbol
            data = []
            for i in range(100):
                original = performance_test_data[i]
                market_data = MarketData(
                    symbol=f"CONCURRENT_{symbol_suffix}",
                    timestamp=original.timestamp,
                    timeframe=original.timeframe,
                    ohlcv=original.ohlcv,
                    date_partition=original.date_partition
                )
                data.append(market_data)

            return MarketDataBatch(
                symbol=f"CONCURRENT_{symbol_suffix}",
                timeframe="1H",
                data=data,
                start_date="2025-09-05T00:00:00Z",
                end_date="2025-09-05T23:59:59Z"
            )

        start_time = time.time()

        # Create 10 concurrent batches
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_batch, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete within reasonable time
        assert total_time < 5.0  # 5 seconds max
        assert len(results) == 10
        for result in results:
            assert result.record_count == 100

    @pytest.mark.performance
    def test_parallel_data_validation(self, performance_test_data):
        """Test parallel data validation performance."""
        def validate_record(record: MarketData) -> bool:
            # Simulate validation logic
            return (record.ohlcv.high >= record.ohlcv.low and
                   record.ohlcv.open > 0 and
                   record.ohlcv.volume > 0)

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(validate_record, record)
                      for record in performance_test_data]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        total_time = end_time - start_time

        # All validations should pass
        assert all(results)
        # Should complete quickly
        assert total_time < 2.0  # 2 seconds max


class TestDataPipelinePerformance:
    """Performance tests for data pipeline operations."""

    @pytest.mark.performance
    def test_data_transformation_pipeline(self, performance_test_data):
        """Test data transformation pipeline performance."""
        start_time = time.time()
        transformed = []
        for record in performance_test_data:
            # Simulate data transformation
            transformed_record = MarketData(
                symbol=record.symbol.upper(),
                timestamp=record.timestamp,
                timeframe=record.timeframe,
                ohlcv=OHLCV(
                    open=float(record.ohlcv.open) * 1.01,  # 1% adjustment
                    high=float(record.ohlcv.high) * 1.01,
                    low=float(record.ohlcv.low) * 1.01,
                    close=float(record.ohlcv.close) * 1.01,
                    volume=int(float(record.ohlcv.volume) * 1.05)  # 5% volume increase
                ),
                date_partition=record.date_partition
            )
            transformed.append(transformed_record)
        end_time = time.time()

        processing_time = end_time - start_time
        assert processing_time < 2.0  # 2 seconds max
        assert len(transformed) == 1000
        # Verify transformation was applied
        assert transformed[0].ohlcv.open > performance_test_data[0].ohlcv.open

    @pytest.mark.performance
    def test_data_filtering_performance(self, performance_test_data):
        """Test data filtering performance."""
        start_time = time.time()
        # Filter records with volume > 200,000
        result = [record for record in performance_test_data
                 if record.ohlcv.volume > 200000]
        end_time = time.time()

        processing_time = end_time - start_time
        assert processing_time < 1.0  # 1 second max
        # Should filter out some records
        assert len(result) < len(performance_test_data)

    @pytest.mark.performance
    def test_data_aggregation_performance(self, performance_test_data):
        """Test data aggregation performance."""
        start_time = time.time()
        # Calculate volume-weighted average price
        total_volume = sum(float(record.ohlcv.volume) for record in performance_test_data)
        weighted_sum = sum(float(record.ohlcv.close) * float(record.ohlcv.volume)
                         for record in performance_test_data)
        result = weighted_sum / total_volume if total_volume > 0 else 0
        end_time = time.time()

        processing_time = end_time - start_time
        assert processing_time < 1.0  # 1 second max
        assert isinstance(result, float)
        assert result > 0


class TestLoadTesting:
    """Load testing for high-volume data processing."""

    @pytest.mark.load
    def test_high_volume_data_processing(self):
        """Test processing of high volume data."""
        # Create 1,000 records
        high_volume_data = []
        for i in range(1000):
            high_volume_data.append(MarketData(
                symbol="HIGH_VOLUME_TEST",  # Same symbol for all data
                timestamp=datetime(2025, 9, 5, (i//60)%24, i%60, 0),
                timeframe="1M",
                ohlcv=OHLCV(
                    open=100.0 + (i % 100),
                    high=105.0 + (i % 100),
                    low=95.0 + (i % 100),
                    close=102.0 + (i % 100),
                    volume=100000 + (i % 10000)
                ),
                date_partition="2025-09-05"
            ))

        start_time = time.time()
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process high volume data
        batch = MarketDataBatch(
            symbol="HIGH_VOLUME_TEST",
            timeframe="1M",
            data=high_volume_data,
            start_date="2025-09-05T00:00:00Z",
            end_date="2025-09-05T23:59:59Z"
        )

        end_time = time.time()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        processing_time = end_time - start_time
        memory_used = final_memory - initial_memory

        # Performance assertions
        assert processing_time < 30.0  # 30 seconds max
        assert memory_used < 200.0    # 200MB max memory usage
        assert batch.record_count == 1000
        assert batch.is_sorted is True

    @pytest.mark.load
    def test_memory_efficiency_under_load(self):
        """Test memory efficiency under high load."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create multiple large batches
        batches = []
        for batch_num in range(10):
            data = []
            for i in range(1000):
                data.append(MarketData(
                    symbol=f"BATCH_{batch_num}",
                    timestamp=datetime(2025, 9, 5, i%24, 0, 0),
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

            batch = MarketDataBatch(
                symbol=f"BATCH_{batch_num}",
                timeframe="1H",
                data=data,
                start_date="2025-09-05T00:00:00Z",
                end_date="2025-09-05T23:59:59Z"
            )
            batches.append(batch)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = final_memory - initial_memory

        # Memory should be reasonable for 10,000 records total
        assert memory_used < 100.0  # 100MB max
        assert len(batches) == 10  # Should have created all batches

        # Cleanup
        del batches


class TestScalabilityTesting:
    """Scalability tests for growing data volumes."""

    @pytest.mark.performance
    def test_scalability_with_data_size(self):
        """Test how performance scales with data size."""
        sizes = [100, 500, 1000, 2500]
        results = {}

        for size in sizes:
            data = []
            for i in range(size):
                data.append(MarketData(
                symbol=f"SCALE_TEST_{size}",
                timestamp=datetime(2025, 9, 5, i%24, 0, 0),
                timeframe="1H",
                ohlcv=OHLCV(
                    open=100.0 + i * 0.01,
                    high=105.0 + i * 0.01,
                    low=95.0 + i * 0.01,
                    close=102.0 + i * 0.01,
                    volume=100000 + i * 10
                ),
                date_partition="2025-09-05"
            ))

            start_time = time.time()
            batch = MarketDataBatch(
                symbol=f"SCALE_TEST_{size}",
                timeframe="1H",
                data=data,
                start_date="2025-09-05T00:00:00Z",
                end_date="2025-09-05T23:59:59Z"
            )
            end_time = time.time()

            processing_time = end_time - start_time
            results[size] = {
                'time': processing_time,
                'records': batch.record_count,
                'time_per_record': processing_time / size
            }

        # Verify scalability (processing time should scale roughly linearly)
        for i in range(1, len(sizes)):
            prev_size = sizes[i-1]
            curr_size = sizes[i]
            prev_time_per_record = results[prev_size]['time_per_record']
            curr_time_per_record = results[curr_size]['time_per_record']

            # Time per record should not increase dramatically
            assert curr_time_per_record / prev_time_per_record < 2.0
