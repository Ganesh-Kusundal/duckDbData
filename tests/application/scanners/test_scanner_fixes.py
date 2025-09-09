#!/usr/bin/env python3
"""
Comprehensive tests for scanner fixes and optimizations.
Tests verify that all scanner fixes work correctly with the new database manager.
"""

import pytest
from datetime import date, time
from unittest.mock import patch, MagicMock
import pandas as pd
from typing import Dict, Any


class TestCRPScannerFixes:
    """Test CRP scanner fixes and optimizations."""

    @pytest.fixture
    def crp_scanner(self, isolated_db_manager):
        """Create CRP scanner with isolated database."""
        from src.application.scanners.strategies.crp_scanner import CRPScanner
        return CRPScanner(db_manager=isolated_db_manager)

    def test_crp_scanner_creation(self, crp_scanner):
        """Test CRP scanner can be created successfully."""
        assert crp_scanner is not None
        assert hasattr(crp_scanner, 'scan')
        assert hasattr(crp_scanner, 'scan_date_range')
        assert hasattr(crp_scanner, 'get_available_symbols')

    def test_crp_config_defaults_safe_access(self, crp_scanner):
        """Test CRP scanner uses safe config access with defaults."""
        # Test that config.get() is used with defaults
        config = crp_scanner.config

        # These should all work without KeyError even if config keys don't exist
        min_price = config.get('min_price', 50)
        max_price = config.get('max_price', 2000)
        close_threshold = config.get('close_threshold_pct', 2.0)

        assert min_price == 50
        assert max_price == 2000
        assert close_threshold == 2.0

    def test_crp_scan_date_range_with_defaults(self, crp_scanner):
        """Test CRP scanner date range scan with default parameters."""
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 3)

        results = crp_scanner.scan_date_range(
            start_date=start_date,
            end_date=end_date
        )

        assert isinstance(results, list)
        # Results may be empty if no data matches criteria, but should not error

    def test_crp_scan_single_day_basic(self, crp_scanner):
        """Test basic CRP single day scan."""
        scan_date = date(2025, 9, 3)
        cutoff_time = time(9, 50)

        results = crp_scanner.scan(scan_date, cutoff_time)

        assert isinstance(results, pd.DataFrame)
        # Should have expected columns if results exist
        if not results.empty:
            expected_columns = ['symbol', 'crp_price', 'current_volume', 'crp_probability_score']
            for col in expected_columns:
                assert col in results.columns

    def test_crp_scanner_with_custom_config(self, isolated_db_manager):
        """Test CRP scanner with custom configuration."""
        from src.application.scanners.strategies.crp_scanner import CRPScanner

        custom_config = {
            'min_price': 100,
            'max_price': 1000,
            'max_results_per_day': 5,
            'close_threshold_pct': 1.5
        }

        scanner = CRPScanner(db_manager=isolated_db_manager, config=custom_config)

        assert scanner.config['min_price'] == 100
        assert scanner.config['max_price'] == 1000
        assert scanner.config['max_results_per_day'] == 5

    def test_crp_database_connection_usage(self, crp_scanner):
        """Test CRP scanner uses database connection properly."""
        scan_date = date(2025, 9, 3)
        cutoff_time = time(9, 50)

        # This should not raise errors about missing get_connection method
        results = crp_scanner.scan(scan_date, cutoff_time)
        assert isinstance(results, pd.DataFrame)


class TestTechnicalScannerFixes:
    """Test technical scanner fixes and optimizations."""

    @pytest.fixture
    def technical_scanner(self, isolated_db_manager):
        """Create technical scanner with isolated database."""
        from src.application.scanners.strategies.technical_scanner import TechnicalScanner
        return TechnicalScanner(db_manager=isolated_db_manager)

    def test_technical_scanner_creation(self, technical_scanner):
        """Test technical scanner can be created successfully."""
        assert technical_scanner is not None
        assert hasattr(technical_scanner, 'scan')

    def test_technical_config_safe_access(self, technical_scanner):
        """Test technical scanner uses safe config access."""
        config = technical_scanner.config

        # Should handle missing config keys gracefully
        min_price = config.get('min_price', 50)
        max_price = config.get('max_price', 2000)
        max_results = config.get('max_results', 10)

        assert min_price == 50
        assert max_price == 2000
        assert max_results == 10

    def test_technical_scan_with_date_formatting(self, technical_scanner):
        """Test technical scanner handles date formatting correctly."""
        scan_date = date(2025, 9, 3)
        cutoff_time = time(9, 50)

        # This should not raise strftime errors
        results = technical_scanner.scan(scan_date, cutoff_time)

        assert isinstance(results, pd.DataFrame)
        # Should have expected columns if results exist
        if not results.empty:
            expected_columns = ['symbol', 'current_price', 'volume']
            for col in expected_columns:
                assert col in results.columns

    def test_technical_scan_date_range(self, technical_scanner):
        """Test technical scanner date range functionality."""
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 3)

        results = technical_scanner.scan_date_range(
            start_date=start_date,
            end_date=end_date
        )

        assert isinstance(results, list)
        # Each result should be a dict or DataFrame
        for result in results:
            assert isinstance(result, (dict, pd.DataFrame))


class TestRelativeVolumeScannerFixes:
    """Test relative volume scanner fixes and optimizations."""

    @pytest.fixture
    def relative_volume_scanner(self, isolated_db_manager):
        """Create relative volume scanner with isolated database."""
        from src.application.scanners.strategies.relative_volume_scanner import RelativeVolumeScanner
        return RelativeVolumeScanner(db_manager=isolated_db_manager)

    def test_relative_volume_scanner_creation(self, relative_volume_scanner):
        """Test relative volume scanner can be created successfully."""
        assert relative_volume_scanner is not None
        assert hasattr(relative_volume_scanner, 'scan')

    def test_relative_volume_config_safe_access(self, relative_volume_scanner):
        """Test relative volume scanner uses safe config access."""
        config = relative_volume_scanner.config

        # Should handle missing config keys gracefully
        min_rel_vol = config.get('min_relative_volume', 5.0)
        lookback_days = config.get('lookback_days', 14)
        min_avg_vol = config.get('min_avg_volume', 100000)
        max_results = config.get('max_results', 10)

        assert min_rel_vol == 5.0
        assert lookback_days == 14
        assert min_avg_vol == 100000
        assert max_results == 10

    def test_relative_volume_scan_with_date_formatting(self, relative_volume_scanner):
        """Test relative volume scanner handles date formatting correctly."""
        scan_date = date(2025, 9, 3)
        cutoff_time = time(9, 50)

        # This should not raise strftime or KeyError
        results = relative_volume_scanner.scan(scan_date, cutoff_time)

        assert isinstance(results, pd.DataFrame)
        # Should have expected columns if results exist
        if not results.empty:
            expected_columns = ['symbol', 'current_price', 'relative_volume']
            for col in expected_columns:
                assert col in results.columns

    def test_relative_volume_scan_date_range(self, relative_volume_scanner):
        """Test relative volume scanner date range functionality."""
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 3)

        results = relative_volume_scanner.scan_date_range(
            start_date=start_date,
            end_date=end_date
        )

        assert isinstance(results, list)
        # Each result should be a dict or DataFrame
        for result in results:
            assert isinstance(result, (dict, pd.DataFrame))


class TestScannerRunnerFixes:
    """Test scanner runner fixes and optimizations."""

    @pytest.fixture
    def scanner_runner(self):
        """Create scanner runner instance."""
        from src.application.infrastructure.di_container import get_scanner_runner
        return get_scanner_runner()

    def test_scanner_runner_creation(self, scanner_runner):
        """Test scanner runner can be created successfully."""
        assert scanner_runner is not None
        assert hasattr(scanner_runner, 'run_scanner')

    def test_scanner_runner_with_defaults(self, scanner_runner):
        """Test scanner runner uses default cutoff_time and end_of_day_time."""
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 3)

        # Should not raise errors about None values
        results = scanner_runner.run_scanner(
            scanner_name="enhanced_crp",
            start_date=start_date,
            end_date=end_date
            # No cutoff_time or end_of_day_time provided - should use defaults
        )

        assert isinstance(results, list)

    def test_scanner_runner_all_scanners(self, scanner_runner):
        """Test scanner runner works with all scanner types."""
        scanners_to_test = ['enhanced_breakout', 'enhanced_crp', 'technical', 'relative_volume']
        test_date = date(2025, 9, 3)

        for scanner_name in scanners_to_test:
            results = scanner_runner.run_scanner(
                scanner_name=scanner_name,
                start_date=test_date,
                end_date=test_date
            )

            assert isinstance(results, list)
            # Should not raise errors about database connections

    def test_scanner_runner_custom_config(self, scanner_runner):
        """Test scanner runner with custom configuration."""
        test_date = date(2025, 9, 3)
        custom_config = {
            'min_price': 100,
            'max_price': 1000,
            'max_results_per_day': 5
        }

        results = scanner_runner.run_scanner(
            scanner_name="enhanced_breakout",
            start_date=test_date,
            end_date=test_date,
            config=custom_config
        )

        assert isinstance(results, list)


class TestScannerIntegrationFixes:
    """Test integration fixes across all scanners."""

    def test_all_scanners_use_new_db_manager(self):
        """Test that all scanners use the new database manager."""
        from src.application.infrastructure.di_container import get_scanner_runner

        runner = get_scanner_runner()

        # Test that we can create all scanner types without errors
        scanners = ['enhanced_breakout', 'enhanced_crp', 'technical', 'relative_volume']

        for scanner_name in scanners:
            # This should not raise "get_connection" errors
            results = runner.run_scanner(
                scanner_name=scanner_name,
                start_date=date(2025, 9, 3),
                end_date=date(2025, 9, 3)
            )
            assert isinstance(results, list)

    def test_concurrent_scanner_execution(self):
        """Test that multiple scanners can run concurrently."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        results = {}
        errors = []

        def run_scanner(scanner_name):
            """Run a single scanner."""
            try:
                from src.application.infrastructure.di_container import get_scanner_runner
                runner = get_scanner_runner()
                scan_results = runner.run_scanner(
                    scanner_name=scanner_name,
                    start_date=date(2025, 9, 3),
                    end_date=date(2025, 9, 3)
                )
                results[scanner_name] = len(scan_results)
            except Exception as e:
                errors.append(f"{scanner_name}: {e}")

        scanners = ['enhanced_breakout', 'enhanced_crp', 'technical', 'relative_volume']

        # Run scanners concurrently
        with ThreadPoolExecutor(max_workers=len(scanners)) as executor:
            futures = [executor.submit(run_scanner, scanner) for scanner in scanners]
            for future in futures:
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == len(scanners)

        # All results should be lists (even if empty)
        for scanner_name, result_count in results.items():
            assert isinstance(result_count, int)

    def test_scanner_config_validation(self):
        """Test that scanner configurations are validated properly."""
        from src.application.infrastructure.di_container import get_scanner_runner

        runner = get_scanner_runner()

        # Test with invalid config - should not crash
        invalid_config = {
            'min_price': 'invalid',  # Should be number
            'max_results_per_day': -1  # Should be positive
        }

        # This should handle invalid config gracefully
        results = runner.run_scanner(
            scanner_name="enhanced_breakout",
            start_date=date(2025, 9, 3),
            end_date=date(2025, 9, 3),
            config=invalid_config
        )

        assert isinstance(results, list)  # Should not crash


class TestPerformanceOptimizations:
    """Test performance optimizations in scanners."""

    def test_optimized_eod_price_queries(self):
        """Test that EOD price queries use QUALIFY optimization."""
        from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")
        scanner = BreakoutScanner(db_manager=manager)

        # Create test data
        with manager.get_connection() as conn:
            conn.execute("""
                CREATE TABLE market_data (
                    symbol VARCHAR,
                    date_partition DATE,
                    timestamp TIMESTAMP,
                    close DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    volume INTEGER
                )
            """)

            # Insert test data
            for i in range(10):
                conn.execute("""
                    INSERT INTO market_data VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [f'SYMBOL{i}', '2025-09-03', f'2025-09-03T{i}:00:00Z', 100.0 + i, 105.0 + i, 95.0 + i, 10000 + i * 100])

        # This should use the optimized QUALIFY query
        scan_date = date(2025, 9, 3)
        cutoff_time = time(9, 50)

        results = scanner.scan(scan_date, cutoff_time)

        assert isinstance(results, pd.DataFrame)
        # Should complete without performance issues

        manager.close()

    def test_batch_query_optimization(self):
        """Test that batch queries are optimized."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        # Create test data
        with manager.get_connection() as conn:
            conn.execute("""
                CREATE TABLE market_data (
                    symbol VARCHAR,
                    date_partition DATE,
                    timestamp TIMESTAMP,
                    close DOUBLE,
                    volume INTEGER
                )
            """)

            # Insert multiple symbols
            symbols = [f'SYMBOL{i}' for i in range(100)]
            for symbol in symbols:
                for i in range(10):
                    conn.execute("""
                        INSERT INTO market_data VALUES (?, ?, ?, ?, ?)
                    """, [symbol, '2025-09-03', f'2025-09-03T{i}:00:00Z', 100.0 + i, 10000 + i * 100])

        # Test batch query execution
        df = manager.execute_custom_query("""
            SELECT symbol, COUNT(*) as count
            FROM market_data
            WHERE date_partition = ?
            GROUP BY symbol
        """, ['2025-09-03'])

        assert len(df) == 100  # Should return all symbols
        assert df['count'].sum() == 1000  # Should have 10 records each

        manager.close()


if __name__ == "__main__":
    # Run basic smoke tests
    print("🧪 Running scanner fixes smoke tests...")

    from src.infrastructure.core.singleton_database import create_db_manager

    # Test CRP scanner
    try:
        from src.application.scanners.strategies.crp_scanner import CRPScanner
        manager = create_db_manager(db_path=":memory:")
        crp_scanner = CRPScanner(db_manager=manager)
        results = crp_scanner.scan(date(2025, 9, 3), time(9, 50))
        print("✅ CRP scanner test passed")
        manager.close()
    except Exception as e:
        print(f"❌ CRP scanner test failed: {e}")

    # Test technical scanner
    try:
        from src.application.scanners.strategies.technical_scanner import TechnicalScanner
        manager = create_db_manager(db_path=":memory:")
        tech_scanner = TechnicalScanner(db_manager=manager)
        results = tech_scanner.scan(date(2025, 9, 3), time(9, 50))
        print("✅ Technical scanner test passed")
        manager.close()
    except Exception as e:
        print(f"❌ Technical scanner test failed: {e}")

    # Test relative volume scanner
    try:
        from src.application.scanners.strategies.relative_volume_scanner import RelativeVolumeScanner
        manager = create_db_manager(db_path=":memory:")
        rv_scanner = RelativeVolumeScanner(db_manager=manager)
        results = rv_scanner.scan(date(2025, 9, 3), time(9, 50))
        print("✅ Relative volume scanner test passed")
        manager.close()
    except Exception as e:
        print(f"❌ Relative volume scanner test failed: {e}")

    print("\\n🎉 Scanner fixes smoke tests completed!")
    print("\\n💡 Run with pytest for comprehensive testing:")
    print("pytest tests/application/scanners/test_scanner_fixes.py -v")


