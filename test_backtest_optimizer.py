"""
Test Backtest Optimizer Script
=============================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from trade_engine.domain.backtest_optimizer import BacktestOptimizer, BacktestConfiguration
from trade_engine.adapters.enhanced_data_feed import EnhancedDataFeed
from trade_engine.domain.algorithm_layer import AlgorithmManager
from trade_engine.adapters.query_optimizer import QueryOptimizer
from datetime import date
from decimal import Decimal
import asyncio

async def test_backtest_optimizer():
    # Setup components
    config = {
        'memory_limit_mb': 512,
        'max_workers': 2,
        'enable_parallel': False  # Disable for testing
    }

    data_feed = EnhancedDataFeed({
        'data': {'duckdb_path': 'data/financial_data.duckdb'},
        'database': {'max_connections': 5, 'connection_timeout': 30.0, 'memory_limit': '2GB', 'threads': 2}
    })

    algorithm_manager = AlgorithmManager({}, None, None, None)
    query_optimizer = QueryOptimizer({})

    optimizer = BacktestOptimizer(config)
    success = await optimizer.initialize(data_feed, algorithm_manager, query_optimizer)

    if success:
        print('✅ Backtest optimizer initialized successfully')

        # Test with a small backtest configuration
        backtest_config = BacktestConfiguration(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),  # Small date range for testing
            symbols=['360ONE'],  # Single symbol for testing
            algorithms=[],  # No algorithms for basic test
            initial_balance=Decimal('100000'),
            chunk_size_days=1
        )

        print('📊 Running backtest with configuration:')
        print(f'   Symbols: {backtest_config.symbols}')
        print(f'   Date range: {backtest_config.start_date} to {backtest_config.end_date}')
        print(f'   Initial balance: ${backtest_config.initial_balance}')
        print(f'   Chunk size: {backtest_config.chunk_size_days} days')

        result = await optimizer.run_backtest(backtest_config)

        print(f'📈 Backtest completed!')
        print(f'   Execution time: {result.execution_stats.get("total_execution_time", 0):.2f}s')
        print(f'   Memory usage: {result.execution_stats.get("memory_stats", {}).get("current_usage_mb", 0):.1f}MB')
        print(f'   Total trades: {result.get_total_trades()}')
        print(f'   Final balance: ${result.portfolio_performance.get("final_balance", backtest_config.initial_balance):.2f}')

        if result.errors:
            print(f'⚠️  Errors: {len(result.errors)}')
            for error in result.errors[:3]:  # Show first 3 errors
                print(f'   - {error}')

        print('✅ Backtest optimizer test completed successfully!')

    else:
        print('❌ Backtest optimizer initialization failed')

if __name__ == "__main__":
    asyncio.run(test_backtest_optimizer())
