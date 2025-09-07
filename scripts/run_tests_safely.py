#!/usr/bin/env python3
"""
Safe Test Runner - Prevents database lock conflicts
===============================================

This script provides multiple strategies to run tests without database conflicts:

1. Process Detection: Checks for running Jupyter kernels
2. Database Backup: Creates isolated test databases
3. Read-Only Mode: Uses read-only connections where possible
4. Process Management: Can terminate conflicting processes (with confirmation)

Usage:
    python scripts/run_tests_safely.py [test_path] [options]

Examples:
    python scripts/run_tests_safely.py tests/application/scanners/
    python scripts/run_tests_safely.py tests/database/ --auto-fix
    python scripts/run_tests_safely.py --check-only
"""

import sys
import os
import subprocess
import signal
import time
from pathlib import Path
from typing import List, Optional
import argparse
import psutil


class SafeTestRunner:
    """Safe test runner that handles database lock conflicts."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.main_db = self.project_root / "data" / "financial_data.duckdb"

    def check_jupyter_kernels(self) -> List[int]:
        """Check for running Jupyter kernels that might lock the database."""
        jupyter_pids = []

        try:
            # Check for jupyter processes
            result = subprocess.run(
                ["pgrep", "-f", "jupyter"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                jupyter_pids = [int(pid) for pid in pids if pid.strip()]

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return jupyter_pids

    def check_database_locks(self) -> List[dict]:
        """Check what processes are locking the database file."""
        locks = []

        if not self.main_db.exists():
            return locks

        try:
            # Use lsof to check file locks
            result = subprocess.run(
                ["lsof", str(self.main_db)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        locks.append({
                            'pid': int(parts[1]),
                            'command': parts[0],
                            'user': parts[2] if len(parts) > 2 else 'unknown'
                        })

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return locks

    def create_test_database(self) -> Path:
        """Create an isolated test database."""
        test_db = self.project_root / "data" / "test_financial_data.duckdb"

        if self.main_db.exists():
            import shutil
            print(f"📋 Creating test database copy: {test_db}")
            shutil.copy2(self.main_db, test_db)

        return test_db

    def terminate_conflicting_processes(self, pids: List[int], force: bool = False) -> bool:
        """Terminate processes that are locking the database."""
        if not force:
            print("⚠️  The following processes are locking the database:")
            for pid in pids:
                try:
                    proc = psutil.Process(pid)
                    print(f"   PID {pid}: {proc.name()} ({proc.cmdline()[:50]}...)")
                except psutil.NoSuchProcess:
                    continue

            response = input("Terminate these processes? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                return False

        terminated = 0
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                terminated += 1
                print(f"✅ Terminated process {pid}")
                time.sleep(0.5)  # Give process time to clean up
            except (ProcessLookupError, PermissionError) as e:
                print(f"❌ Could not terminate {pid}: {e}")

        return terminated > 0

    def run_tests_readonly(self, test_path: str) -> int:
        """Run tests in read-only mode."""
        print("🔒 Running tests in read-only mode...")

        env = os.environ.copy()
        env['TEST_DB_READONLY'] = '1'

        cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]
        result = subprocess.run(cmd, env=env, cwd=self.project_root)

        return result.returncode

    def run_tests_isolated(self, test_path: str) -> int:
        """Run tests with isolated database."""
        print("🛡️  Running tests with isolated database...")

        # Create isolated database
        test_db = self.create_test_database()

        env = os.environ.copy()
        env['TEST_DB_PATH'] = str(test_db)

        cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]
        result = subprocess.run(cmd, env=env, cwd=self.project_root)

        # Cleanup
        if test_db.exists():
            test_db.unlink()

        return result.returncode

    def run_diagnostic(self) -> dict:
        """Run diagnostic to identify issues."""
        print("🔍 Running diagnostic...")

        jupyter_kernels = self.check_jupyter_kernels()
        db_locks = self.check_database_locks()

        diagnostic = {
            'jupyter_kernels': len(jupyter_kernels),
            'db_locks': len(db_locks),
            'main_db_exists': self.main_db.exists(),
            'main_db_size': self.main_db.stat().st_size if self.main_db.exists() else 0,
            'jupyter_pids': jupyter_kernels,
            'lock_details': db_locks
        }

        print(f"📊 Diagnostic Results:")
        print(f"   Jupyter kernels running: {len(jupyter_kernels)}")
        print(f"   Database locks: {len(db_locks)}")
        print(f"   Main DB exists: {diagnostic['main_db_exists']}")
        if diagnostic['main_db_size']:
            print(f"   Main DB size: {diagnostic['main_db_size'] / (1024**3):.2f} GB")

        return diagnostic

    def suggest_solution(self, diagnostic: dict) -> str:
        """Suggest the best solution based on diagnostic."""
        if diagnostic['db_locks'] == 0:
            return "No locks detected - run tests normally"

        if diagnostic['jupyter_kernels'] > 0:
            return "Jupyter kernels detected - terminate them first"

        return "Unknown lock source - use isolated database mode"

    def run(self, test_path: str = "tests/", check_only: bool = False,
            auto_fix: bool = False, readonly: bool = False) -> int:
        """Main execution method."""

        print("🛡️  Safe Test Runner")
        print("=" * 50)

        # Run diagnostic
        diagnostic = self.run_diagnostic()

        if check_only:
            print(f"💡 Suggested action: {self.suggest_solution(diagnostic)}")
            return 0

        # Handle conflicts
        if diagnostic['db_locks'] > 0:
            if auto_fix and diagnostic['jupyter_kernels'] > 0:
                print("🔧 Auto-fixing: terminating Jupyter kernels...")
                self.terminate_conflicting_processes(diagnostic['jupyter_pids'], force=True)
                time.sleep(2)  # Wait for cleanup
            elif diagnostic['jupyter_kernels'] > 0:
                print("⚠️  Jupyter kernels detected. Please close Jupyter notebooks first.")
                print("   Or run with --auto-fix to terminate automatically")
                return 1

        # Choose test strategy
        if readonly:
            return self.run_tests_readonly(test_path)
        elif diagnostic['db_locks'] > 0:
            return self.run_tests_isolated(test_path)
        else:
            # Run normally
            cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]
            result = subprocess.run(cmd, cwd=self.project_root)
            return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Safe Test Runner - Prevents database lock conflicts"
    )
    parser.add_argument(
        "test_path",
        nargs="?",
        default="tests/",
        help="Test path to run (default: tests/)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for conflicts, don't run tests"
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Automatically terminate conflicting processes"
    )
    parser.add_argument(
        "--readonly",
        action="store_true",
        help="Run tests in read-only mode"
    )

    args = parser.parse_args()

    runner = SafeTestRunner()
    exit_code = runner.run(
        test_path=args.test_path,
        check_only=args.check_only,
        auto_fix=args.auto_fix,
        readonly=args.readonly
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
