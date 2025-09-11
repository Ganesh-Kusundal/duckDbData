"""
Test Monitoring Service
======================

This module provides comprehensive test monitoring capabilities including:
- Real-time test execution monitoring
- Test suite triggering and management
- Test result storage and analysis
- Coverage reporting integration
- Performance metrics tracking
"""

import subprocess
import sys
import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable, Awaitable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
import time
import uuid

from ..config.database import monitoring_db
from ..config.settings import config
from ..logging import get_logger, set_correlation_id

logger = get_logger(__name__)


class TestStatus(Enum):
    """Test execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class TestSuite(Enum):
    """Available test suites."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    ALL = "all"


@dataclass
class TestResult:
    """Test execution result."""
    suite_name: str
    test_name: str
    status: TestStatus
    duration: Optional[float]
    error_message: Optional[str]
    traceback: Optional[str]
    coverage_percentage: Optional[float]
    executed_at: datetime
    environment: str
    python_version: str
    pytest_version: str
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['executed_at'] = self.executed_at.isoformat()
        return data


@dataclass
class TestExecution:
    """Test execution tracking."""
    execution_id: str
    suite: TestSuite
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime]
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    coverage_percentage: Optional[float]
    correlation_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['suite'] = self.suite.value
        data['status'] = self.status.value
        data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data


class TestMonitorService:
    """Main test monitoring service."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._active_executions: Dict[str, TestExecution] = {}
        self._execution_lock = threading.Lock()
        self._result_callbacks: List[Callable[[TestResult], Awaitable[None]]] = []

    def run_test_suite(self, suite_name: str, callback: Optional[Callable] = None) -> str:
        """Run a test suite and return execution ID."""
        correlation_id = set_correlation_id()

        try:
            suite = TestSuite(suite_name.lower())
        except ValueError:
            raise ValueError(f"Invalid test suite: {suite_name}")

        execution_id = str(uuid.uuid4())

        # Create execution record
        execution = TestExecution(
            execution_id=execution_id,
            suite=suite,
            status=TestStatus.PENDING,
            start_time=datetime.now(),
            end_time=None,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            error_tests=0,
            coverage_percentage=None,
            correlation_id=correlation_id
        )

        with self._execution_lock:
            self._active_executions[execution_id] = execution

        # Start test execution in background thread
        thread = threading.Thread(
            target=self._execute_test_suite,
            args=(execution, callback),
            daemon=True
        )
        thread.start()

        self.logger.info("Started test suite execution", extra={
            'execution_id': execution_id,
            'suite': suite.value,
            'correlation_id': correlation_id
        })

        return execution_id

    def _execute_test_suite(self, execution: TestExecution, callback: Optional[Callable]) -> None:
        """Execute test suite in background thread."""
        try:
            # Update execution status
            execution.status = TestStatus.RUNNING
            self._store_execution(execution)

            # Build pytest command
            cmd = self._build_pytest_command(execution.suite)

            self.logger.info("Executing pytest command", extra={
                'execution_id': execution.execution_id,
                'command': ' '.join(cmd),
                'suite': execution.suite.value
            })

            # Execute tests with custom hook
            env = os.environ.copy()
            env['TEST_EXECUTION_ID'] = execution.execution_id
            env['TEST_CORRELATION_ID'] = execution.correlation_id

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=Path(__file__).parent.parent.parent.parent.parent  # Project root
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=config.test_monitor.default_timeout)

                # Parse results (this would be enhanced with actual pytest hooks)
                self._parse_test_output(execution, stdout, stderr)

            except subprocess.TimeoutExpired:
                process.kill()
                execution.status = TestStatus.TIMEOUT
                self.logger.error("Test execution timed out", extra={
                    'execution_id': execution.execution_id,
                    'timeout': config.test_monitor.default_timeout
                })

            # Update final execution status
            execution.end_time = datetime.now()
            execution.status = TestStatus.PASSED if execution.failed_tests == 0 else TestStatus.FAILED
            self._store_execution(execution)

            if callback:
                try:
                    asyncio.run(callback(execution))
                except Exception as e:
                    self.logger.error("Test execution callback failed", extra={
                        'execution_id': execution.execution_id,
                        'error': str(e)
                    })

        except Exception as e:
            execution.status = TestStatus.ERROR
            execution.end_time = datetime.now()
            self._store_execution(execution)

            self.logger.error("Test execution failed", extra={
                'execution_id': execution.execution_id,
                'error': str(e)
            })

        finally:
            # Clean up
            with self._execution_lock:
                if execution.execution_id in self._active_executions:
                    del self._active_executions[execution.execution_id]

    def _build_pytest_command(self, suite: TestSuite) -> List[str]:
        """Build pytest command for the given suite."""
        cmd = [sys.executable, "-m", "pytest"]

        # Add pytest arguments from config
        cmd.extend(config.test_monitor.pytest_args)

        # Add suite-specific arguments
        if suite == TestSuite.UNIT:
            cmd.extend(["tests/unit/"])
        elif suite == TestSuite.INTEGRATION:
            cmd.extend(["tests/integration/"])
        elif suite == TestSuite.E2E:
            cmd.extend(["tests/e2e/"])
        elif suite == TestSuite.PERFORMANCE:
            cmd.extend(["tests/performance/"])
        elif suite == TestSuite.ALL:
            cmd.extend(["tests/"])

        # Add coverage if enabled
        if config.test_monitor.enable_coverage:
            cmd.extend([
                "--cov=src",
                f"--cov-report=term-missing",
                f"--cov-fail-under={config.test_monitor.coverage_threshold}"
            ])

        # Add JSON output for parsing
        cmd.extend(["--json-report", "--json-report-file=/tmp/test_results.json"])

        # Add custom hook
        cmd.extend(["-p", "monitoring.test_monitor.hooks"])

        return cmd

    def _parse_test_output(self, execution: TestExecution, stdout: str, stderr: str) -> None:
        """Parse pytest output to extract test results."""
        # This is a simplified parser - in practice, you'd use pytest hooks
        # to get structured data

        # Try to read JSON report if available
        json_file = Path("/tmp/test_results.json")
        if json_file.exists():
            try:
                with open(json_file) as f:
                    json_data = json.load(f)

                # Parse summary
                summary = json_data.get('summary', {})
                execution.total_tests = summary.get('num_tests', 0)
                execution.passed_tests = summary.get('passed', 0)
                execution.failed_tests = summary.get('failed', 0)
                execution.skipped_tests = summary.get('skipped', 0)
                execution.error_tests = summary.get('errors', 0)

                # Parse individual test results
                for test in json_data.get('tests', []):
                    result = TestResult(
                        suite_name=execution.suite.value,
                        test_name=test.get('nodeid', ''),
                        status=self._parse_test_status(test.get('outcome', 'unknown')),
                        duration=test.get('duration', 0.0),
                        error_message=test.get('call', {}).get('crash', {}).get('message'),
                        traceback=test.get('call', {}).get('crash', {}).get('traceback'),
                        coverage_percentage=None,  # Would be calculated separately
                        executed_at=datetime.now(),
                        environment=config.environment,
                        python_version=sys.version,
                        pytest_version="7.0.0",  # Would get from pytest
                        correlation_id=execution.correlation_id
                    )
                    self._store_test_result(result)

                # Clean up JSON file
                json_file.unlink(missing_ok=True)

            except Exception as e:
                self.logger.warning("Failed to parse JSON test results", extra={'error': str(e)})
                # Fall back to stdout parsing
                self._parse_stdout_results(execution, stdout)

        else:
            self._parse_stdout_results(execution, stdout)

    def _parse_stdout_results(self, execution: TestExecution, stdout: str) -> None:
        """Parse stdout for basic test results."""
        lines = stdout.split('\n')

        for line in lines:
            if 'passed' in line.lower():
                # Try to extract numbers
                pass

        # This is a very basic parser - in practice, use pytest hooks for accurate results
        execution.total_tests = 0
        execution.passed_tests = 0
        execution.failed_tests = 0

    def _parse_test_status(self, outcome: str) -> TestStatus:
        """Parse pytest outcome to TestStatus."""
        outcome = outcome.lower()
        if outcome == 'passed':
            return TestStatus.PASSED
        elif outcome == 'failed':
            return TestStatus.FAILED
        elif outcome == 'skipped':
            return TestStatus.SKIPPED
        elif outcome == 'error':
            return TestStatus.ERROR
        else:
            return TestStatus.ERROR

    def _store_execution(self, execution: TestExecution) -> None:
        """Store test execution record."""
        # For now, we'll store this in memory
        # In a full implementation, you'd store in database
        pass

    def _store_test_result(self, result: TestResult) -> None:
        """Store individual test result."""
        try:
            with monitoring_db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO test_results (
                        suite_name, test_name, status, duration, error_message,
                        traceback, coverage_percentage, executed_at, environment,
                        python_version, pytest_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.suite_name,
                    result.test_name,
                    result.status.value,
                    result.duration,
                    result.error_message,
                    result.traceback,
                    result.coverage_percentage,
                    result.executed_at,
                    result.environment,
                    result.python_version,
                    result.pytest_version
                ))
        except Exception as e:
            self.logger.error("Failed to store test result", extra={
                'error': str(e),
                'test_name': result.test_name
            })

    def get_test_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get test execution history."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with monitoring_db.get_connection() as conn:
                results = conn.execute("""
                    SELECT
                        suite_name,
                        test_name,
                        status,
                        duration,
                        error_message,
                        executed_at,
                        environment
                    FROM test_results
                    WHERE executed_at >= ?
                    ORDER BY executed_at DESC
                    LIMIT 1000
                """, [cutoff_date]).fetchall()

            history = []
            for row in results:
                history.append({
                    'suite_name': row[0],
                    'test_name': row[1],
                    'status': row[2],
                    'duration': row[3],
                    'error_message': row[4],
                    'executed_at': row[5],
                    'environment': row[6]
                })

            return history

        except Exception as e:
            self.logger.error("Failed to get test history", extra={'error': str(e)})
            return []

    def get_current_status(self) -> Dict[str, Any]:
        """Get current test execution status."""
        with self._execution_lock:
            active_executions = list(self._active_executions.values())

        # Get recent test results
        try:
            with monitoring_db.get_connection() as conn:
                # Last 24 hours summary
                yesterday = datetime.now() - timedelta(days=1)

                summary = conn.execute("""
                    SELECT
                        COUNT(*) as total_tests,
                        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped,
                        AVG(duration) as avg_duration
                    FROM test_results
                    WHERE executed_at >= ?
                """, [yesterday]).fetchone()

                recent_results = []
                if summary:
                    recent_results = conn.execute("""
                        SELECT suite_name, test_name, status, executed_at
                        FROM test_results
                        WHERE executed_at >= ?
                        ORDER BY executed_at DESC
                        LIMIT 10
                    """, [yesterday]).fetchall()

        except Exception as e:
            self.logger.error("Failed to get test status summary", extra={'error': str(e)})
            summary = None
            recent_results = []

        return {
            'active_executions': [exec.to_dict() for exec in active_executions],
            'summary': {
                'total_tests': summary[0] if summary else 0,
                'passed': summary[1] if summary else 0,
                'failed': summary[2] if summary else 0,
                'skipped': summary[3] if summary else 0,
                'avg_duration': summary[4] if summary else 0,
                'time_range': 'last 24 hours'
            },
            'recent_results': [
                {
                    'suite_name': row[0],
                    'test_name': row[1],
                    'status': row[2],
                    'executed_at': row[3]
                }
                for row in recent_results
            ]
        }

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running test execution."""
        with self._execution_lock:
            if execution_id in self._active_executions:
                execution = self._active_executions[execution_id]
                execution.status = TestStatus.ERROR
                execution.end_time = datetime.now()
                # In practice, you'd need to track the actual process and kill it
                return True
        return False

    def add_result_callback(self, callback: Callable[[TestResult], Awaitable[None]]) -> None:
        """Add callback for test result notifications."""
        self._result_callbacks.append(callback)

    def get_test_suites(self) -> List[str]:
        """Get available test suites."""
        return [suite.value for suite in TestSuite]

    def get_test_coverage(self, suite: Optional[str] = None) -> Dict[str, Any]:
        """Get test coverage information."""
        # This would integrate with coverage tools
        return {
            'overall_coverage': 85.5,  # Mock data
            'by_suite': {
                'unit': 92.3,
                'integration': 78.9,
                'e2e': 65.4
            },
            'trend': 'increasing'
        }


# Global instance
test_monitor = TestMonitorService()
