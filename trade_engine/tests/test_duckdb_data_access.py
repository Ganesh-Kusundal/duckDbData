"""
Test DuckDB Data Access Integration
===================================

Tests for DuckDBDataAdapter integration with UnifiedDuckDBManager.
Validates database connectivity, data retrieval, and performance.
"""

import pytest
import asyncio
from datetime import date, time
from unittest.mock import Mock, patch
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from trade_engine.adapters.duckdb_data_adapter import DuckDBDataAdapter
from trade_engine.adapters.enhanced_data_feed import EnhancedDataFeed
from trade_engine.domain.models import Bar
from decimal import Decimal


class TestDuckDBDataAdapter:
    """Test suite for DuckDBDataAdapter."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'data': {
                'duckdb_path': 'data/financial_data.duckdb'
            },
            'database': {
                'max_connections': 5,
                'connection_timeout': 30.0,
                'memory_limit': '2GB',
                'threads': 2
            }
        }

    @pytest.fixture
    def mock_db_manager(self):
        """Mock UnifiedDuckDBManager."""
        manager = Mock()
        manager.analytics_query.return_value = pd.DataFrame({
            'symbol': ['RELIANCE', 'TCS'],
            'timestamp': [pd.Timestamp('2024-01-01 09:15:00'), pd.Timestamp('2024-01-01 09:16:00')],
            'open': [2500.0, 3200.0],
            'high': [2510.0, 3210.0],
            'low': [2495.0, 3195.0],
            'close': [2505.0, 3205.0],
            'volume': [10000, 15000],
            'timeframe': ['1m', '1m'],
            'date_partition': [date(2024, 1, 1), date(2024, 1, 1)]
        })
        manager.persistence_query.return_value = pd.DataFrame({
            'symbol': ['RELIANCE', 'TCS']
        })
        manager.get_connection_stats.return_value = {
            'active_connections': 2,
            'available_connections': 3,
            'max_connections': 5
        }
        return manager

    @pytest.mark.asyncio
    async def test_initialization_success(self, config, mock_db_manager):
        """Test successful initialization."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_db_manager):
            adapter = DuckDBDataAdapter(config)
            success = await adapter.initialize()

            assert success is True
            assert adapter.db_manager is mock_db_manager

    @pytest.mark.asyncio
    async def test_initialization_failure(self, config):
        """Test initialization failure."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', side_effect=Exception("Connection failed")):
            adapter = DuckDBDataAdapter(config)
            success = await adapter.initialize()

            assert success is False

    @pytest.mark.asyncio
    async def test_get_available_symbols(self, config, mock_db_manager):
        """Test getting available symbols."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_db_manager):
            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            symbols = await adapter.get_available_symbols()

            assert isinstance(symbols, list)
            assert len(symbols) == 2
            assert 'RELIANCE' in symbols
            assert 'TCS' in symbols

    @pytest.mark.asyncio
    async def test_get_available_symbols_with_date_filter(self, config, mock_db_manager):
        """Test getting available symbols with date filtering."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_db_manager):
            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            symbols = await adapter.get_available_symbols(('2024-01-01', '2024-01-02'))

            assert isinstance(symbols, list)
            assert len(symbols) == 2

    @pytest.mark.asyncio
    async def test_get_historical_bars(self, config, mock_db_manager):
        """Test getting historical bars."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_db_manager):
            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            bars = await adapter.get_historical_bars(
                symbol='RELIANCE',
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
                timeframe='1m'
            )

            assert isinstance(bars, list)
            assert len(bars) == 2

            # Check first bar
            bar = bars[0]
            assert isinstance(bar, Bar)
            assert bar.symbol == 'RELIANCE'
            assert bar.open == Decimal('2500.0')
            assert bar.high == Decimal('2510.0')
            assert bar.low == Decimal('2495.0')
            assert bar.close == Decimal('2505.0')
            assert bar.volume == 10000
            assert bar.timeframe == '1m'

    @pytest.mark.asyncio
    async def test_get_historical_bars_with_time_filter(self, config, mock_db_manager):
        """Test getting historical bars with time filtering."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_db_manager):
            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            bars = await adapter.get_historical_bars(
                symbol='RELIANCE',
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
                timeframe='1m',
                start_time=time(9, 15),
                end_time=time(15, 30)
            )

            assert isinstance(bars, list)
            assert len(bars) == 2

    @pytest.mark.asyncio
    async def test_validate_data_integrity(self, config):
        """Test data integrity validation."""
        # Mock successful validation response
        mock_result = pd.DataFrame({
            'total_records': [100],
            'valid_records': [98],
            'avg_volume': [50000.0],
            'min_price': [2490.0],
            'max_price': [2520.0],
            'invalid_price_records': [2]
        })

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            result = await adapter.validate_data_integrity('RELIANCE', '2024-01-01')

            assert result['symbol'] == 'RELIANCE'
            assert result['date'] == '2024-01-01'
            assert result['status'] == 'VALID'
            assert result['total_records'] == 100
            assert result['valid_records'] == 98
            assert result['data_quality_score'] > 0.8

    @pytest.mark.asyncio
    async def test_validate_data_integrity_no_data(self, config):
        """Test data integrity validation with no data."""
        mock_result = pd.DataFrame()

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            result = await adapter.validate_data_integrity('INVALID', '2024-01-01')

            assert result['status'] == 'NO_DATA'
            assert result['total_records'] == 0
            assert result['data_quality_score'] == 0.0

    @pytest.mark.asyncio
    async def test_get_market_summary(self, config):
        """Test getting market summary statistics."""
        mock_result = pd.DataFrame({
            'total_symbols': [500],
            'total_volume': [10000000],
            'avg_return': [0.002],
            'advancing_stocks': [300],
            'declining_stocks': [200]
        })

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.return_value = mock_result
            mock_manager_class.return_value = mock_manager

            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            result = await adapter.get_market_summary('2024-01-01')

            assert result['date'] == '2024-01-01'
            assert result['status'] == 'OK'
            assert result['total_symbols'] == 500
            assert result['total_volume'] == 10000000
            assert result['avg_return'] == 0.002
            assert result['advancing_stocks'] == 300
            assert result['declining_stocks'] == 200

    def test_get_connection_stats(self, config, mock_db_manager):
        """Test getting connection statistics."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_db_manager):
            adapter = DuckDBDataAdapter(config)
            # Initialize the adapter to set the db_manager
            adapter.db_manager = mock_db_manager

            stats = adapter.get_connection_stats()

            assert stats['active_connections'] == 2
            assert stats['available_connections'] == 3
            assert stats['max_connections'] == 5

    @pytest.mark.asyncio
    async def test_error_handling(self, config):
        """Test error handling in queries."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager.analytics_query.side_effect = Exception("Database error")
            mock_manager_class.return_value = mock_manager

            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            # Test that errors are properly handled
            symbols = await adapter.get_available_symbols()
            assert symbols == []  # Should return empty list on error

            bars = await adapter.get_historical_bars(
                'RELIANCE', date(2024, 1, 1), date(2024, 1, 2), '1m'
            )
            assert bars == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_close_connections(self, config, mock_db_manager):
        """Test closing database connections."""
        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_db_manager):
            adapter = DuckDBDataAdapter(config)
            await adapter.initialize()

            await adapter.close()

            mock_db_manager.close.assert_called_once()


class TestEnhancedDataFeed:
    """Test suite for EnhancedDataFeed."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'data': {
                'duckdb_path': 'data/financial_data.duckdb'
            },
            'database': {
                'max_connections': 5,
                'connection_timeout': 30.0,
                'memory_limit': '2GB',
                'threads': 2
            }
        }

    @pytest.mark.asyncio
    async def test_initialization(self, config):
        """Test enhanced data feed initialization."""
        mock_manager = Mock()
        mock_manager.persistence_query.return_value = pd.DataFrame({'test': [1]})

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_manager):
            feed = EnhancedDataFeed(config)
            success = await feed.initialize()

            assert success is True
            assert feed._initialized is True

    @pytest.mark.asyncio
    async def test_subscribe(self, config):
        """Test subscribing to symbols."""
        mock_manager = Mock()
        mock_manager.persistence_query.return_value = pd.DataFrame({'test': [1]})

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_manager):
            feed = EnhancedDataFeed(config)
            await feed.initialize()

            # Mock the data adapter
            mock_bars = [
                Bar(
                    timestamp=pd.Timestamp('2024-01-01 09:15:00'),
                    symbol='RELIANCE',
                    open=Decimal('2500'),
                    high=Decimal('2510'),
                    low=Decimal('2495'),
                    close=Decimal('2505'),
                    volume=10000,
                    timeframe='1m'
                )
            ]

            with patch.object(feed.data_adapter, 'get_historical_bars', return_value=mock_bars):
                bars = []
                async for bar in feed.subscribe(['RELIANCE'], '1m'):
                    bars.append(bar)

                assert len(bars) == 1
                assert bars[0].symbol == 'RELIANCE'

    def test_synchronous_methods(self, config):
        """Test synchronous method fallbacks."""
        mock_manager = Mock()
        mock_manager.persistence_query.return_value = pd.DataFrame({'test': [1]})

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_manager):
            feed = EnhancedDataFeed(config)

            # Test that synchronous methods exist and don't crash
            symbols = feed.get_available_symbols()
            bars = feed.get_historical_bars('RELIANCE', date(2024, 1, 1), date(2024, 1, 2), '1m')

            # These should return empty lists when event loop is not available
            assert isinstance(symbols, list)
            assert isinstance(bars, list)

    def test_connection_stats(self, config):
        """Test getting connection statistics."""
        mock_manager = Mock()
        mock_manager.persistence_query.return_value = pd.DataFrame({'test': [1]})
        mock_manager.get_connection_stats.return_value = {
            'active_connections': 1,
            'available_connections': 4,
            'max_connections': 5
        }

        with patch('trade_engine.adapters.duckdb_data_adapter.UnifiedDuckDBManager', return_value=mock_manager):
            feed = EnhancedDataFeed(config)
            # Initialize the feed to set up the data adapter
            feed.data_adapter.db_manager = mock_manager

            stats = feed.get_connection_stats()

            assert isinstance(stats, dict)
            assert 'active_connections' in stats
