"""
Performance Metrics Collector
=============================

This module collects system and application performance metrics
including CPU, memory, disk, network, and database performance.
"""

import psutil
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import threading
import platform
import os

from ..config.database import monitoring_db
from ..config.settings import config
from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: Optional[List[float]]  # 1, 5, 15 minute averages
    process_count: int
    thread_count: int
    collected_at: datetime


@dataclass
class DatabaseMetrics:
    """Database performance metrics."""
    connection_count: int
    query_count: int
    cache_hit_ratio: float
    database_size_mb: float
    wal_size_mb: float
    active_transactions: int
    collected_at: datetime


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    active_threads: int
    memory_usage_mb: float
    open_file_descriptors: int
    uptime_seconds: float
    request_count: int
    error_count: int
    collected_at: datetime


class MetricsCollector:
    """Collects and stores performance metrics."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._previous_network = psutil.net_io_counters()
        self._start_time = time.time()
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_collection(self) -> None:
        """Start the metrics collection thread."""
        if self._collection_thread and self._collection_thread.is_alive():
            return

        self._stop_event.clear()
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True
        )
        self._collection_thread.start()

        self.logger.info("Started metrics collection")

    def stop_collection(self) -> None:
        """Stop the metrics collection thread."""
        if self._collection_thread:
            self._stop_event.set()
            self._collection_thread.join(timeout=5)
            self.logger.info("Stopped metrics collection")

    def _collection_loop(self) -> None:
        """Main collection loop."""
        system_interval = config.metrics.system_metrics_interval
        database_interval = config.metrics.database_metrics_interval

        system_last_collect = 0
        database_last_collect = 0

        while not self._stop_event.is_set():
            current_time = time.time()

            # Collect system metrics
            if current_time - system_last_collect >= system_interval:
                try:
                    system_metrics = self.collect_system_metrics()
                    self.store_system_metrics(system_metrics)
                    system_last_collect = current_time
                except Exception as e:
                    self.logger.error("Failed to collect system metrics", extra={'error': str(e)})

            # Collect database metrics
            if current_time - database_last_collect >= database_interval:
                try:
                    db_metrics = self.collect_database_metrics()
                    self.store_database_metrics(db_metrics)
                    database_last_collect = current_time
                except Exception as e:
                    self.logger.error("Failed to collect database metrics", extra={'error': str(e)})

            # Sleep for a short interval
            time.sleep(1)

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory metrics
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)

        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)

        # Network metrics
        current_network = psutil.net_io_counters()
        network_bytes_sent = current_network.bytes_sent - self._previous_network.bytes_sent
        network_bytes_recv = current_network.bytes_recv - self._previous_network.bytes_recv
        self._previous_network = current_network

        # Load average (Unix-like systems)
        load_average = None
        try:
            if platform.system() != 'Windows':
                load_average = list(os.getloadavg())
        except (OSError, AttributeError):
            pass

        # Process information
        process_count = len(psutil.pids())

        # Thread count - sample processes safely to avoid pid=0 issues
        thread_count = 0
        try:
            pids = psutil.pids()
            if pids:
                # Sample up to 10 processes, skipping pid 0 and other system processes
                sample_pids = [pid for pid in pids[:10] if pid > 10]  # Skip system pids
                for pid in sample_pids:
                    try:
                        thread_count += len(psutil.Process(pid).threads())
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except Exception:
            # Fallback to a reasonable estimate
            thread_count = process_count * 2

        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            disk_percent=disk.percent,
            disk_used_gb=disk_used_gb,
            disk_total_gb=disk_total_gb,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            load_average=load_average,
            process_count=process_count,
            thread_count=thread_count,
            collected_at=datetime.now()
        )

    def collect_database_metrics(self) -> DatabaseMetrics:
        """Collect database performance metrics."""
        # Get database stats
        stats = monitoring_db.get_stats()

        # Mock additional metrics (in practice, you'd query DuckDB system tables)
        connection_count = 1  # Would get from connection pool
        query_count = 0  # Would track via hooks
        cache_hit_ratio = 0.85  # Mock value
        active_transactions = 0  # Would get from DuckDB

        # Get database file size
        db_path = config.database.database_path
        database_size_mb = 0.0
        wal_size_mb = 0.0

        if db_path.exists():
            database_size_mb = db_path.stat().st_size / (1024 * 1024)

            # Check for WAL file
            wal_path = db_path.with_suffix('.wal')
            if wal_path.exists():
                wal_size_mb = wal_path.stat().st_size / (1024 * 1024)

        return DatabaseMetrics(
            connection_count=connection_count,
            query_count=query_count,
            cache_hit_ratio=cache_hit_ratio,
            database_size_mb=database_size_mb,
            wal_size_mb=wal_size_mb,
            active_transactions=active_transactions,
            collected_at=datetime.now()
        )

    def collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-specific metrics."""
        # Current process metrics
        process = psutil.Process()
        memory_usage_mb = process.memory_info().rss / (1024 * 1024)

        # Thread and file descriptor counts
        active_threads = threading.active_count()
        open_file_descriptors = 0
        try:
            open_file_descriptors = len(process.open_files())
        except (psutil.AccessDenied, AttributeError):
            pass

        # Uptime
        uptime_seconds = time.time() - self._start_time

        # Mock request/error counts (would be collected via middleware)
        request_count = 0
        error_count = 0

        return ApplicationMetrics(
            active_threads=active_threads,
            memory_usage_mb=memory_usage_mb,
            open_file_descriptors=open_file_descriptors,
            uptime_seconds=uptime_seconds,
            request_count=request_count,
            error_count=error_count,
            collected_at=datetime.now()
        )

    def store_system_metrics(self, metrics: SystemMetrics) -> None:
        """Store system metrics in database."""
        try:
            with monitoring_db.get_connection() as conn:
                host_name = platform.node() or 'localhost'
                # Insert metrics individually to avoid constraint issues
                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'cpu', 'system', ?, ?, ?)
                """, [
                    'cpu_percent', metrics.cpu_percent, host_name, metrics.collected_at,
                    '{"unit": "percent"}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'memory', 'system', ?, ?, ?)
                """, [
                    'memory_percent', metrics.memory_percent, host_name, metrics.collected_at,
                    f'{{"used_gb": {metrics.memory_used_gb}, "total_gb": {metrics.memory_total_gb}}}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'disk', 'system', ?, ?, ?)
                """, [
                    'disk_percent', metrics.disk_percent, host_name, metrics.collected_at,
                    f'{{"used_gb": {metrics.disk_used_gb}, "total_gb": {metrics.disk_total_gb}}}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'network', 'system', ?, ?, ?)
                """, [
                    'network_bytes_sent', metrics.network_bytes_sent, host_name, metrics.collected_at,
                    '{"direction": "sent", "unit": "bytes"}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'network', 'system', ?, ?, ?)
                """, [
                    'network_bytes_recv', metrics.network_bytes_recv, host_name, metrics.collected_at,
                    '{"direction": "received", "unit": "bytes"}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'system', 'system', ?, ?, ?)
                """, [
                    'process_count', metrics.process_count, host_name, metrics.collected_at,
                    '{"type": "process_count"}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'system', 'system', ?, ?, ?)
                """, [
                    'thread_count', metrics.thread_count, host_name, metrics.collected_at,
                    '{"type": "thread_count"}'
                ])

        except Exception as e:
            self.logger.error("Failed to store system metrics", extra={'error': str(e)})

    def store_database_metrics(self, metrics: DatabaseMetrics) -> None:
        """Store database metrics in database."""
        try:
            with monitoring_db.get_connection() as conn:
                host_name = platform.node() or 'localhost'
                # Insert database metrics individually
                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'db_connection', 'database', ?, ?, ?)
                """, [
                    'connection_count', metrics.connection_count, host_name, metrics.collected_at,
                    '{"type": "connections"}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'db_query', 'database', ?, ?, ?)
                """, [
                    'query_count', metrics.query_count, host_name, metrics.collected_at,
                    '{"type": "queries"}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'db_cache', 'database', ?, ?, ?)
                """, [
                    'cache_hit_ratio', metrics.cache_hit_ratio, host_name, metrics.collected_at,
                    '{"unit": "ratio"}'
                ])

                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, 'db_size', 'database', ?, ?, ?)
                """, [
                    'database_size_mb', metrics.database_size_mb, host_name, metrics.collected_at,
                    f'{{"wal_size_mb": {metrics.wal_size_mb}}}'
                ])

        except Exception as e:
            self.logger.error("Failed to store database metrics", extra={'error': str(e)})

    def get_recent_metrics(self, metric_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent metrics of specified type."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with monitoring_db.get_connection() as conn:
                results = conn.execute("""
                    SELECT
                        metric_name,
                        metric_value,
                        metric_type,
                        component,
                        collected_at,
                        tags
                    FROM performance_metrics
                    WHERE metric_type = ? AND collected_at >= ?
                    ORDER BY collected_at DESC
                    LIMIT 1000
                """, [metric_type, cutoff_time]).fetchall()

            metrics = []
            for row in results:
                metrics.append({
                    'metric_name': row[0],
                    'metric_value': row[1],
                    'metric_type': row[2],
                    'component': row[3],
                    'collected_at': row[4],
                    'tags': row[5] if row[5] else {}
                })

            return metrics

        except Exception as e:
            self.logger.error("Failed to get recent metrics", extra={
                'error': str(e),
                'metric_type': metric_type
            })
            return []

    def get_metric_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for dashboard."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with monitoring_db.get_connection() as conn:
                # CPU metrics
                cpu_results = conn.execute("""
                    SELECT
                        AVG(metric_value) as avg_value,
                        MAX(metric_value) as max_value,
                        MIN(metric_value) as min_value
                    FROM performance_metrics
                    WHERE metric_name = 'cpu_percent'
                    AND collected_at >= ?
                """, [cutoff_time]).fetchone()

                # Memory metrics
                memory_results = conn.execute("""
                    SELECT
                        AVG(metric_value) as avg_value,
                        MAX(metric_value) as max_value,
                        MIN(metric_value) as min_value
                    FROM performance_metrics
                    WHERE metric_name = 'memory_percent'
                    AND collected_at >= ?
                """, [cutoff_time]).fetchone()

                # Database size
                db_size_results = conn.execute("""
                    SELECT
                        MAX(metric_value) as current_size,
                        AVG(metric_value) as avg_size
                    FROM performance_metrics
                    WHERE metric_name = 'database_size_mb'
                    AND collected_at >= ?
                """, [cutoff_time]).fetchone()

            return {
                'cpu': {
                    'avg_percent': cpu_results[0] if cpu_results and cpu_results[0] else 0.0,
                    'max_percent': cpu_results[1] if cpu_results and cpu_results[1] else 0.0,
                    'min_percent': cpu_results[2] if cpu_results and cpu_results[2] else 0.0
                },
                'memory': {
                    'avg_percent': memory_results[0] if memory_results and memory_results[0] else 0.0,
                    'max_percent': memory_results[1] if memory_results and memory_results[1] else 0.0,
                    'min_percent': memory_results[2] if memory_results and memory_results[2] else 0.0
                },
                'database': {
                    'current_size_mb': db_size_results[0] if db_size_results and db_size_results[0] else 0.0,
                    'avg_size_mb': db_size_results[1] if db_size_results and db_size_results[1] else 0.0
                },
                'time_range': f'last {hours} hours'
            }

        except Exception as e:
            self.logger.error("Failed to get metric summary", extra={'error': str(e)})
            return {
                'cpu': {'avg_percent': 0.0, 'max_percent': 0.0, 'min_percent': 0.0},
                'memory': {'avg_percent': 0.0, 'max_percent': 0.0, 'min_percent': 0.0},
                'database': {'current_size_mb': 0.0, 'avg_size_mb': 0.0}
            }


# Global instance
metrics_collector = MetricsCollector()
