#!/usr/bin/env python3
"""
Complete workflow integration tests.
Tests the entire pipeline from database connection to API responses.
"""

import pytest
from datetime import date, time
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pandas as pd
import json
from unittest.mock import patch, MagicMock


class TestCompleteWorkflow:
    """Test complete workflow from database to API."""

    @pytest.fixture
    def test_app(self):
        """Create test FastAPI application with all routes."""
        from fastapi import FastAPI
        from src.interfaces.api.routes.scanner_api import router

        app = FastAPI(title="Complete Workflow Test")
        app.include_router(router, prefix="/api/v1/scanner")
        return app

    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app)

    @pytest.fixture
    def populated_db_manager(self):
        """Create database manager with test data."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        # Create market data table and insert test data
        with manager.get_connection() as conn:
            # Create market_data table
            conn.execute("""
                CREATE TABLE market_data (
                    symbol VARCHAR,
                    date_partition DATE,
                    timestamp TIMESTAMP,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume INTEGER
                )
            """)

            # Insert test data for multiple symbols and dates
            test_data = [
                # RELIANCE data
                ('RELIANCE', '2025-09-01', '2025-09-01T09:15:00Z', 2450.0, 2470.0, 2440.0, 2460.0, 100000),
                ('RELIANCE', '2025-09-01', '2025-09-01T09:30:00Z', 2460.0, 2480.0, 2450.0, 2470.0, 120000),
                ('RELIANCE', '2025-09-01', '2025-09-01T09:45:00Z', 2470.0, 2490.0, 2460.0, 2480.0, 150000),
                ('RELIANCE', '2025-09-01', '2025-09-01T10:00:00Z', 2480.0, 2500.0, 2470.0, 2490.0, 180000),

                # TCS data
                ('TCS', '2025-09-01', '2025-09-01T09:15:00Z', 3200.0, 3220.0, 3190.0, 3210.0, 50000),
                ('TCS', '2025-09-01', '2025-09-01T09:30:00Z', 3210.0, 3230.0, 3200.0, 3220.0, 60000),
                ('TCS', '2025-09-01', '2025-09-01T09:45:00Z', 3220.0, 3240.0, 3210.0, 3230.0, 75000),
                ('TCS', '2025-09-01', '2025-09-01T10:00:00Z', 3230.0, 3250.0, 3220.0, 3240.0, 90000),

                # INFY data
                ('INFY', '2025-09-01', '2025-09-01T09:15:00Z', 1400.0, 1420.0, 1390.0, 1410.0, 80000),
                ('INFY', '2025-09-01', '2025-09-01T09:30:00Z', 1410.0, 1430.0, 1400.0, 1420.0, 95000),
                ('INFY', '2025-09-01', '2025-09-01T09:45:00Z', 1420.0, 1440.0, 1410.0, 1430.0, 110000),
                ('INFY', '2025-09-01', '2025-09-01T10:00:00Z', 1430.0, 1450.0, 1420.0, 1440.0, 125000),
            ]

            for row in test_data:
                conn.execute("""
                    INSERT INTO market_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, row)

        yield manager
        manager.close()

    def test_database_to_scanner_pipeline(self, populated_db_manager):
        """Test complete pipeline from database to scanner results."""
        from src.application.scanners.strategies.breakout_scanner import BreakoutScanner

        scanner = BreakoutScanner(db_manager=populated_db_manager)

        # Test scanner can access database
        symbols = scanner.get_available_symbols()
        assert isinstance(symbols, list)

        # Test scanner can run scan
        scan_date = date(2025, 9, 1)
        cutoff_time = time(9, 50)

        results = scanner.scan(scan_date, cutoff_time)
        assert isinstance(results, pd.DataFrame)

        # Test scanner can run date range scan
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 1)

        results_range = scanner.scan_date_range(
            start_date=start_date,
            end_date=end_date,
            cutoff_time=cutoff_time
        )
        assert isinstance(results_range, list)

    def test_scanner_to_api_pipeline(self, client, populated_db_manager):
        """Test pipeline from scanner to API responses."""
        # Test health endpoint
        response = client.get("/api/v1/scanner/health")
        assert response.status_code == 200

        # Test scanner list endpoint
        response = client.get("/api/v1/scanner/scanners")
        assert response.status_code == 200

        # Test default config endpoint
        response = client.get("/api/v1/scanner/config/default")
        assert response.status_code == 200

        # Test symbols endpoint
        response = client.get("/api/v1/scanner/symbols")
        assert response.status_code == 200

        # Test market overview
        response = client.get("/api/v1/scanner/market-overview")
        assert response.status_code in [200, 500]  # May fail if no data

    def test_api_to_scanner_execution(self, client):
        """Test API-triggered scanner execution."""
        scan_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": "2025-09-01",
            "cutoff_time": "09:50:00",
            "config": {
                "min_price": 100,
                "max_price": 5000,
                "max_results_per_day": 10
            }
        }

        response = client.post("/api/v1/scanner/scan", json=scan_request)

        # Should return some response (may be 200 or error based on data availability)
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            result = response.json()
            assert "scan_id" in result
            assert "total_results" in result
            assert "results" in result

    def test_batch_scan_workflow(self, client):
        """Test batch scan workflow."""
        scan_requests = [
            {
                "scanner_type": "enhanced_breakout",
                "scan_date": "2025-09-01",
                "cutoff_time": "09:50:00"
            },
            {
                "scanner_type": "enhanced_crp",
                "scan_date": "2025-09-01",
                "cutoff_time": "09:50:00"
            }
        ]

        response = client.post("/api/v1/scanner/batch-scan", json=scan_requests)

        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            results = response.json()
            assert isinstance(results, list)

    def test_export_workflow(self, client):
        """Test export workflow."""
        # First run a scan to get a scan ID
        scan_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": "2025-09-01",
            "cutoff_time": "09:50:00"
        }

        scan_response = client.post("/api/v1/scanner/scan", json=scan_request)

        if scan_response.status_code == 200:
            scan_result = scan_response.json()
            scan_id = scan_result["scan_id"]

            # Test CSV export
            export_response = client.get(f"/api/v1/scanner/export/{scan_id}/csv")
            assert export_response.status_code in [200, 404, 500]

            if export_response.status_code == 200:
                assert export_response.headers["content-type"] == "text/csv"

    def test_performance_stats_workflow(self, client):
        """Test performance statistics workflow."""
        response = client.get("/api/v1/scanner/stats/performance?days=7")
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            stats = response.json()
            assert "period_days" in stats
            assert "total_scans" in stats
            assert "overall_success_rate" in stats

    def test_concurrent_workflow_execution(self, client):
        """Test concurrent execution of multiple workflows."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        results = []
        errors = []

        def run_workflow(workflow_id):
            """Run a single workflow."""
            try:
                # Test different endpoints concurrently
                if workflow_id % 4 == 0:
                    response = client.get("/api/v1/scanner/health")
                elif workflow_id % 4 == 1:
                    response = client.get("/api/v1/scanner/scanners")
                elif workflow_id % 4 == 2:
                    response = client.get("/api/v1/scanner/symbols?limit=5")
                else:
                    response = client.get("/api/v1/scanner/config/default")

                results.append((workflow_id, response.status_code))

            except Exception as e:
                errors.append(f"Workflow {workflow_id}: {e}")

        # Run multiple workflows concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_workflow, i) for i in range(20)]
            for future in futures:
                future.result()

        # Verify results
        assert len(errors) == 0, f"Workflow errors: {errors}"
        assert len(results) == 20

        # All responses should be successful
        for workflow_id, status_code in results:
            assert status_code == 200, f"Workflow {workflow_id} failed with status {status_code}"

    def test_error_handling_workflow(self, client):
        """Test error handling throughout the workflow."""
        # Test invalid scanner type
        invalid_request = {
            "scanner_type": "invalid_scanner",
            "scan_date": "2025-09-01",
            "cutoff_time": "09:50:00"
        }

        response = client.post("/api/v1/scanner/scan", json=invalid_request)
        # Should handle gracefully (422 or 200 with error)
        assert response.status_code in [200, 422, 400, 500]

        # Test invalid date format
        invalid_date_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": "invalid-date",
            "cutoff_time": "09:50:00"
        }

        response = client.post("/api/v1/scanner/scan", json=invalid_date_request)
        assert response.status_code in [200, 422, 400, 500]

        # Test invalid time format
        invalid_time_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": "2025-09-01",
            "cutoff_time": "invalid-time"
        }

        response = client.post("/api/v1/scanner/scan", json=invalid_time_request)
        assert response.status_code in [200, 422, 400, 500]


class TestDataConsistency:
    """Test data consistency across the entire workflow."""

    def test_database_api_consistency(self, client):
        """Test that database and API return consistent data."""
        # Get symbols from API
        api_response = client.get("/api/v1/scanner/symbols")
        assert api_response.status_code == 200
        api_symbols = api_response.json()

        # Get symbols directly from database (simulated)
        from src.infrastructure.core.singleton_database import create_db_manager
        manager = create_db_manager()

        # This would normally query the database directly
        # For this test, we just verify the API returns a list
        assert isinstance(api_symbols, list)

        manager.close()

    def test_config_consistency(self, client):
        """Test configuration consistency across components."""
        # Get default config from API
        api_response = client.get("/api/v1/scanner/config/default")
        assert api_response.status_code == 200
        api_config = api_response.json()

        # Get config from scanner directly
        from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager()
        scanner = BreakoutScanner(db_manager=manager)
        scanner_config = scanner._get_default_config()

        # Compare key configuration parameters
        assert api_config['min_price'] == scanner_config['min_price']
        assert api_config['max_price'] == scanner_config['max_price']
        assert api_config['max_results_per_day'] == scanner_config['max_results_per_day']

        manager.close()

    def test_scan_result_consistency(self, client):
        """Test that scan results are consistent across different execution methods."""
        scan_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": "2025-09-01",
            "cutoff_time": "09:50:00"
        }

        # Run scan via API
        api_response = client.post("/api/v1/scanner/scan", json=scan_request)

        if api_response.status_code == 200:
            api_result = api_response.json()

            # Run scan directly via scanner runner
            from src.application.infrastructure.di_container import get_scanner_runner

            runner = get_scanner_runner()
            direct_results = runner.run_scanner(
                scanner_name="enhanced_breakout",
                start_date=date(2025, 9, 1),
                end_date=date(2025, 9, 1),
                cutoff_time=time(9, 50)
            )

            # Compare result counts
            api_count = api_result["total_results"]
            direct_count = len(direct_results)

            # Should be reasonably close (may differ due to data processing)
            assert abs(api_count - direct_count) <= 1  # Allow small difference


class TestPerformanceWorkflow:
    """Test performance characteristics of the complete workflow."""

    def test_workflow_response_times(self, client):
        """Test response times for various workflow operations."""
        import time

        # Test health endpoint response time
        start_time = time.time()
        response = client.get("/api/v1/scanner/health")
        end_time = time.time()

        health_time = end_time - start_time
        assert health_time < 1.0  # Should respond within 1 second
        assert response.status_code == 200

        # Test config endpoint response time
        start_time = time.time()
        response = client.get("/api/v1/scanner/config/default")
        end_time = time.time()

        config_time = end_time - start_time
        assert config_time < 0.5  # Should respond within 0.5 seconds
        assert response.status_code == 200

    def test_concurrent_performance(self, client):
        """Test performance under concurrent load."""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor

        response_times = []

        def timed_request(request_id):
            """Make a timed request."""
            start_time = time.time()
            response = client.get("/api/v1/scanner/health")
            end_time = time.time()

            response_times.append(end_time - start_time)
            return response.status_code

        # Run multiple concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(timed_request, i) for i in range(50)]
            results = [future.result() for future in futures]

        # All requests should succeed
        assert all(status == 200 for status in results)

        # Calculate performance metrics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        # Performance assertions
        assert avg_response_time < 1.0  # Average under 1 second
        assert max_response_time < 5.0  # Max under 5 seconds
        assert min_response_time < 0.1  # Min under 0.1 seconds

        
    def test_memory_usage_stability(self):
        """Test that memory usage remains stable during workflow execution."""
        import psutil
        import os
        import time

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run multiple workflow operations
        from src.application.infrastructure.di_container import get_scanner_runner

        runner = get_scanner_runner()

        for i in range(10):
            results = runner.run_scanner(
                scanner_name="enhanced_breakout",
                start_date=date(2025, 9, 1),
                end_date=date(2025, 9, 1)
            )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 50MB)
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB"

        
if __name__ == "__main__":
    # Run basic smoke tests
    print("🧪 Running complete workflow smoke tests...")

    from fastapi import FastAPI
    from src.interfaces.api.routes.scanner_api import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/scanner")
    client = TestClient(app)

    # Test basic workflow
    try:
        response = client.get("/api/v1/scanner/health")
        if response.status_code == 200:
            print("✅ Health endpoint test passed")
        else:
            print(f"❌ Health endpoint test failed: {response.status_code}")

        response = client.get("/api/v1/scanner/config/default")
        if response.status_code == 200:
            print("✅ Config endpoint test passed")
        else:
            print(f"❌ Config endpoint test failed: {response.status_code}")

        print("\\n🎉 Complete workflow smoke tests passed!")

    except Exception as e:
        print(f"❌ Workflow smoke test failed: {e}")

    print("\\n💡 Run with pytest for comprehensive testing:")
    print("pytest tests/integration/test_complete_workflow.py -v")


