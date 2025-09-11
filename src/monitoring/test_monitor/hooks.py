"""
Pytest Hooks for Test Monitoring
================================

This module provides pytest hooks to capture test execution data
and integrate with the monitoring dashboard.
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

import pytest

from ..logging import get_logger, set_correlation_id
from .service import TestStatus, TestResult

logger = get_logger(__name__)


class TestMonitorPlugin:
    """Pytest plugin for monitoring test execution."""

    def __init__(self):
        self.execution_id = os.environ.get('TEST_EXECUTION_ID')
        self.correlation_id = os.environ.get('TEST_CORRELATION_ID') or set_correlation_id()
        self.start_times: Dict[str, float] = {}
        self.test_results: Dict[str, Dict[str, Any]] = {}

    def pytest_sessionstart(self, session):
        """Called at the start of test session."""
        logger.info("Test session started", extra={
            'execution_id': self.execution_id,
            'correlation_id': self.correlation_id,
            'test_count': session.testscollected
        })

    def pytest_sessionfinish(self, session, exitstatus):
        """Called at the end of test session."""
        logger.info("Test session finished", extra={
            'execution_id': self.execution_id,
            'correlation_id': self.correlation_id,
            'exit_status': exitstatus,
            'duration': getattr(session, '_session_duration', 0)
        })

    def pytest_runtest_setup(self, item):
        """Called before test setup."""
        test_id = self._get_test_id(item)
        self.start_times[test_id] = time.time()

        logger.debug("Test setup started", extra={
            'execution_id': self.execution_id,
            'correlation_id': self.correlation_id,
            'test_id': test_id,
            'test_name': item.name,
            'module': item.module.__name__ if item.module else None
        })

    def pytest_runtest_call(self, item):
        """Called when test is executed."""
        test_id = self._get_test_id(item)

        logger.debug("Test execution started", extra={
            'execution_id': self.execution_id,
            'correlation_id': self.correlation_id,
            'test_id': test_id,
            'test_name': item.name
        })

    def pytest_runtest_teardown(self, item, nextitem):
        """Called after test teardown."""
        test_id = self._get_test_id(item)

        logger.debug("Test teardown completed", extra={
            'execution_id': self.execution_id,
            'correlation_id': self.correlation_id,
            'test_id': test_id,
            'test_name': item.name
        })

    def pytest_runtest_makereport(self, item, call):
        """Called when test report is created."""
        test_id = self._get_test_id(item)
        start_time = self.start_times.get(test_id, time.time())
        duration = time.time() - start_time

        # Extract test information
        test_info = {
            'test_id': test_id,
            'test_name': item.name,
            'module': item.module.__name__ if item.module else 'unknown',
            'class': item.cls.__name__ if item.cls else None,
            'file': str(item.fspath),
            'line': item.location[1] if len(item.location) > 1 else 0,
            'duration': duration,
            'stage': call.when,
            'outcome': call.excinfo is None
        }

        if call.excinfo:
            test_info['exception_type'] = call.excinfo.type.__name__
            test_info['exception_message'] = str(call.excinfo.value)
            test_info['traceback'] = self._format_traceback(call.excinfo.traceback)

        # Store test result for final report
        if call.when == 'call':  # Final result
            self.test_results[test_id] = test_info

            # Log test result
            log_data = {
                'execution_id': self.execution_id,
                'correlation_id': self.correlation_id,
                'test_id': test_id,
                'test_name': item.name,
                'module': test_info['module'],
                'duration': duration,
                'outcome': 'passed' if test_info['outcome'] else 'failed'
            }

            if not test_info['outcome']:
                log_data['exception_type'] = test_info.get('exception_type')
                log_data['exception_message'] = test_info.get('exception_message')

                logger.error("Test failed", extra=log_data)
            else:
                logger.info("Test passed", extra=log_data)

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config):
        """Called at the end to create summary."""
        # Collect final statistics
        stats = {}
        for key, value in terminalreporter.stats.items():
            stats[key] = len(value)

        logger.info("Test session summary", extra={
            'execution_id': self.execution_id,
            'correlation_id': self.correlation_id,
            'stats': stats,
            'exit_status': exitstatus
        })

    def _get_test_id(self, item) -> str:
        """Generate unique test ID."""
        parts = []
        if item.module:
            parts.append(item.module.__name__)
        if item.cls:
            parts.append(item.cls.__name__)
        parts.append(item.name)
        return '::'.join(parts)

    def _format_traceback(self, traceback) -> str:
        """Format traceback for logging."""
        lines = []
        while traceback:
            frame = traceback.frame
            filename = frame.f_code.co_filename
            line_number = traceback.lineno
            function_name = frame.f_code.co_name

            lines.append(f"  File \"{filename}\", line {line_number}, in {function_name}")
            if traceback.line:
                lines.append(f"    {traceback.line.strip()}")

            traceback = traceback.tb_next

        return '\n'.join(lines)


# Register the plugin
def pytest_configure(config):
    """Configure pytest with monitoring plugin."""
    plugin = TestMonitorPlugin()
    config.pluginmanager.register(plugin, "test_monitor")


def pytest_unconfigure(config):
    """Unconfigure pytest monitoring plugin."""
    pass
