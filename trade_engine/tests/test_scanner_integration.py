"""
Test Scanner Integration
========================

Tests for scanner integration adapter functionality.
Validates algorithm loading, execution, and signal generation.
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from trade_engine.adapters.scanner_adapter import ScannerIntegrationAdapter, ScannerAlgorithm
from trade_engine.domain.models import Signal, SignalType


class TestScannerAlgorithm:
    """Test suite for ScannerAlgorithm."""

    def test_algorithm_creation(self):
        """Test creating a scanner algorithm."""
        algorithm = ScannerAlgorithm(
            algorithm_id="test_scanner",
            name="Test Scanner",
            description="A test scanner algorithm",
            parameters={"param1": "value1", "param2": 42},
            rule_definitions=[{"rule": "test_rule"}]
        )

        assert algorithm.algorithm_id == "test_scanner"
        assert algorithm.name == "Test Scanner"
        assert algorithm.description == "A test scanner algorithm"
        assert algorithm.parameters == {"param1": "value1", "param2": 42}
        assert algorithm.rule_definitions == [{"rule": "test_rule"}]

    def test_algorithm_to_dict(self):
        """Test converting algorithm to dictionary."""
        algorithm = ScannerAlgorithm(
            algorithm_id="test_scanner",
            name="Test Scanner",
            description="A test scanner algorithm",
            parameters={"param1": "value1"}
        )

        result = algorithm.to_dict()

        assert result['algorithm_id'] == "test_scanner"
        assert result['name'] == "Test Scanner"
        assert result['parameters'] == {"param1": "value1"}


class TestScannerIntegrationAdapter:
    """Test suite for ScannerIntegrationAdapter."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'scanner': {
                'max_workers': 4,
                'default_parameters': {
                    'min_volume_multiplier': 1.5,
                    'min_price_move': 0.02
                }
            }
        }

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing."""
        return pd.DataFrame({
            'symbol': ['RELIANCE', 'TCS', 'RELIANCE', 'TCS', 'RELIANCE'],
            'timestamp': [
                datetime(2024, 1, 1, 9, 15),
                datetime(2024, 1, 1, 9, 16),
                datetime(2024, 1, 1, 9, 17),
                datetime(2024, 1, 1, 9, 18),
                datetime(2024, 1, 1, 9, 19)
            ],
            'open': [2500.0, 3200.0, 2505.0, 3205.0, 2510.0],
            'high': [2510.0, 3210.0, 2515.0, 3215.0, 2520.0],
            'low': [2495.0, 3195.0, 2500.0, 3200.0, 2505.0],
            'close': [2505.0, 3205.0, 2510.0, 3210.0, 2515.0],
            'volume': [10000, 15000, 12000, 16000, 11000]
        })

    @pytest.mark.asyncio
    async def test_adapter_initialization(self, config):
        """Test adapter initialization."""
        adapter = ScannerIntegrationAdapter(config)
        assert adapter.config == config
        assert adapter.algorithms == {}

    @pytest.mark.asyncio
    async def test_load_breakout_scanner(self, config):
        """Test loading breakout scanner algorithm."""
        adapter = ScannerIntegrationAdapter(config)

        algorithm = await adapter.load_scanner_algorithm("breakout_scanner")

        assert algorithm is not None
        assert algorithm.algorithm_id == "breakout_scanner"
        assert algorithm.name == "Breakout Scanner"
        assert 'min_volume_multiplier' in algorithm.parameters
        assert 'min_price_move' in algorithm.parameters

    @pytest.mark.asyncio
    async def test_load_momentum_scanner(self, config):
        """Test loading momentum scanner algorithm."""
        adapter = ScannerIntegrationAdapter(config)

        algorithm = await adapter.load_scanner_algorithm("momentum_scanner")

        assert algorithm is not None
        assert algorithm.algorithm_id == "momentum_scanner"
        assert algorithm.name == "Momentum Scanner"
        assert 'rsi_period' in algorithm.parameters
        assert 'rsi_overbought' in algorithm.parameters

    @pytest.mark.asyncio
    async def test_load_unknown_algorithm(self, config):
        """Test loading unknown algorithm."""
        adapter = ScannerIntegrationAdapter(config)

        algorithm = await adapter.load_scanner_algorithm("unknown_scanner")

        assert algorithm is None

    @pytest.mark.asyncio
    async def test_execute_breakout_scanner(self, config, sample_market_data):
        """Test executing breakout scanner on sample data."""
        adapter = ScannerIntegrationAdapter(config)

        algorithm = await adapter.load_scanner_algorithm("breakout_scanner")
        assert algorithm is not None

        signals = await adapter.execute_scanner_on_data(algorithm, sample_market_data)

        assert isinstance(signals, list)
        # Breakout scanner may or may not generate signals depending on data
        for signal in signals:
            assert isinstance(signal, Signal)
            assert signal.symbol in ['RELIANCE', 'TCS']
            assert signal.signal_type == SignalType.ENTRY
            assert signal.quantity > 0
            assert 0 <= signal.confidence_score <= 1

    @pytest.mark.asyncio
    async def test_execute_momentum_scanner(self, config, sample_market_data):
        """Test executing momentum scanner on sample data."""
        adapter = ScannerIntegrationAdapter(config)

        algorithm = await adapter.load_scanner_algorithm("momentum_scanner")
        assert algorithm is not None

        signals = await adapter.execute_scanner_on_data(algorithm, sample_market_data)

        assert isinstance(signals, list)
        # Momentum scanner may or may not generate signals depending on data
        for signal in signals:
            assert isinstance(signal, Signal)
            assert signal.symbol in ['RELIANCE', 'TCS']
            assert signal.signal_type in [SignalType.ENTRY, SignalType.EXIT]
            assert signal.quantity > 0
            assert 0 <= signal.confidence_score <= 1

    @pytest.mark.asyncio
    async def test_validate_scanner_output(self, config):
        """Test scanner output validation."""
        adapter = ScannerIntegrationAdapter(config)

        # Create valid signals
        signals = [
            Signal(
                id="test_signal_1",
                symbol="RELIANCE",
                signal_type=SignalType.ENTRY,
                price=Decimal('2500.0'),
                quantity=100,
                reason="Test signal",
                confidence_score=0.8,
                timestamp=datetime(2024, 1, 1, 9, 15)
            ),
            Signal(
                id="test_signal_2",
                symbol="TCS",
                signal_type=SignalType.EXIT,
                price=Decimal('3200.0'),
                quantity=50,
                reason="Test signal 2",
                confidence_score=0.7,
                timestamp=datetime(2024, 1, 1, 9, 16)
            )
        ]

        validation_results = await adapter.validate_scanner_output(signals)

        assert validation_results['total_signals'] == 2
        assert validation_results['valid_signals'] == 2
        assert validation_results['invalid_signals'] == 0
        assert validation_results['validation_passed'] is True
        assert 'signals_by_type' in validation_results
        assert 'signals_by_symbol' in validation_results
        assert 'confidence_distribution' in validation_results

    @pytest.mark.asyncio
    async def test_validate_invalid_signals(self, config):
        """Test validation of invalid signals."""
        adapter = ScannerIntegrationAdapter(config)

        # Create signals with validation issues
        signals = [
            Signal(
                id="invalid_signal_1",
                symbol="",  # Empty symbol
                signal_type=SignalType.ENTRY,
                price=Decimal('2500.0'),
                quantity=100,
                reason="Invalid signal",
                confidence_score=0.8,
                timestamp=datetime(2024, 1, 1, 9, 15)
            ),
            Signal(
                id="invalid_signal_2",
                symbol="TCS",
                signal_type=SignalType.ENTRY,
                price=Decimal('3200.0'),
                quantity=-50,  # Negative quantity
                reason="Invalid signal 2",
                confidence_score=1.5,  # Invalid confidence (> 1)
                timestamp=datetime(2024, 1, 1, 9, 16)
            )
        ]

        validation_results = await adapter.validate_scanner_output(signals)

        assert validation_results['total_signals'] == 2
        assert validation_results['valid_signals'] == 0
        assert validation_results['invalid_signals'] == 2
        assert validation_results['validation_passed'] is False
        assert len(validation_results['issues']) > 0

    @pytest.mark.asyncio
    async def test_get_scanner_performance_metrics(self, config):
        """Test getting scanner performance metrics."""
        adapter = ScannerIntegrationAdapter(config)

        metrics = await adapter.get_scanner_performance_metrics("breakout_scanner")

        assert isinstance(metrics, dict)
        assert metrics['scanner_name'] == "breakout_scanner"
        assert 'total_executions' in metrics
        assert 'success_rate' in metrics
        assert 'average_execution_time_ms' in metrics

    @pytest.mark.asyncio
    async def test_update_scanner_parameters(self, config):
        """Test updating scanner parameters."""
        adapter = ScannerIntegrationAdapter(config)

        # First load an algorithm
        algorithm = await adapter.load_scanner_algorithm("breakout_scanner")
        assert algorithm is not None

        # Update parameters
        new_params = {'min_volume_multiplier': 2.0, 'new_param': 'test_value'}
        success = await adapter.update_scanner_parameters("breakout_scanner", new_params)

        assert success is True

        # Verify parameters were updated
        updated_algorithm = adapter.algorithms["breakout_scanner"]
        assert updated_algorithm.parameters['min_volume_multiplier'] == 2.0
        assert updated_algorithm.parameters['new_param'] == 'test_value'

    @pytest.mark.asyncio
    async def test_update_nonexistent_scanner(self, config):
        """Test updating parameters for non-existent scanner."""
        adapter = ScannerIntegrationAdapter(config)

        success = await adapter.update_scanner_parameters("nonexistent_scanner", {'param': 'value'})

        assert success is False

    def test_get_available_algorithms(self, config):
        """Test getting available algorithms."""
        adapter = ScannerIntegrationAdapter(config)

        algorithms = adapter.get_available_algorithms()

        assert isinstance(algorithms, list)
        assert 'breakout_scanner' in algorithms
        assert 'momentum_scanner' in algorithms

    @pytest.mark.asyncio
    async def test_execute_bulk_scanners(self, config, sample_market_data):
        """Test executing multiple scanners in bulk."""
        adapter = ScannerIntegrationAdapter(config)

        algorithms = ['breakout_scanner', 'momentum_scanner']
        results = await adapter.execute_bulk_scanners(algorithms, sample_market_data)

        assert isinstance(results, dict)
        assert len(results) == 2
        assert 'breakout_scanner' in results
        assert 'momentum_scanner' in results

        # Each result should be a list of signals
        for algorithm_results in results.values():
            assert isinstance(algorithm_results, list)
            for signal in algorithm_results:
                if signal:  # Only check non-empty signals
                    assert isinstance(signal, Signal)

    @pytest.mark.asyncio
    async def test_error_handling_in_execution(self, config):
        """Test error handling during scanner execution."""
        adapter = ScannerIntegrationAdapter(config)

        # Test with empty dataframe
        empty_data = pd.DataFrame()
        algorithm = await adapter.load_scanner_algorithm("breakout_scanner")

        if algorithm:
            signals = await adapter.execute_scanner_on_data(algorithm, empty_data)
            assert isinstance(signals, list)
            # Should handle empty data gracefully

    @pytest.mark.asyncio
    async def test_signal_properties(self, config, sample_market_data):
        """Test that generated signals have all required properties."""
        adapter = ScannerIntegrationAdapter(config)

        algorithm = await adapter.load_scanner_algorithm("breakout_scanner")
        assert algorithm is not None

        signals = await adapter.execute_scanner_on_data(algorithm, sample_market_data)

        for signal in signals:
            assert hasattr(signal, 'id')
            assert hasattr(signal, 'symbol')
            assert hasattr(signal, 'signal_type')
            assert hasattr(signal, 'price')
            assert hasattr(signal, 'quantity')
            assert hasattr(signal, 'reason')
            assert hasattr(signal, 'confidence_score')
            assert hasattr(signal, 'timestamp')

            # Validate types
            assert isinstance(signal.id, str)
            assert isinstance(signal.symbol, str)
            assert isinstance(signal.price, Decimal)
            assert isinstance(signal.quantity, int)
            assert isinstance(signal.confidence_score, (int, float))
            assert 0 <= signal.confidence_score <= 1
