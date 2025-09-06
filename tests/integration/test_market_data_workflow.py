"""Integration tests for Market Data workflow using TDD approach."""

import pytest
import tempfile
import os
from datetime import datetime
from decimal import Decimal

from src.domain.entities.market_data import (
    OHLCV,
    MarketData,
    MarketDataBatch
)
from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter


class TestMarketDataWorkflow:
    """Integration tests for complete market data workflow."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database for integration testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def db_adapter(self, temp_db_path):
        """Create a DuckDB adapter for testing."""
        return DuckDBAdapter(database_path=temp_db_path)

    @pytest.fixture
    def sample_market_data_batch(self):
        """Create a batch of sample market data for testing."""
        # Create multiple market data points
        timestamps = [
            datetime(2025, 1, 15, 10, 0, 0),
            datetime(2025, 1, 15, 11, 0, 0),
            datetime(2025, 1, 15, 12, 0, 0),
            datetime(2025, 1, 15, 13, 0, 0),
            datetime(2025, 1, 15, 14, 0, 0)
        ]

        market_data_list = []
        for i, ts in enumerate(timestamps):
            # Create realistic OHLCV data with some variation
            base_price = Decimal("100.00") + Decimal(str(i))
            ohlcv = OHLCV(
                open=base_price,
                high=base_price + Decimal("2.50"),
                low=base_price - Decimal("1.25"),
                close=base_price + Decimal("1.75"),
                volume=1000 + (i * 100)
            )

            market_data = MarketData(
                symbol="AAPL",
                timestamp=ts,
                timeframe="1H",
                ohlcv=ohlcv,
                date_partition="2025-01-15"
            )
            market_data_list.append(market_data)

        return MarketDataBatch(
            symbol="AAPL",
            timeframe="1H",
            data=market_data_list,
            start_date=market_data_list[0].timestamp,
            end_date=market_data_list[-1].timestamp
        )

    def test_market_data_persistence_workflow(self, db_adapter, sample_market_data_batch):
        """Test the complete workflow of persisting market data."""
        # Step 1: Clear existing data for clean test
        db_adapter.execute_query("DELETE FROM market_data")

        # Step 2: Insert market data batch using correct column names
        for market_data in sample_market_data_batch.data:
            insert_query = f"""
            INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
            VALUES (
                '{market_data.symbol}',
                '{market_data.timestamp.isoformat()}',
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
        assert result.iloc[0]['count'] == len(sample_market_data_batch.data)

        # Step 4: Query and verify data integrity
        result = db_adapter.execute_query("""
        SELECT * FROM market_data
        WHERE symbol = 'AAPL'
        ORDER BY timestamp
        """)

        assert len(result) == 5

        # Verify first record
        first_record = result.iloc[0]
        first_original = sample_market_data_batch.data[0]

        assert first_record['symbol'] == first_original.symbol
        assert first_record['timeframe'] == first_original.timeframe
        assert first_record['open'] == float(first_original.ohlcv.open)
        assert first_record['close'] == float(first_original.ohlcv.close)
        assert first_record['volume'] == first_original.ohlcv.volume

    def test_market_data_aggregation_workflow(self, db_adapter, sample_market_data_batch):
        """Test market data aggregation workflow."""
        # Setup: Insert sample data
        db_adapter.execute_query("""
        -- Table already exists from schema initialization
        -- Clear existing data for clean test
        DELETE FROM market_data
        """)

        for market_data in sample_market_data_batch.data:
            insert_query = f"""
            INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
            VALUES (
                '{market_data.symbol}',
                '{market_data.timestamp.isoformat()}',
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

        # Test aggregation queries
        # Daily OHLC aggregation
        daily_ohlc = db_adapter.execute_query("""
        SELECT
            symbol,
            date_partition,
            MIN(low) as daily_low,
            MAX(high) as daily_high,
            FIRST(open) as daily_open,
            LAST(close) as daily_close,
            SUM(volume) as total_volume
        FROM market_data
        WHERE symbol = 'AAPL' AND date_partition = '2025-01-15'
        GROUP BY symbol, date_partition
        """)

        assert len(daily_ohlc) == 1
        daily = daily_ohlc.iloc[0]

        assert daily['symbol'] == 'AAPL'
        assert str(daily['date_partition'].date()) == '2025-01-15'
        assert daily['total_volume'] == sum(md.ohlcv.volume for md in sample_market_data_batch.data)

        # Verify OHLC calculations
        expected_low = min(float(md.ohlcv.low) for md in sample_market_data_batch.data)
        expected_high = max(float(md.ohlcv.high) for md in sample_market_data_batch.data)

        assert daily['daily_low'] == expected_low
        assert daily['daily_high'] == expected_high
        assert daily['daily_open'] == float(sample_market_data_batch.data[0].ohlcv.open)
        assert daily['daily_close'] == float(sample_market_data_batch.data[-1].ohlcv.close)

    def test_market_data_filtering_workflow(self, db_adapter, sample_market_data_batch):
        """Test market data filtering and querying workflow."""
        # Setup: Insert sample data
        db_adapter.execute_query("""
        -- Table already exists from schema initialization
        -- Clear existing data for clean test
        DELETE FROM market_data
        """)

        for market_data in sample_market_data_batch.data:
            insert_query = f"""
            INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
            VALUES (
                '{market_data.symbol}',
                '{market_data.timestamp.isoformat()}',
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

        # Test time range filtering
        time_filtered = db_adapter.execute_query("""
        SELECT * FROM market_data
        WHERE timestamp >= '2025-01-15 11:00:00'
        AND timestamp <= '2025-01-15 13:00:00'
        ORDER BY timestamp
        """)

        assert len(time_filtered) == 3  # Records from 11:00, 12:00, 13:00

        # Test volume filtering
        high_volume = db_adapter.execute_query("""
        SELECT * FROM market_data
        WHERE volume > 1200
        ORDER BY volume DESC
        """)

        assert len(high_volume) == 2  # Last two records have volume > 1200

        # Test price range filtering
        price_range = db_adapter.execute_query("""
        SELECT * FROM market_data
        WHERE close BETWEEN 102.00 AND 106.00
        """)

        # Should include records where close price is in range
        assert len(price_range) >= 1

    def test_market_data_validation_workflow(self, db_adapter):
        """Test market data validation during persistence."""
        # Clear existing data for clean test
        db_adapter.execute_query("DELETE FROM market_data")

        # Test valid data insertion
        valid_data = MarketData(
            symbol="AAPL",
            timestamp=datetime(2025, 1, 15, 10, 30, 0),
            timeframe="1H",
            ohlcv=OHLCV(
                open=Decimal("100.50"),
                high=Decimal("105.25"),
                low=Decimal("99.75"),
                close=Decimal("104.00"),
                volume=1000
            ),
            date_partition="2025-01-15"
        )

        insert_query = f"""
        INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
        VALUES (
            '{valid_data.symbol}',
            '{valid_data.timestamp.isoformat()}',
            '{valid_data.timeframe}',
            {valid_data.ohlcv.open},
            {valid_data.ohlcv.high},
            {valid_data.ohlcv.low},
            {valid_data.ohlcv.close},
            {valid_data.ohlcv.volume},
            '{valid_data.date_partition}'
        )
        """

        db_adapter.execute_query(insert_query)

        # Verify insertion
        result = db_adapter.execute_query("SELECT COUNT(*) as count FROM market_data")
        assert result.iloc[0]['count'] == 1

        # Test invalid data (negative price) - should fail
        with pytest.raises(Exception):
            invalid_insert = """
            INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
            VALUES (
                'AAPL',
                '2025-01-15 10:30:00',
                '1H',
                -100.50,  -- Negative price should fail
                105.25,
                99.75,
                104.00,
                1000,
                '2025-01-15'
            )
            """
            db_adapter.execute_query(invalid_insert)

    def test_market_data_performance_workflow(self, db_adapter):
        """Test market data performance with larger datasets."""
        # Use existing market_data table
        db_adapter.execute_query("DELETE FROM market_data")

        # Generate larger dataset (100 records)
        import random

        records = []
        base_time = datetime(2025, 1, 15, 9, 30, 0)

        for i in range(100):
            # Generate unique timestamps by using seconds as well
            hour = 9 + (i // 60)  # Change every 60 records
            minute = (i // 6) % 10  # 0-9 minutes
            second = (i % 6) * 10   # 0, 10, 20, 30, 40, 50 seconds
            if hour >= 24:
                hour = 23
            timestamp = base_time.replace(hour=hour, minute=minute, second=second)
            open_price = Decimal(str(100 + random.uniform(-5, 5)))
            high_price = open_price + Decimal(str(random.uniform(0.5, 3)))
            low_price = open_price - Decimal(str(random.uniform(0.5, 2)))
            close_price = Decimal(str(random.uniform(float(low_price), float(high_price))))
            volume = random.randint(500, 2000)

            records.append((
                'AAPL',
                timestamp.isoformat(),
                open_price,
                high_price,
                low_price,
                close_price,
                volume
            ))

        # Bulk insert
        bulk_insert_query = f"""
        INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
        VALUES
        {','.join([f"('{record[0]}', '{record[1]}', '1H', {record[2]}, {record[3]}, {record[4]}, {record[5]}, {record[6]}, '2025-01-15')" for record in records])}
        """

        db_adapter.execute_query(bulk_insert_query)

        # Verify bulk insert
        result = db_adapter.execute_query("SELECT COUNT(*) as count FROM market_data")
        assert result.iloc[0]['count'] == 100

        # Test performance query
        performance_result = db_adapter.execute_query("""
        SELECT
            symbol,
            COUNT(*) as total_records,
            AVG(close) as avg_close,
            MAX(high) as max_high,
            MIN(low) as min_low,
            SUM(volume) as total_volume
        FROM market_data
        GROUP BY symbol
        """)

        assert len(performance_result) == 1
        perf_data = performance_result.iloc[0]

        assert perf_data['total_records'] == 100
        assert perf_data['symbol'] == 'AAPL'
        assert perf_data['total_volume'] > 0
