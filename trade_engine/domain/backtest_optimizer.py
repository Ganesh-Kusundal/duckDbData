"""
Backtesting Performance Optimizer
=================================

Optimizes backtesting performance for large datasets and multiple algorithms.
Provides memory management, parallel processing, and performance monitoring.
"""

import asyncio
import time
import psutil
import gc
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import logging
import pandas as pd
import numpy as np

from .models import Bar, Signal, Position, OrderIntent
from .algorithm_layer import AlgorithmManager, AlgorithmContext, AlgorithmResult
from ..adapters.enhanced_data_feed import EnhancedDataFeed
from ..adapters.query_optimizer import QueryOptimizer
from ..adapters.duckdb_data_adapter import DuckDBDataAdapter
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestConfiguration:
    """Configuration for backtesting execution."""
    start_date: date
    end_date: date
    symbols: List[str]
    algorithms: List[str]
    initial_balance: Decimal = Decimal('100000')
    risk_per_trade: Decimal = Decimal('0.01')  # 1%
    max_positions: int = 5
    enable_parallel: bool = True
    max_workers: int = 4
    chunk_size_days: int = 30  # Process data in chunks
    memory_limit_mb: int = 1024
    cache_results: bool = True
    progress_reporting: bool = True


@dataclass
class BacktestResult:
    """Results from a backtesting run."""
    algorithm_results: Dict[str, List[AlgorithmResult]] = field(default_factory=dict)
    portfolio_performance: Dict[str, Any] = field(default_factory=dict)
    trade_log: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    execution_stats: Dict[str, Any] = field(default_factory=dict)
    memory_usage: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def get_total_trades(self) -> int:
        """Get total number of trades across all algorithms."""
        return len(self.trade_log)

    def get_total_return(self) -> float:
        """Get total portfolio return."""
        return self.portfolio_performance.get('total_return', 0.0)

    def get_sharpe_ratio(self) -> float:
        """Get Sharpe ratio of the portfolio."""
        return self.portfolio_performance.get('sharpe_ratio', 0.0)

    def get_max_drawdown(self) -> float:
        """Get maximum drawdown of the portfolio."""
        return self.portfolio_performance.get('max_drawdown', 0.0)


@dataclass
class MemoryManager:
    """Manages memory usage during backtesting."""
    max_memory_mb: int
    gc_threshold: int = 1000
    cleanup_interval: int = 1000  # Clean up every N operations

    def __post_init__(self):
        self.operation_count = 0
        self.memory_peaks: List[float] = []
        self.last_cleanup = time.time()

    def check_memory_usage(self) -> float:
        """Check current memory usage in MB."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_peaks.append(memory_mb)

        # Force garbage collection if memory is high
        if memory_mb > self.max_memory_mb * 0.8:
            gc.collect()

        return memory_mb

    def should_cleanup(self) -> bool:
        """Check if cleanup should be performed."""
        self.operation_count += 1
        should_cleanup = self.operation_count % self.cleanup_interval == 0
        logger.debug(f"Operation count: {self.operation_count}, should cleanup: {should_cleanup}")
        return should_cleanup

    def cleanup(self) -> None:
        """Perform memory cleanup."""
        gc.collect()
        self.last_cleanup = time.time()
        logger.debug(f"Memory cleanup performed. Current usage: {self.check_memory_usage():.1f}MB")

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        avg_usage = sum(self.memory_peaks) / len(self.memory_peaks) if self.memory_peaks else 0
        return {
            'current_usage_mb': self.check_memory_usage(),
            'peak_usage_mb': max(self.memory_peaks) if self.memory_peaks else 0,
            'avg_usage_mb': avg_usage,
            'cleanup_count': self.operation_count // self.cleanup_interval
        }


class ParallelExecutor:
    """Handles parallel execution of algorithms."""

    def __init__(self, max_workers: int, enable_parallel: bool = True):
        self.max_workers = max_workers
        self.enable_parallel = enable_parallel
        self.executor = ThreadPoolExecutor(max_workers=max_workers) if enable_parallel else None

    async def execute_parallel(self, tasks: List[callable]) -> List[Any]:
        """Execute tasks in parallel."""
        if not self.enable_parallel or len(tasks) == 1:
            # Execute sequentially
            results = []
            for task in tasks:
                try:
                    result = await task()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Task execution failed: {e}")
                    results.append(None)
            return results

        # Execute in parallel using threads
        loop = asyncio.get_event_loop()
        futures = []

        for task in tasks:
            future = loop.run_in_executor(self.executor, self._run_async_task, task)
            futures.append(future)

        results = []
        for future in futures:
            try:
                result = await future
                results.append(result)
            except Exception as e:
                logger.error(f"Parallel task execution failed: {e}")
                results.append(None)

        return results

    def _run_async_task(self, async_task: callable) -> Any:
        """Helper to run async task in thread executor."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_task())
        finally:
            loop.close()

    def shutdown(self) -> None:
        """Shutdown the executor."""
        if self.executor:
            self.executor.shutdown(wait=True)


class BacktestOptimizer:
    """
    Optimizes backtesting performance for large datasets and multiple algorithms.

    Provides memory management, parallel processing, and intelligent data loading
    to ensure efficient backtesting execution.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize backtest optimizer.

        Args:
            config: Configuration dictionary with optimization settings
        """
        self.config = config

        # Core components
        self.memory_manager = MemoryManager(
            max_memory_mb=config.get('memory_limit_mb', 1024)
        )
        self.parallel_executor = ParallelExecutor(
            max_workers=config.get('max_workers', 4),
            enable_parallel=config.get('enable_parallel', True)
        )

        # Data and algorithm components
        self.data_feed: Optional[EnhancedDataFeed] = None
        self.algorithm_manager: Optional[AlgorithmManager] = None
        self.query_optimizer: Optional[QueryOptimizer] = None

        # Caching
        self.result_cache: Dict[str, Any] = {}
        self.data_cache: Dict[str, pd.DataFrame] = {}

        # Performance tracking
        self.execution_start_time: Optional[float] = None
        self.performance_stats: Dict[str, Any] = {}

        logger.info("BacktestOptimizer initialized")

    async def initialize(self, data_feed: EnhancedDataFeed,
                        algorithm_manager: AlgorithmManager,
                        query_optimizer: QueryOptimizer) -> bool:
        """
        Initialize optimizer with required components.

        Args:
            data_feed: Enhanced data feed for market data
            algorithm_manager: Algorithm manager for trading strategies
            query_optimizer: Query optimizer for performance

        Returns:
            True if initialization successful
        """
        try:
            self.data_feed = data_feed
            self.algorithm_manager = algorithm_manager
            self.query_optimizer = query_optimizer

            # Initialize components
            success = await self.data_feed.initialize()
            if not success:
                logger.error("Failed to initialize data feed")
                return False

            logger.info("BacktestOptimizer initialization successful")
            return True

        except Exception as e:
            logger.error(f"Error initializing backtest optimizer: {e}")
            return False

    async def run_backtest(self, backtest_config: BacktestConfiguration) -> BacktestResult:
        """
        Run optimized backtesting with given configuration.

        Args:
            backtest_config: Backtesting configuration

        Returns:
            BacktestResult with comprehensive results
        """
        self.execution_start_time = time.time()

        try:
            logger.info(f"Starting optimized backtest: {len(backtest_config.symbols)} symbols, "
                       f"{len(backtest_config.algorithms)} algorithms, "
                       f"{(backtest_config.end_date - backtest_config.start_date).days} days")

            # Validate configuration
            if not await self._validate_configuration(backtest_config):
                return BacktestResult(errors=["Configuration validation failed"])

            # Prepare data in optimized chunks
            data_chunks = await self._prepare_data_chunks(backtest_config)

            # Execute backtest
            result = await self._execute_backtest(backtest_config, data_chunks)

            # Calculate final performance metrics
            await self._calculate_performance_metrics(result, backtest_config)

            # Update execution statistics
            result.execution_stats = self._get_execution_stats()

            execution_time = time.time() - self.execution_start_time
            logger.info(f"Backtest completed in {execution_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Backtest execution failed: {e}")
            return BacktestResult(errors=[f"Backtest failed: {str(e)}"])

    async def _validate_configuration(self, config: BacktestConfiguration) -> bool:
        """
        Validate backtesting configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid
        """
        try:
            # Validate date range
            if config.start_date >= config.end_date:
                logger.error("Start date must be before end date")
                return False

            # Validate symbols
            if not config.symbols:
                logger.error("No symbols specified")
                return False

            # Validate algorithms
            if not config.algorithms:
                logger.error("No algorithms specified")
                return False

            # Check available symbols
            if self.data_feed:
                available_symbols = await self.data_feed.get_available_symbols_async()
                missing_symbols = set(config.symbols) - set(available_symbols)
                if missing_symbols:
                    logger.warning(f"Symbols not available: {missing_symbols}")

            # Validate algorithms exist
            if self.algorithm_manager:
                algorithm_status = self.algorithm_manager.get_algorithm_status()
                missing_algorithms = []
                for algo_id in config.algorithms:
                    if algo_id not in algorithm_status:
                        missing_algorithms.append(algo_id)
                    elif not algorithm_status[algo_id]['is_active']:
                        logger.warning(f"Algorithm {algo_id} is not active")

                if missing_algorithms:
                    logger.error(f"Algorithms not found: {missing_algorithms}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    async def _prepare_data_chunks(self, config: BacktestConfiguration) -> List[Dict[str, Any]]:
        """
        Prepare data in optimized chunks for processing.

        Args:
            config: Backtesting configuration

        Returns:
            List of data chunks
        """
        chunks = []
        current_date = config.start_date

        while current_date < config.end_date:
            chunk_end = min(current_date + timedelta(days=config.chunk_size_days), config.end_date)

            chunk = {
                'start_date': current_date.isoformat(),
                'end_date': chunk_end.isoformat(),
                'symbols': config.symbols,
                'data': None
            }

            # Preload data for this chunk if caching is enabled
            if config.cache_results:
                cache_key = f"data_{current_date.isoformat()}_{chunk_end.isoformat()}_{'_'.join(config.symbols)}"
                if cache_key in self.data_cache:
                    chunk['data'] = self.data_cache[cache_key]
                else:
                    # Load data in optimized way
                    chunk['data'] = await self._load_chunk_data(config.symbols, current_date, chunk_end)
                    self.data_cache[cache_key] = chunk['data']

                    # Memory management
                    if self.memory_manager.should_cleanup():
                        self.memory_manager.cleanup()

            chunks.append(chunk)
            current_date = chunk_end

        logger.info(f"Prepared {len(chunks)} data chunks for processing")
        return chunks

    async def _load_chunk_data(self, symbols: List[str], start_date: date, end_date: date) -> pd.DataFrame:
        """
        Load market data for a specific chunk in an optimized way.

        Args:
            symbols: List of symbols to load
            start_date: Start date for chunk
            end_date: End date for chunk

        Returns:
            DataFrame with market data
        """
        if not self.data_feed:
            return pd.DataFrame()

        try:
            # Use batch loading for better performance
            batch_data = await self.data_feed.get_optimized_bars_batch(
                symbols, start_date.isoformat(), end_date.isoformat()
            )

            # Combine all symbol data into single DataFrame
            all_data = []
            for symbol, bars in batch_data.items():
                for bar in bars:
                    all_data.append({
                        'symbol': symbol,
                        'timestamp': bar.timestamp,
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'volume': bar.volume
                    })

            df = pd.DataFrame(all_data)
            logger.debug(f"Loaded {len(df)} records for chunk {start_date} to {end_date}")
            return df

        except Exception as e:
            logger.error(f"Error loading chunk data: {e}")
            return pd.DataFrame()

    async def _execute_backtest(self, config: BacktestConfiguration,
                              data_chunks: List[Dict[str, Any]]) -> BacktestResult:
        """
        Execute backtesting with optimized processing.

        Args:
            config: Backtesting configuration
            data_chunks: Prepared data chunks

        Returns:
            BacktestResult with execution results
        """
        result = BacktestResult()
        portfolio_balance = float(config.initial_balance)

        # Initialize portfolio tracking
        portfolio_history = []

        for chunk in data_chunks:
            chunk_start_time = time.time()

            # Process chunk
            chunk_result = await self._process_data_chunk(chunk, config)

            # Update portfolio
            portfolio_balance = await self._update_portfolio(chunk_result, portfolio_balance, config)
            portfolio_history.append({
                'date': chunk['end_date'],
                'balance': portfolio_balance
            })

            # Memory management
            if self.memory_manager.should_cleanup():
                self.memory_manager.cleanup()

            # Progress reporting
            if config.progress_reporting:
                chunk_time = time.time() - chunk_start_time
                logger.info(f"Processed chunk {chunk['start_date']} to {chunk['end_date']} in {chunk_time:.2f}s")

        # Calculate final portfolio performance
        result.portfolio_performance = await self._calculate_portfolio_performance(
            portfolio_history, config.initial_balance
        )

        return result

    async def _process_data_chunk(self, chunk: Dict[str, Any],
                                config: BacktestConfiguration) -> Dict[str, Any]:
        """
        Process a single data chunk.

        Args:
            chunk: Data chunk to process
            config: Backtesting configuration

        Returns:
            Processing results for the chunk
        """
        chunk_result = {
            'algorithm_results': {},
            'trade_signals': [],
            'memory_usage': self.memory_manager.check_memory_usage()
        }

        try:
            # Get data for this chunk
            if chunk['data'] is None:
                chunk['data'] = await self._load_chunk_data(
                    chunk['symbols'], chunk['start_date'], chunk['end_date']
                )

            if chunk['data'].empty:
                logger.warning(f"No data available for chunk {chunk['start_date']} to {chunk['end_date']}")
                return chunk_result

            # Convert data to bars
            bars = []
            for _, row in chunk['data'].iterrows():
                bar = Bar(
                    timestamp=row['timestamp'],
                    symbol=row['symbol'],
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=int(row['volume']),
                    timeframe='1m'
                )
                bars.append(bar)

            # Execute algorithms on this chunk
            algorithm_tasks = []
            for algorithm_id in config.algorithms:
                task = self._execute_algorithm_on_chunk(algorithm_id, bars, config)
                algorithm_tasks.append(task)

            # Execute algorithms (potentially in parallel)
            algorithm_results = await self.parallel_executor.execute_parallel(algorithm_tasks)

            # Process results
            for i, algo_result in enumerate(algorithm_results):
                if algo_result and config.algorithms[i] in self.algorithm_manager.active_algorithms:
                    algorithm_id = config.algorithms[i]
                    chunk_result['algorithm_results'][algorithm_id] = algo_result

                    # Extract trade signals
                    for signal in algo_result.signals:
                        chunk_result['trade_signals'].append({
                            'algorithm_id': algorithm_id,
                            'signal': signal,
                            'timestamp': signal.timestamp
                        })

        except Exception as e:
            logger.error(f"Error processing data chunk: {e}")
            chunk_result['error'] = str(e)

        return chunk_result

    async def _execute_algorithm_on_chunk(self, algorithm_id: str, bars: List[Bar],
                                        config: BacktestConfiguration) -> Optional[AlgorithmResult]:
        """
        Execute a single algorithm on a data chunk.

        Args:
            algorithm_id: Algorithm to execute
            bars: Market data bars
            config: Backtesting configuration

        Returns:
            Algorithm execution result
        """
        try:
            if not self.algorithm_manager:
                return None

            # Create algorithm context
            context = AlgorithmContext(
                trading_date=bars[0].timestamp.date() if bars else date.today(),
                current_time=bars[0].timestamp.time() if bars else time(9, 30),
                account_balance=config.initial_balance,
                risk_per_trade=config.risk_per_trade,
                max_positions=config.max_positions
            )

            # Execute algorithm
            result = await self.algorithm_manager.execute_algorithms(bars, context)

            return result.get(algorithm_id)

        except Exception as e:
            logger.error(f"Error executing algorithm {algorithm_id} on chunk: {e}")
            return None

    async def _update_portfolio(self, chunk_result: Dict[str, Any],
                              current_balance: float, config: BacktestConfiguration) -> float:
        """
        Update portfolio based on chunk results.

        Args:
            chunk_result: Results from chunk processing
            current_balance: Current portfolio balance
            config: Backtesting configuration

        Returns:
            Updated portfolio balance
        """
        # This is a simplified portfolio update
        # In a real implementation, this would handle position management,
        # P&L calculation, risk management, etc.

        balance = current_balance

        # Process trade signals
        for trade_signal in chunk_result.get('trade_signals', []):
            signal = trade_signal['signal']

            # Simplified trade execution logic
            if signal.signal_type.value == 'ENTRY':
                # Calculate position size
                position_value = balance * float(config.risk_per_trade)
                if signal.price and signal.price > 0:
                    quantity = int(position_value / float(signal.price))

                    # Update balance (simplified)
                    balance -= position_value

                    logger.debug(f"Executed entry trade: {signal.symbol} @ {signal.price}, qty: {quantity}")

        return balance

    async def _calculate_portfolio_performance(self, portfolio_history: List[Dict[str, Any]],
                                            initial_balance: Decimal) -> Dict[str, Any]:
        """
        Calculate portfolio performance metrics.

        Args:
            portfolio_history: Historical portfolio values
            initial_balance: Initial portfolio balance

        Returns:
            Performance metrics dictionary
        """
        if not portfolio_history:
            return {'total_return': 0.0, 'sharpe_ratio': 0.0, 'max_drawdown': 0.0}

        try:
            balances = [entry['balance'] for entry in portfolio_history]
            initial = float(initial_balance)
            final = balances[-1]

            # Calculate returns
            total_return = (final - initial) / initial

            # Calculate Sharpe ratio (simplified)
            returns = np.diff(balances) / balances[:-1]
            if len(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            else:
                sharpe_ratio = 0

            # Calculate max drawdown
            peak = initial
            max_drawdown = 0
            for balance in balances:
                if balance > peak:
                    peak = balance
                drawdown = (peak - balance) / peak
                max_drawdown = max(max_drawdown, drawdown)

            return {
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'final_balance': final,
                'initial_balance': initial
            }

        except Exception as e:
            logger.error(f"Error calculating portfolio performance: {e}")
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'error': str(e)
            }

    async def _calculate_performance_metrics(self, result: BacktestResult,
                                          config: BacktestConfiguration) -> None:
        """
        Calculate comprehensive performance metrics.

        Args:
            result: Backtest result to update
            config: Backtesting configuration
        """
        try:
            # Calculate algorithm performance
            for algorithm_id, results in result.algorithm_results.items():
                if results:
                    total_signals = sum(len(r.signals) for r in results)
                    total_execution_time = sum(r.execution_time for r in results)
                    avg_execution_time = total_execution_time / len(results) if results else 0

                    result.performance_metrics[f'{algorithm_id}_total_signals'] = total_signals
                    result.performance_metrics[f'{algorithm_id}_avg_execution_time'] = avg_execution_time

            # Overall metrics
            result.performance_metrics['total_execution_time'] = time.time() - self.execution_start_time
            result.performance_metrics['memory_usage'] = self.memory_manager.get_memory_stats()

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")

    def _get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Execution statistics dictionary
        """
        execution_time = time.time() - self.execution_start_time if self.execution_start_time else 0

        return {
            'total_execution_time': execution_time,
            'memory_stats': self.memory_manager.get_memory_stats(),
            'cache_size': len(self.result_cache),
            'data_cache_size': len(self.data_cache)
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.result_cache.clear()
        self.data_cache.clear()
        gc.collect()
        logger.info("Backtest optimizer cache cleared")

    async def shutdown(self) -> None:
        """Shutdown the optimizer and cleanup resources."""
        if self.parallel_executor:
            self.parallel_executor.shutdown()

        self.clear_cache()
        logger.info("BacktestOptimizer shutdown complete")
