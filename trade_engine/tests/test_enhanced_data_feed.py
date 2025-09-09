"""
Test Enhanced Data Feed
=======================

Tests for enhanced data feed functionality with optimized DuckDB queries.
Validates batch operations, data quality validation, and performance optimizations.
"""

import pytest
import asyncio
from datetime import date
from decimal import Decimal
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from trade_engine.adapters.enhanced_data_feed import EnhancedDataFeed
from trade_engine.domain.models import Bar


class TestEnhancedDataFeed:
    """Test suite for EnhancedDataFeed."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'data': {'duckdb_path': 'data/financial_data.duckdb'},
            'database': {'max_connections': 5, 'connection_timeout': 30.0, 'memory_limit': '2GB', 'threads': 2}
        }

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing."""
        return pd.DataFrame({
            'symbol': ['RELIANCE', 'TCS', 'RELIANCE', 'TCS', 'RELIANCE'],
            'timestamp': [
                pd.Timestamp('2024-01-01 09:15:00'),
                pd.Timestamp('2024-01-01 09:16:00'),
                pd.Timestamp('2024-01-01 09:17:00'),
                pd.Timestamp('2024-01-01 09:18:00'),
                pd.Timestamp('2024-01-01 09:19:00')
            ],
            'open': [2500.0, 3200.0, 2505.0, 3205.0, 2510.0],
            'high': [2510.0, 3210.0, 2515.0, 3215.0, 2520.0],
            'low': [2495.0, 3195.0, 2500.0, 3200.0, 2505.0],
            'close': [2505.0, 3205.0, 2510.0, 3210.0, 2515.0],
            'volume': [10000, 15000, 12000, 16000, 11000]
        })

    @pytest.mark.asyncio
    async def test_enhanced_feed_initialization(self, config):
        """Test enhanced data feed initialization."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.persistence_query.return_value = pd.DataFrame({'test': [1]})
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            success = await feed.initialize()

            assert success is True
            assert feed._initialized is True

    @pytest.mark.asyncio
    async def test_get_optimized_bars_batch(self, config, sample_market_data):
        """Test optimized batch bars retrieval."""
        # Mock the database manager
        mock_result = sample_market_data.copy()
        mock_result['timeframe'] = '1m'

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the data adapter's _execute_async_query method
            with patch.object(feed.data_adapter, '_execute_async_query', return_value=mock_result):
                symbols = ['RELIANCE', 'TCS']
                result = await feed.get_optimized_bars_batch(symbols, '2024-01-01', '2024-01-02')

                assert isinstance(result, dict)
                assert len(result) == 2
                assert 'RELIANCE' in result
                assert 'TCS' in result

                # Check that bars are properly constructed
                reliance_bars = result['RELIANCE']
                assert len(reliance_bars) > 0

                bar = reliance_bars[0]
                assert isinstance(bar, Bar)
                assert bar.symbol == 'RELIANCE'
                assert isinstance(bar.open, Decimal)

    @pytest.mark.asyncio
    async def test_get_market_data_summary(self, config):
        """Test comprehensive market data summary."""
        # Mock basic summary
        mock_summary_result = pd.DataFrame({
            'total_symbols': [500],
            'total_volume': [10000000],
            'avg_return': [0.002],
            'advancing_stocks': [300],
            'declining_stocks': [200]
        })

        # Mock enhanced statistics
        mock_enhanced_result = pd.DataFrame({
            'gainers_2pct': [50],
            'losers_2pct': [30],
            'avg_volume_per_symbol': [50000.0],
            'max_volume': [5000000],
            'high_volume_stocks': [25]
        })

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_enhanced_result
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the data adapter's methods
            with patch.object(feed.data_adapter, 'get_market_summary', return_value={
                'status': 'OK',
                'total_symbols': 500,
                'total_volume': 10000000,
                'avg_return': 0.002
            }):
                with patch.object(feed.data_adapter, '_execute_async_query', return_value=mock_enhanced_result):
                    summary = await feed.get_market_data_summary('2024-01-01')

                    assert summary['status'] == 'OK'
                    assert summary['total_symbols'] == 500
                    assert summary['gainers_2pct'] == 50
                    assert summary['losers_2pct'] == 30
                    assert summary['high_volume_stocks'] == 25

    @pytest.mark.asyncio
    async def test_validate_data_quality(self, config):
        """Test data quality validation for multiple symbols."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager'):
            feed = EnhancedDataFeed(config)
            await feed.initialize()

            symbols = ['RELIANCE', 'TCS']

            # Mock validation results
            mock_validation = {
                'symbol': 'RELIANCE',
                'date': '2024-01-01',
                'status': 'VALID',
                'data_quality_score': 0.95
            }

            with patch.object(feed.data_adapter, 'validate_data_integrity', return_value=mock_validation):
                results = await feed.validate_data_quality(symbols, '2024-01-01')

                assert isinstance(results, dict)
                assert len(results) == 2
                assert 'RELIANCE' in results
                assert 'TCS' in results

                # Check structure of validation results
                for symbol_result in results.values():
                    assert 'symbol' in symbol_result
                    assert 'status' in symbol_result
                    assert 'data_quality_score' in symbol_result

    @pytest.mark.asyncio
    async def test_get_symbols_by_criteria(self, config):
        """Test getting symbols that match specific criteria."""
        mock_result = pd.DataFrame({
            'symbol': ['RELIANCE', 'TCS', 'INFY']
        })

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            criteria = {
                'min_volume': 100000,
                'date': '2024-01-01',
                'limit': 10
            }

            symbols = await feed.get_symbols_by_criteria(criteria)

            assert isinstance(symbols, list)
            assert len(symbols) == 3
            assert 'RELIANCE' in symbols

    @pytest.mark.asyncio
    async def test_get_symbols_by_criteria_complex(self, config):
        """Test getting symbols with complex criteria."""
        mock_result = pd.DataFrame({
            'symbol': ['HIGH_VOL_STOCK']
        })

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the _execute_async_query method
            with patch.object(feed.data_adapter, '_execute_async_query', return_value=mock_result):
                criteria = {
                    'min_volume': 1000000,
                    'max_volume': 10000000,
                    'min_price': 100.0,
                    'max_price': 5000.0,
                    'min_volatility': 0.05,
                    'date': '2024-01-01',
                    'limit': 50
                }

                symbols = await feed.get_symbols_by_criteria(criteria)

                assert isinstance(symbols, list)
                assert 'HIGH_VOL_STOCK' in symbols

    @pytest.mark.asyncio
    async def test_preload_market_data(self, config):
        """Test market data preload functionality."""
        mock_result = pd.DataFrame({
            'total_records': [10000]
        })

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the _execute_async_query method
            with patch.object(feed.data_adapter, '_execute_async_query', return_value=mock_result):
                symbols = ['RELIANCE', 'TCS', 'INFY']
                date_range = ('2024-01-01', '2024-01-02')

                result = await feed.preload_market_data(symbols, date_range)

                assert isinstance(result, dict)
                assert result['symbols_requested'] == 3
                assert result['estimated_records'] == 10000
                assert result['status'] == 'COMPLETED'
                assert '2024-01-01 to 2024-01-02' in result['date_range']

    @pytest.mark.asyncio
    async def test_preload_market_data_error(self, config):
        """Test market data preload with error handling."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.side_effect = Exception("Database error")
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the _execute_async_query method to raise an exception
            with patch.object(feed.data_adapter, '_execute_async_query', side_effect=Exception("Database error")):
                symbols = ['RELIANCE', 'TCS']
                date_range = ('2024-01-01', '2024-01-02')

                result = await feed.preload_market_data(symbols, date_range)

                assert result['status'] == 'ERROR'
                assert 'Database error' in result['error']

    @pytest.mark.asyncio
    async def test_batch_bars_error_handling(self, config):
        """Test batch bars retrieval with error handling."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.side_effect = Exception("Query failed")
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the _execute_async_query method to raise an exception
            with patch.object(feed.data_adapter, '_execute_async_query', side_effect=Exception("Query failed")):
                symbols = ['RELIANCE', 'TCS']
                result = await feed.get_optimized_bars_batch(symbols, '2024-01-01', '2024-01-02')

                assert isinstance(result, dict)
                assert len(result) == 2
                assert result['RELIANCE'] == []
                assert result['TCS'] == []

    @pytest.mark.asyncio
    async def test_market_summary_error_handling(self, config):
        """Test market summary with error handling."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.side_effect = Exception("Query error")
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the data adapter to return error
            with patch.object(feed.data_adapter, 'get_market_summary', return_value={'status': 'ERROR'}):
                with patch.object(feed.data_adapter, '_execute_async_query', side_effect=Exception("Query error")):
                    result = await feed.get_market_data_summary('2024-01-01')

                    assert result['status'] == 'ERROR'

    def test_synchronous_fallbacks(self, config):
        """Test synchronous method fallbacks."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager'):
            feed = EnhancedDataFeed(config)

            # These should return empty lists when event loop is not available
            symbols = feed.get_available_symbols()
            bars = feed.get_historical_bars('RELIANCE', date(2024, 1, 1), date(2024, 1, 2), '1m')

            assert isinstance(symbols, list)
            assert isinstance(bars, list)

    def test_connection_stats_fallback(self, config):
        """Test connection stats with data adapter fallback."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager'):
            feed = EnhancedDataFeed(config)

            # Mock the data adapter's connection stats
            feed.data_adapter = Mock()
            feed.data_adapter.get_connection_stats.return_value = {
                'active_connections': 2,
                'available_connections': 3,
                'max_connections': 5
            }

            stats = feed.get_connection_stats()

            assert isinstance(stats, dict)
            assert stats['active_connections'] == 2

    @pytest.mark.asyncio
    async def test_symbols_criteria_empty_conditions(self, config):
        """Test getting symbols with no filtering conditions."""
        mock_result = pd.DataFrame({
            'symbol': ['ALL_SYMBOLS']
        })

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the _execute_async_query method
            with patch.object(feed.data_adapter, '_execute_async_query', return_value=mock_result):
                criteria = {
                    'date': '2024-01-01',
                    'limit': 10
                }

                symbols = await feed.get_symbols_by_criteria(criteria)

                assert isinstance(symbols, list)
                assert 'ALL_SYMBOLS' in symbols

    @pytest.mark.asyncio
    async def test_data_quality_validation_partial_failure(self, config):
        """Test data quality validation with partial failures."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager'):
            feed = EnhancedDataFeed(config)
            await feed.initialize()

            symbols = ['GOOD_SYMBOL', 'BAD_SYMBOL']

            def mock_validate(symbol, date_str):
                if symbol == 'GOOD_SYMBOL':
                    return {
                        'symbol': symbol,
                        'date': date_str,
                        'status': 'VALID',
                        'data_quality_score': 0.95
                    }
                else:
                    raise Exception("Validation failed for bad symbol")

            with patch.object(feed.data_adapter, 'validate_data_integrity', side_effect=mock_validate):
                results = await feed.validate_data_quality(symbols, '2024-01-01')

                assert isinstance(results, dict)
                assert len(results) == 2
                assert results['GOOD_SYMBOL']['status'] == 'VALID'
                assert results['BAD_SYMBOL']['status'] == 'ERROR'

    @pytest.mark.asyncio
    async def test_close_functionality(self, config):
        """Test proper cleanup on close."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager'):
            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the data adapter with async close method
            mock_adapter = Mock()
            mock_adapter.close = AsyncMock()
            feed.data_adapter = mock_adapter

            await feed.close()

            assert feed._initialized is False
            mock_adapter.close.assert_called_once()
