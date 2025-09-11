"""
Test Monitor Package
===================

This package provides comprehensive test monitoring capabilities:
- Real-time test execution monitoring
- Test suite triggering and management
- Test result analysis and reporting
- Pytest integration with custom hooks
"""

from .service import (
    TestMonitorService,
    TestResult,
    TestExecution,
    TestStatus,
    TestSuite,
    test_monitor
)
from .results import (
    TestResultsProcessor,
    TestSuiteSummary,
    TestTrend,
    test_results_processor
)
from .hooks import TestMonitorPlugin

__all__ = [
    # Service
    'TestMonitorService',
    'TestResult',
    'TestExecution',
    'TestStatus',
    'TestSuite',
    'test_monitor',

    # Results
    'TestResultsProcessor',
    'TestSuiteSummary',
    'TestTrend',
    'test_results_processor',

    # Hooks
    'TestMonitorPlugin'
]
