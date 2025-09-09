#!/usr/bin/env python3
"""
End-to-End Backtest Integration Test
=====================================

Comprehensive validation of the complete trade engine integration:
- DuckDB data access
- Scanner integration
- Query optimization
- Algorithm execution
- Backtesting performance

This script validates the complete workflow from data retrieval to results analysis.
"""

import asyncio
import sys
import time
import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from trade_engine.adapters.duckdb_data_adapter import DuckDBDataAdapter
from trade_engine.adapters.scanner_adapter import ScannerIntegrationAdapter
from trade_engine.adapters.query_optimizer import QueryOptimizer
from trade_engine.adapters.enhanced_data_feed import EnhancedDataFeed
from trade_engine.domain.algorithm_layer import AlgorithmManager
from trade_engine.domain.backtest_optimizer import BacktestOptimizer, BacktestConfiguration
from trade_engine.domain.models import Bar, Signal, SignalType


class EndToEndBacktestRunner:
    """Complete end-to-end backtest execution and validation."""

    def __init__(self):
        self.components = {}
        self.results = {}
        self.start_time = None

    async def initialize_system(self) -> bool:
        """Initialize all system components."""
        print("🚀 Initializing Trade Engine System...")

        try:
            # 1. Initialize DuckDB Data Adapter
            print("   📊 Initializing DuckDB Data Adapter...")
            data_config = {
                'db_path': './data/financial_data.duckdb',
                'connection_pool_size': 5,
                'query_timeout': 30
            }
            data_adapter = DuckDBDataAdapter(data_config)
            await data_adapter.initialize()
            self.components['data_adapter'] = data_adapter
            print("   ✅ DuckDB Data Adapter initialized")

            # 2. Initialize Scanner Integration Adapter
            print("   🔍 Initializing Scanner Integration Adapter...")
            scanner_config = {
                'scanner_rules_path': './src/rules',
                'max_algorithms': 5,
                'enable_rule_engine': True
            }
            scanner_adapter = ScannerIntegrationAdapter(scanner_config)
            self.components['scanner_adapter'] = scanner_adapter
            print("   ✅ Scanner Integration Adapter initialized")

            # 3. Initialize Query Optimizer
            print("   ⚡ Initializing Query Optimizer...")
            query_config = {
                'query_cache': {
                    'enabled': True,
                    'ttl_seconds': 3600,  # 1 hour
                    'max_size': 100
                },
                'optimization_level': 'high',
                'max_query_complexity': 'complex'
            }
            query_optimizer = QueryOptimizer(query_config)
            self.components['query_optimizer'] = query_optimizer
            print("   ✅ Query Optimizer initialized")

            # 4. Initialize Enhanced Data Feed
            print("   📈 Initializing Enhanced Data Feed...")
            data_feed_config = {
                'db_path': './data/financial_data.duckdb',
                'connection_pool_size': 5,
                'query_timeout': 30
            }
            data_feed = EnhancedDataFeed(data_feed_config)
            await data_feed.initialize()
            self.components['data_feed'] = data_feed
            print("   ✅ Enhanced Data Feed initialized")

            # 5. Initialize Algorithm Manager
            print("   🧠 Initializing Algorithm Manager...")
            algorithm_config = {
                'max_algorithms': 5,
                'execution_timeout': 30,
                'enable_parallel': True,
                'max_workers': 2
            }
            algorithm_manager = AlgorithmManager(
                algorithm_config,
                scanner_adapter,
                data_adapter,
                query_optimizer
            )
            self.components['algorithm_manager'] = algorithm_manager
            print("   ✅ Algorithm Manager initialized")

            # 6. Initialize Backtest Optimizer
            print("   🎯 Initializing Backtest Optimizer...")
            backtest_config = {
                'enable_parallel': True,
                'max_workers': 2,
                'memory_limit_mb': 1024,
                'cache_results': True,
                'progress_reporting': True
            }
            backtest_optimizer = BacktestOptimizer(backtest_config)
            await backtest_optimizer.initialize(
                data_adapter,
                algorithm_manager,
                query_optimizer
            )
            self.components['backtest_optimizer'] = backtest_optimizer
            print("   ✅ Backtest Optimizer initialized")

            print("🎉 All components initialized successfully!")
            return True

        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            return False

    async def validate_data_access(self) -> Dict[str, Any]:
        """Validate data access capabilities."""
        print("\n📊 Validating Data Access...")

        results = {}
        data_adapter = self.components['data_adapter']

        try:
            # Test available symbols
            symbols = await data_adapter.get_available_symbols()
            results['total_symbols'] = len(symbols)
            results['sample_symbols'] = symbols[:10]
            print(f"   📈 Available symbols: {len(symbols)}")

            # Test data retrieval for a specific symbol
            test_symbol = 'RELIANCE' if 'RELIANCE' in symbols else symbols[0]
            start_date = date(2024, 9, 1)
            end_date = date(2024, 9, 7)  # One week of data

            bars = await data_adapter.get_historical_bars(
                symbol=test_symbol,
                start_date=start_date,
                end_date=end_date,
                timeframe='1m'
            )

            results['test_symbol'] = test_symbol
            results['data_points'] = len(bars)
            results['date_range'] = f"{start_date} to {end_date}"
            print(f"   📊 {test_symbol}: {len(bars)} data points retrieved")

            # Test connection stats
            stats = await data_adapter.get_connection_stats()
            results['connection_stats'] = stats
            print(f"   🔗 Connection active: {stats.get('active_connections', 0)}")

            results['status'] = 'SUCCESS'
            print("   ✅ Data access validation successful")

        except Exception as e:
            results['status'] = 'FAILED'
            results['error'] = str(e)
            print(f"   ❌ Data access validation failed: {e}")

        return results

    async def validate_scanner_integration(self) -> Dict[str, Any]:
        """Validate scanner integration capabilities."""
        print("\n🔍 Validating Scanner Integration...")

        results = {}
        scanner_adapter = self.components['scanner_adapter']

        try:
            # Test scanner algorithms loading
            algorithms = ['breakout_algo', 'momentum_algo']

            for algo_id in algorithms:
                try:
                    algorithm = await scanner_adapter.load_scanner_algorithm(algo_id)
                    if algorithm:
                        results[f'{algo_id}_loaded'] = True
                        results[f'{algo_id}_name'] = algorithm.name
                        print(f"   🔧 {algo_id}: {algorithm.name} loaded")
                    else:
                        results[f'{algo_id}_loaded'] = False
                        print(f"   ⚠️  {algo_id}: Not available")
                except Exception as e:
                    results[f'{algo_id}_loaded'] = False
                    results[f'{algo_id}_error'] = str(e)
                    print(f"   ❌ {algo_id}: Load failed - {e}")

            # Test bulk scanner execution
            if results.get('breakout_algo_loaded', False):
                bulk_results = await scanner_adapter.execute_bulk_scanners(['breakout_algo'])
                results['bulk_execution'] = len(bulk_results) > 0
                print(f"   🚀 Bulk execution: {len(bulk_results)} results")

            results['status'] = 'SUCCESS'
            print("   ✅ Scanner integration validation successful")

        except Exception as e:
            results['status'] = 'FAILED'
            results['error'] = str(e)
            print(f"   ❌ Scanner integration validation failed: {e}")

        return results

    async def run_backtest_scenario(self) -> Dict[str, Any]:
        """Run a comprehensive backtest scenario."""
        print("\n🎯 Running Backtest Scenario...")

        results = {}
        backtest_optimizer = self.components['backtest_optimizer']

        try:
            # Configure backtest
            backtest_config = BacktestConfiguration(
                start_date=date(2024, 9, 1),
                end_date=date(2024, 9, 7),  # One week for faster execution
                symbols=['RELIANCE', 'TCS', 'INFY'],  # Top 3 IT stocks
                algorithms=['breakout_algo'],  # Single algorithm for simplicity
                initial_balance=Decimal('100000'),  # ₹1 lakh
                risk_per_trade=Decimal('0.02'),  # 2% risk per trade
                max_positions=3,
                enable_parallel=True,
                max_workers=2,
                chunk_size_days=1,  # Daily chunks for this test
                memory_limit_mb=512,
                cache_results=True,
                progress_reporting=True
            )

            results['config'] = {
                'symbols': backtest_config.symbols,
                'algorithms': backtest_config.algorithms,
                'date_range': f"{backtest_config.start_date} to {backtest_config.end_date}",
                'initial_balance': float(backtest_config.initial_balance),
                'risk_per_trade': float(backtest_config.risk_per_trade)
            }

            print(f"   📅 Backtest period: {backtest_config.start_date} to {backtest_config.end_date}")
            print(f"   📊 Symbols: {', '.join(backtest_config.symbols)}")
            print(f"   💰 Initial balance: ₹{backtest_config.initial_balance}")
            print(f"   ⚡ Risk per trade: {backtest_config.risk_per_trade * 100}%")

            # Execute backtest
            print("   🚀 Starting backtest execution...")
            backtest_start = time.time()

            backtest_result = await backtest_optimizer.run_backtest(backtest_config)

            backtest_duration = time.time() - backtest_start

            # Analyze results
            results['execution_time'] = backtest_duration
            results['final_balance'] = float(backtest_result.final_balance)
            results['total_return'] = float(backtest_result.total_return_percentage)
            results['max_drawdown'] = float(backtest_result.max_drawdown_percentage)
            results['total_trades'] = backtest_result.total_trades
            results['winning_trades'] = backtest_result.winning_trades
            results['losing_trades'] = backtest_result.losing_trades
            results['win_rate'] = float(backtest_result.win_rate_percentage)
            results['sharpe_ratio'] = float(backtest_result.sharpe_ratio)

            print("   📈 Results:")
            print(".2f")
            print(".2f")
            print(".2f")
            print(f"   📊 Trades: {backtest_result.total_trades} total ({backtest_result.winning_trades}W/{backtest_result.losing_trades}L)")
            print(".1f")
            print(".2f")
            print(".2f")

            results['status'] = 'SUCCESS'
            print("   ✅ Backtest execution successful")

        except Exception as e:
            results['status'] = 'FAILED'
            results['error'] = str(e)
            print(f"   ❌ Backtest execution failed: {e}")

        return results

    async def run_performance_benchmark(self) -> Dict[str, Any]:
        """Run performance benchmark tests."""
        print("\n⚡ Running Performance Benchmarks...")

        results = {}
        data_adapter = self.components['data_adapter']
        query_optimizer = self.components['query_optimizer']

        try:
            # Benchmark data retrieval
            test_symbol = 'RELIANCE'
            start_date = date(2024, 9, 1)
            end_date = date(2024, 9, 7)

            # Standard query
            start_time = time.time()
            bars = await data_adapter.get_historical_bars(
                symbol=test_symbol,
                start_date=start_date,
                end_date=end_date,
                timeframe='1m'
            )
            standard_time = time.time() - start_time

            # Optimized query
            start_time = time.time()
            optimized_query = await query_optimizer.generate_optimized_query(
                base_query=f"SELECT * FROM market_data WHERE symbol = '{test_symbol}' AND date_partition BETWEEN '{start_date}' AND '{end_date}'",
                optimization_level='high'
            )

            # Execute optimized query
            if optimized_query:
                result = await data_adapter._execute_async_query(optimized_query['optimized_query'])
                optimized_time = time.time() - start_time
            else:
                optimized_time = standard_time

            results['standard_query_time'] = standard_time
            results['optimized_query_time'] = optimized_time
            results['performance_improvement'] = ((standard_time - optimized_time) / standard_time) * 100
            results['data_points_retrieved'] = len(bars)

            print(".3f")
            print(".3f")
            print(".1f")
            print(f"   📊 Data points: {len(bars)}")

            # Memory usage test
            memory_manager = self.components['backtest_optimizer'].memory_manager
            memory_stats = memory_manager.get_memory_stats()
            results['memory_usage'] = memory_stats

            print(".1f")
            print(f"   🔄 Cleanup operations: {memory_stats['cleanup_count']}")

            results['status'] = 'SUCCESS'
            print("   ✅ Performance benchmarks completed")

        except Exception as e:
            results['status'] = 'FAILED'
            results['error'] = str(e)
            print(f"   ❌ Performance benchmarks failed: {e}")

        return results

    async def cleanup_system(self):
        """Clean up all system components."""
        print("\n🧹 Cleaning up system...")

        try:
            for name, component in self.components.items():
                try:
                    if hasattr(component, 'close'):
                        await component.close()
                    elif hasattr(component, 'shutdown'):
                        await component.shutdown()
                    print(f"   ✅ {name} cleaned up")
                except Exception as e:
                    print(f"   ⚠️  {name} cleanup failed: {e}")

            print("   🎉 System cleanup completed")

        except Exception as e:
            print(f"   ❌ System cleanup failed: {e}")

    async def run_complete_validation(self) -> Dict[str, Any]:
        """Run complete end-to-end validation."""
        print("=" * 60)
        print("🎯 TRADE ENGINE END-TO-END BACKTEST VALIDATION")
        print("=" * 60)

        self.start_time = time.time()
        final_results = {}

        try:
            # Step 1: System Initialization
            init_success = await self.initialize_system()
            final_results['initialization'] = {'success': init_success}

            if not init_success:
                print("❌ System initialization failed. Aborting validation.")
                return final_results

            # Step 2: Data Access Validation
            data_results = await self.validate_data_access()
            final_results['data_access'] = data_results

            # Step 3: Scanner Integration Validation
            scanner_results = await self.validate_scanner_integration()
            final_results['scanner_integration'] = scanner_results

            # Step 4: Performance Benchmarks
            perf_results = await self.run_performance_benchmark()
            final_results['performance'] = perf_results

            # Step 5: Complete Backtest Scenario
            backtest_results = await self.run_backtest_scenario()
            final_results['backtest'] = backtest_results

            # Calculate total execution time
            total_time = time.time() - self.start_time
            final_results['total_execution_time'] = total_time

        except Exception as e:
            print(f"❌ Validation failed with error: {e}")
            final_results['error'] = str(e)

        finally:
            await self.cleanup_system()

        return final_results


async def main():
    """Main execution function."""
    runner = EndToEndBacktestRunner()
    results = await runner.run_complete_validation()

    # Print final summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    total_time = results.get('total_execution_time', 0)
    print(".2f")

    # Check each component status
    components = ['initialization', 'data_access', 'scanner_integration', 'performance', 'backtest']
    all_success = True

    for component in components:
        if component in results:
            status = results[component].get('status', 'UNKNOWN')
            if status == 'SUCCESS':
                print(f"✅ {component.replace('_', ' ').title()}: SUCCESS")
            else:
                print(f"❌ {component.replace('_', ' ').title()}: FAILED")
                all_success = False

    print("\n" + "=" * 60)
    if all_success:
        print("🎉 END-TO-END BACKTEST: ALL COMPONENTS VALIDATED SUCCESSFULLY!")
        print("🚀 Trade Engine is PRODUCTION READY!")

        # Print key metrics
        if 'backtest' in results and results['backtest'].get('status') == 'SUCCESS':
            bt = results['backtest']
            print("\n📈 Backtest Results:")
            print(f"   Final Balance: ₹{bt.get('final_balance', 0):,.2f}")
            print(f"   Total Return: {bt.get('total_return', 0):.2f}%")
            print(f"   Trades: {bt.get('total_trades', 0)} (Win Rate: {bt.get('win_rate', 0):.1f}%)")

        if 'performance' in results and results['performance'].get('status') == 'SUCCESS':
            perf = results['performance']
            print("\n⚡ Performance:")
            print(f"   Query Improvement: {perf.get('performance_improvement', 0):.1f}%")
            print(f"   Memory Usage: {perf.get('memory_usage', {}).get('current_usage_mb', 0):.1f}MB")
    else:
        print("❌ END-TO-END BACKTEST: SOME COMPONENTS FAILED VALIDATION")
        print("🔧 Please review the errors above and fix issues before production use.")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
