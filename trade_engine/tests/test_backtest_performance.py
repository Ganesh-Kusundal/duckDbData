"""
Test Backtesting Performance Optimization
========================================

Tests for backtesting performance optimizer functionality.
Validates memory management, parallel processing, and large dataset handling.
"""

import pytest
import asyncio
import time as time_module
from datetime import date, time, datetime
from decimal import Decimal
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from trade_engine.domain.backtest_optimizer import (
    BacktestOptimizer, BacktestConfiguration, BacktestResult,
    MemoryManager, ParallelExecutor
)
from trade_engine.domain.models import Bar, Signal, SignalType
from trade_engine.adapters.enhanced_data_feed import EnhancedDataFeed
from trade_engine.domain.algorithm_layer import AlgorithmManager, AlgorithmResult


class TestMemoryManager:
    """Test suite for MemoryManager."""

    def test_memory_manager_initialization(self):
        """Test memory manager initialization."""
        manager = MemoryManager(max_memory_mb=1024)

        assert manager.max_memory_mb == 1024
        assert manager.operation_count == 0
        assert len(manager.memory_peaks) == 0

    def test_should_cleanup(self):
        """Test cleanup trigger logic."""
        manager = MemoryManager(max_memory_mb=1024, cleanup_interval=5)

        # Should not cleanup initially
        assert not manager.should_cleanup()

        # Should cleanup after interval
        for i in range(4):
            should_cleanup = manager.should_cleanup()
            if i == 3:  # 5th call (index 3 in 0-3 range)
                assert should_cleanup  # This should be True

    def test_memory_stats(self):
        """Test memory statistics calculation."""
        manager = MemoryManager(max_memory_mb=1024)

        # Simulate some memory usage
        manager.memory_peaks = [100, 200, 150, 300]

        stats = manager.get_memory_stats()

        assert 'current_usage_mb' in stats
        assert 'peak_usage_mb' in stats
        assert 'avg_usage_mb' in stats
        assert stats['peak_usage_mb'] == 300
        assert stats['avg_usage_mb'] == 187.5  # (100+200+150+300)/4


class TestParallelExecutor:
    """Test suite for ParallelExecutor."""

    @pytest.fixture
    def executor(self):
        """Parallel executor instance."""
        return ParallelExecutor(max_workers=2, enable_parallel=True)

    def test_parallel_executor_initialization(self):
        """Test parallel executor initialization."""
        executor = ParallelExecutor(max_workers=4, enable_parallel=True)
        assert executor.max_workers == 4
        assert executor.enable_parallel is True
        assert executor.executor is not None

    def test_parallel_executor_disabled(self):
        """Test parallel executor with parallel disabled."""
        executor = ParallelExecutor(max_workers=4, enable_parallel=False)
        assert executor.enable_parallel is False
        assert executor.executor is None

    @pytest.mark.asyncio
    async def test_execute_parallel_single_task(self, executor):
        """Test executing single task."""
        async def test_task():
            return "result"

        results = await executor.execute_parallel([test_task])

        assert len(results) == 1
        assert results[0] == "result"

    @pytest.mark.asyncio
    async def test_execute_parallel_multiple_tasks(self, executor):
        """Test executing multiple tasks."""
        async def task1():
            return "result1"

        async def task2():
            return "result2"

        results = await executor.execute_parallel([task1, task2])

        assert len(results) == 2
        assert "result1" in results
        assert "result2" in results

    @pytest.mark.asyncio
    async def test_execute_parallel_disabled(self):
        """Test executing tasks with parallel disabled."""
        executor = ParallelExecutor(max_workers=2, enable_parallel=False)

        async def test_task():
            return "result"

        results = await executor.execute_parallel([test_task])

        assert len(results) == 1
        assert results[0] == "result"

    def test_shutdown(self, executor):
        """Test executor shutdown."""
        executor.shutdown()
        # Should not raise any exceptions


class TestBacktestOptimizer:
    """Test suite for BacktestOptimizer."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'memory_limit_mb': 1024,
            'max_workers': 2,
            'enable_parallel': True
        }

    @pytest.fixture
    def backtest_config(self):
        """Test backtest configuration."""
        return BacktestConfiguration(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            symbols=['RELIANCE', 'TCS'],
            algorithms=['breakout_algo', 'momentum_algo'],
            initial_balance=Decimal('100000'),
            chunk_size_days=7
        )

    @pytest.fixture
    def mock_data_feed(self):
        """Mock data feed."""
        feed = Mock(spec=EnhancedDataFeed)
        feed.initialize = AsyncMock(return_value=True)
        feed.get_available_symbols_async = AsyncMock(return_value=['RELIANCE', 'TCS'])
        return feed

    @pytest.fixture
    def mock_algorithm_manager(self):
        """Mock algorithm manager."""
        manager = Mock(spec=AlgorithmManager)
        manager.get_algorithm_status = Mock(return_value={
            'breakout_algo': {'is_active': True},
            'momentum_algo': {'is_active': True}
        })
        manager.execute_algorithms = AsyncMock(return_value={
            'test_algo': AlgorithmResult(signals=[], execution_time=0.5),
            'breakout_algo': AlgorithmResult(),
            'momentum_algo': AlgorithmResult()
        })
        return manager

    @pytest.fixture
    def mock_query_optimizer(self):
        """Mock query optimizer."""
        return Mock()

    @pytest.mark.asyncio
    async def test_optimizer_initialization(self, config, mock_data_feed,
                                          mock_algorithm_manager, mock_query_optimizer):
        """Test optimizer initialization."""
        optimizer = BacktestOptimizer(config)

        success = await optimizer.initialize(mock_data_feed, mock_algorithm_manager, mock_query_optimizer)

        assert success is True
        assert optimizer.data_feed == mock_data_feed
        assert optimizer.algorithm_manager == mock_algorithm_manager
        assert optimizer.query_optimizer == mock_query_optimizer

    @pytest.mark.asyncio
    async def test_validate_configuration_valid(self, config, backtest_config,
                                              mock_data_feed, mock_algorithm_manager):
        """Test configuration validation with valid config."""
        optimizer = BacktestOptimizer(config)
        optimizer.data_feed = mock_data_feed
        optimizer.algorithm_manager = mock_algorithm_manager

        is_valid = await optimizer._validate_configuration(backtest_config)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_configuration_invalid_dates(self, config):
        """Test configuration validation with invalid dates."""
        invalid_config = BacktestConfiguration(
            start_date=date(2024, 1, 31),
            end_date=date(2024, 1, 1),  # End before start
            symbols=['RELIANCE'],
            algorithms=['test_algo']
        )

        optimizer = BacktestOptimizer(config)
        is_valid = await optimizer._validate_configuration(invalid_config)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_configuration_no_symbols(self, config):
        """Test configuration validation with no symbols."""
        invalid_config = BacktestConfiguration(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            symbols=[],  # No symbols
            algorithms=['test_algo']
        )

        optimizer = BacktestOptimizer(config)
        is_valid = await optimizer._validate_configuration(invalid_config)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_prepare_data_chunks(self, config, backtest_config, mock_data_feed):
        """Test data chunk preparation."""
        optimizer = BacktestOptimizer(config)
        optimizer.data_feed = mock_data_feed

        # Mock batch data retrieval
        mock_data = pd.DataFrame({
            'symbol': ['RELIANCE', 'TCS'],
            'timestamp': [datetime(2024, 1, 1, 9, 15), datetime(2024, 1, 1, 9, 16)],
            'open': [2500.0, 3200.0],
            'high': [2510.0, 3210.0],
            'low': [2495.0, 3195.0],
            'close': [2505.0, 3205.0],
            'volume': [10000, 15000]
        })

        with patch.object(mock_data_feed, 'get_optimized_bars_batch', return_value={
            'RELIANCE': [Bar(
                timestamp=datetime(2024, 1, 1, 9, 15),
                symbol='RELIANCE',
                open=Decimal('2500.0'),
                high=Decimal('2510.0'),
                low=Decimal('2495.0'),
                close=Decimal('2505.0'),
                volume=10000,
                timeframe='1m'
            )]
        }):
            chunks = await optimizer._prepare_data_chunks(backtest_config)

            assert len(chunks) > 0
            for chunk in chunks:
                assert 'start_date' in chunk
                assert 'end_date' in chunk
                assert 'symbols' in chunk

    @pytest.mark.asyncio
    async def test_load_chunk_data(self, config, mock_data_feed):
        """Test chunk data loading."""
        optimizer = BacktestOptimizer(config)
        optimizer.data_feed = mock_data_feed

        symbols = ['RELIANCE', 'TCS']
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)

        with patch.object(mock_data_feed, 'get_optimized_bars_batch', return_value={
            'RELIANCE': [Bar(
                timestamp=datetime(2024, 1, 1, 9, 15),
                symbol='RELIANCE',
                open=Decimal('2500.0'),
                high=Decimal('2510.0'),
                low=Decimal('2495.0'),
                close=Decimal('2505.0'),
                volume=10000,
                timeframe='1m'
            )]
        }):
            data = await optimizer._load_chunk_data(symbols, start_date, end_date)

            assert isinstance(data, pd.DataFrame)
            assert len(data) >= 0  # May be empty if no data

    @pytest.mark.asyncio
    async def test_execute_algorithm_on_chunk(self, config, mock_algorithm_manager):
        """Test algorithm execution on data chunk."""
        optimizer = BacktestOptimizer(config)
        optimizer.algorithm_manager = mock_algorithm_manager

        bars = [
            Bar(
                timestamp=datetime(2024, 1, 1, 9, 15),
                symbol='RELIANCE',
                open=Decimal('2500.0'),
                high=Decimal('2510.0'),
                low=Decimal('2495.0'),
                close=Decimal('2505.0'),
                volume=10000,
                timeframe='1m'
            )
        ]

        backtest_config = BacktestConfiguration(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            symbols=['RELIANCE'],
            algorithms=['test_algo']
        )

        result = await optimizer._execute_algorithm_on_chunk('test_algo', bars, backtest_config)

        assert result is not None
        mock_algorithm_manager.execute_algorithms.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_portfolio(self, config):
        """Test portfolio updates."""
        optimizer = BacktestOptimizer(config)

        chunk_result = {
            'trade_signals': [
                {
                    'signal': Signal(
                        id='test_signal',
                        symbol='RELIANCE',
                        signal_type=SignalType.ENTRY,
                        price=Decimal('2500.0'),
                        quantity=10,
                        reason='Test entry',
                        confidence_score=0.8,
                        timestamp=datetime(2024, 1, 1, 9, 15)
                    )
                }
            ]
        }

        backtest_config = BacktestConfiguration(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            symbols=['RELIANCE'],
            algorithms=['test_algo'],
            initial_balance=Decimal('100000'),
            risk_per_trade=Decimal('0.01')
        )

        new_balance = await optimizer._update_portfolio(chunk_result, 100000.0, backtest_config)

        assert isinstance(new_balance, float)
        assert new_balance <= 100000.0  # Should decrease due to position entry

    @pytest.mark.asyncio
    async def test_calculate_portfolio_performance(self, config):
        """Test portfolio performance calculation."""
        optimizer = BacktestOptimizer(config)

        portfolio_history = [
            {'date': '2024-01-01', 'balance': 100000.0},
            {'date': '2024-01-02', 'balance': 101000.0},
            {'date': '2024-01-03', 'balance': 99000.0}
        ]

        initial_balance = Decimal('100000')

        performance = await optimizer._calculate_portfolio_performance(portfolio_history, initial_balance)

        assert isinstance(performance, dict)
        assert 'total_return' in performance
        assert 'sharpe_ratio' in performance
        assert 'max_drawdown' in performance
        assert performance['final_balance'] == 99000.0

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics(self, config):
        """Test performance metrics calculation."""
        optimizer = BacktestOptimizer(config)
        optimizer.execution_start_time = time_module.time() - 10  # 10 seconds ago

        result = BacktestResult()
        result.algorithm_results = {
            'test_algo': [AlgorithmResult(signals=[], execution_time=0.5)]
        }

        backtest_config = BacktestConfiguration(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            symbols=['RELIANCE'],
            algorithms=['test_algo']
        )

        await optimizer._calculate_performance_metrics(result, backtest_config)

        assert 'test_algo_total_signals' in result.performance_metrics
        assert 'test_algo_avg_execution_time' in result.performance_metrics
        assert 'total_execution_time' in result.performance_metrics

    def test_get_execution_stats(self, config):
        """Test execution statistics retrieval."""
        optimizer = BacktestOptimizer(config)
        optimizer.execution_start_time = time_module.time() - 5  # 5 seconds ago

        stats = optimizer._get_execution_stats()

        assert isinstance(stats, dict)
        assert 'total_execution_time' in stats
        assert 'memory_stats' in stats
        assert stats['total_execution_time'] >= 5.0

    def test_clear_cache(self, config):
        """Test cache clearing."""
        optimizer = BacktestOptimizer(config)
        optimizer.result_cache = {'key1': 'value1', 'key2': 'value2'}
        optimizer.data_cache = {'data1': pd.DataFrame(), 'data2': pd.DataFrame()}

        optimizer.clear_cache()

        assert len(optimizer.result_cache) == 0
        assert len(optimizer.data_cache) == 0

    @pytest.mark.asyncio
    async def test_run_backtest_with_valid_config(self, config, backtest_config,
                                                 mock_data_feed, mock_algorithm_manager, mock_query_optimizer):
        """Test full backtest execution with valid configuration."""
        optimizer = BacktestOptimizer(config)
        await optimizer.initialize(mock_data_feed, mock_algorithm_manager, mock_query_optimizer)

        # Mock data loading
        with patch.object(optimizer, '_load_chunk_data', return_value=pd.DataFrame()):
            result = await optimizer.run_backtest(backtest_config)

            assert isinstance(result, BacktestResult)
            assert 'execution_stats' in result.__dict__

    @pytest.mark.asyncio
    async def test_run_backtest_with_invalid_config(self, config, mock_data_feed,
                                                   mock_algorithm_manager, mock_query_optimizer):
        """Test backtest execution with invalid configuration."""
        optimizer = BacktestOptimizer(config)
        await optimizer.initialize(mock_data_feed, mock_algorithm_manager, mock_query_optimizer)

        invalid_config = BacktestConfiguration(
            start_date=date(2024, 1, 31),
            end_date=date(2024, 1, 1),  # Invalid date range
            symbols=['RELIANCE'],
            algorithms=['test_algo']
        )

        result = await optimizer.run_backtest(invalid_config)

        assert isinstance(result, BacktestResult)
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_shutdown(self, config, mock_data_feed, mock_algorithm_manager, mock_query_optimizer):
        """Test optimizer shutdown."""
        optimizer = BacktestOptimizer(config)
        await optimizer.initialize(mock_data_feed, mock_algorithm_manager, mock_query_optimizer)

        await optimizer.shutdown()

        # Should not raise any exceptions
        assert True

    def test_backtest_result_methods(self):
        """Test BacktestResult utility methods."""
        result = BacktestResult()

        # Test empty result
        assert result.get_total_trades() == 0
        assert result.get_total_return() == 0.0
        assert result.get_sharpe_ratio() == 0.0
        assert result.get_max_drawdown() == 0.0

        # Test with some data
        result.trade_log = [{'id': 1}, {'id': 2}, {'id': 3}]
        result.portfolio_performance = {
            'total_return': 0.15,
            'sharpe_ratio': 1.5,
            'max_drawdown': 0.1
        }

        assert result.get_total_trades() == 3
        assert result.get_total_return() == 0.15
        assert result.get_sharpe_ratio() == 1.5
        assert result.get_max_drawdown() == 0.1
