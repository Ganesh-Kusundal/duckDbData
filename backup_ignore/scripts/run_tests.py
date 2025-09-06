#!/usr/bin/env python3
"""
Test Runner Script
==================

Comprehensive test runner for the DuckDB Financial Infrastructure.
Supports different test categories and reporting options.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any


class TestRunner:
    """Test runner for the DuckDB Financial Infrastructure."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = {}

    def run_command(self, command: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result
        except subprocess.TimeoutExpired:
            print("❌ Command timed out")
            return None

    def run_unit_tests(self) -> bool:
        """Run unit tests."""
        print("\n🧪 Running Unit Tests...")
        print("=" * 50)

        cmd = [
            "python", "-m", "pytest",
            "tests/unit/",
            "-v",
            "--tb=short",
            "--cov=src/duckdb_financial_infra",
            "--cov-report=term-missing",
            "--cov-report=html:reports/coverage/unit",
            "--cov-fail-under=90"
        ]

        result = self.run_command(cmd)
        self.test_results['unit'] = result

        if result and result.returncode == 0:
            print("✅ Unit tests passed")
            return True
        else:
            print("❌ Unit tests failed")
            if result:
                print(result.stdout)
                print(result.stderr)
            return False

    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        print("\n🔗 Running Integration Tests...")
        print("=" * 50)

        cmd = [
            "python", "-m", "pytest",
            "tests/integration/",
            "-v",
            "--tb=short",
            "--cov=src/duckdb_financial_infra",
            "--cov-report=term-missing",
            "--cov-report=html:reports/coverage/integration",
            "--cov-append"
        ]

        result = self.run_command(cmd)
        self.test_results['integration'] = result

        if result and result.returncode == 0:
            print("✅ Integration tests passed")
            return True
        else:
            print("❌ Integration tests failed")
            if result:
                print(result.stdout)
                print(result.stderr)
            return False

    def run_regression_tests(self) -> bool:
        """Run regression tests."""
        print("\n🔄 Running Regression Tests...")
        print("=" * 50)

        cmd = [
            "python", "-m", "pytest",
            "tests/regression/",
            "-v",
            "--tb=short",
            "-m", "regression",
            "--cov=src/duckdb_financial_infra",
            "--cov-report=term-missing",
            "--cov-report=html:reports/coverage/regression",
            "--cov-append"
        ]

        result = self.run_command(cmd)
        self.test_results['regression'] = result

        if result and result.returncode == 0:
            print("✅ Regression tests passed")
            return True
        else:
            print("❌ Regression tests failed")
            if result:
                print(result.stdout)
                print(result.stderr)
            return False

    def run_performance_tests(self) -> bool:
        """Run performance tests."""
        print("\n⚡ Running Performance Tests...")
        print("=" * 50)

        cmd = [
            "python", "-m", "pytest",
            "tests/performance/",
            "-v",
            "--tb=short",
            "-m", "performance",
            "--durations=10"
        ]

        result = self.run_command(cmd)
        self.test_results['performance'] = result

        if result and result.returncode == 0:
            print("✅ Performance tests passed")
            return True
        else:
            print("❌ Performance tests failed")
            if result:
                print(result.stdout)
                print(result.stderr)
            return False

    def run_load_tests(self) -> bool:
        """Run load tests."""
        print("\n🏋️ Running Load Tests...")
        print("=" * 50)

        cmd = [
            "python", "-m", "pytest",
            "tests/performance/",
            "-v",
            "--tb=short",
            "-m", "load",
            "--durations=10"
        ]

        result = self.run_command(cmd)
        self.test_results['load'] = result

        if result and result.returncode == 0:
            print("✅ Load tests passed")
            return True
        else:
            print("❌ Load tests failed")
            if result:
                print(result.stdout)
                print(result.stderr)
            return False

    def run_all_tests(self) -> bool:
        """Run all test categories."""
        print("\n🚀 Running Complete Test Suite...")
        print("=" * 60)

        start_time = time.time()

        results = []
        results.append(("Unit Tests", self.run_unit_tests()))
        results.append(("Integration Tests", self.run_integration_tests()))
        results.append(("Regression Tests", self.run_regression_tests()))
        results.append(("Performance Tests", self.run_performance_tests()))
        results.append(("Load Tests", self.run_load_tests()))

        end_time = time.time()
        total_time = end_time - start_time

        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 60)

        passed = 0
        total = len(results)

        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print("25")
            if success:
                passed += 1

        print(f"\n⏱️ Total execution time: {total_time:.2f} seconds")
        print(f"📈 Overall result: {passed}/{total} test categories passed")

        if passed == total:
            print("🎉 ALL TESTS PASSED! System is ready for deployment.")
            return True
        else:
            print("⚠️ Some tests failed. Please review the results above.")
            return False

    def run_smoke_tests(self) -> bool:
        """Run quick smoke tests for basic functionality."""
        print("\n💨 Running Smoke Tests...")
        print("=" * 50)

        cmd = [
            "python", "-m", "pytest",
            "tests/regression/test_regression_suite.py::TestCoreFunctionalityRegression::test_market_data_entity_creation",
            "tests/regression/test_regression_suite.py::TestCoreFunctionalityRegression::test_plugin_system_initialization",
            "tests/regression/test_regression_suite.py::TestAPISystemRegression::test_api_app_creation",
            "-v",
            "--tb=short"
        ]

        result = self.run_command(cmd)
        self.test_results['smoke'] = result

        if result and result.returncode == 0:
            print("✅ Smoke tests passed")
            return True
        else:
            print("❌ Smoke tests failed")
            if result:
                print(result.stdout)
                print(result.stderr)
            return False

    def generate_coverage_report(self):
        """Generate comprehensive coverage report."""
        print("\n📊 Generating Coverage Report...")
        print("=" * 50)

        cmd = [
            "python", "-m", "pytest",
            "--cov=src/duckdb_financial_infra",
            "--cov-report=html:reports/coverage/full",
            "--cov-report=term-missing",
            "--cov-report=xml:reports/coverage/coverage.xml",
            "tests/"
        ]

        result = self.run_command(cmd)

        if result and result.returncode == 0:
            print("✅ Coverage report generated")
            print("📁 Reports available in: reports/coverage/")
        else:
            print("❌ Coverage report generation failed")

    def run_with_options(self, args):
        """Run tests based on command line arguments."""
        if args.smoke:
            return self.run_smoke_tests()
        elif args.unit:
            return self.run_unit_tests()
        elif args.integration:
            return self.run_integration_tests()
        elif args.regression:
            return self.run_regression_tests()
        elif args.performance:
            return self.run_performance_tests()
        elif args.load:
            return self.run_load_tests()
        elif args.coverage:
            self.generate_coverage_report()
            return True
        else:
            return self.run_all_tests()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DuckDB Financial Infrastructure Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_tests.py                    # Run all tests
  python scripts/run_tests.py --smoke           # Quick smoke tests
  python scripts/run_tests.py --unit            # Unit tests only
  python scripts/run_tests.py --regression      # Regression tests
  python scripts/run_tests.py --performance     # Performance tests
  python scripts/run_tests.py --coverage        # Generate coverage report
        """
    )

    parser.add_argument('--smoke', action='store_true',
                       help='Run quick smoke tests')
    parser.add_argument('--unit', action='store_true',
                       help='Run unit tests only')
    parser.add_argument('--integration', action='store_true',
                       help='Run integration tests only')
    parser.add_argument('--regression', action='store_true',
                       help='Run regression tests only')
    parser.add_argument('--performance', action='store_true',
                       help='Run performance tests only')
    parser.add_argument('--load', action='store_true',
                       help='Run load tests only')
    parser.add_argument('--coverage', action='store_true',
                       help='Generate coverage report only')

    args = parser.parse_args()

    runner = TestRunner()
    success = runner.run_with_options(args)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
