"""
Test Results Processing and Analysis
====================================

This module handles test result processing, analysis, and reporting
for the monitoring dashboard.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from ..config.database import monitoring_db
from ..config.settings import config
from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class TestSuiteSummary:
    """Summary of test suite execution."""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    success_rate: float
    avg_duration: float
    total_duration: float
    executed_at: datetime


@dataclass
class TestTrend:
    """Test execution trend data."""
    date: datetime
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    avg_duration: float


class TestResultsProcessor:
    """Process and analyze test results."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def get_test_summary(self, days: int = 7) -> Dict[str, TestSuiteSummary]:
        """Get test execution summary for the specified period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with monitoring_db.get_connection() as conn:
                # Get results by suite
                results = conn.execute("""
                    SELECT
                        suite_name,
                        COUNT(*) as total_tests,
                        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
                        AVG(duration) as avg_duration,
                        SUM(duration) as total_duration,
                        MAX(executed_at) as last_executed
                    FROM test_results
                    WHERE executed_at >= ?
                    GROUP BY suite_name
                    ORDER BY last_executed DESC
                """, [cutoff_date]).fetchall()

            summaries = {}
            for row in results:
                suite_name = row[0]
                total_tests = row[1] or 0
                passed_tests = row[2] or 0
                failed_tests = row[3] or 0
                skipped_tests = row[4] or 0
                error_tests = row[5] or 0
                avg_duration = row[6] or 0.0
                total_duration = row[7] or 0.0
                executed_at = row[8] or datetime.now()

                success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

                summaries[suite_name] = TestSuiteSummary(
                    suite_name=suite_name,
                    total_tests=total_tests,
                    passed_tests=passed_tests,
                    failed_tests=failed_tests,
                    skipped_tests=skipped_tests,
                    error_tests=error_tests,
                    success_rate=success_rate,
                    avg_duration=avg_duration,
                    total_duration=total_duration,
                    executed_at=executed_at
                )

            return summaries

        except Exception as e:
            self.logger.error("Failed to get test summary", extra={'error': str(e)})
            return {}

    def get_test_trends(self, days: int = 30) -> List[TestTrend]:
        """Get test execution trends over time."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with monitoring_db.get_connection() as conn:
                # Get daily aggregations
                results = conn.execute("""
                    SELECT
                        DATE(executed_at) as date,
                        COUNT(*) as total_tests,
                        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        AVG(duration) as avg_duration
                    FROM test_results
                    WHERE executed_at >= ?
                    GROUP BY DATE(executed_at)
                    ORDER BY date
                """, [cutoff_date]).fetchall()

            trends = []
            for row in results:
                date = datetime.strptime(row[0], '%Y-%m-%d')
                total_tests = row[1] or 0
                passed_tests = row[2] or 0
                failed_tests = row[3] or 0
                avg_duration = row[4] or 0.0

                success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0

                trends.append(TestTrend(
                    date=date,
                    total_tests=total_tests,
                    passed_tests=passed_tests,
                    failed_tests=failed_tests,
                    success_rate=success_rate,
                    avg_duration=avg_duration
                ))

            return trends

        except Exception as e:
            self.logger.error("Failed to get test trends", extra={'error': str(e)})
            return []

    def get_failed_tests(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent failed tests."""
        try:
            with monitoring_db.get_connection() as conn:
                results = conn.execute("""
                    SELECT
                        suite_name,
                        test_name,
                        error_message,
                        traceback,
                        duration,
                        executed_at,
                        environment
                    FROM test_results
                    WHERE status = 'failed'
                    ORDER BY executed_at DESC
                    LIMIT ?
                """, [limit]).fetchall()

            failed_tests = []
            for row in results:
                failed_tests.append({
                    'suite_name': row[0],
                    'test_name': row[1],
                    'error_message': row[2],
                    'traceback': row[3],
                    'duration': row[4],
                    'executed_at': row[5],
                    'environment': row[6]
                })

            return failed_tests

        except Exception as e:
            self.logger.error("Failed to get failed tests", extra={'error': str(e)})
            return []

    def get_test_performance_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get test performance statistics."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with monitoring_db.get_connection() as conn:
                # Overall performance stats
                overall_stats = conn.execute("""
                    SELECT
                        COUNT(*) as total_tests,
                        AVG(duration) as avg_duration,
                        MIN(duration) as min_duration,
                        MAX(duration) as max_duration,
                        SUM(duration) as total_duration
                    FROM test_results
                    WHERE executed_at >= ? AND duration IS NOT NULL
                """, [cutoff_date]).fetchone()

                # Performance by suite
                suite_stats = conn.execute("""
                    SELECT
                        suite_name,
                        COUNT(*) as test_count,
                        AVG(duration) as avg_duration,
                        MIN(duration) as min_duration,
                        MAX(duration) as max_duration
                    FROM test_results
                    WHERE executed_at >= ? AND duration IS NOT NULL
                    GROUP BY suite_name
                    ORDER BY test_count DESC
                """, [cutoff_date]).fetchall()

                # Slowest tests
                slowest_tests = conn.execute("""
                    SELECT
                        suite_name,
                        test_name,
                        duration,
                        executed_at
                    FROM test_results
                    WHERE executed_at >= ? AND duration IS NOT NULL
                    ORDER BY duration DESC
                    LIMIT 10
                """, [cutoff_date]).fetchall()

            return {
                'overall': {
                    'total_tests': overall_stats[0] or 0,
                    'avg_duration': overall_stats[1] or 0.0,
                    'min_duration': overall_stats[2] or 0.0,
                    'max_duration': overall_stats[3] or 0.0,
                    'total_duration': overall_stats[4] or 0.0
                },
                'by_suite': [
                    {
                        'suite_name': row[0],
                        'test_count': row[1],
                        'avg_duration': row[2] or 0.0,
                        'min_duration': row[3] or 0.0,
                        'max_duration': row[4] or 0.0
                    }
                    for row in suite_stats
                ],
                'slowest_tests': [
                    {
                        'suite_name': row[0],
                        'test_name': row[1],
                        'duration': row[2] or 0.0,
                        'executed_at': row[3]
                    }
                    for row in slowest_tests
                ]
            }

        except Exception as e:
            self.logger.error("Failed to get test performance stats", extra={'error': str(e)})
            return {
                'overall': {'total_tests': 0, 'avg_duration': 0.0},
                'by_suite': [],
                'slowest_tests': []
            }

    def get_test_coverage_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get test coverage trends (mock data for now)."""
        # This would integrate with actual coverage tools
        trends = []
        base_date = datetime.now() - timedelta(days=days)

        for i in range(days):
            date = base_date + timedelta(days=i)
            coverage = 75.0 + (i * 0.5)  # Mock increasing trend

            trends.append({
                'date': date,
                'coverage_percentage': min(coverage, 95.0),
                'lines_covered': int(8500 + (i * 25)),
                'total_lines': 11250
            })

        return trends

    def cleanup_old_results(self) -> int:
        """Clean up old test results based on retention policy."""
        try:
            retention_days = config.test_monitor.test_history_retention
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            with monitoring_db.get_connection() as conn:
                result = conn.execute(
                    "DELETE FROM test_results WHERE executed_at < ?",
                    [cutoff_date]
                )
                deleted_count = result.fetchone()[0]

            self.logger.info("Cleaned up old test results", extra={
                'deleted_count': deleted_count,
                'retention_days': retention_days
            })

            return deleted_count

        except Exception as e:
            self.logger.error("Failed to cleanup old test results", extra={'error': str(e)})
            return 0

    def export_test_results(self, start_date: datetime, end_date: datetime, format: str = 'json') -> str:
        """Export test results in specified format."""
        try:
            with monitoring_db.get_connection() as conn:
                results = conn.execute("""
                    SELECT
                        suite_name,
                        test_name,
                        status,
                        duration,
                        error_message,
                        traceback,
                        executed_at,
                        environment
                    FROM test_results
                    WHERE executed_at BETWEEN ? AND ?
                    ORDER BY executed_at DESC
                """, [start_date, end_date]).fetchall()

            data = []
            for row in results:
                data.append({
                    'suite_name': row[0],
                    'test_name': row[1],
                    'status': row[2],
                    'duration': row[3],
                    'error_message': row[4],
                    'traceback': row[5],
                    'executed_at': row[6],
                    'environment': row[7]
                })

            if format.lower() == 'json':
                import json
                return json.dumps(data, indent=2, default=str)
            elif format.lower() == 'csv':
                if not data:
                    return "No test results found"

                import csv
                from io import StringIO

                output = StringIO()
                if data:
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)

                return output.getvalue()
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            self.logger.error("Failed to export test results", extra={'error': str(e)})
            return "Error exporting test results"


# Global instance
test_results_processor = TestResultsProcessor()
