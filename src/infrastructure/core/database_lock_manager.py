"""
Database Lock Manager - Proper Handling of DuckDB Concurrent Access

This module provides proper handling of DuckDB database locks and concurrent access
issues without resorting to test data or mock databases.
"""

import os
import time
import psutil
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseLockManager:
    """
    Manages DuckDB database locks and concurrent access issues.

    This class provides proper analysis and resolution of database lock conflicts
    by identifying processes holding locks and providing actionable solutions.
    """

    def __init__(self, db_path: str):
        """
        Initialize the lock manager.

        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = Path(db_path)
        self.lock_file = self.db_path.with_suffix('.duckdb.lock')
        self.wal_file = self.db_path.with_suffix('.duckdb.wal')

    def analyze_lock_situation(self) -> Dict[str, Any]:
        """
        Analyze the current lock situation and provide detailed information.

        Returns:
            Dictionary containing lock analysis information
        """
        analysis = {
            'database_file': str(self.db_path),
            'lock_file_exists': self.lock_file.exists(),
            'wal_file_exists': self.wal_file.exists(),
            'database_accessible': False,
            'lock_holders': [],
            'recommendations': []
        }

        # Check if database is accessible
        analysis['database_accessible'] = self._check_database_accessibility()

        # Analyze lock file if it exists
        if analysis['lock_file_exists']:
            lock_holders = self._analyze_lock_file()
            analysis['lock_holders'] = lock_holders

            if lock_holders:
                analysis['recommendations'].append({
                    'action': 'close_processes',
                    'description': f'Close the following processes: {lock_holders}',
                    'severity': 'high'
                })

        # Check for WAL file (Write-Ahead Logging)
        if analysis['wal_file_exists']:
            analysis['recommendations'].append({
                'action': 'wait_wal',
                'description': 'WAL file exists - database may be in the middle of a transaction',
                'severity': 'medium'
            })

        # Provide general recommendations
        if not analysis['database_accessible']:
            analysis['recommendations'].extend([
                {
                    'action': 'wait_lock_release',
                    'description': 'Wait for database operations to complete',
                    'severity': 'low'
                },
                {
                    'action': 'check_processes',
                    'description': 'Use database_lock_manager.analyze_lock_situation() for detailed analysis',
                    'severity': 'medium'
                }
            ])

        return analysis

    def _check_database_accessibility(self) -> bool:
        """Check if the database file is accessible for reading."""
        try:
            # Try to open the file in read-only mode
            with open(self.db_path, 'rb') as f:
                # Just try to read the first few bytes
                f.read(1024)
            return True
        except (OSError, PermissionError):
            return False

    def _analyze_lock_file(self) -> List[Dict[str, Any]]:
        """Analyze the lock file to identify processes holding locks."""
        lock_holders = []

        try:
            if not self.lock_file.exists():
                return lock_holders

            # Read lock file content
            with open(self.lock_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()

            # Try to extract PID information
            if content:
                # DuckDB lock files typically contain process information
                lines = content.split('\n')
                for line in lines:
                    if line.strip():
                        process_info = self._parse_lock_file_line(line)
                        if process_info:
                            lock_holders.append(process_info)

        except Exception as e:
            logger.warning(f"Failed to analyze lock file: {e}")

        return lock_holders

    def _parse_lock_file_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a line from the lock file to extract process information."""
        try:
            # DuckDB lock files can contain various formats
            # Try to extract PID and process information
            parts = line.strip().split()

            for part in parts:
                if part.isdigit():
                    pid = int(part)
                    process_info = self._get_process_info(pid)
                    if process_info:
                        return {
                            'pid': pid,
                            'process_name': process_info.get('name', 'Unknown'),
                            'cmdline': process_info.get('cmdline', []),
                            'status': process_info.get('status', 'Unknown'),
                            'is_alive': process_info.get('is_alive', False)
                        }

        except Exception as e:
            logger.debug(f"Failed to parse lock file line '{line}': {e}")

        return None

    def _get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get information about a process by PID."""
        try:
            process = psutil.Process(pid)

            return {
                'name': process.name(),
                'cmdline': process.cmdline(),
                'status': process.status(),
                'is_alive': process.is_running()
            }

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process doesn't exist or we can't access it
            return {
                'name': 'Unknown (process may have ended)',
                'cmdline': [],
                'status': 'Not running',
                'is_alive': False
            }

        except Exception as e:
            logger.debug(f"Failed to get process info for PID {pid}: {e}")
            return None

    def cleanup_stale_locks(self) -> Dict[str, Any]:
        """
        Clean up stale lock files from processes that are no longer running.

        Returns:
            Dictionary containing cleanup results
        """
        results = {
            'lock_files_checked': 0,
            'stale_locks_removed': 0,
            'active_locks_found': 0,
            'errors': []
        }

        try:
            if not self.lock_file.exists():
                return results

            results['lock_files_checked'] = 1

            # Analyze the lock file
            lock_holders = self._analyze_lock_file()

            if not lock_holders:
                # No processes found in lock file, might be safe to remove
                logger.info("No active processes found in lock file, removing it")
                self.lock_file.unlink()
                results['stale_locks_removed'] = 1
                return results

            # Check if any processes are still alive
            all_dead = True
            for holder in lock_holders:
                if holder.get('is_alive', False):
                    all_dead = False
                    results['active_locks_found'] += 1
                    logger.info(f"Active process found: {holder['process_name']} (PID: {holder['pid']})")
                else:
                    logger.info(f"Dead process found: {holder['process_name']} (PID: {holder['pid']})")

            if all_dead:
                logger.info("All processes in lock file are dead, safe to remove lock file")
                self.lock_file.unlink()
                results['stale_locks_removed'] = 1
            else:
                logger.warning(f"Found {results['active_locks_found']} active processes, not removing lock file")

        except Exception as e:
            results['errors'].append(str(e))
            logger.error(f"Lock cleanup failed: {e}")

        return results

    def wait_for_lock_release(self, timeout: int = 60, check_interval: int = 2) -> bool:
        """
        Wait for database lock to be released.

        Args:
            timeout: Maximum time to wait in seconds
            check_interval: How often to check for lock release

        Returns:
            True if lock was released, False if timeout occurred
        """
        logger.info(f"Waiting for database lock release (timeout: {timeout}s)")

        start_time = time.time()

        while time.time() - start_time < timeout:
            if not self.lock_file.exists():
                logger.info("✅ Database lock released")
                return True

            logger.info(f"⏳ Waiting for lock release... ({int(time.time() - start_time)}/{timeout}s)")
            time.sleep(check_interval)

        logger.error(f"Database lock not released within {timeout}s timeout")
        return False

    def get_lock_diagnostics(self) -> Dict[str, Any]:
        """
        Get comprehensive diagnostics about the database lock situation.

        Returns:
            Dictionary with detailed diagnostic information
        """
        diagnostics = {
            'timestamp': time.time(),
            'database_path': str(self.db_path),
            'lock_analysis': self.analyze_lock_situation(),
            'system_processes': self._get_database_related_processes(),
            'file_permissions': self._check_file_permissions(),
            'disk_space': self._check_disk_space()
        }

        return diagnostics

    def _get_database_related_processes(self) -> List[Dict[str, Any]]:
        """Get information about processes that might be accessing the database."""
        db_processes = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'open_files']):
                try:
                    # Check if process has the database file open
                    if proc.info['open_files']:
                        for open_file in proc.info['open_files']:
                            if str(self.db_path) in open_file.path:
                                db_processes.append({
                                    'pid': proc.info['pid'],
                                    'name': proc.info['name'],
                                    'cmdline': proc.info['cmdline'],
                                    'file': open_file.path
                                })
                                break

                    # Also check command line for database references
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if str(self.db_path) in cmdline:
                        if not any(p['pid'] == proc.info['pid'] for p in db_processes):
                            db_processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cmdline': proc.info['cmdline']
                            })

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.warning(f"Failed to get database processes: {e}")

        return db_processes

    def _check_file_permissions(self) -> Dict[str, Any]:
        """Check file permissions for database and lock files."""
        permissions = {}

        for file_path in [self.db_path, self.lock_file]:
            try:
                stat = os.stat(file_path)
                permissions[str(file_path)] = {
                    'readable': os.access(file_path, os.R_OK),
                    'writable': os.access(file_path, os.W_OK),
                    'executable': os.access(file_path, os.X_OK),
                    'mode': oct(stat.st_mode),
                    'uid': stat.st_uid,
                    'gid': stat.st_gid
                }
            except OSError:
                permissions[str(file_path)] = {'error': 'File not accessible'}

        return permissions

    def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space in the database directory."""
        try:
            stat = os.statvfs(self.db_path.parent)
            return {
                'total_bytes': stat.f_blocks * stat.f_frsize,
                'available_bytes': stat.f_available * stat.f_frsize,
                'available_gb': (stat.f_available * stat.f_frsize) / (1024**3)
            }
        except Exception as e:
            return {'error': str(e)}


def get_lock_manager(db_path: str) -> DatabaseLockManager:
    """
    Get a database lock manager instance.

    Args:
        db_path: Path to the DuckDB database file

    Returns:
        DatabaseLockManager instance
    """
    return DatabaseLockManager(db_path)


@contextmanager
def database_lock_context(db_path: str):
    """
    Context manager for database operations with lock handling.

    Usage:
        with database_lock_context('data/financial_data.duckdb') as lock_mgr:
            analysis = lock_mgr.analyze_lock_situation()
            if not analysis['database_accessible']:
                # Handle lock situation
                pass
    """
    lock_manager = get_lock_manager(db_path)
    try:
        yield lock_manager
    finally:
        pass



