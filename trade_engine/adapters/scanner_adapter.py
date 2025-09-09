"""
Scanner Integration Adapter
===========================

Integrates trade engine with the existing scanner/rule infrastructure
for algorithm implementation and signal generation.
"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import date, time
from decimal import Decimal
import pandas as pd

from ..domain.models import Signal, SignalType
from src.infrastructure.logging import get_logger

# Import rule engine components
try:
    from src.rules.engine.rule_engine import RuleEngine
    from src.rules.engine.signal_generator import TradingSignal as RuleSignal, SignalGenerator
    from src.rules.schema.rule_types import SignalType as RuleSignalType
    RULE_ENGINE_AVAILABLE = True
except ImportError:
    logger = get_logger(__name__)
    logger.warning("Rule engine not available, using fallback implementation")
    RULE_ENGINE_AVAILABLE = False
    RuleEngine = None
    RuleSignal = None
    SignalGenerator = None
    RuleSignalType = None

logger = get_logger(__name__)


class ScannerAlgorithm:
    """
    Represents a scanner algorithm that can be executed on market data.
    """

    def __init__(self, algorithm_id: str, name: str, description: str,
                 parameters: Dict[str, Any], rule_definitions: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize scanner algorithm.

        Args:
            algorithm_id: Unique identifier for the algorithm
            name: Human-readable name
            description: Description of what the algorithm does
            parameters: Algorithm-specific parameters
            rule_definitions: Optional rule definitions for rule-based algorithms
        """
        self.algorithm_id = algorithm_id
        self.name = name
        self.description = description
        self.parameters = parameters
        self.rule_definitions = rule_definitions or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'algorithm_id': self.algorithm_id,
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters,
            'rule_definitions': self.rule_definitions
        }


class ScannerIntegrationAdapter:
    """
    Adapter for integrating scanner algorithms with the trade engine.

    Provides a unified interface for:
    - Loading and managing scanner algorithms
    - Executing algorithms on market data
    - Converting scanner results to trading signals
    - Managing algorithm performance and validation
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize scanner integration adapter.

        Args:
            config: Configuration dictionary with scanner settings
        """
        self.config = config
        self.rule_engine = None
        self.signal_generator = None
        self.algorithms: Dict[str, ScannerAlgorithm] = {}

        # Initialize rule engine if available
        if RULE_ENGINE_AVAILABLE:
            try:
                self.rule_engine = RuleEngine()
                self.signal_generator = SignalGenerator()
                logger.info("Rule engine initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize rule engine: {e}")
                self.rule_engine = None
                self.signal_generator = None

        logger.info("ScannerIntegrationAdapter initialized")

    async def load_scanner_algorithm(self, algorithm_id: str) -> Optional[ScannerAlgorithm]:
        """
        Load a scanner algorithm by ID.

        Args:
            algorithm_id: Algorithm identifier

        Returns:
            ScannerAlgorithm instance or None if not found
        """
        # For now, create a basic algorithm structure
        # In a real implementation, this would load from a database or file system
        if algorithm_id == "breakout_scanner":
            algorithm = ScannerAlgorithm(
                algorithm_id=algorithm_id,
                name="Breakout Scanner",
                description="Detects price breakouts with volume confirmation",
                parameters={
                    'min_volume_multiplier': 1.5,
                    'min_price_move': 0.02,
                    'lookback_periods': 20,
                    'confirmation_periods': 5
                }
            )
        elif algorithm_id == "momentum_scanner":
            algorithm = ScannerAlgorithm(
                algorithm_id=algorithm_id,
                name="Momentum Scanner",
                description="Identifies momentum-based trading opportunities",
                parameters={
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30,
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'macd_signal': 9
                }
            )
        else:
            logger.warning(f"Algorithm {algorithm_id} not found")
            return None

        self.algorithms[algorithm_id] = algorithm
        logger.info(f"Loaded algorithm: {algorithm.name}")
        return algorithm

    async def execute_scanner_on_data(self, algorithm: ScannerAlgorithm,
                                    data: pd.DataFrame) -> List[Signal]:
        """
        Execute scanner algorithm on market data.

        Args:
            algorithm: Scanner algorithm to execute
            data: Market data as pandas DataFrame

        Returns:
            List of trading signals
        """
        try:
            signals = []

            if algorithm.algorithm_id == "breakout_scanner":
                signals = await self._execute_breakout_scanner(algorithm, data)
            elif algorithm.algorithm_id == "momentum_scanner":
                signals = await self._execute_momentum_scanner(algorithm, data)
            else:
                logger.warning(f"Unknown algorithm type: {algorithm.algorithm_id}")
                return []

            logger.info(f"Executed {algorithm.name} on {len(data)} data points, generated {len(signals)} signals")
            return signals

        except Exception as e:
            logger.error(f"Error executing scanner {algorithm.algorithm_id}: {e}")
            return []

    async def _execute_breakout_scanner(self, algorithm: ScannerAlgorithm,
                                      data: pd.DataFrame) -> List[Signal]:
        """
        Execute breakout scanner algorithm.

        Args:
            algorithm: Breakout scanner algorithm
            data: Market data

        Returns:
            List of breakout signals
        """
        signals = []
        params = algorithm.parameters

        # Group data by symbol for analysis
        for symbol in data['symbol'].unique():
            symbol_data = data[data['symbol'] == symbol].copy()

            if len(symbol_data) < params['lookback_periods']:
                continue

            # Calculate breakout conditions
            symbol_data = symbol_data.sort_values('timestamp')

            # Simple breakout logic (would be more sophisticated in real implementation)
            for idx, row in symbol_data.iterrows():
                try:
                    # Check for volume spike and price breakout
                    recent_high = symbol_data.loc[:idx, 'high'].tail(params['lookback_periods']).max()
                    recent_volume_avg = symbol_data.loc[:idx, 'volume'].tail(params['lookback_periods']).mean()

                    current_price = row['close']
                    current_volume = row['volume']

                    # Breakout conditions
                    price_breakout = current_price > recent_high * (1 + params['min_price_move'])
                    volume_spike = current_volume > recent_volume_avg * params['min_volume_multiplier']

                    if price_breakout and volume_spike:
                        signal = Signal(
                            id=f"breakout_{symbol}_{row['timestamp'].strftime('%Y%m%d_%H%M%S')}",
                            symbol=symbol,
                            signal_type=SignalType.ENTRY,
                            price=Decimal(str(current_price)),
                            quantity=100,  # Default quantity
                            reason=f"Breakout detected: price {current_price:.2f}, volume {current_volume}",
                            confidence_score=0.8,
                            timestamp=row['timestamp']
                        )
                        signals.append(signal)

                except Exception as e:
                    logger.warning(f"Error processing breakout for {symbol}: {e}")
                    continue

        return signals

    async def _execute_momentum_scanner(self, algorithm: ScannerAlgorithm,
                                      data: pd.DataFrame) -> List[Signal]:
        """
        Execute momentum scanner algorithm.

        Args:
            algorithm: Momentum scanner algorithm
            data: Market data

        Returns:
            List of momentum signals
        """
        signals = []
        params = algorithm.parameters

        # Group data by symbol for analysis
        for symbol in data['symbol'].unique():
            symbol_data = data[data['symbol'] == symbol].copy()

            if len(symbol_data) < params['rsi_period'] + 10:  # Need enough data for calculations
                continue

            # Calculate RSI and MACD (simplified implementation)
            symbol_data = symbol_data.sort_values('timestamp')

            # Simple RSI calculation (would use TA-Lib or similar in real implementation)
            symbol_data['price_change'] = symbol_data['close'].diff()
            symbol_data['gain'] = symbol_data['price_change'].clip(lower=0)
            symbol_data['loss'] = -symbol_data['price_change'].clip(upper=0)

            # Rolling averages for RSI
            symbol_data['avg_gain'] = symbol_data['gain'].rolling(window=params['rsi_period']).mean()
            symbol_data['avg_loss'] = symbol_data['loss'].rolling(window=params['rsi_period']).mean()
            symbol_data['rs'] = symbol_data['avg_gain'] / symbol_data['avg_loss']
            symbol_data['rsi'] = 100 - (100 / (1 + symbol_data['rs']))

            # Generate signals based on RSI levels
            for idx, row in symbol_data.iterrows():
                try:
                    rsi = row['rsi']
                    current_price = row['close']

                    if pd.notna(rsi):
                        if rsi < params['rsi_oversold']:
                            # Oversold condition - potential buy signal
                            signal = Signal(
                                id=f"momentum_buy_{symbol}_{row['timestamp'].strftime('%Y%m%d_%H%M%S')}",
                                symbol=symbol,
                                signal_type=SignalType.ENTRY,
                                price=Decimal(str(current_price)),
                                quantity=100,
                                reason=f"Oversold RSI: {rsi:.2f}",
                                confidence_score=0.7,
                                timestamp=row['timestamp']
                            )
                            signals.append(signal)

                        elif rsi > params['rsi_overbought']:
                            # Overbought condition - potential sell signal
                            signal = Signal(
                                id=f"momentum_sell_{symbol}_{row['timestamp'].strftime('%Y%m%d_%H%M%S')}",
                                symbol=symbol,
                                signal_type=SignalType.EXIT,
                                price=Decimal(str(current_price)),
                                quantity=100,
                                reason=f"Overbought RSI: {rsi:.2f}",
                                confidence_score=0.7,
                                timestamp=row['timestamp']
                            )
                            signals.append(signal)

                except Exception as e:
                    logger.warning(f"Error processing momentum for {symbol}: {e}")
                    continue

        return signals

    async def validate_scanner_output(self, signals: List[Signal]) -> Dict[str, Any]:
        """
        Validate scanner output for consistency and quality.

        Args:
            signals: List of signals to validate

        Returns:
            Validation results dictionary
        """
        try:
            validation_results = {
                'total_signals': len(signals),
                'valid_signals': 0,
                'invalid_signals': 0,
                'signals_by_type': {},
                'signals_by_symbol': {},
                'confidence_distribution': {
                    'high': 0,    # > 0.8
                    'medium': 0,  # 0.6-0.8
                    'low': 0      # < 0.6
                },
                'issues': []
            }

            for signal in signals:
                # Basic validation
                is_valid = True

                # Check required fields
                if not signal.symbol or not signal.price or signal.quantity <= 0:
                    validation_results['issues'].append(f"Invalid signal data: {signal.id}")
                    is_valid = False

                # Check confidence score range
                if not (0 <= signal.confidence_score <= 1):
                    validation_results['issues'].append(f"Invalid confidence score for {signal.id}: {signal.confidence_score}")
                    is_valid = False

                # Check timestamp
                if not signal.timestamp:
                    validation_results['issues'].append(f"Missing timestamp for {signal.id}")
                    is_valid = False

                if is_valid:
                    validation_results['valid_signals'] += 1

                    # Categorize by type
                    signal_type = signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type)
                    validation_results['signals_by_type'][signal_type] = validation_results['signals_by_type'].get(signal_type, 0) + 1

                    # Categorize by symbol
                    validation_results['signals_by_symbol'][signal.symbol] = validation_results['signals_by_symbol'].get(signal.symbol, 0) + 1

                    # Categorize by confidence
                    if signal.confidence_score > 0.8:
                        validation_results['confidence_distribution']['high'] += 1
                    elif signal.confidence_score > 0.6:
                        validation_results['confidence_distribution']['medium'] += 1
                    else:
                        validation_results['confidence_distribution']['low'] += 1
                else:
                    validation_results['invalid_signals'] += 1

            validation_results['validation_passed'] = validation_results['invalid_signals'] == 0

            logger.info(f"Validated {len(signals)} signals: {validation_results['valid_signals']} valid, {validation_results['invalid_signals']} invalid")
            return validation_results

        except Exception as e:
            logger.error(f"Error validating scanner output: {e}")
            return {
                'validation_passed': False,
                'error': str(e),
                'total_signals': len(signals)
            }

    async def get_scanner_performance_metrics(self, scanner_name: str) -> Dict[str, Any]:
        """
        Get performance metrics for a scanner.

        Args:
            scanner_name: Name of the scanner

        Returns:
            Performance metrics dictionary
        """
        # This would typically query a database for historical performance
        # For now, return mock metrics
        return {
            'scanner_name': scanner_name,
            'total_executions': 100,
            'average_signals_per_execution': 5.2,
            'average_execution_time_ms': 150,
            'success_rate': 0.78,
            'last_execution': '2024-01-01T10:30:00Z',
            'performance_trend': 'improving'
        }

    async def update_scanner_parameters(self, scanner_name: str,
                                      parameters: Dict[str, Any]) -> bool:
        """
        Update scanner parameters.

        Args:
            scanner_name: Name of the scanner
            parameters: New parameters to update

        Returns:
            True if update successful, False otherwise
        """
        try:
            if scanner_name in self.algorithms:
                algorithm = self.algorithms[scanner_name]
                algorithm.parameters.update(parameters)
                logger.info(f"Updated parameters for scanner {scanner_name}: {parameters}")
                return True
            else:
                logger.warning(f"Scanner {scanner_name} not found")
                return False
        except Exception as e:
            logger.error(f"Error updating scanner parameters: {e}")
            return False

    def get_available_algorithms(self) -> List[str]:
        """
        Get list of available scanner algorithms.

        Returns:
            List of algorithm IDs
        """
        return list(self.algorithms.keys()) + ['breakout_scanner', 'momentum_scanner']

    async def execute_bulk_scanners(self, algorithms: List[str],
                                  data: pd.DataFrame) -> Dict[str, List[Signal]]:
        """
        Execute multiple scanners in parallel.

        Args:
            algorithms: List of algorithm IDs to execute
            data: Market data for scanning

        Returns:
            Dictionary mapping algorithm IDs to their signals
        """
        results = {}

        # Execute scanners concurrently
        tasks = []
        for algorithm_id in algorithms:
            algorithm = await self.load_scanner_algorithm(algorithm_id)
            if algorithm:
                task = self.execute_scanner_on_data(algorithm, data)
                tasks.append((algorithm_id, task))

        # Wait for all tasks to complete
        for algorithm_id, task in tasks:
            try:
                signals = await task
                results[algorithm_id] = signals
                logger.info(f"Completed bulk execution for {algorithm_id}: {len(signals)} signals")
            except Exception as e:
                logger.error(f"Error in bulk execution for {algorithm_id}: {e}")
                results[algorithm_id] = []

        return results
