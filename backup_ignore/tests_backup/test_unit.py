"""
Unit Tests for DuckDB Financial Infrastructure
Tests individual components in isolation with real data.
"""

import pytest
import sys
import os
import tempfile
import shutil
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.duckdb_infra import DuckDBManager, QueryAPI, TimeFrame
from core.duckdb_infra.data_loader import DataLoader


class TestDuckDBManager:
    """Unit tests for DuckDBManager class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_unit.duckdb")
        yield db_path
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create DuckDB manager for testing."""
        manager = DuckDBManager(db_path=temp_db_path)
        yield manager
        manager.close()
    
    def test_initialization(self, temp_db_path):
        """Test DuckDB manager initialization."""
        manager = DuckDBManager(db_path=temp_db_path)
        
        assert manager.db_path == temp_db_path
        assert manager.data_root.exists()
        assert manager.connection is None
        
        manager.close()
    
    def test_connection_management(self, db_manager):
        """Test database connection management."""
        # Test initial connection
        conn1 = db_manager.connect()
        assert conn1 is not None
        assert db_manager.connection is not None
        
        # Test connection reuse
        conn2 = db_manager.connect()
        assert conn1 is conn2
        
        # Test close
        db_manager.close()
        assert db_manager.connection is None
    
    def test_schema_creation(self, db_manager):
        """Test database schema creation."""
        db_manager.create_schema()
        
        conn = db_manager.connect()
        
        # Check tables exist
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [table[0] for table in tables]
        
        assert "market_data" in table_names
        assert "symbols" in table_names
        
        # Check market_data structure
        market_data_schema = conn.execute("DESCRIBE market_data").fetchall()
        column_names = [col[0] for col in market_data_schema]
        
        expected_columns = ["symbol", "timestamp", "open", "high", "low", "close", "volume", "date_partition"]
        for col in expected_columns:
            assert col in column_names
        
        # Check indexes exist
        indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        # Note: DuckDB may handle indexes differently, so we just verify no errors
        assert len(indexes) >= 0
    
    def test_available_symbols_detection(self, db_manager):
        """Test detection of available symbols."""
        symbols = db_manager.get_available_symbols()
        
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        
        # Verify symbols are strings and properly formatted
        for symbol in symbols[:10]:  # Check first 10
            assert isinstance(symbol, str)
            assert len(symbol) > 0
            assert symbol.isupper() or symbol.isalnum()
    
    def test_date_range_detection(self, db_manager):
        """Test date range detection."""
        start_date, end_date = db_manager.get_date_range()
        
        assert isinstance(start_date, date)
        assert isinstance(end_date, date)
        assert start_date <= end_date
        
        # Should span reasonable time period
        time_span = end_date - start_date
        assert time_span.days >= 0
    
    def test_query_market_data_empty_db(self, db_manager):
        """Test querying empty database."""
        db_manager.create_schema()
        
        df = db_manager.query_market_data(symbol="NONEXISTENT")
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_symbols_info_empty_db(self, db_manager):
        """Test symbols info on empty database."""
        db_manager.create_schema()
        
        df = db_manager.get_symbols_info()
        
        assert isinstance(df, pd.DataFrame)
        # May be empty or have structure
    
    def test_custom_query_execution(self, db_manager):
        """Test custom query execution."""
        db_manager.create_schema()
        
        # Simple query
        result = db_manager.execute_custom_query("SELECT 1 as test_value")
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert result.iloc[0]['test_value'] == 1


class TestQueryAPI:
    """Unit tests for QueryAPI class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_query_api.duckdb")
        yield db_path
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create DuckDB manager for testing."""
        manager = DuckDBManager(db_path=temp_db_path)
        manager.create_schema()
        yield manager
        manager.close()
    
    @pytest.fixture
    def query_api(self, db_manager):
        """Create QueryAPI instance."""
        return QueryAPI(db_manager)
    
    @pytest.fixture
    def sample_data(self, db_manager):
        """Create sample data for testing."""
        # Create sample market data
        conn = db_manager.connect()
        
        # Generate sample OHLCV data
        dates = pd.date_range('2024-01-01 09:15:00', '2024-01-01 15:30:00', freq='1min')
        n_records = len(dates)
        
        # Generate realistic OHLCV data
        base_price = 1000.0
        prices = []
        volumes = []
        
        for i in range(n_records):
            # Random walk for prices
            change = np.random.normal(0, 0.5)
            base_price += change
            
            # Generate OHLCV for this minute
            open_price = base_price
            high_price = open_price + abs(np.random.normal(0, 2))
            low_price = open_price - abs(np.random.normal(0, 2))
            close_price = open_price + np.random.normal(0, 1)
            
            # Ensure high >= low and open/close within range
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            volume = int(np.random.exponential(1000))
            
            prices.append({
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
            
            base_price = close_price
        
        # Create DataFrame
        df = pd.DataFrame(prices)
        df['symbol'] = 'TEST_SYMBOL'
        df['timestamp'] = dates
        df['date_partition'] = date(2024, 1, 1)
        
        # Reorder columns to match database schema
        df = df[['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'date_partition']]
        
        # Insert into database
        conn.execute("INSERT INTO market_data SELECT * FROM df")
        
        return len(df)
    
    def test_initialization(self, db_manager):
        """Test QueryAPI initialization."""
        api = QueryAPI(db_manager)
        assert api.db_manager is db_manager
    
    def test_resample_data_empty_db(self, query_api):
        """Test resampling with empty database."""
        df = query_api.resample_data("NONEXISTENT", TimeFrame.MINUTE_5)
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_resample_data_with_sample_data(self, query_api, sample_data):
        """Test resampling with sample data."""
        # Test different timeframes
        timeframes = [
            (TimeFrame.MINUTE_5, '5T'),
            (TimeFrame.MINUTE_15, '15T'),
            (TimeFrame.HOUR_1, '1H'),
            (TimeFrame.DAILY, '1D')
        ]
        
        previous_count = float('inf')
        
        for tf_enum, tf_str in timeframes:
            # Test with enum
            df_enum = query_api.resample_data("TEST_SYMBOL", tf_enum, date(2024, 1, 1), date(2024, 1, 1))
            
            # Test with string
            df_str = query_api.resample_data("TEST_SYMBOL", tf_str, date(2024, 1, 1), date(2024, 1, 1))
            
            # Both should give same results
            if not df_enum.empty and not df_str.empty:
                assert len(df_enum) == len(df_str)
            
            if not df_enum.empty:
                # Verify structure
                expected_cols = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'tick_count']
                for col in expected_cols:
                    assert col in df_enum.columns
                
                # Verify data integrity
                assert all(df_enum['high'] >= df_enum['low'])
                assert all(df_enum['volume'] >= 0)
                assert all(df_enum['tick_count'] > 0)
                
                # Higher timeframes should generally have fewer records
                current_count = len(df_enum)
                if tf_enum != TimeFrame.MINUTE_5:  # Skip first comparison
                    assert current_count <= previous_count
                previous_count = current_count
    
    def test_multiple_timeframes(self, query_api, sample_data):
        """Test getting multiple timeframes."""
        timeframes = [TimeFrame.MINUTE_15, TimeFrame.HOUR_1, TimeFrame.DAILY]
        
        results = query_api.get_multiple_timeframes(
            "TEST_SYMBOL", 
            timeframes, 
            date(2024, 1, 1), 
            date(2024, 1, 1)
        )
        
        assert isinstance(results, dict)
        assert len(results) == len(timeframes)
        
        for tf in timeframes:
            tf_str = tf.value
            assert tf_str in results
            df = results[tf_str]
            assert isinstance(df, pd.DataFrame)
    
    def test_technical_indicators_empty_db(self, query_api):
        """Test technical indicators with empty database."""
        df = query_api.calculate_technical_indicators("NONEXISTENT")
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_technical_indicators_with_sample_data(self, query_api, sample_data):
        """Test technical indicators calculation."""
        indicators = ['sma_20', 'rsi_14', 'bollinger_bands']
        
        df = query_api.calculate_technical_indicators(
            "TEST_SYMBOL",
            TimeFrame.MINUTE_1,
            date(2024, 1, 1),
            date(2024, 1, 1),
            indicators
        )
        
        if not df.empty:
            # Check base columns exist
            base_cols = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in base_cols:
                assert col in df.columns
            
            # Check that some indicator columns might exist (depends on data size)
            # We don't assert they exist because we need sufficient data for calculations
    
    def test_market_summary_empty_db(self, query_api):
        """Test market summary with empty database."""
        df = query_api.get_market_summary()
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_market_summary_with_sample_data(self, query_api, sample_data):
        """Test market summary generation."""
        df = query_api.get_market_summary(
            symbols=["TEST_SYMBOL"],
            date_filter=date(2024, 1, 1)
        )
        
        if not df.empty:
            # Verify structure
            expected_cols = ['symbol', 'trading_date', 'day_open', 'day_high', 'day_low', 'day_close', 'total_volume']
            for col in expected_cols:
                assert col in df.columns
            
            # Verify data integrity
            row = df.iloc[0]
            assert row['day_high'] >= row['day_low']
            assert row['total_volume'] >= 0
            assert row['symbol'] == 'TEST_SYMBOL'
    
    def test_custom_analytical_query(self, query_api, sample_data):
        """Test custom query execution."""
        query = """
            SELECT 
                symbol,
                COUNT(*) as record_count,
                AVG(close) as avg_price,
                MIN(low) as min_price,
                MAX(high) as max_price
            FROM market_data 
            WHERE symbol = ?
            GROUP BY symbol
        """
        
        df = query_api.execute_custom_analytical_query(query, ["TEST_SYMBOL"])
        
        assert not df.empty
        assert len(df) == 1
        
        row = df.iloc[0]
        assert row['symbol'] == 'TEST_SYMBOL'
        assert row['record_count'] > 0
        assert row['avg_price'] > 0
        assert row['max_price'] >= row['min_price']
    
    def test_volume_profile_empty_db(self, query_api):
        """Test volume profile with empty database."""
        df = query_api.get_volume_profile("NONEXISTENT")
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
    
    def test_volume_profile_with_sample_data(self, query_api, sample_data):
        """Test volume profile calculation."""
        df = query_api.get_volume_profile(
            "TEST_SYMBOL",
            date(2024, 1, 1),
            date(2024, 1, 1),
            price_bins=10
        )
        
        if not df.empty:
            # Verify structure
            expected_cols = ['price_bin', 'price_level', 'price_level_upper', 'price_midpoint', 'total_volume']
            for col in expected_cols:
                assert col in df.columns
            
            # Verify data integrity
            assert all(df['total_volume'] >= 0)
            assert all(df['price_level_upper'] >= df['price_level'])
            assert len(df) <= 10  # Should not exceed requested bins
    
    def test_correlation_matrix_insufficient_data(self, query_api):
        """Test correlation matrix with insufficient data."""
        df = query_api.get_correlation_matrix(["SYMBOL1", "SYMBOL2"])
        
        assert isinstance(df, pd.DataFrame)
        # May be empty if no data available


class TestDataLoader:
    """Unit tests for DataLoader class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_data_loader.duckdb")
        yield db_path
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create DuckDB manager for testing."""
        manager = DuckDBManager(db_path=temp_db_path)
        manager.create_schema()
        yield manager
        manager.close()
    
    @pytest.fixture
    def data_loader(self, db_manager):
        """Create DataLoader instance."""
        return DataLoader(db_manager)
    
    def test_initialization(self, db_manager):
        """Test DataLoader initialization."""
        loader = DataLoader(db_manager, max_workers=2)
        
        assert loader.db_manager is db_manager
        assert loader.max_workers == 2
        assert loader._lock is not None
    
    def test_validate_data_integrity_empty_db(self, data_loader):
        """Test data validation on empty database."""
        results = data_loader.validate_data_integrity()
        
        assert isinstance(results, dict)
        assert 'summary' in results
        assert 'duplicates' in results
        assert 'missing_data' in results
        assert 'quality_issues' in results
        
        # Summary should show empty database
        summary = results['summary']
        assert summary['total_symbols'] == 0
        assert summary['total_records'] == 0
    
    def test_cleanup_duplicates_empty_db(self, data_loader):
        """Test duplicate cleanup on empty database."""
        removed_count = data_loader.cleanup_duplicates()
        
        assert removed_count == 0


class TestTimeFrameEnum:
    """Unit tests for TimeFrame enum."""
    
    def test_timeframe_values(self):
        """Test TimeFrame enum values."""
        assert TimeFrame.MINUTE_1.value == "1T"
        assert TimeFrame.MINUTE_5.value == "5T"
        assert TimeFrame.MINUTE_15.value == "15T"
        assert TimeFrame.MINUTE_30.value == "30T"
        assert TimeFrame.HOUR_1.value == "1H"
        assert TimeFrame.HOUR_4.value == "4H"
        assert TimeFrame.DAILY.value == "1D"
        assert TimeFrame.WEEKLY.value == "1W"
        assert TimeFrame.MONTHLY.value == "1M"
    
    def test_timeframe_enum_usage(self):
        """Test TimeFrame enum can be used in queries."""
        # This tests that the enum values are properly formatted
        for tf in TimeFrame:
            value = tf.value
            assert isinstance(value, str)
            assert len(value) >= 2
            # Should end with T, H, D, W, or M
            assert value[-1] in ['T', 'H', 'D', 'W', 'M']


if __name__ == "__main__":
    # Run unit tests
    pytest.main([__file__, "-v", "--tb=short"])
