"""
Unit tests for UnifiedDuckDBScannerReadAdapter.

Tests the unified scanner read adapter's integration with the unified DuckDB layer,
including caching, error handling, and performance optimizations.
"""

import pytest
from datetime import date, time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from src.infrastructure.adapters.scanner_read_adapter import DuckDBScannerReadAdapter
from src.infrastructure.database.unified_duckdb import UnifiedDuckDBManager, DuckDBConfig


class TestDuckDBScannerReadAdapter:
    """Test suite for unified scanner read adapter."""

    @pytest.fixture
    def mock_unified_manager(self):
        """Create a mock unified manager for testing."""
        manager = Mock(spec=UnifiedDuckDBManager)

        # Mock analytics_query method
        manager.analytics_query = Mock()

        # Mock persistence_query method
        manager.persistence_query = Mock()

        return manager

    @pytest.fixture
    def adapter(self, mock_unified_manager):
        """Create adapter instance with mock unified manager."""
        return DuckDBScannerReadAdapter(
            unified_manager=mock_unified_manager,
            enable_cache=True,
            cache_ttl=300
        )

    @pytest.fixture
    def adapter_no_cache(self, mock_unified_manager):
        """Create adapter instance without caching."""
        return DuckDBScannerReadAdapter(
            unified_manager=mock_unified_manager,
            enable_cache=False
        )

    @pytest.fixture
    def sample_crp_config(self):
        """Sample CRP scanner configuration."""
        return {
            'close_threshold_pct': 2.0,
            'range_threshold_pct': 3.0,
            'min_price': 50,
            'max_price': 2000,
            'min_volume': 50000,
            'max_volume': 5000000
        }

    @pytest.fixture
    def sample_breakout_config(self):
        """Sample breakout scanner configuration."""
        return {
            'min_price': 50,
            'max_price': 2000,
            'volume_threshold': 10000
        }

    def test_initialization(self, mock_unified_manager):
        """Test adapter initialization with different configurations."""
        # Test with caching enabled
        adapter = DuckDBScannerReadAdapter(unified_manager=mock_unified_manager, enable_cache=True)
        assert adapter.enable_cache is True
        assert adapter.cache_ttl == 300  # default
        assert adapter._cache == {}

        # Test with caching disabled
        adapter_no_cache = DuckDBScannerReadAdapter(unified_manager=mock_unified_manager, enable_cache=False)
        assert adapter_no_cache.enable_cache is False
        assert adapter_no_cache._cache is None

        # Test with custom TTL
        adapter_custom_ttl = DuckDBScannerReadAdapter(
            unified_manager=mock_unified_manager,
            enable_cache=True,
            cache_ttl=600
        )
        assert adapter_custom_ttl.cache_ttl == 600

    def test_get_crp_candidates_success(self, adapter, mock_unified_manager, sample_crp_config):
        """Test successful CRP candidates retrieval."""
        # Mock DataFrame result
        mock_df = Mock()
        mock_df.empty = False
        mock_df.iterrows.return_value = [
            (0, Mock(
                get=lambda key, default=0: {
                    'symbol': 'TEST1',
                    'crp_price': 100.0,
                    'open_price': 98.0,
                    'current_high': 102.0,
                    'current_low': 97.0,
                    'current_volume': 100000,
                    'current_range_pct': 5.0,
                    'close_score': 0.4,
                    'range_score': 0.3,
                    'volume_score': 0.2,
                    'momentum_score': 0.1,
                    'crp_probability_score': 85.0,
                    'close_position': 'Near High'
                }.get(key, default)
            ))
        ]

        mock_unified_manager.analytics_query.return_value = mock_df

        scan_date = date.today()
        cutoff_time = time(9, 50)
        max_results = 5

        results = adapter.get_crp_candidates(scan_date, cutoff_time, sample_crp_config, max_results)

        # Verify query was called
        mock_unified_manager.analytics_query.assert_called_once()

        # Verify results structure
        assert len(results) == 1
        assert results[0]['symbol'] == 'TEST1'
        assert results[0]['crp_probability_score'] == 85.0

        # Verify result is cached
        cache_key = adapter._get_cache_key("crp_candidates", scan_date, cutoff_time, str(sample_crp_config), max_results)
        assert cache_key in adapter._cache

    def test_get_crp_candidates_empty_results(self, adapter, mock_unified_manager, sample_crp_config):
        """Test CRP candidates with empty results."""
        mock_df = Mock()
        mock_df.empty = True

        mock_unified_manager.analytics_query.return_value = mock_df

        scan_date = date.today()
        cutoff_time = time(9, 50)
        max_results = 5

        results = adapter.get_crp_candidates(scan_date, cutoff_time, sample_crp_config, max_results)

        assert results == []

    def test_get_crp_candidates_cache_hit(self, adapter, mock_unified_manager, sample_crp_config):
        """Test CRP candidates cache hit."""
        # Set up cache
        scan_date = date.today()
        cutoff_time = time(9, 50)
        max_results = 5
        cache_key = adapter._get_cache_key("crp_candidates", scan_date, cutoff_time, str(sample_crp_config), max_results)

        cached_results = [{'symbol': 'CACHED', 'crp_probability_score': 90.0}]
        import time as time_module
        future_timestamp = time_module.time() + 100  # 100 seconds in the future
        adapter._cache[cache_key] = (future_timestamp, cached_results)

        results = adapter.get_crp_candidates(scan_date, cutoff_time, sample_crp_config, max_results)

        # Verify cached result returned
        assert results == cached_results

        # Verify unified manager was not called
        mock_unified_manager.analytics_query.assert_not_called()

    def test_get_crp_candidates_error_handling(self, adapter, mock_unified_manager, sample_crp_config):
        """Test CRP candidates error handling."""
        mock_unified_manager.analytics_query.side_effect = Exception("Database error")

        scan_date = date.today()
        cutoff_time = time(9, 50)
        max_results = 5

        with pytest.raises(Exception, match="Database error"):
            adapter.get_crp_candidates(scan_date, cutoff_time, sample_crp_config, max_results)

    def test_get_end_of_day_prices_success(self, adapter, mock_unified_manager):
        """Test successful end-of-day prices retrieval."""
        # Mock DataFrame result
        mock_df = Mock()
        mock_df.empty = False
        mock_df.iterrows.return_value = [
            (0, Mock(
                get=lambda key, default=0: {
                    'symbol': 'TEST1',
                    'eod_price': 105.0,
                    'eod_high': 107.0,
                    'eod_low': 103.0,
                    'eod_volume': 120000
                }.get(key, default)
            ))
        ]

        mock_unified_manager.persistence_query.return_value = mock_df

        symbols = ['TEST1', 'TEST2']
        scan_date = date.today()
        end_time = time(15, 15)

        results = adapter.get_end_of_day_prices(symbols, scan_date, end_time)

        # Verify query was called
        mock_unified_manager.persistence_query.assert_called_once()

        # Verify results structure
        assert 'TEST1' in results
        assert results['TEST1']['eod_price'] == 105.0

        # Verify result is cached
        cache_key = adapter._get_cache_key("eod_prices", str(symbols), scan_date, end_time)
        assert cache_key in adapter._cache

    def test_get_end_of_day_prices_empty_symbols(self, adapter, mock_unified_manager):
        """Test end-of-day prices with empty symbols list."""
        results = adapter.get_end_of_day_prices([], date.today(), time(15, 15))

        assert results == {}
        mock_unified_manager.persistence_query.assert_not_called()

    def test_get_end_of_day_prices_cache_hit(self, adapter, mock_unified_manager):
        """Test end-of-day prices cache hit."""
        symbols = ['TEST1']
        scan_date = date.today()
        end_time = time(15, 15)
        cache_key = adapter._get_cache_key("eod_prices", str(symbols), scan_date, end_time)

        cached_results = {'TEST1': {'eod_price': 100.0}}
        import time as time_module
        future_timestamp = time_module.time() + 100  # 100 seconds in the future
        adapter._cache[cache_key] = (future_timestamp, cached_results)

        results = adapter.get_end_of_day_prices(symbols, scan_date, end_time)

        assert results == cached_results
        mock_unified_manager.persistence_query.assert_not_called()

    def test_get_breakout_candidates_success(self, adapter, mock_unified_manager, sample_breakout_config):
        """Test successful breakout candidates retrieval."""
        # Mock DataFrame result
        mock_df = Mock()
        mock_df.empty = False
        mock_df.iterrows.return_value = [
            (0, Mock(
                get=lambda key, default=0: {
                    'symbol': 'TEST1',
                    'breakout_price': 100.0,
                    'current_high': 103.0,
                    'current_volume': 150000,
                    'breakout_pct': 3.0,
                    'volume_ratio': 2.5,
                    'probability_score': 85.0
                }.get(key, default)
            ))
        ]

        mock_unified_manager.analytics_query.return_value = mock_df

        scan_date = date.today()
        cutoff_time = time(9, 50)
        max_results = 5

        results = adapter.get_breakout_candidates(scan_date, cutoff_time, sample_breakout_config, max_results)

        # Verify query was called
        mock_unified_manager.analytics_query.assert_called_once()

        # Verify results structure
        assert len(results) == 1
        assert results[0]['symbol'] == 'TEST1'
        assert results[0]['probability_score'] == 85.0

    def test_cache_management(self, adapter):
        """Test cache management operations."""
        # Test initial state
        assert adapter.enable_cache is True
        assert isinstance(adapter._cache, dict)

        # Test cache stats
        stats = adapter.get_cache_stats()
        assert stats['enabled'] is True
        assert 'total_entries' in stats

        # Test cache clearing
        adapter._cache['test_key'] = (0, 'test_value')
        adapter.clear_cache()
        assert len(adapter._cache) == 0

    def test_cache_disabled(self, adapter_no_cache, mock_unified_manager, sample_crp_config):
        """Test behavior when caching is disabled."""
        # Verify cache is disabled
        assert adapter_no_cache.enable_cache is False
        assert adapter_no_cache._cache is None

        # Verify cache operations don't work
        cache_key = adapter_no_cache._get_cache_key("test", "key")
        assert cache_key == ""

        cached_result = adapter_no_cache._get_cached_result("test_key")
        assert cached_result is None

        # Verify operation still works without caching
        mock_df = Mock()
        mock_df.empty = True
        mock_unified_manager.analytics_query.return_value = mock_df

        results = adapter_no_cache.get_crp_candidates(
            date.today(), time(9, 50), sample_crp_config, 5
        )

        assert results == []

    def test_cache_expiration(self, adapter):
        """Test cache expiration behavior."""
        # Set a very short TTL for testing
        adapter.cache_ttl = 0.1  # 100ms

        cache_key = "test_key"
        test_data = "test_value"

        # Set cached result
        adapter._set_cached_result(cache_key, test_data)

        # Immediately retrieve (should work)
        result = adapter._get_cached_result(cache_key)
        assert result == test_data

        # Wait for expiration
        import time
        time.sleep(0.2)

        # Try to retrieve again (should be expired)
        result = adapter._get_cached_result(cache_key)
        assert result is None

        # Verify expired entry was removed
        assert cache_key not in adapter._cache

    def test_performance_logging(self, adapter, mock_unified_manager, sample_crp_config):
        """Test performance logging in scanner operations."""
        mock_df = Mock()
        mock_df.empty = True
        mock_unified_manager.analytics_query.return_value = mock_df

        # Test that operation completes successfully and doesn't raise exceptions
        result = adapter.get_crp_candidates(date.today(), time(9, 50), sample_crp_config, 5)

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 0  # Empty results for empty DataFrame

        # Verify the operation was called
        mock_unified_manager.analytics_query.assert_called_once()

    def test_error_logging(self, adapter, mock_unified_manager, sample_crp_config):
        """Test error logging in scanner operations."""
        mock_unified_manager.analytics_query.side_effect = Exception("Test error")

        # Test that exceptions are properly propagated
        with pytest.raises(Exception, match="Test error"):
            adapter.get_crp_candidates(date.today(), time(9, 50), sample_crp_config, 5)

        # Verify the operation was attempted
        mock_unified_manager.analytics_query.assert_called_once()
