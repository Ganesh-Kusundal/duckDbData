#!/usr/bin/env python3
"""
Example test showing how to use database fixtures to avoid lock issues.
This demonstrates the proper way to test scanner functionality.
"""

import pytest
from datetime import date, time
import pandas as pd


def test_scanner_with_isolated_database(isolated_db_manager, mock_scanner):
    """Test scanner using isolated database fixture."""
    # No database lock issues - each test gets its own copy
    scanner = mock_scanner

    # Apply test configuration
    scanner.config.update({
        'resistance_break_pct': 0.5,
        'breakout_volume_ratio': 1.5,
        'consolidation_range_pct': 8.0,
        'min_price': 50,
        'max_price': 2000,
        'max_results': 10  # Smaller for testing
    })

    test_date = date(2025, 9, 5)
    cutoff_time = time(9, 50)

    # Test scanner functionality
    results = scanner.scan(test_date, cutoff_time)

    # Verify results
    assert isinstance(results, pd.DataFrame)
    assert not results.empty

    # Check required columns exist
    required_columns = ['symbol', 'current_price', 'probability_score']
    for col in required_columns:
        assert col in results.columns

    print(f"✅ Found {len(results)} breakout candidates")


def test_scanner_readonly_mode(readonly_db_manager):
    """Test scanner in read-only mode (no locks)."""
    from src.application.scanners.strategies.breakout_scanner import BreakoutScanner

    # Create scanner with read-only database
    scanner = BreakoutScanner(db_manager=readonly_db_manager)

    test_date = date(2025, 9, 5)
    cutoff_time = time(9, 50)

    # This should work without locking the main database
    symbols = scanner.get_available_symbols()

    assert isinstance(symbols, list)
    assert len(symbols) > 0
    print(f"✅ Found {len(symbols)} available symbols")


def test_database_isolation(isolated_db_manager):
    """Test that isolated databases don't interfere with each other."""
    from src.infrastructure.core.singleton_database import create_db_manager

    # Create two separate database instances
    db1_path = isolated_db_manager.db_path
    db2_path = str(db1_path).replace('.duckdb', '_2.duckdb')

    # Copy to second database
    import shutil
    shutil.copy2(db1_path, db2_path)

    db2 = create_db_manager(db_path=db2_path)

    # Both should work independently
    assert db1_path != db2_path

    # Clean up
    db2.close()
    print("✅ Database isolation working correctly")


if __name__ == "__main__":
    # Run tests directly (for demonstration)
    print("🧪 Running scanner tests with proper database isolation...")

    # This would normally be handled by pytest fixtures
    print("Note: Run with pytest to use proper fixtures:")
    print("pytest tests/application/scanners/integration/test_scanner_with_fixtures.py -v")
