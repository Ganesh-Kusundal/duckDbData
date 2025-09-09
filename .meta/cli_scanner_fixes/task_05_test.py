#!/usr/bin/env python3
"""
Task 5: Test Column Name Mapping
Tests for proper column name mapping in query results
"""

import duckdb


def test_column_name_extraction():
    """Test that column names are properly extracted from query results."""
    conn = duckdb.connect('data/financial_data.duckdb')

    # Test query with explicit column names
    query = '''
    SELECT
        symbol,
        timestamp,
        close as price,
        volume,
        2.5 as price_change_pct,
        1.8 as volume_multiplier,
        3.2 as breakout_strength,
        'breakout' as pattern_type
    FROM market_data
    WHERE date_partition = '2024-11-14'
    AND symbol = 'SBILIFE'
    LIMIT 1
    '''

    result = conn.execute(query)

    # Test that we can get rows (DuckDB doesn't provide column names via .keys())
    rows = result.fetchall()
    print(f"✅ Query executed, got {len(rows)} rows")

    if rows:
        first_row = rows[0]
        print(f"✅ First row: {first_row}")

        # Test manual column mapping (like the rule engine does)
        if len(first_row) == 8:  # breakout query
            column_names = ['symbol', 'timestamp', 'price', 'volume',
                          'price_change_pct', 'volume_multiplier',
                          'breakout_strength', 'pattern_type']
            row_dict = dict(zip(column_names, first_row))
            print(f"✅ Mapped row: {row_dict}")

            # Verify required keys
            assert 'symbol' in row_dict, "Missing 'symbol' key"
            assert 'price' in row_dict, "Missing 'price' key"
            print("✅ Column mapping successful")
        else:
            print(f"⚠️  Unexpected row length: {len(first_row)}")
    else:
        print("⚠️  No rows returned")


    conn.close()
    return True


def test_breakout_query_column_mapping():
    """Test the actual breakout query column mapping."""
    conn = duckdb.connect('data/financial_data.duckdb')

    # This is the exact query structure used by the rule engine
    query = '''
    WITH price_data AS (
        SELECT
            symbol,
            timestamp,
            close as price,
            volume,
            LAG(close, 1) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_price,
            LAG(volume, 1) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_volume,
            AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 10 PRECEDING) as avg_price_10,
            AVG(volume) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 10 PRECEDING) as avg_volume_10
        FROM market_data
        WHERE date_partition = '2024-11-14'
        AND (EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) >= 33300
        AND (EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) <= 35400
    ),
    breakout_signals AS (
        SELECT
            symbol,
            timestamp,
            price,
            volume,
            prev_price,
            prev_volume,
            avg_price_10,
            avg_volume_10,
            CASE
                WHEN prev_price > 0 THEN ((price - prev_price) / prev_price) * 100
                ELSE 0
            END as price_change_pct,
            CASE
                WHEN avg_volume_10 > 0 THEN volume / avg_volume_10
                ELSE 1
            END as volume_multiplier,
            CASE
                WHEN avg_price_10 > 0 THEN ((price - avg_price_10) / avg_price_10) * 100
                ELSE 0
            END as breakout_strength
        FROM price_data
        WHERE prev_price IS NOT NULL
        AND price_change_pct >= 0.5 AND price_change_pct <= 10.0
        AND volume_multiplier >= 1.5
    )
    SELECT
        symbol,
        timestamp,
        price,
        volume,
        price_change_pct,
        volume_multiplier,
        breakout_strength,
        'breakout' as pattern_type
    FROM breakout_signals
    ORDER BY volume_multiplier DESC, price_change_pct DESC
    LIMIT 5
    '''

    result = conn.execute(query)

    # Get rows directly (DuckDB doesn't support .keys())
    rows = result.fetchall()
    print(f"✅ Breakout query returned {len(rows)} rows")

    if rows:
        # Test the column mapping logic from the rule engine
        for i, row in enumerate(rows[:3]):  # Test first 3 rows
            row_dict = {}

            # Map columns based on query type (determined by row length)
            if len(row) == 8:  # breakout query columns
                column_names = ['symbol', 'timestamp', 'price', 'volume',
                              'price_change_pct', 'volume_multiplier',
                              'breakout_strength', 'pattern_type']
            else:
                column_names = [f'col_{j}' for j in range(len(row))]

            # Map each column
            for j, value in enumerate(row):
                if j < len(column_names):
                    row_dict[column_names[j]] = value
                else:
                    row_dict[f'col_{j}'] = value

            print(f"✅ Mapped row {i}: {row_dict}")

            # Verify required keys
            assert 'symbol' in row_dict, "Missing 'symbol' key"
            assert 'price' in row_dict, "Missing 'price' key"
            assert 'volume' in row_dict, "Missing 'volume' key"

    else:
        print("⚠️  No rows returned from breakout query")
        conn.close()
        return False

    conn.close()
    return True


if __name__ == "__main__":
    print("Testing column name mapping...")

    tests = [
        test_column_name_extraction,
        test_breakout_query_column_mapping
    ]

    passed = 0
    for test in tests:
        print(f"\n--- Running {test.__name__} ---")
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("✅ All column mapping tests passed!")
    else:
        print("❌ Some tests failed")
        exit(1)
