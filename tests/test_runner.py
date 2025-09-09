#!/usr/bin/env python3
"""
Comprehensive test runner for the DuckDB Financial Infrastructure.
Runs all test suites and provides detailed reporting.
"""

import subprocess
import sys
import time
from pathlib import Path
import json
from datetime import datetime


class TestRunner:
    """Comprehensive test runner with detailed reporting."""

    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def run_pytest_suite(self, test_path, suite_name):
        """Run a pytest test suite and capture results."""
        print(f"\\n🔍 Running {suite_name}...")

        try:
            # Run pytest with basic output
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                test_path,
                "-v",
                "--tb=short"
            ], capture_output=True, text=True, timeout=300)

            # Parse results
            success = result.returncode == 0
            output = result.stdout
            errors = result.stderr

            self.test_results[suite_name] = {
                "success": success,
                "return_code": result.returncode,
                "output": output,
                "errors": errors,
                "detailed": {}
            }

            if success:
                print(f"✅ {suite_name} PASSED")
            else:
                print(f"❌ {suite_name} FAILED")
                if errors:
                    print(f"   Error: {errors[-200:]}...")

            return success

        except subprocess.TimeoutExpired:
            print(f"⏰ {suite_name} TIMED OUT")
            self.test_results[suite_name] = {
                "success": False,
                "return_code": -1,
                "output": "",
                "errors": "Test suite timed out",
                "detailed": {}
            }
            return False
        except Exception as e:
            print(f"💥 {suite_name} ERROR: {e}")
            self.test_results[suite_name] = {
                "success": False,
                "return_code": -1,
                "output": "",
                "errors": str(e),
                "detailed": {}
            }
            return False

    def run_all_tests(self):
        """Run all test suites."""
        self.start_time = time.time()

        print("🚀 Starting Comprehensive Test Suite")
        print("=" * 60)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Define test suites to run
        test_suites = [
            # Database tests
            ("tests/database/test_connection_manager.py", "Database Connection Manager"),
            ("tests/database/test_db_manager.py", "Database Manager"),

            # Scanner tests
            ("tests/application/scanners/test_scanner_fixes.py", "Scanner Fixes"),
            ("tests/application/scanners/integration/test_scanner_with_fixtures.py", "Scanner Integration"),
            ("tests/application/scanners/integration/test_optimal_scanner.py", "Optimal Scanner"),

            # API tests
            ("tests/infrastructure/test_api_server.py", "API Server"),

            # Integration tests
            ("tests/integration/test_complete_workflow.py", "Complete Workflow"),
            ("tests/integration/test_market_data_workflow.py", "Market Data Workflow"),

            # Performance tests
            ("tests/performance/test_database_performance.py", "Database Performance"),
            ("tests/performance/test_performance.py", "General Performance"),

            # Domain tests
            ("tests/domain/test_market_data.py", "Market Data Domain"),
            ("tests/domain/test_exceptions.py", "Domain Exceptions"),

            # Infrastructure tests
            ("tests/infrastructure/test_config_manager.py", "Configuration Manager"),
            ("tests/infrastructure/test_retry.py", "Retry Mechanisms"),
        ]

        successful_suites = 0
        total_suites = len(test_suites)

        for test_path, suite_name in test_suites:
            if Path(test_path).exists():
                if self.run_pytest_suite(test_path, suite_name):
                    successful_suites += 1
            else:
                print(f"⚠️  {suite_name} test file not found: {test_path}")
                self.test_results[suite_name] = {
                    "success": False,
                    "return_code": -1,
                    "output": "",
                    "errors": "Test file not found",
                    "detailed": {}
                }

        self.end_time = time.time()
        return successful_suites, total_suites

    def run_specific_test(self, test_name):
        """Run a specific test by name."""
        test_mapping = {
            "database": "tests/database/test_connection_manager.py",
            "connection": "tests/database/test_connection_manager.py",
            "scanner": "tests/application/scanners/test_scanner_fixes.py",
            "api": "tests/infrastructure/test_api_server.py",
            "integration": "tests/integration/test_complete_workflow.py",
            "performance": "tests/performance/test_database_performance.py",
            "workflow": "tests/integration/test_complete_workflow.py",
        }

        if test_name in test_mapping:
            test_path = test_mapping[test_name]
            suite_name = f"{test_name.title()} Tests"

            print(f"🎯 Running specific test: {suite_name}")
            self.start_time = time.time()
            success = self.run_pytest_suite(test_path, suite_name)
            self.end_time = time.time()
            return success, 1
        else:
            print(f"❌ Unknown test name: {test_name}")
            print("Available tests: database, connection, scanner, api, integration, performance, workflow")
            return False, 0

    def generate_report(self, successful_suites, total_suites):
        """Generate comprehensive test report."""
        duration = self.end_time - self.start_time

        print("\\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        print(f"Total Duration: {duration:.2f} seconds")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Overall results
        success_rate = (successful_suites / total_suites * 100) if total_suites > 0 else 0

        print("🎯 OVERALL RESULTS:")
        print(f"   ✅ Passed: {successful_suites}/{total_suites}")
        print(f"   📊 Success Rate: {success_rate:.1f}%")
        print(f"   ⏱️  Total Time: {duration:.2f}s")
        print()

        # Detailed results
        print("📋 DETAILED RESULTS:")
        print("-" * 80)

        for suite_name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{suite_name:<30} {status}")

            if not result["success"]:
                if result["errors"]:
                    error_preview = result["errors"][:100] + "..." if len(result["errors"]) > 100 else result["errors"]
                    print(f"      Error: {error_preview}")

        print("\\n" + "=" * 80)

        # Performance metrics
        if duration > 0:
            tests_per_second = total_suites / duration
            print("⚡ PERFORMANCE METRICS:")
            print(f"   🔄 Tests/Second: {tests_per_second:.2f}")
            print(f"   📈 Avg Test Time: {duration/total_suites:.3f}s")
        # Recommendations
        if success_rate < 80:
            print("\\n⚠️  RECOMMENDATIONS:")
            print("   • Review failing test suites for critical issues")
            print("   • Check database connections and configurations")
            print("   • Verify scanner implementations are correct")
            print("   • Ensure API endpoints are properly configured")
        elif success_rate >= 95:
            print("\\n🎉 EXCELLENT RESULTS!")
            print("   • All core functionality is working correctly")
            print("   • Database optimizations are effective")
            print("   • Scanner system is fully operational")
            print("   • API endpoints are functioning properly")
        else:
            print("\\n👍 GOOD RESULTS!")
            print("   • Core functionality is working")
            print("   • Some minor issues to address")
            print("   • Overall system health is good")

        print("\\n" + "=" * 80)

        return success_rate >= 80  # Consider 80% success as overall pass


def main():
    """Main entry point for test runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Comprehensive Test Runner")
    parser.add_argument("--test", help="Run specific test (database, scanner, api, etc.)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", help="Output results to JSON file")

    args = parser.parse_args()

    runner = TestRunner()

    if args.test:
        # Run specific test
        successful, total = runner.run_specific_test(args.test)
    else:
        # Run all tests
        successful, total = runner.run_all_tests()

    # Generate report
    overall_success = runner.generate_report(successful, total)

    # Output JSON if requested
    if args.json:
        results = {
            "timestamp": datetime.now().isoformat(),
            "duration": runner.end_time - runner.start_time,
            "successful_suites": successful,
            "total_suites": total,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "overall_success": overall_success,
            "detailed_results": runner.test_results
        }

        with open(args.json, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\\n📄 Results saved to: {args.json}")

    # Exit with appropriate code
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()
