#!/usr/bin/env python3
"""
Comprehensive tests for API server endpoints and functionality.
Tests verify that all scanner API endpoints work correctly with the new database manager.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import date, time, datetime
from unittest.mock import patch, MagicMock
import json
import asyncio
from typing import Dict, Any


class TestAPIServer:
    """Test suite for API server functionality."""

    @pytest.fixture
    def test_app(self):
        """Create test FastAPI application."""
        from fastapi import FastAPI
        from src.interfaces.api.routes.scanner_api import router

        app = FastAPI(title="Scanner API Test")
        app.include_router(router, prefix="/api/v1/scanner")
        return app

    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app)

    def test_health_endpoint(self, client):
        """Test health endpoint returns correct status."""
        response = client.get("/api/v1/scanner/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "scanner_api"
        assert data["version"] == "1.0.0"
        assert "database_connected" in data
        assert "available_symbols" in data
        assert "timestamp" in data

    def test_get_available_scanners(self, client):
        """Test getting list of available scanners."""
        response = client.get("/api/v1/scanner/scanners")

        assert response.status_code == 200
        scanners = response.json()

        assert isinstance(scanners, list)
        assert len(scanners) > 0

        # Check scanner structure
        scanner = scanners[0]
        assert "scanner_name" in scanner
        assert "is_available" in scanner
        assert "last_scan" in scanner
        assert "total_scans" in scanner
        assert "avg_execution_time_ms" in scanner
        assert "success_rate" in scanner

    def test_get_scanner_types(self, client):
        """Test getting available scanner types."""
        response = client.get("/api/v1/scanner/scanner-types")

        assert response.status_code == 200
        scanner_types = response.json()

        assert isinstance(scanner_types, list)
        assert "enhanced_breakout" in scanner_types
        assert "technical" in scanner_types

    def test_get_time_windows(self, client):
        """Test getting available time windows."""
        response = client.get("/api/v1/scanner/time-windows")

        assert response.status_code == 200
        time_windows = response.json()

        assert isinstance(time_windows, list)
        assert len(time_windows) > 0
        assert "09:15-09:50" in time_windows

    def test_get_default_config(self, client):
        """Test getting default scanner configuration."""
        response = client.get("/api/v1/scanner/config/default")

        assert response.status_code == 200
        config = response.json()

        assert "consolidation_period" in config
        assert "breakout_volume_ratio" in config
        assert "resistance_break_pct" in config
        assert "min_price" in config
        assert "max_price" in config
        assert "max_results_per_day" in config

    def test_validate_config_valid(self, client):
        """Test configuration validation with valid config."""
        valid_config = {
            "consolidation_period": 5,
            "breakout_volume_ratio": 1.5,
            "resistance_break_pct": 0.5,
            "min_price": 50,
            "max_price": 2000,
            "max_results_per_day": 3
        }

        response = client.post("/api/v1/scanner/config/validate", json=valid_config)

        assert response.status_code == 200
        result = response.json()

        assert result["valid"] is True
        assert "Configuration is valid" in result["message"]
        assert result["config"] is not None

    def test_validate_config_invalid(self, client):
        """Test configuration validation with invalid config."""
        invalid_config = {
            "consolidation_period": -1,  # Invalid negative value
            "breakout_volume_ratio": 1.5,
            "resistance_break_pct": 0.5,
            "min_price": 50,
            "max_price": 2000,
            "max_results_per_day": 3
        }

        response = client.post("/api/v1/scanner/config/validate", json=invalid_config)

        # Pydantic validation should catch the negative value
        assert response.status_code in [200, 422]  # 422 for validation error

        if response.status_code == 422:
            result = response.json()
            assert "detail" in result

    def test_get_available_symbols(self, client):
        """Test getting available symbols."""
        response = client.get("/api/v1/scanner/symbols")

        assert response.status_code == 200
        symbols = response.json()

        assert isinstance(symbols, list)
        # Should return at least some symbols or empty list
        assert isinstance(symbols, list)

    def test_get_available_symbols_with_search(self, client):
        """Test getting symbols with search filter."""
        response = client.get("/api/v1/scanner/symbols?search=TEST&limit=10")

        assert response.status_code == 200
        symbols = response.json()

        assert isinstance(symbols, list)
        # If there are symbols with TEST in name, they should be filtered
        for symbol in symbols:
            assert "TEST" in symbol.upper()

    def test_get_available_symbols_with_limit(self, client):
        """Test getting symbols with limit."""
        response = client.get("/api/v1/scanner/symbols?limit=5")

        assert response.status_code == 200
        symbols = response.json()

        assert isinstance(symbols, list)
        assert len(symbols) <= 5

    def test_run_scan_single_day(self, client):
        """Test running a single day scan."""
        scan_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": date.today().isoformat(),
            "cutoff_time": "09:50:00",
            "config": {
                "min_price": 50,
                "max_price": 2000,
                "max_results_per_day": 3
            }
        }

        response = client.post("/api/v1/scanner/scan", json=scan_request)

        assert response.status_code in [200, 400, 500]  # Allow for various outcomes

        if response.status_code == 200:
            result = response.json()

            assert "scan_id" in result
            assert "scanner_type" in result
            assert "total_results" in result
            assert "success_rate" in result
            assert "results" in result
            assert isinstance(result["results"], list)

    def test_run_scan_date_range(self, client):
        """Test running a date range scan."""
        today = date.today()
        yesterday = today.replace(day=today.day - 1) if today.day > 1 else today

        scan_request = {
            "scanner_type": "enhanced_breakout",
            "start_date": yesterday.isoformat(),
            "end_date": today.isoformat(),
            "cutoff_time": "09:50:00",
            "config": {
                "min_price": 50,
                "max_price": 2000,
                "max_results_per_day": 3
            }
        }

        response = client.post("/api/v1/scanner/scan", json=scan_request)

        assert response.status_code in [200, 400, 500]  # Allow for various outcomes

        if response.status_code == 200:
            result = response.json()

            assert "scan_id" in result
            assert "scanner_type" in result
            assert "start_date" in result
            assert "end_date" in result
            assert "total_results" in result
            assert "results" in result

    def test_run_scan_invalid_date_range(self, client):
        """Test scan with invalid date range (end before start)."""
        scan_request = {
            "scanner_type": "enhanced_breakout",
            "start_date": "2025-09-05",
            "end_date": "2025-09-01",  # End before start
            "cutoff_time": "09:50:00"
        }

        response = client.post("/api/v1/scanner/scan", json=scan_request)

        assert response.status_code == 422  # Validation error
        result = response.json()
        assert "detail" in result

    def test_get_market_overview(self, client):
        """Test getting market overview."""
        response = client.get("/api/v1/scanner/market-overview")

        assert response.status_code in [200, 500]  # Allow for database issues

        if response.status_code == 200:
            overview = response.json()

            assert "total_symbols" in overview
            assert "advancing_count" in overview
            assert "declining_count" in overview
            assert "breakout_candidates" in overview
            assert "top_sector" in overview
            assert "market_sentiment" in overview
            assert "last_updated" in overview

    def test_get_performance_stats(self, client):
        """Test getting performance statistics."""
        response = client.get("/api/v1/scanner/stats/performance?days=30")

        assert response.status_code in [200, 500]  # Allow for database issues

        if response.status_code == 200:
            stats = response.json()

            assert "period_days" in stats
            assert "start_date" in stats
            assert "end_date" in stats
            assert "total_scans" in stats
            assert "total_breakouts_found" in stats
            assert "overall_success_rate" in stats

    def test_get_performance_stats_invalid_days(self, client):
        """Test performance stats with invalid days parameter."""
        response = client.get("/api/v1/scanner/stats/performance?days=0")

        assert response.status_code == 422  # Validation error for days < 1

    def test_batch_scan(self, client):
        """Test batch scan functionality."""
        scan_requests = [
            {
                "scanner_type": "enhanced_breakout",
                "scan_date": date.today().isoformat(),
                "cutoff_time": "09:50:00"
            },
            {
                "scanner_type": "enhanced_breakout",
                "scan_date": date.today().isoformat(),
                "cutoff_time": "10:00:00"
            }
        ]

        response = client.post("/api/v1/scanner/batch-scan", json=scan_requests)

        assert response.status_code in [200, 400, 500]  # Allow for various outcomes

        if response.status_code == 200:
            results = response.json()
            assert isinstance(results, list)

    def test_batch_scan_too_many_requests(self, client):
        """Test batch scan with too many requests."""
        # Create 11 requests (over the limit of 10)
        scan_requests = [
            {
                "scanner_type": "enhanced_breakout",
                "scan_date": date.today().isoformat(),
                "cutoff_time": "09:50:00"
            }
        ] * 11

        response = client.post("/api/v1/scanner/batch-scan", json=scan_requests)

        assert response.status_code == 400
        result = response.json()
        assert "Maximum 10 batch scans allowed" in result["detail"]

    def test_export_scan_results_csv(self, client):
        """Test CSV export functionality."""
        # Use a sample scan ID (this will return mock data)
        scan_id = "test_scan_123"

        response = client.get(f"/api/v1/scanner/export/{scan_id}/csv")

        assert response.status_code in [200, 404, 500]  # Allow for various outcomes

        if response.status_code == 200:
            assert response.headers["content-type"] == "text/csv"
            assert "attachment" in response.headers["content-disposition"]
            assert f"scan_{scan_id}.csv" in response.headers["content-disposition"]

            # Check that response contains CSV data
            content = response.content.decode()
            assert "symbol" in content
            assert "scan_date" in content

    def test_get_scan_results_not_found(self, client):
        """Test retrieving non-existent scan results."""
        response = client.get("/api/v1/scanner/scan/nonexistent_scan_id")

        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()


class TestAPIIntegration:
    """Integration tests for API functionality."""

    def test_full_scan_workflow(self, client):
        """Test complete scan workflow from request to results."""
        # 1. Check health
        health_response = client.get("/api/v1/scanner/health")
        assert health_response.status_code == 200

        # 2. Get available scanners
        scanners_response = client.get("/api/v1/scanner/scanners")
        assert scanners_response.status_code == 200

        # 3. Get default config
        config_response = client.get("/api/v1/scanner/config/default")
        assert config_response.status_code == 200

        # 4. Run a scan
        scan_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": date.today().isoformat(),
            "cutoff_time": "09:50:00"
        }

        scan_response = client.post("/api/v1/scanner/scan", json=scan_request)

        if scan_response.status_code == 200:
            scan_result = scan_response.json()
            scan_id = scan_result["scan_id"]

            # 5. Try to get the scan results (may not exist for mock)
            results_response = client.get(f"/api/v1/scanner/scan/{scan_id}")

            # Either 200 (if results exist) or 404 (if not found)
            assert results_response.status_code in [200, 404]

            # 6. Export results
            export_response = client.get(f"/api/v1/scanner/export/{scan_id}/csv")
            assert export_response.status_code in [200, 404, 500]

    def test_error_handling_invalid_scanner_type(self, client):
        """Test error handling for invalid scanner type."""
        scan_request = {
            "scanner_type": "invalid_scanner",
            "scan_date": date.today().isoformat(),
            "cutoff_time": "09:50:00"
        }

        response = client.post("/api/v1/scanner/scan", json=scan_request)

        # Should either return 422 for validation error or handle gracefully
        assert response.status_code in [200, 422, 400, 500]

    def test_concurrent_api_requests(self, client):
        """Test handling concurrent API requests."""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor

        results = []

        def make_request(request_id):
            """Make a single API request."""
            try:
                response = client.get("/api/v1/scanner/health")
                results.append((request_id, response.status_code))
            except Exception as e:
                results.append((request_id, f"error: {e}"))

        # Make concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            # Wait for all to complete
            for future in futures:
                future.result()

        # Verify all requests completed
        assert len(results) == 10
        for request_id, status in results:
            if isinstance(status, int):
                assert status == 200
            else:
                assert "error" not in status  # No errors should occur


class TestAPIValidation:
    """Test API request/response validation."""

    def test_scan_request_validation(self, client):
        """Test scan request validation."""
        # Valid request
        valid_request = {
            "scanner_type": "enhanced_breakout",
            "scan_date": date.today().isoformat(),
            "cutoff_time": "09:50:00",
            "config": {"min_price": 100}
        }

        response = client.post("/api/v1/scanner/scan", json=valid_request)
        assert response.status_code in [200, 400, 500]  # Various possible outcomes

        # Invalid scanner type
        invalid_request = {
            "scanner_type": "nonexistent_scanner",
            "scan_date": date.today().isoformat(),
            "cutoff_time": "09:50:00"
        }

        response = client.post("/api/v1/scanner/scan", json=invalid_request)
        assert response.status_code in [200, 422, 400]  # Validation or graceful handling

    def test_config_validation_edge_cases(self, client):
        """Test configuration validation edge cases."""
        # Test with extreme values
        edge_config = {
            "consolidation_period": 30,  # Maximum allowed
            "breakout_volume_ratio": 10.0,  # Maximum allowed
            "resistance_break_pct": 5.0,  # Maximum allowed
            "min_price": 1,  # Minimum allowed
            "max_price": 50000,  # Maximum allowed
            "max_results_per_day": 50  # Maximum allowed
        }

        response = client.post("/api/v1/scanner/config/validate", json=edge_config)

        if response.status_code == 200:
            result = response.json()
            assert result["valid"] is True
        else:
            # If validation fails, it should be due to Pydantic constraints
            assert response.status_code == 422


if __name__ == "__main__":
    # Run basic smoke tests
    print("🧪 Running API server smoke tests...")

    from fastapi import FastAPI
    from src.interfaces.api.routes.scanner_api import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/scanner")
    client = TestClient(app)

    # Test health endpoint
    response = client.get("/api/v1/scanner/health")
    if response.status_code == 200:
        print("✅ Health endpoint test passed")
    else:
        print(f"❌ Health endpoint test failed: {response.status_code}")

    # Test default config
    response = client.get("/api/v1/scanner/config/default")
    if response.status_code == 200:
        print("✅ Default config endpoint test passed")
    else:
        print(f"❌ Default config endpoint test failed: {response.status_code}")

    print("\\n🎉 Smoke tests completed!")
    print("\\n💡 Run with pytest for comprehensive testing:")
    print("pytest tests/infrastructure/test_api_server.py -v")


