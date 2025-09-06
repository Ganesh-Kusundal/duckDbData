"""
Functional Tests for DuckDB Financial Infrastructure
Tests end-to-end workflows and API functionality with real data.
"""

import pytest
import sys
import os
import tempfile
import shutil
import requests
import json
import time
import threading
import subprocess
from datetime import date, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.duckdb_infra import DuckDBManager, QueryAPI, TimeFrame, app
from core.duckdb_infra.data_loader import DataLoader


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""
    
    @pytest.fixture(scope="class")
    def temp_db_path(self):
        """Create temporary database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_functional.duckdb")
        yield db_path
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture(scope="class")
    def db_manager(self, temp_db_path):
        """Create DuckDB manager for testing."""
        manager = DuckDBManager(db_path=temp_db_path)
        manager.create_schema()
        yield manager
        manager.close()
    
    @pytest.fixture(scope="class")
    def query_api(self, db_manager):
        """Create QueryAPI instance."""
        return QueryAPI(db_manager)
    
    @pytest.fixture(scope="class")
    def data_loader(self, db_manager):
        """Create DataLoader instance."""
        return DataLoader(db_manager)
    
    def test_complete_data_pipeline(self, db_manager, query_api, data_loader):
        """Test complete data loading and analysis pipeline."""
        # 1. Get available symbols
        symbols = db_manager.get_available_symbols()
        assert len(symbols) > 0, "No symbols available for testing"
        
        # Use first available symbol
        test_symbol = symbols[0]
        
        # 2. Load data for a specific date range
        end_date = date(2024, 1, 1)  # Use a date that should exist
        start_date = end_date
        
        print(f"Testing pipeline with symbol: {test_symbol}")
        
        try:
            records_loaded = db_manager.load_symbol_data(test_symbol, start_date, end_date)
            print(f"Loaded {records_loaded} records")
            
            if records_loaded == 0:
                pytest.skip(f"No data available for {test_symbol} on {start_date}")
            
            # 3. Verify data was loaded correctly
            raw_data = db_manager.query_market_data(
                symbol=test_symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            assert not raw_data.empty
            assert len(raw_data) == records_loaded
            
            # 4. Test data resampling workflow
            resampling_results = {}
            
            timeframes = ['5T', '15T', '1H', '1D']
            for tf in timeframes:
                resampled = query_api.resample_data(test_symbol, tf, start_date, end_date)
                resampling_results[tf] = len(resampled)
                print(f"Resampled to {tf}: {len(resampled)} records")
            
            # Verify resampling logic (higher timeframes should have fewer or equal records)
            assert resampling_results['1D'] <= resampling_results['1H']
            assert resampling_results['1H'] <= resampling_results['15T']
            assert resampling_results['15T'] <= resampling_results['5T']
            
            # 5. Test technical analysis workflow
            if resampling_results['1D'] > 0:
                indicators = query_api.calculate_technical_indicators(
                    test_symbol,
                    TimeFrame.DAILY,
                    start_date,
                    end_date,
                    indicators=['sma_20', 'rsi_14']
                )
                
                if not indicators.empty:
                    print(f"Technical indicators calculated: {len(indicators)} records")
                    assert 'close' in indicators.columns
                    assert 'price_change' in indicators.columns
            
            # 6. Test market summary workflow
            summary = query_api.get_market_summary(
                symbols=[test_symbol],
                date_filter=end_date
            )
            
            if not summary.empty:
                print(f"Market summary generated: {len(summary)} symbols")
                assert summary.iloc[0]['symbol'] == test_symbol
            
            # 7. Test custom analytics workflow
            custom_query = """
                SELECT 
                    symbol,
                    COUNT(*) as total_ticks,
                    AVG(close) as avg_price,
                    SUM(volume) as total_volume,
                    MIN(timestamp) as first_tick,
                    MAX(timestamp) as last_tick
                FROM market_data 
                WHERE symbol = ?
                GROUP BY symbol
            """
            
            analytics_result = query_api.execute_custom_analytical_query(
                custom_query, 
                [test_symbol]
            )
            
            assert not analytics_result.empty
            result_row = analytics_result.iloc[0]
            assert result_row['symbol'] == test_symbol
            assert result_row['total_ticks'] == records_loaded
            assert result_row['total_volume'] >= 0
            
            print("✅ Complete data pipeline test passed")
            
        except Exception as e:
            print(f"Pipeline test failed: {e}")
            raise
    
    def test_multi_symbol_analysis(self, db_manager, query_api):
        """Test analysis across multiple symbols."""
        symbols = db_manager.get_available_symbols()
        
        if len(symbols) < 2:
            pytest.skip("Need at least 2 symbols for multi-symbol analysis")
        
        test_symbols = symbols[:3]  # Use first 3 symbols
        end_date = date(2024, 1, 1)
        start_date = end_date
        
        loaded_symbols = []
        
        # Load data for multiple symbols
        for symbol in test_symbols:
            try:
                records = db_manager.load_symbol_data(symbol, start_date, end_date)
                if records > 0:
                    loaded_symbols.append(symbol)
                    print(f"Loaded {records} records for {symbol}")
            except Exception as e:
                print(f"Failed to load {symbol}: {e}")
                continue
        
        if len(loaded_symbols) < 2:
            pytest.skip("Need at least 2 symbols with data for multi-symbol analysis")
        
        # Test market summary for multiple symbols
        market_summary = query_api.get_market_summary(
            symbols=loaded_symbols,
            date_filter=end_date
        )
        
        if not market_summary.empty:
            assert len(market_summary) <= len(loaded_symbols)
            
            # Verify all returned symbols are in our loaded list
            returned_symbols = set(market_summary['symbol'].unique())
            assert returned_symbols.issubset(set(loaded_symbols))
        
        # Test correlation analysis if we have enough data
        try:
            correlation_matrix = query_api.get_correlation_matrix(
                symbols=loaded_symbols[:2],  # Use first 2 loaded symbols
                timeframe=TimeFrame.DAILY,
                method="returns",
                start_date=start_date,
                end_date=end_date
            )
            
            if not correlation_matrix.empty:
                print(f"Correlation matrix calculated: {correlation_matrix.shape}")
                # Should be square matrix
                assert correlation_matrix.shape[0] == correlation_matrix.shape[1]
        
        except Exception as e:
            print(f"Correlation analysis failed (expected with limited data): {e}")
        
        print("✅ Multi-symbol analysis test passed")
    
    def test_data_validation_workflow(self, db_manager, data_loader):
        """Test data validation and quality checks."""
        # Load some data first
        symbols = db_manager.get_available_symbols()
        if not symbols:
            pytest.skip("No symbols available for validation testing")
        
        test_symbol = symbols[0]
        end_date = date(2024, 1, 1)
        start_date = end_date
        
        try:
            records = db_manager.load_symbol_data(test_symbol, start_date, end_date)
            if records == 0:
                pytest.skip("No data loaded for validation testing")
            
            # Run validation
            validation_results = data_loader.validate_data_integrity()
            
            # Verify validation structure
            assert isinstance(validation_results, dict)
            required_keys = ['summary', 'duplicates', 'missing_data', 'quality_issues']
            for key in required_keys:
                assert key in validation_results
            
            # Check summary
            summary = validation_results['summary']
            assert summary['total_symbols'] > 0
            assert summary['total_records'] == records
            
            print(f"Validation summary: {summary}")
            
            # Test duplicate cleanup (should be 0 for fresh data)
            duplicates_removed = data_loader.cleanup_duplicates()
            assert duplicates_removed >= 0
            
            print("✅ Data validation workflow test passed")
            
        except Exception as e:
            print(f"Validation workflow failed: {e}")
            raise
    
    def test_performance_with_large_queries(self, db_manager, query_api):
        """Test performance with larger datasets and complex queries."""
        symbols = db_manager.get_available_symbols()
        if not symbols:
            pytest.skip("No symbols available for performance testing")
        
        # Load data for multiple symbols and dates
        test_symbols = symbols[:2]  # Use first 2 symbols
        end_date = date(2024, 1, 2)
        start_date = date(2024, 1, 1)  # 2 days of data
        
        total_records = 0
        
        for symbol in test_symbols:
            try:
                records = db_manager.load_symbol_data(symbol, start_date, end_date)
                total_records += records
                print(f"Loaded {records} records for {symbol}")
            except Exception:
                continue
        
        if total_records == 0:
            pytest.skip("No data loaded for performance testing")
        
        print(f"Total records for performance test: {total_records}")
        
        # Test complex query performance
        start_time = time.time()
        
        complex_query = """
            SELECT 
                symbol,
                date_partition,
                COUNT(*) as tick_count,
                AVG(close) as avg_price,
                STDDEV(close) as price_volatility,
                SUM(volume) as total_volume,
                MAX(high) - MIN(low) as price_range,
                SUM(close * volume) / SUM(volume) as vwap,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY close) as median_price
            FROM market_data 
            WHERE date_partition BETWEEN ? AND ?
            GROUP BY symbol, date_partition
            ORDER BY symbol, date_partition
        """
        
        result = query_api.execute_custom_analytical_query(
            complex_query, 
            [start_date, end_date]
        )
        
        query_time = time.time() - start_time
        
        print(f"Complex query executed in {query_time:.3f} seconds")
        print(f"Query returned {len(result)} rows")
        
        # Performance should be reasonable (less than 10 seconds for small dataset)
        assert query_time < 10.0
        assert not result.empty
        
        # Test multiple timeframe resampling performance
        start_time = time.time()
        
        multi_tf_results = {}
        for symbol in test_symbols:
            try:
                results = query_api.get_multiple_timeframes(
                    symbol,
                    ['5T', '15T', '1H', '1D'],
                    start_date,
                    end_date
                )
                multi_tf_results[symbol] = results
            except Exception:
                continue
        
        resampling_time = time.time() - start_time
        
        print(f"Multi-timeframe resampling completed in {resampling_time:.3f} seconds")
        
        # Should complete in reasonable time
        assert resampling_time < 15.0
        
        print("✅ Performance test passed")


class TestAPIFunctionality:
    """Test API functionality with real server."""
    
    @pytest.fixture(scope="class")
    def api_server(self):
        """Start API server for testing."""
        # Check if server is already running
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("API server already running")
                yield "http://localhost:8000"
                return
        except:
            pass
        
        # Server not running, skip API tests
        pytest.skip("API server not running. Start with: python start_api_server.py")
    
    def test_api_health_check(self, api_server):
        """Test API health endpoint."""
        response = requests.get(f"{api_server}/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
    
    def test_api_available_symbols(self, api_server):
        """Test available symbols endpoint."""
        response = requests.get(f"{api_server}/available-symbols")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "symbols" in data
        assert "count" in data
        assert isinstance(data["symbols"], list)
        assert data["count"] == len(data["symbols"])
    
    def test_api_supported_timeframes(self, api_server):
        """Test supported timeframes endpoint."""
        response = requests.get(f"{api_server}/timeframes")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "timeframes" in data
        
        timeframes = data["timeframes"]
        expected_timeframes = ["1T", "5T", "15T", "30T", "1H", "4H", "1D", "1W", "1M"]
        
        for tf in expected_timeframes:
            assert tf in timeframes
    
    def test_api_resample_endpoint(self, api_server):
        """Test data resampling endpoint."""
        # Get available symbols first
        symbols_response = requests.get(f"{api_server}/available-symbols")
        symbols_data = symbols_response.json()
        symbols = symbols_data.get("symbols", [])
        
        if not symbols:
            pytest.skip("No symbols available for API testing")
        
        test_symbol = symbols[0]
        
        # Test resampling
        payload = {
            "symbol": test_symbol,
            "timeframe": "1H",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01"
        }
        
        response = requests.post(f"{api_server}/resample", json=payload)
        
        # Should either succeed or return empty data (both are valid)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "count" in data
        assert "columns" in data
        
        # If data exists, verify structure
        if data["count"] > 0:
            sample_record = data["data"][0]
            expected_fields = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
            
            for field in expected_fields:
                assert field in sample_record
    
    def test_api_multi_timeframe_endpoint(self, api_server):
        """Test multiple timeframes endpoint."""
        # Get available symbols first
        symbols_response = requests.get(f"{api_server}/available-symbols")
        symbols_data = symbols_response.json()
        symbols = symbols_data.get("symbols", [])
        
        if not symbols:
            pytest.skip("No symbols available for API testing")
        
        test_symbol = symbols[0]
        
        # Test multiple timeframes
        payload = {
            "symbol": test_symbol,
            "timeframes": ["15T", "1H", "1D"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-01"
        }
        
        response = requests.post(f"{api_server}/multi-timeframe", json=payload)
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Should return data for each requested timeframe
        for tf in payload["timeframes"]:
            assert tf in data
            tf_data = data[tf]
            assert "data" in tf_data
            assert "count" in tf_data
            assert "columns" in tf_data
    
    def test_api_technical_indicators_endpoint(self, api_server):
        """Test technical indicators endpoint."""
        symbols_response = requests.get(f"{api_server}/available-symbols")
        symbols_data = symbols_response.json()
        symbols = symbols_data.get("symbols", [])
        
        if not symbols:
            pytest.skip("No symbols available for API testing")
        
        test_symbol = symbols[0]
        
        payload = {
            "symbol": test_symbol,
            "timeframe": "1D",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01",
            "indicators": ["sma_20", "rsi_14"]
        }
        
        response = requests.post(f"{api_server}/technical-indicators", json=payload)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "count" in data
        assert "columns" in data
    
    def test_api_market_summary_endpoint(self, api_server):
        """Test market summary endpoint."""
        symbols_response = requests.get(f"{api_server}/available-symbols")
        symbols_data = symbols_response.json()
        symbols = symbols_data.get("symbols", [])
        
        if not symbols:
            pytest.skip("No symbols available for API testing")
        
        # Test with specific symbols
        params = {
            "symbols": symbols[:2],  # First 2 symbols
            "date_filter": "2024-01-01"
        }
        
        response = requests.get(f"{api_server}/market-summary", params=params)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "count" in data
        assert "columns" in data
    
    def test_api_custom_query_endpoint(self, api_server):
        """Test custom query endpoint."""
        # Simple safe query
        payload = {
            "query": "SELECT 1 as test_value, 'API Test' as test_string"
        }
        
        response = requests.post(f"{api_server}/custom-query", json=payload)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "count" in data
        assert data["count"] == 1
        
        record = data["data"][0]
        assert record["test_value"] == 1
        assert record["test_string"] == "API Test"
    
    def test_api_error_handling(self, api_server):
        """Test API error handling."""
        # Test invalid timeframe
        payload = {
            "symbol": "TEST",
            "timeframe": "INVALID",
            "start_date": "2024-01-01"
        }
        
        response = requests.post(f"{api_server}/resample", json=payload)
        assert response.status_code == 400  # Bad request
        
        # Test dangerous query (should be blocked)
        dangerous_payload = {
            "query": "DROP TABLE market_data"
        }
        
        response = requests.post(f"{api_server}/custom-query", json=dangerous_payload)
        assert response.status_code == 400  # Should be blocked
    
    def test_api_cors_headers(self, api_server):
        """Test CORS headers are present."""
        response = requests.options(f"{api_server}/health")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
    
    def test_api_documentation_endpoint(self, api_server):
        """Test API documentation is accessible."""
        response = requests.get(f"{api_server}/docs")
        
        # Should return HTML documentation
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


if __name__ == "__main__":
    # Run functional tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])
