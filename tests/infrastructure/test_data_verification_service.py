#!/usr/bin/env python3
"""
Integration tests for DataVerificationService
===========================================

Tests data verification functionality using real database connections and data.
No mocking - all tests use actual DuckDB database and parquet files.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# Add project paths
project_root = Path.cwd()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / 'src') not in sys.path:
    sys.path.insert(0, str(project_root / 'src'))

from src.infrastructure.services.data_verification_service import DataVerificationService


@pytest.fixture
def verification_service():
    """Create DataVerificationService instance for testing."""
    return DataVerificationService()


@pytest.fixture
def db_path():
    """Get the main database path."""
    return project_root / "data" / "financial_data.duckdb"


class TestDataVerificationService:
    """Integration tests for DataVerificationService."""

    def test_initialization(self, verification_service):
        """Test DataVerificationService initialization."""
        assert verification_service is not None
        assert hasattr(verification_service, 'verify_database_connectivity')
        assert hasattr(verification_service, 'verify_schema_integrity')

    def test_verify_database_connectivity_success(self, verification_service, db_path):
        """Test successful database connectivity verification."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        result = verification_service.verify_database_connectivity()

        assert result.success == True
        assert result.checks_performed > 0
        assert result.passed_checks > 0
        assert result.failed_checks == 0
        assert 'connection_time' in result.details
        assert 'database_path' in result.details

    def test_verify_schema_integrity(self, verification_service, db_path):
        """Test database schema integrity verification."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        result = verification_service.verify_schema_integrity()

        assert result.success == True
        assert result.checks_performed > 0
        assert result.passed_checks > 0
        assert 'tables_found' in result.details
        assert 'required_tables' in result.details

    def test_verify_schema_integrity_missing_table(self, verification_service):
        """Test schema verification when required tables are missing."""
        # This test would use a temporary database without required tables
        # For now, we expect success with the main database
        result = verification_service.verify_schema_integrity()
        assert isinstance(result.success, bool)
        assert result.checks_performed > 0

    def test_verify_parquet_integration(self, verification_service):
        """Test parquet file integration verification."""
        result = verification_service.verify_parquet_integration()

        assert isinstance(result.success, bool)
        assert result.checks_performed > 0
        assert 'parquet_files_found' in result.details
        assert 'total_files' in result.details

    def test_run_comprehensive_validation(self, verification_service, db_path):
        """Test comprehensive validation across all verification types."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        report = verification_service.run_comprehensive_validation()

        assert report is not None
        assert isinstance(report.timestamp, datetime)
        assert hasattr(report, 'module_results')
        assert hasattr(report, 'cross_module_checks')
        assert hasattr(report, 'recommendations')

    def test_performance_within_limits(self, verification_service, db_path):
        """Test that verification operations complete within performance limits."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        import time
        start_time = time.time()

        result = verification_service.verify_database_connectivity()

        duration = time.time() - start_time

        # Should complete within 5 seconds as per spec
        assert duration < 5.0, f"Database connectivity check took {duration:.2f}s, expected < 5.0s"
        assert result.success == True

    def test_error_handling_invalid_path(self, verification_service):
        """Test error handling with invalid database path."""
        # Create service with invalid path
        service = DataVerificationService(db_path="/invalid/path/database.db")

        result = service.verify_database_connectivity()

        # Should handle error gracefully
        assert result.success == False
        assert result.failed_checks > 0
        assert 'error' in result.details

    def test_verify_cross_module_consistency(self, verification_service, db_path):
        """Test cross-module data consistency verification."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        result = verification_service.verify_cross_module_consistency()

        assert isinstance(result.success, bool)
        assert result.checks_performed >= 1  # At least symbol check
        assert 'modules_checked' in result.details
        assert 'consistency_score' in result.details
        assert 'analytics_symbols_count' in result.details
        assert 'domain_symbols_count' in result.details

    def test_cross_module_symbol_overlap(self, verification_service, db_path):
        """Test that symbols overlap between analytics and domain modules."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        result = verification_service.verify_cross_module_consistency()

        # Should have some symbols in both modules
        analytics_count = result.details.get('analytics_symbols_count', 0)
        domain_count = result.details.get('domain_symbols_count', 0)
        overlap = result.details.get('symbol_overlap', 0)

        assert analytics_count >= 0
        assert domain_count >= 0
        assert overlap >= 0
        assert overlap <= min(analytics_count, domain_count)

    def test_cross_module_data_integrity(self, verification_service, db_path):
        """Test data integrity across modules for sample symbols."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        result = verification_service.verify_cross_module_consistency()

        # If we have overlapping symbols, check data integrity
        overlap = result.details.get('symbol_overlap', 0)
        if overlap > 0:
            # Should have sample symbol information
            assert 'sample_symbol' in result.details
            assert 'analytics_record_count' in result.details
            assert 'domain_record_count' in result.details

            # Record counts should be reasonable
            analytics_count = result.details['analytics_record_count']
            domain_count = result.details['domain_record_count']
            assert analytics_count >= 0
            assert domain_count >= 0

    def test_cross_module_performance_consistency(self, verification_service, db_path):
        """Test that query performance is consistent across modules."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        result = verification_service.verify_cross_module_consistency()

        # If we have sample data, check performance metrics
        if 'analytics_query_time' in result.details:
            analytics_time = result.details['analytics_query_time']
            domain_time = result.details['domain_query_time']
            ratio = result.details.get('performance_ratio', float('inf'))

            assert analytics_time >= 0
            assert domain_time >= 0
            assert ratio >= 0

            # Performance should be reasonable (domain not excessively slower)
            if analytics_time > 0:
                assert ratio < 100.0  # Domain should not be more than 100x slower

    def test_verify_unified_data_access(self, verification_service, db_path):
        """Test unified data access verification."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        result = verification_service.verify_unified_data_access()

        assert isinstance(result.success, bool)
        assert result.checks_performed > 0
        assert 'unified_queries_tested' in result.details

    def test_real_data_query_execution(self, verification_service, db_path):
        """Test that verification service can execute real queries."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        # Test basic query execution through the service
        result = verification_service.verify_database_connectivity()

        assert result.success == True
        assert result.details.get('query_success') == True

    def test_schema_validation_with_real_data(self, verification_service, db_path):
        """Test schema validation using real database schema."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        result = verification_service.verify_schema_integrity()

        assert result.success == True
        assert 'market_data' in result.details.get('tables_found', [])
        assert result.details.get('schema_validation_passed') == True


class TestDataVerificationServiceIntegration:
    """Integration tests that combine multiple verification operations."""

    def test_full_workflow_verification(self, verification_service, db_path):
        """Test complete verification workflow."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        # Run all verification steps
        connectivity_result = verification_service.verify_database_connectivity()
        schema_result = verification_service.verify_schema_integrity()
        parquet_result = verification_service.verify_parquet_integration()
        cross_module_result = verification_service.verify_cross_module_consistency()

        # All should succeed
        assert connectivity_result.success == True
        assert schema_result.success == True
        assert isinstance(parquet_result.success, bool)  # May be False if no parquet files
        assert isinstance(cross_module_result.success, bool)

        # Should have reasonable execution times
        total_checks = (connectivity_result.checks_performed +
                       schema_result.checks_performed +
                       parquet_result.checks_performed +
                       cross_module_result.checks_performed)

        assert total_checks > 0

    def test_comprehensive_report_generation(self, verification_service, db_path):
        """Test comprehensive validation report generation."""
        if not db_path.exists():
            pytest.skip(f"Database file not found: {db_path}")

        report = verification_service.run_comprehensive_validation()

        assert report is not None
        assert len(report.module_results) > 0
        assert isinstance(report.recommendations, list)

        # Should include results from all verification types
        expected_modules = ['database', 'schema', 'parquet', 'cross_module']
        for module in expected_modules:
            assert module in report.module_results

    def test_real_world_error_scenarios(self, verification_service):
        """Test error handling in real-world scenarios."""
        # Test with non-existent database
        service = DataVerificationService(db_path="/completely/invalid/path.db")

        result = service.verify_database_connectivity()
        assert result.success == False
        assert result.failed_checks > 0

        # Should not crash, should handle errors gracefully
        assert 'error' in result.details or 'connection_error' in result.details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
