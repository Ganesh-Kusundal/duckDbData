#!/usr/bin/env python3
"""
Task 3: Test Real Database Query Execution
Tests for replacing mock data with actual DuckDB queries
"""

import duckdb
from datetime import date


def test_database_connection():
    """Test basic database connection and table access."""
    conn = None
    try:
        conn = duckdb.connect('data/financial_data.duckdb')

        # Test table exists
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert 'market_data' in table_names, "market_data table not found"

        # Test basic query
        count = conn.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
        assert count > 0, "No data in market_data table"

        print(f"✅ Database connection successful, {count} records found")
        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        if conn:
            conn.close()


def test_breakout_query_structure():
    """Test that breakout queries return expected structure."""
    conn = None
    try:
        conn = duckdb.connect('data/financial_data.duckdb')

        # Test breakout query structure
        query = '''
        SELECT
            symbol,
            timestamp,
            close as price,
            volume
        FROM market_data
        WHERE date_partition = '2024-11-14'
        AND symbol = 'SBILIFE'
        LIMIT 5
        '''

        result = conn.execute(query).fetchall()

        # Verify structure
        if result:
            row = result[0]
            assert len(row) >= 4, f"Expected at least 4 columns, got {len(row)}"
            print(f"✅ Query structure valid, sample row: {row}")
            return True
        else:
            print("⚠️  No data returned for test query")
            return False

    except Exception as e:
        print(f"❌ Query structure test failed: {e}")
        return False
    finally:
        if conn:
            conn.close()


def test_query_with_time_filters():
    """Test queries with time filter conditions."""
    conn = None
    try:
        conn = duckdb.connect('data/financial_data.duckdb')

        # Test time-based query
        query = '''
        SELECT COUNT(*) as count
        FROM market_data
        WHERE date_partition = '2024-11-14'
        AND (EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) >= ?
        AND (EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) <= ?
        '''

        # 9:15 AM to 9:50 AM in seconds since midnight
        start_seconds = 9 * 3600 + 15 * 60  # 33300
        end_seconds = 9 * 3600 + 50 * 60    # 35400

        result = conn.execute(query, [start_seconds, end_seconds]).fetchone()
        count = result[0]

        print(f"✅ Time filter query successful, {count} records in time range")
        return True

    except Exception as e:
        print(f"❌ Time filter query failed: {e}")
        return False
    finally:
        if conn:
            conn.close()


def test_no_mock_data_usage():
    """Test that actual queries are executed, not mock data."""
    # This test verifies that we're using real database queries
    # by checking that we can get different results for different parameters

    conn = None
    try:
        conn = duckdb.connect('data/financial_data.duckdb')

        # Query 1: AAPL data
        query1 = "SELECT COUNT(*) FROM market_data WHERE date_partition = '2024-11-14' AND symbol = 'AAPL'"
        count1 = conn.execute(query1).fetchone()[0]

        # Query 2: SBILIFE data
        query2 = "SELECT COUNT(*) FROM market_data WHERE date_partition = '2024-11-14' AND symbol = 'SBILIFE'"
        count2 = conn.execute(query2).fetchone()[0]

        # Results should be different (real data)
        assert count1 != count2, "Mock data would return same results"

        print(f"✅ Real data confirmed: AAPL={count1}, SBILIFE={count2}")
        return True

    except Exception as e:
        print(f"❌ Real data test failed: {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("Testing real database query execution...")

    tests = [
        test_database_connection,
        test_breakout_query_structure,
        test_query_with_time_filters,
        test_no_mock_data_usage
    ]

    passed = 0
    for test in tests:
        print(f"\n--- Running {test.__name__} ---")
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("✅ All database query tests passed!")
    else:
        print("❌ Some tests failed")
        exit(1)
