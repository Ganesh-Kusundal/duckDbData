#!/usr/bin/env python3
"""
Simple Analytics Query Test
===========================

Basic test to validate analytics queries work against real data.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from analytics.core.duckdb_connector import DuckDBAnalytics


def test_simple_analytics():
    """Test basic analytics functionality."""
    print("🧪 Testing Basic Analytics Connector...")

    # Test the analytics connector directly
    connector = DuckDBAnalytics()

    # Test basic data access without unified view
    try:
        # Test available symbols
        symbols = connector.get_available_symbols()
        print(f"✅ Found {len(symbols)} symbols")
        if len(symbols) > 0:
            print(f"   Sample symbols: {symbols[:5]}")

        # Test date range
        start_date, end_date = connector.get_date_range()
        print(f"✅ Date range: {start_date} to {end_date}")

        # Test a simple analytics query
        query = """
        SELECT COUNT(*) as total_records,
               COUNT(DISTINCT regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1)) as unique_symbols
        FROM parquet_scan('./data/2024/01/02/*.parquet')
        """
        result = connector.execute_analytics_query(query)
        print(f"✅ Query result: {result.iloc[0]['total_records']} records, {result.iloc[0]['unique_symbols']} symbols")

        connector.close()
        print("✅ Basic analytics test passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_simple_analytics()
    sys.exit(0 if success else 1)
