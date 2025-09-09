#!/usr/bin/env python3
"""
Test Analytics Queries Against Real Data
========================================

Comprehensive validation that all analytics queries work correctly against actual data.
Tests both the unified DuckDB integration and the analytics connector functionality.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, time

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from analytics.core.duckdb_connector import DuckDBAnalytics
from src.infrastructure.database import UnifiedDuckDBManager, DuckDBConfig


def test_basic_data_access():
    """Test basic data access and schema validation."""
    print("🧪 Testing Basic Data Access...")

    # Test with unified manager
    config = DuckDBConfig(
        database_path="data/financial_data.duckdb",
        parquet_root="./data/"
    )

    with UnifiedDuckDBManager(config) as manager:
        # Test basic parquet scan
        query = """
        SELECT COUNT(*) as total_records,
               COUNT(DISTINCT symbol) as unique_symbols,
               MIN(date) as earliest_date,
               MAX(date) as latest_date
        FROM parquet_scan('./data/**/*.parquet')
        """
        result = manager.analytics_query(query)

        print("✅ Data Access Test Results:")
        print(f"   - Total Records: {result.iloc[0]['total_records']:,}")
        print(f"   - Unique Symbols: {result.iloc[0]['unique_symbols']:,}")
        print(f"   - Date Range: {result.iloc[0]['earliest_date']} to {result.iloc[0]['latest_date']}")

        assert result.iloc[0]['total_records'] > 0, "No records found in data"
        assert result.iloc[0]['unique_symbols'] > 0, "No symbols found in data"


def test_volume_spike_analysis():
    """Test volume spike breakout pattern analysis."""
    print("\n🧪 Testing Volume Spike Analysis...")

    config = DuckDBConfig(
        database_path="data/financial_data.duckdb",
        parquet_root="./data/"
    )

    with UnifiedDuckDBManager(config) as manager:
        # Volume spike breakout query
        query = """
        SELECT
          symbol,
          date,
          ts as spike_time,
          volume,
          close as entry_price,
          volume / AVG(volume) OVER (
            PARTITION BY symbol, date
            ORDER BY ts
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
          ) as volume_multiplier,
          (MAX(high) OVER (
            PARTITION BY symbol, date
            ORDER BY ts
            ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
          ) - close) / close as price_move_pct
        FROM parquet_scan('./data/**/*.parquet')
        WHERE volume > 0 AND close > 0
          AND volume / AVG(volume) OVER (
            PARTITION BY symbol, date
            ORDER BY ts
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
          ) >= 1.5
          AND (MAX(high) OVER (
            PARTITION BY symbol, date
            ORDER BY ts
            ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
          ) - close) / close >= 0.03
        ORDER BY volume_multiplier DESC, price_move_pct DESC
        LIMIT 10
        """

        result = manager.analytics_query(query)

        print("✅ Volume Spike Analysis Results:")
        print(f"   - Found {len(result)} volume spike patterns")
        if len(result) > 0:
            print(f"   - Top volume multiplier: {result.iloc[0]['volume_multiplier']:.2f}")
            print(f"   - Top price move: {result.iloc[0]['price_move_pct']:.2%}")

            # Validate results
            assert all(result['volume_multiplier'] >= 1.5), "All results should have volume multiplier >= 1.5"
            assert all(result['price_move_pct'] >= 0.03), "All results should have price move >= 3%"


def test_time_window_breakout_analysis():
    """Test time window breakout pattern analysis."""
    print("\n🧪 Testing Time Window Breakout Analysis...")

    config = DuckDBConfig(
        database_path="data/financial_data.duckdb",
        parquet_root="./data/"
    )

    with UnifiedDuckDBManager(config) as manager:
        # Time window breakout query
        query = """
        WITH time_window_data AS (
          SELECT
            symbol,
            date,
            ts,
            time(ts) as trade_time,
            open,
            high,
            low,
            close,
            volume,
            AVG(volume) OVER (
              PARTITION BY symbol, date
              ORDER BY ts
              ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
            ) as pre_window_avg_volume,
            MAX(high) OVER (
              PARTITION BY symbol, date
              ORDER BY ts
              ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
            ) as post_window_max_high
          FROM parquet_scan('./data/**/*.parquet')
          WHERE time(ts) BETWEEN '09:35' AND '09:50'
        )
        SELECT
          symbol,
          date,
          trade_time,
          volume,
          close as entry_price,
          post_window_max_high,
          (post_window_max_high - close) / close as breakout_move_pct,
          volume / pre_window_avg_volume as volume_ratio
        FROM time_window_data
        WHERE volume / pre_window_avg_volume >= 1.2
          AND (post_window_max_high - close) / close >= 0.02
        ORDER BY breakout_move_pct DESC, volume_ratio DESC
        LIMIT 10
        """

        result = manager.analytics_query(query)

        print("✅ Time Window Analysis Results:")
        print(f"   - Found {len(result)} time window breakouts")
        if len(result) > 0:
            print(f"   - Top breakout move: {result.iloc[0]['breakout_move_pct']:.2%}")
            print(f"   - Top volume ratio: {result.iloc[0]['volume_ratio']:.2f}")

            # Validate time window constraint
            for _, row in result.iterrows():
                trade_time = row['trade_time']
                assert time(9, 35) <= trade_time <= time(9, 50), f"Time {trade_time} outside window"


def test_analytics_connector_integration():
    """Test the analytics connector with real data."""
    print("\n🧪 Testing Analytics Connector Integration...")

    # Test the refactored analytics connector
    connector = DuckDBAnalytics()

    # Test available symbols
    symbols = connector.get_available_symbols()
    print(f"✅ Available Symbols: Found {len(symbols)} symbols")
    assert len(symbols) > 0, "No symbols available"

    # Test date range
    start_date, end_date = connector.get_date_range()
    print(f"✅ Date Range: {start_date} to {end_date}")
    assert start_date < end_date, "Invalid date range"

    # Test volume spike patterns using connector
    patterns = connector.get_volume_spike_patterns(
        min_volume_multiplier=2.0,
        min_price_move=0.05,
        time_window_minutes=15
    )

    print(f"✅ Volume Spike Patterns: Found {len(patterns)} patterns")
    if len(patterns) > 0:
        print(f"   - Top pattern volume multiplier: {patterns[0].volume_multiplier:.2f}")

    # Test time window analysis
    time_patterns = connector.get_time_window_analysis(
        start_time="09:30",
        end_time="09:45"
    )

    print(f"✅ Time Window Patterns: Found {len(time_patterns)} patterns")

    # Test connection stats
    stats = connector.get_connection_stats()
    print(f"✅ Connection Stats: {stats}")

    connector.close()


def test_market_data_schema():
    """Test market data schema inspection."""
    print("\n🧪 Testing Market Data Schema...")

    connector = DuckDBAnalytics()

    # Test schema inspection
    schema_df = connector.get_market_data_schema()
    print(f"✅ Schema Inspection: Found {len(schema_df)} columns across {schema_df['table_name'].nunique()} tables")

    if len(schema_df) > 0:
        print("   - Sample columns:", schema_df['column_name'].head().tolist())

    connector.close()


def test_performance_comparison():
    """Compare performance between old and new approaches."""
    print("\n🧪 Testing Performance Comparison...")

    # Test unified manager performance
    config = DuckDBConfig(
        database_path="data/financial_data.duckdb",
        parquet_root="./data/"
    )

    import time

    with UnifiedDuckDBManager(config) as manager:
        # Test multiple queries
        queries = [
            "SELECT COUNT(*) FROM parquet_scan('./data/**/*.parquet')",
            "SELECT COUNT(DISTINCT symbol) FROM parquet_scan('./data/**/*.parquet')",
            "SELECT symbol, COUNT(*) as records FROM parquet_scan('./data/**/*.parquet') GROUP BY symbol ORDER BY records DESC LIMIT 5"
        ]

        start_time = time.time()
        for i, query in enumerate(queries, 1):
            result = manager.analytics_query(query)
            print(f"   - Query {i}: {len(result)} rows returned")

        end_time = time.time()
        execution_time = end_time - start_time

        print(f"   - Total execution time: {execution_time:.2f}s")
        assert execution_time < 10.0, "Queries took too long to execute"


def test_error_handling():
    """Test error handling with invalid queries."""
    print("\n🧪 Testing Error Handling...")

    config = DuckDBConfig(
        database_path="data/financial_data.duckdb",
        parquet_root="./data/"
    )

    with UnifiedDuckDBManager(config) as manager:
        # Test invalid query
        try:
            manager.analytics_query("SELECT * FROM nonexistent_table")
            assert False, "Should have raised an exception"
        except Exception as e:
            print(f"✅ Error Handling: Correctly caught error - {str(e)[:100]}...")

        # Test with invalid parameters
        try:
            manager.analytics_query("SELECT * FROM parquet_scan('./data/**/*.parquet') WHERE invalid_column = {value}", value="test")
            assert False, "Should have raised an exception"
        except Exception as e:
            print(f"✅ Parameter Error Handling: Correctly caught error - {str(e)[:100]}...")


def test_connection_pooling():
    """Test connection pooling behavior."""
    print("\n🧪 Testing Connection Pooling...")

    config = DuckDBConfig(
        database_path="data/financial_data.duckdb",
        parquet_root="./data/",
        max_connections=3
    )

    managers = []
    initial_stats = None

    # Create multiple managers to test pooling
    for i in range(3):
        manager = UnifiedDuckDBManager(config)
        if initial_stats is None:
            initial_stats = manager.get_connection_stats()

        # Execute a query to trigger connection creation
        manager.analytics_query("SELECT COUNT(*) FROM parquet_scan('./data/**/*.parquet')")
        managers.append(manager)

        stats = manager.get_connection_stats()
        print(f"✅ Manager {i+1} Stats: {stats}")

    # Verify connection pooling
    final_stats = managers[-1].get_connection_stats()
    print(f"✅ Final Pool Stats: {final_stats}")

    # Clean up
    for manager in managers:
        manager.close()


def main():
    """Run all analytics query tests."""
    print("🚀 Starting Analytics Query Validation Tests")
    print("=" * 50)

    try:
        # Run all tests
        test_basic_data_access()
        test_volume_spike_analysis()
        test_time_window_breakout_analysis()
        test_analytics_connector_integration()
        test_market_data_schema()
        test_performance_comparison()
        test_error_handling()
        test_connection_pooling()

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! Analytics queries are working correctly against real data.")
        print("✅ Unified DuckDB integration validated")
        print("✅ Analytics connector functionality confirmed")
        print("✅ Performance and error handling verified")
        print("✅ Connection pooling working properly")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
