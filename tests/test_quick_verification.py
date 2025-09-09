#!/usr/bin/env python3
"""
Quick verification tests - fast and focused on core functionality.
These tests verify that the singleton removal and database fixes work correctly.
"""

import sys
import time as time_module
from pathlib import Path
from datetime import date, time
from concurrent.futures import ThreadPoolExecutor


def test_database_connection_manager():
    """Quick test for database connection manager."""
    print("🗄️ Testing Database Connection Manager...")

    try:
        from src.infrastructure.core.singleton_database import create_db_manager

        # Test creation
        manager = create_db_manager(db_path=":memory:")
        print("   ✅ Manager created successfully")

        # Test connection
        with manager.get_connection() as conn:
            result = conn.execute("SELECT 1 as test").fetchone()
            assert result[0] == 1
            print("   ✅ Connection works")

        # Test query execution
        df = manager.execute_query("SELECT 'hello' as message")
        assert len(df) == 1
        assert df.iloc[0]['message'] == 'hello'
        print("   ✅ Query execution works")

        manager.close()
        print("   ✅ Manager closed successfully")

        return True

    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False


def test_singleton_removal():
    """Test that singleton pattern has been removed."""
    print("\\n🔄 Testing Singleton Removal...")

    try:
        from src.infrastructure.core.singleton_database import create_db_manager

        # Create multiple managers
        manager1 = create_db_manager(db_path=":memory:")
        manager2 = create_db_manager(db_path=":memory:")

        # They should be different objects
        assert manager1 is not manager2
        print("   ✅ Multiple managers can exist")

        # Both should work independently
        with manager1.get_connection() as conn1:
            result1 = conn1.execute("SELECT 1").fetchone()

        with manager2.get_connection() as conn2:
            result2 = conn2.execute("SELECT 2").fetchone()

        assert result1[0] == 1
        assert result2[0] == 2
        print("   ✅ Managers work independently")

        manager1.close()
        manager2.close()
        print("   ✅ Both managers closed")

        return True

    except Exception as e:
        print(f"   ❌ Singleton removal test failed: {e}")
        return False


def test_connection_pool():
    """Test connection pool functionality."""
    print("\\n🏊 Testing Connection Pool...")

    try:
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:", max_connections=3)

        # Test concurrent connections
        def worker(worker_id):
            with manager.get_connection() as conn:
                result = conn.execute(f"SELECT {worker_id}").fetchone()
                return result[0]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            results = [future.result() for future in futures]

        # Should have 5 results
        assert len(results) == 5
        assert set(results) == {0, 1, 2, 3, 4}
        print("   ✅ Concurrent connections work")

        manager.close()
        print("   ✅ Connection pool test passed")

        return True

    except Exception as e:
        print(f"   ❌ Connection pool test failed: {e}")
        return False


def test_scanner_basic():
    """Test basic scanner functionality."""
    print("\\n🔍 Testing Scanner Basic Functionality...")

    try:
        from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        # Create scanner
        scanner = BreakoutScanner(db_manager=manager)
        print("   ✅ Scanner created successfully")

        # Test basic scan (should not crash)
        test_date = date(2025, 9, 3)
        cutoff_time = time(9, 50)

        results = scanner.scan(test_date, cutoff_time)
        print(f"   ✅ Scan completed (returned {len(results)} results)")

        # Should return a DataFrame
        import pandas as pd
        assert isinstance(results, pd.DataFrame)
        print("   ✅ Results are DataFrame")

        manager.close()
        print("   ✅ Scanner test passed")

        return True

    except Exception as e:
        print(f"   ❌ Scanner test failed: {e}")
        return False


def test_scanner_runner():
    """Test scanner runner functionality."""
    print("\\n🏃 Testing Scanner Runner...")

    try:
        from src.application.infrastructure.di_container import get_scanner_runner

        runner = get_scanner_runner()
        print("   ✅ Scanner runner created")

        # Test basic scanner execution
        test_date = date(2025, 9, 3)

        results = runner.run_scanner(
            scanner_name="enhanced_breakout",
            start_date=test_date,
            end_date=test_date
        )
        print(f"   ✅ Scanner runner executed (returned {len(results)} results)")

        # Should return a list
        assert isinstance(results, list)
        print("   ✅ Results are list")

        return True

    except Exception as e:
        print(f"   ❌ Scanner runner test failed: {e}")
        return False


def test_api_endpoints():
    """Test basic API endpoint functionality."""
    print("\\n🌐 Testing API Endpoints...")

    try:
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.interfaces.api.routes.scanner_api import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/scanner")
        client = TestClient(app)

        # Test health endpoint
        response = client.get("/api/v1/scanner/health")
        assert response.status_code == 200
        print("   ✅ Health endpoint works")

        # Test config endpoint
        response = client.get("/api/v1/scanner/config/default")
        assert response.status_code == 200
        print("   ✅ Config endpoint works")

        # Test scanners endpoint
        response = client.get("/api/v1/scanner/scanners")
        assert response.status_code == 200
        print("   ✅ Scanners endpoint works")

        return True

    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        return False


def test_concurrent_access():
    """Test concurrent access to database."""
    print("\\n⚡ Testing Concurrent Access...")

    try:
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        # Create test table
        with manager.get_connection() as conn:
            conn.execute("""
                CREATE TABLE test_concurrent (
                    id INTEGER,
                    value INTEGER
                )
            """)
            for i in range(10):
                conn.execute("INSERT INTO test_concurrent VALUES (?, ?)", [i, i * 10])

        # Test concurrent reads
        def concurrent_reader(worker_id):
            df = manager.execute_query("SELECT COUNT(*) FROM test_concurrent")
            return df.iloc[0, 0]

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_reader, i) for i in range(10)]
            results = [future.result() for future in futures]

        # All should return 10
        assert all(result == 10 for result in results)
        print("   ✅ Concurrent reads work")

        manager.close()
        print("   ✅ Concurrent access test passed")

        return True

    except Exception as e:
        print(f"   ❌ Concurrent access test failed: {e}")
        return False


def main():
    """Run all quick verification tests."""
    print("🚀 Quick Verification Test Suite")
    print("=" * 50)

    start_time = time_module.time()

    tests = [
        ("Database Connection Manager", test_database_connection_manager),
        ("Singleton Removal", test_singleton_removal),
        ("Connection Pool", test_connection_pool),
        ("Scanner Basic", test_scanner_basic),
        ("Scanner Runner", test_scanner_runner),
        ("API Endpoints", test_api_endpoints),
        ("Concurrent Access", test_concurrent_access),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")

    end_time = time_module.time()
    duration = end_time - start_time

    print("\\n" + "=" * 50)
    print("📊 QUICK VERIFICATION RESULTS")
    print("=" * 50)
    print(f"✅ Passed: {passed}/{total}")
    print(f"📊 Success Rate: {passed/total*100:.1f}%")
    print(f"⏱️  Duration: {duration:.3f}s")
    if passed == total:
        print("\\n🎉 ALL TESTS PASSED!")
        print("✅ Singleton pattern removed successfully")
        print("✅ Database connection manager working")
        print("✅ Scanners functioning correctly")
        print("✅ API endpoints operational")
        print("✅ Concurrent access supported")
        return True
    else:
        print(f"\\n⚠️  {total - passed} test(s) failed")
        print("🔧 Check the error messages above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
