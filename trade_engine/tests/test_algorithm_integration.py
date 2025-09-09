"""
Test Algorithm Integration Layer
=================================

Tests for algorithm integration layer functionality.
Validates scanner-based algorithm execution and management.
"""

import pytest
import asyncio
from datetime import datetime, date, time
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from trade_engine.domain.algorithm_layer import (
    TradingAlgorithm, ScannerBasedAlgorithm, AlgorithmManager,
    AlgorithmContext, AlgorithmResult
)
from trade_engine.domain.models import Bar, Signal, SignalType, Position
from trade_engine.adapters.scanner_adapter import ScannerIntegrationAdapter, ScannerAlgorithm
from trade_engine.adapters.duckdb_data_adapter import DuckDBDataAdapter
from trade_engine.adapters.query_optimizer import QueryOptimizer
from datetime import timedelta


class ConcreteTradingAlgorithm(TradingAlgorithm):
    """Concrete implementation for testing."""

    async def initialize(self, context):
        self.is_initialized = True
        return True

    async def process_market_data(self, bars, context):
        return AlgorithmResult()

    async def handle_signals(self, signals, context):
        return AlgorithmResult()

    async def update_positions(self, positions, context):
        return AlgorithmResult()


class TestTradingAlgorithm:
    """Test suite for TradingAlgorithm base class."""

    def test_algorithm_initialization(self):
        """Test algorithm initialization."""
        config = {'param1': 'value1', 'param2': 42}

        algorithm = ConcreteTradingAlgorithm('test_algo', 'Test Algorithm', config)

        assert algorithm.algorithm_id == 'test_algo'
        assert algorithm.name == 'Test Algorithm'
        assert algorithm.config == config
        assert algorithm.is_initialized is False
        assert algorithm.execution_count == 0
        assert algorithm.success_count == 0

    def test_get_algorithm_info(self):
        """Test getting algorithm information."""
        config = {'param1': 'value1'}
        algorithm = ConcreteTradingAlgorithm('test_algo', 'Test Algorithm', config)

        info = algorithm.get_algorithm_info()

        assert info['algorithm_id'] == 'test_algo'
        assert info['name'] == 'Test Algorithm'
        assert info['config'] == config
        assert info['is_initialized'] is False
        assert info['execution_count'] == 0
        assert info['success_count'] == 0
        assert info['success_rate'] == 0.0


class TestScannerBasedAlgorithm:
    """Test suite for ScannerBasedAlgorithm."""

    @pytest.fixture
    def scanner_adapter(self):
        """Mock scanner adapter."""
        adapter = Mock(spec=ScannerIntegrationAdapter)
        return adapter

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'scanner_algorithm': 'breakout_scanner',
            'required_scanner_params': ['min_volume_multiplier'],
            'parameter_ranges': {
                'min_volume_multiplier': [1.0, 3.0]
            },
            'confidence_multiplier': 0.9,
            'min_position_size': 10,
            'max_position_size': 1000
        }

    @pytest.fixture
    def context(self):
        """Test algorithm context."""
        return AlgorithmContext(
            trading_date=date.today(),
            current_time=time(9, 30),
            account_balance=Decimal('100000'),
            risk_per_trade=Decimal('0.01')
        )

    @pytest.fixture
    def scanner_algorithm(self):
        """Mock scanner algorithm."""
        return ScannerAlgorithm(
            algorithm_id='breakout_scanner',
            name='Breakout Scanner',
            description='Test scanner',
            parameters={'min_volume_multiplier': 1.5}
        )

    @pytest.mark.asyncio
    async def test_scanner_algorithm_initialization_success(self, scanner_adapter, config, scanner_algorithm):
        """Test successful scanner algorithm initialization."""
        scanner_adapter.load_scanner_algorithm.return_value = scanner_algorithm

        algorithm = ScannerBasedAlgorithm('test_algo', 'Test Algorithm', config, scanner_adapter)
        success = await algorithm.initialize(AlgorithmContext(
            trading_date=date.today(),
            current_time=time(9, 30)
        ))

        assert success is True
        assert algorithm.is_initialized is True
        assert algorithm.scanner_algorithm == scanner_algorithm

    @pytest.mark.asyncio
    async def test_scanner_algorithm_initialization_failure(self, scanner_adapter, config):
        """Test scanner algorithm initialization failure."""
        scanner_adapter.load_scanner_algorithm.return_value = None

        algorithm = ScannerBasedAlgorithm('test_algo', 'Test Algorithm', config, scanner_adapter)
        success = await algorithm.initialize(AlgorithmContext(
            trading_date=date.today(),
            current_time=time(9, 30)
        ))

        assert success is False
        assert algorithm.is_initialized is False

    @pytest.mark.asyncio
    async def test_process_market_data(self, scanner_adapter, config, context, scanner_algorithm):
        """Test processing market data."""
        # Setup mocks
        scanner_adapter.load_scanner_algorithm.return_value = scanner_algorithm
        scanner_adapter.execute_scanner_on_data.return_value = [
            Signal(
                id='test_signal_1',
                symbol='RELIANCE',
                signal_type=SignalType.ENTRY,
                price=Decimal('2500.0'),
                quantity=100,
                reason='Test breakout signal',
                confidence_score=0.8,
                timestamp=datetime.now()
            )
        ]

        algorithm = ScannerBasedAlgorithm('test_algo', 'Test Algorithm', config, scanner_adapter)
        await algorithm.initialize(context)

        bars = [
            Bar(
                timestamp=datetime.now(),
                symbol='RELIANCE',
                open=Decimal('2495.0'),
                high=Decimal('2510.0'),
                low=Decimal('2490.0'),
                close=Decimal('2505.0'),
                volume=10000,
                timeframe='1m'
            )
        ]

        result = await algorithm.process_market_data(bars, context)

        assert isinstance(result, AlgorithmResult)
        assert len(result.signals) > 0
        assert result.execution_time > 0
        assert 'scanner_signals_generated' in result.performance_metrics

    @pytest.mark.asyncio
    async def test_handle_signals(self, scanner_adapter, config, context):
        """Test handling incoming signals."""
        algorithm = ScannerBasedAlgorithm('test_algo', 'Test Algorithm', config, scanner_adapter)

        signals = [
            Signal(
                id='external_signal_1',
                symbol='TCS',
                signal_type=SignalType.ENTRY,
                price=Decimal('3200.0'),
                quantity=50,
                reason='External signal',
                confidence_score=0.7,
                timestamp=datetime.now()
            )
        ]

        result = await algorithm.handle_signals(signals, context)

        assert isinstance(result, AlgorithmResult)
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_should_process_signal_filters(self, scanner_adapter, config, context):
        """Test signal processing filters."""
        algorithm = ScannerBasedAlgorithm('test_algo', 'Test Algorithm', config, scanner_adapter)

        # Test entry signal when already have position
        context.positions['RELIANCE'] = Position(
            symbol='RELIANCE',
            quantity=100,
            avg_cost=Decimal('2500.0'),
            current_price=Decimal('2510.0'),
            entry_timestamp=datetime.now()
        )

        signal = Signal(
            id='test_signal',
            symbol='RELIANCE',
            signal_type=SignalType.ENTRY,
            price=Decimal('2515.0'),
            quantity=50,
            reason='Test signal',
            confidence_score=0.8,
            timestamp=datetime.now()
        )

        should_process = await algorithm._should_process_signal(signal, context)
        assert should_process is False  # Should not process because already have position

    @pytest.mark.asyncio
    async def test_position_size_calculation(self, scanner_adapter, config, context):
        """Test position size calculation."""
        algorithm = ScannerBasedAlgorithm('test_algo', 'Test Algorithm', config, scanner_adapter)

        signal = Signal(
            id='test_signal',
            symbol='RELIANCE',
            signal_type=SignalType.ENTRY,
            price=Decimal('2500.0'),
            quantity=100,
            reason='Test signal',
            confidence_score=0.8,
            timestamp=datetime.now()
        )

        position_size = await algorithm._calculate_position_size(signal, context)

        assert position_size > 0
        assert isinstance(position_size, int)
        assert config['min_position_size'] <= position_size <= config['max_position_size']

    @pytest.mark.asyncio
    async def test_update_positions(self, scanner_adapter, config, context):
        """Test position updates."""
        algorithm = ScannerBasedAlgorithm('test_algo', 'Test Algorithm', config, scanner_adapter)

        positions = {
            'RELIANCE': Position(
                symbol='RELIANCE',
                quantity=100,
                avg_cost=Decimal('2500.0'),
                current_price=Decimal('2525.0'),  # 1% profit
                entry_timestamp=datetime.now()
            )
        }

        result = await algorithm.update_positions(positions, context)

        assert isinstance(result, AlgorithmResult)
        assert result.performance_metrics['active_positions'] == 1

    @pytest.mark.asyncio
    async def test_transform_scanner_signal(self, scanner_adapter, config, context):
        """Test scanner signal transformation."""
        algorithm = ScannerBasedAlgorithm('test_algo', 'Test Algorithm', config, scanner_adapter)

        scanner_signal = Signal(
            id='scanner_123',
            symbol='RELIANCE',
            signal_type=SignalType.ENTRY,
            price=Decimal('2500.0'),
            quantity=100,
            reason='Breakout detected',
            confidence_score=0.8,
            timestamp=datetime.now()
        )

        transformed_signal = await algorithm._transform_scanner_signal(scanner_signal, context)

        assert transformed_signal is not None
        assert transformed_signal.id.startswith('test_algo_')
        assert transformed_signal.symbol == 'RELIANCE'
        assert transformed_signal.confidence_score == 0.8 * config['confidence_multiplier']


class TestAlgorithmManager:
    """Test suite for AlgorithmManager."""

    @pytest.fixture
    def scanner_adapter(self):
        """Mock scanner adapter."""
        return Mock(spec=ScannerIntegrationAdapter)

    @pytest.fixture
    def data_adapter(self):
        """Mock data adapter."""
        return Mock(spec=DuckDBDataAdapter)

    @pytest.fixture
    def query_optimizer(self):
        """Mock query optimizer."""
        return Mock(spec=QueryOptimizer)

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'max_concurrent_algorithms': 5,
            'execution_timeout': 30.0,
            'performance_monitoring': True
        }

    @pytest.fixture
    def context(self):
        """Test algorithm context."""
        return AlgorithmContext(
            trading_date=date.today(),
            current_time=time(9, 30),
            account_balance=Decimal('100000')
        )

    def test_manager_initialization(self, scanner_adapter, data_adapter, query_optimizer, config):
        """Test algorithm manager initialization."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        assert manager.config == config
        assert manager.scanner_adapter == scanner_adapter
        assert manager.data_adapter == data_adapter
        assert manager.query_optimizer == query_optimizer
        assert len(manager.algorithms) == 0
        assert len(manager.active_algorithms) == 0

    @pytest.mark.asyncio
    async def test_register_algorithm(self, scanner_adapter, data_adapter, query_optimizer, config):
        """Test algorithm registration."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        algorithm = TradingAlgorithm('test_algo', 'Test Algorithm', {})
        success = await manager.register_algorithm(algorithm)

        assert success is True
        assert 'test_algo' in manager.algorithms
        assert manager.algorithms['test_algo'] == algorithm

    @pytest.mark.asyncio
    async def test_register_duplicate_algorithm(self, scanner_adapter, data_adapter, query_optimizer, config):
        """Test registering duplicate algorithm."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        algorithm1 = TradingAlgorithm('test_algo', 'Test Algorithm 1', {})
        algorithm2 = TradingAlgorithm('test_algo', 'Test Algorithm 2', {})

        success1 = await manager.register_algorithm(algorithm1)
        success2 = await manager.register_algorithm(algorithm2)

        assert success1 is True
        assert success2 is False
        assert manager.algorithms['test_algo'] == algorithm1

    @pytest.mark.asyncio
    async def test_activate_algorithm(self, scanner_adapter, data_adapter, query_optimizer, config, context):
        """Test algorithm activation."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        # Mock algorithm with async initialize method
        algorithm = Mock(spec=TradingAlgorithm)
        algorithm.algorithm_id = 'test_algo'
        algorithm.name = 'Test Algorithm'
        algorithm.initialize = AsyncMock(return_value=True)

        await manager.register_algorithm(algorithm)
        success = await manager.activate_algorithm('test_algo', context)

        assert success is True
        assert 'test_algo' in manager.active_algorithms
        algorithm.initialize.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_activate_nonexistent_algorithm(self, scanner_adapter, data_adapter, query_optimizer, config, context):
        """Test activating non-existent algorithm."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        success = await manager.activate_algorithm('nonexistent', context)

        assert success is False

    @pytest.mark.asyncio
    async def test_execute_algorithms(self, scanner_adapter, data_adapter, query_optimizer, config, context):
        """Test executing multiple algorithms."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        # Mock algorithm
        algorithm = Mock(spec=TradingAlgorithm)
        algorithm.algorithm_id = 'test_algo'
        algorithm.name = 'Test Algorithm'
        algorithm.initialize = AsyncMock(return_value=True)
        algorithm.process_market_data = AsyncMock(return_value=AlgorithmResult())

        await manager.register_algorithm(algorithm)
        await manager.activate_algorithm('test_algo', context)

        bars = [
            Bar(
                timestamp=datetime.now(),
                symbol='RELIANCE',
                open=Decimal('2500.0'),
                high=Decimal('2510.0'),
                low=Decimal('2495.0'),
                close=Decimal('2505.0'),
                volume=10000,
                timeframe='1m'
            )
        ]

        results = await manager.execute_algorithms(bars, context)

        assert 'test_algo' in results
        assert isinstance(results['test_algo'], AlgorithmResult)
        algorithm.process_market_data.assert_called_once()

    def test_get_algorithm_status(self, scanner_adapter, data_adapter, query_optimizer, config):
        """Test getting algorithm status."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        algorithm = TradingAlgorithm('test_algo', 'Test Algorithm', {})
        manager.algorithms['test_algo'] = algorithm

        status = manager.get_algorithm_status()

        assert 'test_algo' in status
        assert status['test_algo']['is_active'] is False
        assert status['test_algo']['info']['algorithm_id'] == 'test_algo'

    def test_get_performance_summary_no_history(self, scanner_adapter, data_adapter, query_optimizer, config):
        """Test performance summary with no execution history."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        summary = manager.get_performance_summary()

        assert summary['total_executions'] == 0
        assert len(summary['algorithms']) == 0

    @pytest.mark.asyncio
    async def test_optimize_algorithm_parameters(self, scanner_adapter, data_adapter, query_optimizer, config):
        """Test algorithm parameter optimization."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        algorithm = TradingAlgorithm('test_algo', 'Test Algorithm', {'param1': 'value1'})
        await manager.register_algorithm(algorithm)

        optimization_config = {
            'optimization_method': 'grid_search',
            'parameter_ranges': {'param1': ['value1', 'value2']}
        }

        result = await manager.optimize_algorithm_parameters('test_algo', optimization_config)

        assert result['status'] == 'completed'
        assert result['algorithm_id'] == 'test_algo'
        assert 'optimized_parameters' in result

    @pytest.mark.asyncio
    async def test_optimize_nonexistent_algorithm(self, scanner_adapter, data_adapter, query_optimizer, config):
        """Test optimizing non-existent algorithm."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        result = await manager.optimize_algorithm_parameters('nonexistent', {})

        assert result['status'] == 'error'
        assert 'not found' in result['message']

    def test_clear_execution_history(self, scanner_adapter, data_adapter, query_optimizer, config):
        """Test clearing execution history."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        # Add some mock history
        manager.execution_history = [
            {'timestamp': datetime.now() - timedelta(days=40), 'results': {}},
            {'timestamp': datetime.now() - timedelta(days=20), 'results': {}},
            {'timestamp': datetime.now() - timedelta(days=5), 'results': {}}
        ]

        removed_count = manager.clear_execution_history(days_to_keep=30)

        assert removed_count == 1
        assert len(manager.execution_history) == 2

    @pytest.mark.asyncio
    async def test_error_handling_in_execution(self, scanner_adapter, data_adapter, query_optimizer, config, context):
        """Test error handling during algorithm execution."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        # Mock algorithm that raises exception
        algorithm = Mock(spec=TradingAlgorithm)
        algorithm.algorithm_id = 'failing_algo'
        algorithm.name = 'Failing Algorithm'
        algorithm.initialize = AsyncMock(return_value=True)
        algorithm.process_market_data = AsyncMock(side_effect=Exception("Algorithm failed"))

        await manager.register_algorithm(algorithm)
        await manager.activate_algorithm('failing_algo', context)

        bars = [
            Bar(
                timestamp=datetime.now(),
                symbol='RELIANCE',
                open=Decimal('2500.0'),
                high=Decimal('2510.0'),
                low=Decimal('2495.0'),
                close=Decimal('2505.0'),
                volume=10000,
                timeframe='1m'
            )
        ]

        results = await manager.execute_algorithms(bars, context)

        assert 'failing_algo' in results
        assert len(results['failing_algo'].error_messages) > 0
        assert 'Algorithm failed' in results['failing_algo'].error_messages[0]

    @pytest.mark.asyncio
    async def test_multiple_algorithm_execution(self, scanner_adapter, data_adapter, query_optimizer, config, context):
        """Test executing multiple algorithms simultaneously."""
        manager = AlgorithmManager(config, scanner_adapter, data_adapter, query_optimizer)

        # Create multiple mock algorithms
        algorithms = []
        for i in range(3):
            algorithm = Mock(spec=TradingAlgorithm)
            algorithm.algorithm_id = f'algo_{i}'
            algorithm.name = f'Algorithm {i}'
            algorithm.initialize = AsyncMock(return_value=True)
            algorithm.process_market_data = AsyncMock(return_value=AlgorithmResult())

            await manager.register_algorithm(algorithm)
            await manager.activate_algorithm(f'algo_{i}', context)
            algorithms.append(algorithm)

        bars = [
            Bar(
                timestamp=datetime.now(),
                symbol='RELIANCE',
                open=Decimal('2500.0'),
                high=Decimal('2510.0'),
                low=Decimal('2495.0'),
                close=Decimal('2505.0'),
                volume=10000,
                timeframe='1m'
            )
        ]

        results = await manager.execute_algorithms(bars, context)

        assert len(results) == 3
        for i in range(3):
            assert f'algo_{i}' in results
            algorithms[i].process_market_data.assert_called_once()
