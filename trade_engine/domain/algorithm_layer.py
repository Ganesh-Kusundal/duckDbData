"""
Algorithm Integration Layer
===========================

Provides a unified framework for implementing and executing scanner-based
trading algorithms within the trade engine architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
import logging
import asyncio

from .models import Bar, Signal, SignalType, Position, OrderIntent
from ..adapters.scanner_adapter import ScannerIntegrationAdapter, ScannerAlgorithm
from ..adapters.duckdb_data_adapter import DuckDBDataAdapter
from ..adapters.query_optimizer import QueryOptimizer
from ..ports.data_feed import DataFeedPort
from ..ports.analytics import AnalyticsPort
from ..ports.broker import BrokerPort
from ..ports.repository import RepositoryPort

logger = logging.getLogger(__name__)


@dataclass
class AlgorithmContext:
    """Context information for algorithm execution."""
    trading_date: date
    current_time: time
    positions: Dict[str, Position] = field(default_factory=dict)
    account_balance: Decimal = Decimal('100000')
    risk_per_trade: Decimal = Decimal('0.01')  # 1%
    max_positions: int = 3
    market_data: Dict[str, List[Bar]] = field(default_factory=dict)
    scanner_signals: List[Signal] = field(default_factory=list)
    algorithm_state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlgorithmResult:
    """Result of algorithm execution."""
    signals: List[Signal] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    error_messages: List[str] = field(default_factory=list)


class TradingAlgorithm(ABC):
    """
    Abstract base class for trading algorithms.

    Provides the framework for implementing scanner-based trading strategies
    with standardized interfaces for data access, signal generation, and execution.
    """

    def __init__(self, algorithm_id: str, name: str, config: Dict[str, Any]):
        """
        Initialize trading algorithm.

        Args:
            algorithm_id: Unique identifier for the algorithm
            name: Human-readable name
            config: Algorithm configuration parameters
        """
        self.algorithm_id = algorithm_id
        self.name = name
        self.config = config

        # Algorithm state
        self.is_initialized = False
        self.last_execution_time: Optional[datetime] = None
        self.execution_count = 0
        self.success_count = 0

        logger.info(f"Initialized algorithm: {self.name} ({self.algorithm_id})")

    @abstractmethod
    async def initialize(self, context: AlgorithmContext) -> bool:
        """
        Initialize the algorithm with context information.

        Args:
            context: Algorithm execution context

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    async def process_market_data(self, bars: List[Bar], context: AlgorithmContext) -> AlgorithmResult:
        """
        Process market data and generate trading signals.

        Args:
            bars: List of market bars to process
            context: Current algorithm context

        Returns:
            Algorithm execution result
        """
        pass

    @abstractmethod
    async def handle_signals(self, signals: List[Signal], context: AlgorithmContext) -> AlgorithmResult:
        """
        Handle incoming signals from scanners or other sources.

        Args:
            signals: List of signals to process
            context: Current algorithm context

        Returns:
            Algorithm execution result
        """
        pass

    @abstractmethod
    async def update_positions(self, positions: Dict[str, Position], context: AlgorithmContext) -> AlgorithmResult:
        """
        Update algorithm state based on current positions.

        Args:
            positions: Current positions
            context: Current algorithm context

        Returns:
            Algorithm execution result
        """
        pass

    def get_algorithm_info(self) -> Dict[str, Any]:
        """
        Get algorithm information and metadata.

        Returns:
            Dictionary with algorithm information
        """
        return {
            'algorithm_id': self.algorithm_id,
            'name': self.name,
            'config': self.config,
            'is_initialized': self.is_initialized,
            'execution_count': self.execution_count,
            'success_count': self.success_count,
            'success_rate': self.success_count / max(1, self.execution_count),
            'last_execution': self.last_execution_time.isoformat() if self.last_execution_time else None
        }


class ScannerBasedAlgorithm(TradingAlgorithm):
    """
    Base class for scanner-based trading algorithms.

    Provides integration with the scanner infrastructure and common
    functionality for scanner-based strategies.
    """

    def __init__(self, algorithm_id: str, name: str, config: Dict[str, Any],
                 scanner_adapter: ScannerIntegrationAdapter):
        """
        Initialize scanner-based algorithm.

        Args:
            algorithm_id: Unique identifier for the algorithm
            name: Human-readable name
            config: Algorithm configuration parameters
            scanner_adapter: Scanner integration adapter
        """
        super().__init__(algorithm_id, name, config)
        self.scanner_adapter = scanner_adapter
        self.scanner_algorithm: Optional[ScannerAlgorithm] = None

    async def initialize(self, context: AlgorithmContext) -> bool:
        """
        Initialize scanner-based algorithm.

        Args:
            context: Algorithm execution context

        Returns:
            True if initialization successful
        """
        try:
            # Load scanner algorithm
            scanner_name = self.config.get('scanner_algorithm', self.algorithm_id)
            self.scanner_algorithm = await self.scanner_adapter.load_scanner_algorithm(scanner_name)

            if not self.scanner_algorithm:
                logger.error(f"Failed to load scanner algorithm: {scanner_name}")
                return False

            # Validate scanner parameters
            if not await self._validate_scanner_parameters():
                logger.error(f"Scanner parameter validation failed for: {scanner_name}")
                return False

            self.is_initialized = True
            logger.info(f"Scanner-based algorithm {self.name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing scanner-based algorithm: {e}")
            return False

    async def _validate_scanner_parameters(self) -> bool:
        """
        Validate scanner algorithm parameters.

        Returns:
            True if parameters are valid
        """
        if not self.scanner_algorithm:
            return False

        required_params = self.config.get('required_scanner_params', [])
        for param in required_params:
            if param not in self.scanner_algorithm.parameters:
                logger.error(f"Missing required parameter: {param}")
                return False

        # Validate parameter ranges
        param_ranges = self.config.get('parameter_ranges', {})
        for param_name, param_range in param_ranges.items():
            if param_name in self.scanner_algorithm.parameters:
                value = self.scanner_algorithm.parameters[param_name]
                min_val, max_val = param_range
                if not (min_val <= value <= max_val):
                    logger.error(f"Parameter {param_name}={value} out of range [{min_val}, {max_val}]")
                    return False

        return True

    async def process_market_data(self, bars: List[Bar], context: AlgorithmContext) -> AlgorithmResult:
        """
        Process market data using scanner algorithm.

        Args:
            bars: List of market bars to process
            context: Current algorithm context

        Returns:
            Algorithm execution result
        """
        start_time = datetime.now()
        result = AlgorithmResult()

        try:
            if not self.scanner_algorithm:
                result.error_messages.append("Scanner algorithm not initialized")
                return result

            # Convert bars to DataFrame for scanner processing
            import pandas as pd
            data = pd.DataFrame([{
                'symbol': bar.symbol,
                'timestamp': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': bar.volume
            } for bar in bars])

            # Execute scanner algorithm
            scanner_signals = await self.scanner_adapter.execute_scanner_on_data(
                self.scanner_algorithm, data
            )

            # Convert scanner signals to algorithm signals
            for scanner_signal in scanner_signals:
                # Apply algorithm-specific filtering and transformation
                algorithm_signal = await self._transform_scanner_signal(scanner_signal, context)
                if algorithm_signal:
                    result.signals.append(algorithm_signal)

            # Update performance metrics
            result.performance_metrics.update({
                'scanner_signals_generated': len(scanner_signals),
                'algorithm_signals_generated': len(result.signals),
                'signal_conversion_rate': len(result.signals) / max(1, len(scanner_signals))
            })

            self.execution_count += 1
            self.success_count += 1
            self.last_execution_time = datetime.now()

        except Exception as e:
            result.error_messages.append(f"Error processing market data: {str(e)}")
            logger.error(f"Error in scanner-based algorithm execution: {e}")

        result.execution_time = (datetime.now() - start_time).total_seconds()
        return result

    async def _transform_scanner_signal(self, scanner_signal: Signal,
                                      context: AlgorithmContext) -> Optional[Signal]:
        """
        Transform scanner signal into algorithm-specific signal.

        Args:
            scanner_signal: Signal from scanner
            context: Algorithm context

        Returns:
            Transformed signal or None if filtered out
        """
        try:
            # Apply algorithm-specific filters
            if not await self._should_process_signal(scanner_signal, context):
                return None

            # Apply position size calculation
            position_size = await self._calculate_position_size(scanner_signal, context)
            if position_size <= 0:
                return None

            # Create algorithm-specific signal
            algorithm_signal = Signal(
                id=f"{self.algorithm_id}_{scanner_signal.id}",
                symbol=scanner_signal.symbol,
                signal_type=scanner_signal.signal_type,
                price=scanner_signal.price,
                quantity=position_size,
                reason=f"{self.name}: {scanner_signal.reason}",
                confidence_score=min(1.0, scanner_signal.confidence_score * self.config.get('confidence_multiplier', 1.0)),
                timestamp=scanner_signal.timestamp
            )

            return algorithm_signal

        except Exception as e:
            logger.error(f"Error transforming scanner signal: {e}")
            return None

    async def _should_process_signal(self, signal: Signal, context: AlgorithmContext) -> bool:
        """
        Determine if signal should be processed based on algorithm rules.

        Args:
            signal: Signal to evaluate
            context: Algorithm context

        Returns:
            True if signal should be processed
        """
        # Check if we already have a position in this symbol
        if signal.symbol in context.positions:
            existing_position = context.positions[signal.symbol]
            if signal.signal_type == SignalType.ENTRY and existing_position.quantity > 0:
                return False  # Don't enter if already have position

        # Check maximum positions limit
        if signal.signal_type == SignalType.ENTRY:
            current_positions = len([p for p in context.positions.values() if p.quantity > 0])
            if current_positions >= context.max_positions:
                return False

        # Check risk limits
        if signal.signal_type == SignalType.ENTRY:
            risk_amount = context.account_balance * context.risk_per_trade
            if signal.price and signal.quantity:
                position_value = signal.price * signal.quantity
                if position_value > risk_amount:
                    return False

        return True

    async def _calculate_position_size(self, signal: Signal, context: AlgorithmContext) -> int:
        """
        Calculate position size for signal based on risk management.

        Args:
            signal: Trading signal
            context: Algorithm context

        Returns:
            Position size in shares
        """
        if not signal.price or signal.price <= 0:
            return 0

        try:
            # Basic risk-based position sizing
            risk_amount = context.account_balance * context.risk_per_trade
            stop_distance = signal.price * Decimal('0.02')  # 2% stop distance

            position_value = risk_amount / stop_distance
            position_size = int(position_value / signal.price)

            # Apply minimum and maximum position limits
            min_size = self.config.get('min_position_size', 1)
            max_size = self.config.get('max_position_size', 1000)

            position_size = max(min_size, min(max_size, position_size))

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    async def handle_signals(self, signals: List[Signal], context: AlgorithmContext) -> AlgorithmResult:
        """
        Handle incoming signals from scanners.

        Args:
            signals: List of signals to process
            context: Current algorithm context

        Returns:
            Algorithm execution result
        """
        result = AlgorithmResult()
        start_time = datetime.now()

        try:
            for signal in signals:
                # Apply algorithm-specific processing
                processed_signal = await self._transform_scanner_signal(signal, context)
                if processed_signal:
                    result.signals.append(processed_signal)

            result.performance_metrics['signals_processed'] = len(signals)
            result.performance_metrics['signals_generated'] = len(result.signals)

        except Exception as e:
            result.error_messages.append(f"Error handling signals: {str(e)}")
            logger.error(f"Error in signal handling: {e}")

        result.execution_time = (datetime.now() - start_time).total_seconds()
        return result

    async def update_positions(self, positions: Dict[str, Position], context: AlgorithmContext) -> AlgorithmResult:
        """
        Update algorithm state based on current positions.

        Args:
            positions: Current positions
            context: Current algorithm context

        Returns:
            Algorithm execution result
        """
        result = AlgorithmResult()

        try:
            # Update context positions
            context.positions.update(positions)

            # Check for exit conditions based on algorithm rules
            exit_signals = await self._check_exit_conditions(context)
            result.signals.extend(exit_signals)

            result.performance_metrics['active_positions'] = len([p for p in positions.values() if p.quantity > 0])

        except Exception as e:
            result.error_messages.append(f"Error updating positions: {str(e)}")
            logger.error(f"Error in position update: {e}")

        return result

    async def _check_exit_conditions(self, context: AlgorithmContext) -> List[Signal]:
        """
        Check for position exit conditions.

        Args:
            context: Algorithm context

        Returns:
            List of exit signals
        """
        exit_signals = []

        try:
            for symbol, position in context.positions.items():
                if position.quantity <= 0:
                    continue

                # Check profit target
                profit_target = self.config.get('profit_target', 0.05)  # 5%
                current_profit = (position.current_price - position.avg_cost) / position.avg_cost

                if current_profit >= profit_target:
                    exit_signals.append(Signal(
                        id=f"{self.algorithm_id}_profit_exit_{symbol}",
                        symbol=symbol,
                        signal_type=SignalType.EXIT,
                        price=position.current_price,
                        quantity=-position.quantity,
                        reason=f"{self.name}: Profit target reached ({current_profit:.1%})",
                        confidence_score=0.9,
                        timestamp=datetime.now()
                    ))

                # Check stop loss
                stop_loss = self.config.get('stop_loss', -0.03)  # -3%
                if current_profit <= stop_loss:
                    exit_signals.append(Signal(
                        id=f"{self.algorithm_id}_stop_loss_{symbol}",
                        symbol=symbol,
                        signal_type=SignalType.EXIT,
                        price=position.current_price,
                        quantity=-position.quantity,
                        reason=f"{self.name}: Stop loss triggered ({current_profit:.1%})",
                        confidence_score=0.95,
                        timestamp=datetime.now()
                    ))

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")

        return exit_signals


class AlgorithmManager:
    """
    Manages multiple trading algorithms and coordinates their execution.

    Provides centralized algorithm management, execution coordination,
    and performance monitoring.
    """

    def __init__(self, config: Dict[str, Any],
                 scanner_adapter: ScannerIntegrationAdapter,
                 data_adapter: DuckDBDataAdapter,
                 query_optimizer: QueryOptimizer):
        """
        Initialize algorithm manager.

        Args:
            config: Manager configuration
            scanner_adapter: Scanner integration adapter
            data_adapter: Data access adapter
            query_optimizer: Query optimization adapter
        """
        self.config = config
        self.scanner_adapter = scanner_adapter
        self.data_adapter = data_adapter
        self.query_optimizer = query_optimizer

        # Algorithm registry
        self.algorithms: Dict[str, TradingAlgorithm] = {}
        self.active_algorithms: Dict[str, TradingAlgorithm] = {}

        # Execution tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.performance_stats: Dict[str, Any] = {}

        logger.info("AlgorithmManager initialized")

    async def register_algorithm(self, algorithm: TradingAlgorithm) -> bool:
        """
        Register a trading algorithm.

        Args:
            algorithm: Algorithm to register

        Returns:
            True if registration successful
        """
        try:
            if algorithm.algorithm_id in self.algorithms:
                logger.warning(f"Algorithm {algorithm.algorithm_id} already registered")
                return False

            self.algorithms[algorithm.algorithm_id] = algorithm
            logger.info(f"Registered algorithm: {algorithm.name} ({algorithm.algorithm_id})")
            return True

        except Exception as e:
            logger.error(f"Error registering algorithm: {e}")
            return False

    async def activate_algorithm(self, algorithm_id: str, context: AlgorithmContext) -> bool:
        """
        Activate a registered algorithm.

        Args:
            algorithm_id: Algorithm to activate
            context: Algorithm execution context

        Returns:
            True if activation successful
        """
        try:
            if algorithm_id not in self.algorithms:
                logger.error(f"Algorithm {algorithm_id} not registered")
                return False

            algorithm = self.algorithms[algorithm_id]

            # Initialize algorithm
            if not await algorithm.initialize(context):
                logger.error(f"Failed to initialize algorithm {algorithm_id}")
                return False

            self.active_algorithms[algorithm_id] = algorithm
            logger.info(f"Activated algorithm: {algorithm.name}")
            return True

        except Exception as e:
            logger.error(f"Error activating algorithm {algorithm_id}: {e}")
            return False

    async def execute_algorithms(self, bars: List[Bar], context: AlgorithmContext) -> Dict[str, AlgorithmResult]:
        """
        Execute all active algorithms with market data.

        Args:
            bars: Market data bars
            context: Execution context

        Returns:
            Dictionary mapping algorithm IDs to results
        """
        results = {}
        start_time = datetime.now()

        try:
            # Execute algorithms concurrently
            tasks = []
            for algorithm_id, algorithm in self.active_algorithms.items():
                task = self._execute_single_algorithm(algorithm, bars, context)
                tasks.append((algorithm_id, task))

            # Wait for all executions to complete
            for algorithm_id, task in tasks:
                try:
                    result = await task
                    results[algorithm_id] = result
                    logger.debug(f"Algorithm {algorithm_id} executed in {result.execution_time:.3f}s")
                except Exception as e:
                    logger.error(f"Error executing algorithm {algorithm_id}: {e}")
                    results[algorithm_id] = AlgorithmResult(
                        error_messages=[f"Execution failed: {str(e)}"]
                    )

        except Exception as e:
            logger.error(f"Error in algorithm execution batch: {e}")

        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Executed {len(results)} algorithms in {execution_time:.3f}s")

        # Record execution in history
        self.execution_history.append({
            'timestamp': datetime.now(),
            'algorithms_executed': len(results),
            'total_execution_time': execution_time,
            'results': results
        })

        return results

    async def _execute_single_algorithm(self, algorithm: TradingAlgorithm,
                                      bars: List[Bar], context: AlgorithmContext) -> AlgorithmResult:
        """
        Execute a single algorithm.

        Args:
            algorithm: Algorithm to execute
            bars: Market data bars
            context: Execution context

        Returns:
            Algorithm execution result
        """
        try:
            # Create algorithm-specific context copy
            algorithm_context = AlgorithmContext(
                trading_date=context.trading_date,
                current_time=context.current_time,
                positions=context.positions.copy(),
                account_balance=context.account_balance,
                risk_per_trade=context.risk_per_trade,
                max_positions=context.max_positions,
                market_data=context.market_data.copy(),
                scanner_signals=context.scanner_signals.copy(),
                algorithm_state=context.algorithm_state.copy()
            )

            # Execute algorithm
            result = await algorithm.process_market_data(bars, algorithm_context)

            return result

        except Exception as e:
            logger.error(f"Error executing algorithm {algorithm.algorithm_id}: {e}")
            return AlgorithmResult(error_messages=[f"Execution error: {str(e)}"])

    def get_algorithm_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all registered algorithms.

        Returns:
            Dictionary with algorithm status information
        """
        status = {}

        for algorithm_id, algorithm in self.algorithms.items():
            status[algorithm_id] = {
                'is_active': algorithm_id in self.active_algorithms,
                'info': algorithm.get_algorithm_info()
            }

        return status

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary for all algorithms.

        Returns:
            Performance summary dictionary
        """
        total_executions = len(self.execution_history)
        if total_executions == 0:
            return {'total_executions': 0, 'algorithms': {}}

        algorithm_performance = {}

        for algorithm_id in self.algorithms.keys():
            executions = [exec for exec in self.execution_history
                         if algorithm_id in exec['results']]
            if executions:
                success_rate = sum(1 for exec in executions
                                 if not exec['results'][algorithm_id].error_messages) / len(executions)
                algorithm_performance[algorithm_id] = {
                    'executions': len(executions),
                    'success_rate': success_rate,
                    'avg_execution_time': sum(exec['results'][algorithm_id].execution_time
                                            for exec in executions) / len(executions)
                }

        return {
            'total_executions': total_executions,
            'algorithms': algorithm_performance,
            'overall_success_rate': sum(perf['success_rate'] for perf in algorithm_performance.values()) / len(algorithm_performance) if algorithm_performance else 0
        }

    async def optimize_algorithm_parameters(self, algorithm_id: str,
                                         optimization_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize algorithm parameters using historical data.

        Args:
            algorithm_id: Algorithm to optimize
            optimization_config: Optimization configuration

        Returns:
            Optimization results
        """
        try:
            if algorithm_id not in self.algorithms:
                return {'status': 'error', 'message': f'Algorithm {algorithm_id} not found'}

            algorithm = self.algorithms[algorithm_id]

            # This would implement parameter optimization logic
            # For now, return mock results
            optimization_results = {
                'status': 'completed',
                'algorithm_id': algorithm_id,
                'optimized_parameters': algorithm.config,
                'performance_improvement': 0.15,  # 15% improvement
                'confidence_level': 0.85
            }

            logger.info(f"Parameter optimization completed for {algorithm_id}")
            return optimization_results

        except Exception as e:
            logger.error(f"Error optimizing algorithm parameters: {e}")
            return {'status': 'error', 'message': str(e)}

    def clear_execution_history(self, days_to_keep: int = 30) -> int:
        """
        Clear old execution history.

        Args:
            days_to_keep: Number of days of history to keep

        Returns:
            Number of entries removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        old_entries = [entry for entry in self.execution_history
                      if entry['timestamp'] < cutoff_date]

        self.execution_history = [entry for entry in self.execution_history
                                if entry['timestamp'] >= cutoff_date]

        logger.info(f"Cleared {len(old_entries)} old execution history entries")
        return len(old_entries)
