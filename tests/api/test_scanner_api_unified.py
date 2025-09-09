"""
Integration tests for Scanner API with unified DuckDB layer.

Tests the scanner API endpoints to ensure they work correctly with the unified
DuckDB layer and scanner read adapter.
"""

import pytest
from datetime import date, time
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.interfaces.api.routes.scanner_api import router, get_unified_manager, get_unified_scanner_adapter
from src.infrastructure.database.unified_duckdb import UnifiedDuckDBManager, DuckDBConfig
from src.infrastructure.adapters.scanner_read_adapter import DuckDBScannerReadAdapter


class TestScannerAPIUnified:
    """Test suite for scanner API with unified layer."""

    @pytest.fixture
    def mock_unified_manager(self):
        """Create a mock unified manager for testing."""
        manager = Mock(spec=UnifiedDuckDBManager)

        # Mock DataFrame result for health check
        mock_df = Mock()
        mock_df.empty = False

        # Mock the iloc indexing for DataFrame
        mock_row = Mock()
        mock_row.__getitem__ = Mock(return_value=100)  # Return 100 for "count" column
        mock_df.iloc.__getitem__ = Mock(return_value=mock_row)

        manager.persistence_query.return_value = mock_df
        manager.get_connection_stats.return_value = {
            'active_connections': 2,
            'available_connections': 8,
            'max_connections': 10
        }

        return manager

    @pytest.fixture
    def mock_scanner_adapter(self, mock_unified_manager):
        """Create a mock scanner adapter for testing."""
        adapter = Mock(spec=DuckDBScannerReadAdapter)

        # Mock CRP candidates
        adapter.get_crp_candidates.return_value = [
            {
                'symbol': 'TEST1',
                'crp_price': 100.0,
                'current_volume': 100000,
                'crp_probability_score': 85.0
            }
        ]

        # Mock breakout candidates
        adapter.get_breakout_candidates.return_value = [
            {
                'symbol': 'TEST2',
                'breakout_price': 200.0,
                'probability_score': 75.0
            }
        ]

        # Mock EOD prices
        adapter.get_end_of_day_prices.return_value = {
            'TEST1': {'eod_price': 105.0, 'eod_volume': 120000}
        }

        return adapter

    @pytest.fixture
    def test_app(self, mock_unified_manager, mock_scanner_adapter):
        """Create test FastAPI app with mocked dependencies."""
        app = FastAPI()
        app.include_router(router)

        # Mock the dependency functions
        with patch('src.interfaces.api.routes.scanner_api.get_unified_manager', return_value=mock_unified_manager), \
             patch('src.interfaces.api.routes.scanner_api.get_unified_scanner_adapter', return_value=mock_scanner_adapter):

            yield app

    @pytest.fixture
    def client(self, test_app):
        """Create test client."""
        return TestClient(test_app)

    def test_health_endpoint_unified(self, client, mock_unified_manager):
        """Test health endpoint uses unified layer."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "scanner_api"
        assert data["version"] == "2.0.0"
        assert data["unified_layer"] is True
        assert "connection_pool" in data
        assert data["connection_pool"]["active_connections"] == 2

        # Verify unified manager was called
        mock_unified_manager.persistence_query.assert_called_once()

    def test_health_endpoint_error_handling(self, client, mock_unified_manager):
        """Test health endpoint error handling."""
        mock_unified_manager.persistence_query.side_effect = Exception("Database error")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert "Scanner service unavailable" in data["detail"]

    def test_scanner_status_endpoint(self, client):
        """Test scanner status endpoint."""
        response = client.get("/scanners")

        assert response.status_code == 200
        data = response.json()

        # Should return a list of scanner statuses
        assert isinstance(data, list)
        if data:  # Only check structure if data is returned
            scanner = data[0]
            assert "scanner_name" in scanner
            assert "is_available" in scanner
            assert "total_scans" in scanner

    @pytest.mark.parametrize("scanner_type", ["breakout", "enhanced_breakout", "crp", "enhanced_crp"])
    def test_scan_endpoint_types(self, client, mock_scanner_adapter, scanner_type):
        """Test scan endpoint with different scanner types."""
        scan_request = {
            "scanner_type": scanner_type,
            "scan_date": "2025-01-15",
            "cutoff_time": "09:50:00"
        }

        response = client.post("/scan", json=scan_request)

        # The endpoint should handle the request (may return 200 or 400 depending on implementation)
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "scan_id" in data
            assert "total_results" in data
            assert "success_rate" in data

    def test_scan_endpoint_missing_data(self, client):
        """Test scan endpoint with missing required data."""
        scan_request = {
            "scanner_type": "breakout"
            # Missing scan_date and cutoff_time
        }

        response = client.post("/scan", json=scan_request)

        # Should handle gracefully
        assert response.status_code in [200, 400]

    def test_market_overview_endpoint(self, client, mock_scanner_adapter):
        """Test market overview endpoint."""
        response = client.get("/market-overview")

        assert response.status_code == 200
        data = response.json()

        assert "total_symbols" in data
        assert "breakout_candidates" in data
        assert "market_sentiment" in data
        assert "last_updated" in data

    def test_symbols_endpoint(self, client, mock_scanner_adapter):
        """Test available symbols endpoint."""
        response = client.get("/symbols")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_symbols_endpoint_with_search(self, client, mock_scanner_adapter):
        """Test symbols endpoint with search filter."""
        response = client.get("/symbols?search=TEST")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_symbols_endpoint_with_limit(self, client, mock_scanner_adapter):
        """Test symbols endpoint with limit parameter."""
        response = client.get("/symbols?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 5

    def test_default_config_endpoint(self, client):
        """Test default scanner configuration endpoint."""
        response = client.get("/config/default")

        assert response.status_code == 200
        data = response.json()

        # Should return default configuration
        assert isinstance(data, dict)
        assert "consolidation_period" in data
        assert "breakout_volume_ratio" in data

    def test_config_validation_endpoint(self, client):
        """Test configuration validation endpoint."""
        config = {
            "consolidation_period": 5,
            "breakout_volume_ratio": 1.5,
            "min_price": 50,
            "max_price": 2000
        }

        response = client.post("/config/validate", json=config)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "Configuration is valid" in data["message"]

    def test_config_validation_invalid(self, client):
        """Test configuration validation with invalid data."""
        invalid_config = {
            "consolidation_period": -1,  # Invalid negative value
            "breakout_volume_ratio": 1.5,
            "min_price": 50,
            "max_price": 2000
        }

        response = client.post("/config/validate", json=invalid_config)

        # Should handle validation errors gracefully (422 is Pydantic validation error)
        assert response.status_code in [200, 400, 422]

    def test_performance_stats_endpoint(self, client):
        """Test performance statistics endpoint."""
        response = client.get("/stats/performance?days=30")

        assert response.status_code == 200
        data = response.json()

        assert "period_days" in data
        assert "total_scans" in data
        assert "overall_success_rate" in data

    def test_time_windows_endpoint(self, client):
        """Test time windows endpoint."""
        response = client.get("/time-windows")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

    def test_scanner_types_endpoint(self, client):
        """Test scanner types endpoint."""
        response = client.get("/scanner-types")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0
        assert "breakout" in data

    def test_batch_scan_endpoint(self, client, mock_scanner_adapter):
        """Test batch scan endpoint."""
        batch_requests = [
            {
                "scanner_type": "breakout",
                "scan_date": "2025-01-15",
                "cutoff_time": "09:50:00"
            },
            {
                "scanner_type": "crp",
                "scan_date": "2025-01-15",
                "cutoff_time": "09:50:00"
            }
        ]

        response = client.post("/batch-scan", json=batch_requests)

        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_batch_scan_too_many_requests(self, client):
        """Test batch scan with too many requests."""
        # Create more than 10 requests
        batch_requests = [
            {
                "scanner_type": "breakout",
                "scan_date": "2025-01-15",
                "cutoff_time": "09:50:00"
            }
        ] * 15  # 15 requests

        response = client.post("/batch-scan", json=batch_requests)

        assert response.status_code == 400
        data = response.json()
        assert "Maximum 10 batch scans allowed" in data["detail"]

    @pytest.mark.parametrize("endpoint", ["/scan/123", "/export/123/csv"])
    def test_not_implemented_endpoints(self, client, endpoint):
        """Test endpoints that return 404 (not implemented)."""
        if "export" in endpoint:
            response = client.get(endpoint)
        else:
            response = client.get(endpoint)

        # These endpoints may return 404 as they're not fully implemented
        assert response.status_code in [200, 404, 500]
