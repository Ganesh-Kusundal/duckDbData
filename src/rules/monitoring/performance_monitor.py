#!/usr/bin/env python3
"""
Performance Monitor - Comprehensive Performance Monitoring System

This module provides enterprise-grade performance monitoring for the rule-based
trading system, including real-time metrics, historical analysis, and alerting.
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional, Callable
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
import sqlite3


@dataclass
class PerformanceMetric:
    """Represents a single performance metric."""
    name: str
    value: Any
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleExecutionMetric:
    """Metrics for individual rule execution."""
    rule_id: str
    execution_time: float
    success: bool
    signals_generated: int
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None


@dataclass
class SystemHealthMetric:
    """System health and resource usage metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_connections: int
    active_threads: int
    timestamp: datetime = field(default_factory=datetime.now)


class PerformanceMonitor:
    """Main performance monitoring system."""

    def __init__(self, db_path: str = "performance.db", retention_days: int = 30):
        self.db_path = Path(db_path)
        self.retention_days = retention_days
        self._monitoring_active = False
        self._collection_thread = None

        # In-memory metrics storage
        self.metrics_buffer = deque(maxlen=10000)
        self.rule_metrics = defaultdict(list)
        self.system_metrics = deque(maxlen=1000)

        # Alert thresholds
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'execution_time': 5.0,  # seconds
            'error_rate': 0.05,     # 5%
            'rule_success_rate': 0.7  # 70%
        }

        # Alert callbacks
        self.alert_callbacks: List[Callable] = []

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self._setup_database()

    def _setup_database(self):
        """Initialize the performance database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_metrics (
                    id INTEGER PRIMARY KEY,
                    rule_id TEXT,
                    execution_time REAL,
                    success BOOLEAN,
                    signals_generated INTEGER,
                    error_message TEXT,
                    timestamp TEXT,
                    memory_usage REAL,
                    cpu_usage REAL
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_used_mb REAL,
                    disk_usage_percent REAL,
                    network_connections INTEGER,
                    active_threads INTEGER,
                    timestamp TEXT
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT,
                    rule_id TEXT,
                    value REAL,
                    threshold REAL,
                    timestamp TEXT
                )
            ''')

            # Create indexes for better query performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rule_metrics_rule_id ON rule_metrics(rule_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rule_metrics_timestamp ON rule_metrics(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)')

    def start_monitoring(self):
        """Start the performance monitoring system."""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._collection_thread.start()

        self.logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop the performance monitoring system."""
        self._monitoring_active = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5)

        # Flush remaining metrics to database
        self._flush_metrics_to_db()
        self.logger.info("Performance monitoring stopped")

    def _collection_loop(self):
        """Main monitoring collection loop."""
        while self._monitoring_active:
            try:
                # Collect system metrics
                system_metric = self._collect_system_metrics()
                self.system_metrics.append(system_metric)

                # Check for alerts
                self._check_alerts()

                # Flush metrics to database periodically
                if len(self.metrics_buffer) >= 100:
                    self._flush_metrics_to_db()

                time.sleep(1)  # Collect every second

            except Exception as e:
                self.logger.error(f"Error in monitoring collection loop: {e}")
                time.sleep(5)

    def _collect_system_metrics(self) -> SystemHealthMetric:
        """Collect current system health metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_connections()
        threads = threading.active_count()

        return SystemHealthMetric(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            disk_usage_percent=disk.percent,
            network_connections=len(network),
            active_threads=threads
        )

    def record_rule_execution(self, metric: RuleExecutionMetric):
        """Record a rule execution metric."""
        self.rule_metrics[metric.rule_id].append(metric)

        # Keep only recent metrics (last 1000 per rule)
        if len(self.rule_metrics[metric.rule_id]) > 1000:
            self.rule_metrics[metric.rule_id] = self.rule_metrics[metric.rule_id][-1000:]

        # Store in database
        self._store_rule_metric(metric)

        # Check for rule-specific alerts
        self._check_rule_alerts(metric)

    def _store_rule_metric(self, metric: RuleExecutionMetric):
        """Store rule metric in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO rule_metrics
                    (rule_id, execution_time, success, signals_generated,
                     error_message, timestamp, memory_usage, cpu_usage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metric.rule_id,
                    metric.execution_time,
                    metric.success,
                    metric.signals_generated,
                    metric.error_message,
                    metric.timestamp.isoformat(),
                    metric.memory_usage,
                    metric.cpu_usage
                ))
        except Exception as e:
            self.logger.error(f"Failed to store rule metric: {e}")

    def _store_system_metric(self, metric: SystemHealthMetric):
        """Store system metric in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO system_metrics
                    (cpu_percent, memory_percent, memory_used_mb, disk_usage_percent,
                     network_connections, active_threads, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metric.cpu_percent,
                    metric.memory_percent,
                    metric.memory_used_mb,
                    metric.disk_usage_percent,
                    metric.network_connections,
                    metric.active_threads,
                    metric.timestamp.isoformat()
                ))
        except Exception as e:
            self.logger.error(f"Failed to store system metric: {e}")

    def _flush_metrics_to_db(self):
        """Flush buffered metrics to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store system metrics
                for metric in self.system_metrics:
                    self._store_system_metric(metric)

                # Clear buffers
                self.system_metrics.clear()
                self.metrics_buffer.clear()

        except Exception as e:
            self.logger.error(f"Failed to flush metrics to database: {e}")

    def _check_alerts(self):
        """Check for system-level alerts."""
        if not self.system_metrics:
            return

        latest = self.system_metrics[-1]

        alerts = []

        # CPU usage alert
        if latest.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f'High CPU usage: {latest.cpu_percent:.1f}%',
                'value': latest.cpu_percent,
                'threshold': self.alert_thresholds['cpu_percent']
            })

        # Memory usage alert
        if latest.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'severity': 'critical',
                'message': f'High memory usage: {latest.memory_percent:.1f}%',
                'value': latest.memory_percent,
                'threshold': self.alert_thresholds['memory_percent']
            })

        # Trigger alerts
        for alert in alerts:
            self._trigger_alert(alert)

    def _check_rule_alerts(self, metric: RuleExecutionMetric):
        """Check for rule-specific alerts."""
        alerts = []

        # Execution time alert
        if metric.execution_time > self.alert_thresholds['execution_time']:
            alerts.append({
                'type': 'execution_slow',
                'severity': 'warning',
                'message': f'Slow rule execution: {metric.execution_time:.2f}s',
                'rule_id': metric.rule_id,
                'value': metric.execution_time,
                'threshold': self.alert_thresholds['execution_time']
            })

        # Success rate alert
        rule_metrics = self.rule_metrics[metric.rule_id][-100:]  # Last 100 executions
        if len(rule_metrics) >= 10:
            success_rate = sum(1 for m in rule_metrics if m.success) / len(rule_metrics)
            if success_rate < self.alert_thresholds['rule_success_rate']:
                alerts.append({
                    'type': 'rule_low_success',
                    'severity': 'error',
                    'message': f'Low success rate for {metric.rule_id}: {success_rate:.1f}%',
                    'rule_id': metric.rule_id,
                    'value': success_rate,
                    'threshold': self.alert_thresholds['rule_success_rate']
                })

        # Trigger alerts
        for alert in alerts:
            self._trigger_alert(alert)

    def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger an alert through registered callbacks."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO alerts
                    (alert_type, severity, message, rule_id, value, threshold, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert['type'],
                    alert['severity'],
                    alert['message'],
                    alert.get('rule_id'),
                    alert.get('value'),
                    alert.get('threshold'),
                    datetime.now().isoformat()
                ))

            # Call registered callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback error: {e}")

            self.logger.warning(f"ALERT [{alert['severity'].upper()}]: {alert['message']}")

        except Exception as e:
            self.logger.error(f"Failed to trigger alert: {e}")

    def add_alert_callback(self, callback: Callable):
        """Add an alert callback function."""
        self.alert_callbacks.append(callback)

    def get_rule_performance_summary(self, rule_id: str, days: int = 7) -> Dict[str, Any]:
        """Get performance summary for a specific rule."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT execution_time, success, signals_generated
                    FROM rule_metrics
                    WHERE rule_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                ''', (rule_id, cutoff_date.isoformat()))

                metrics = cursor.fetchall()

            if not metrics:
                return {
                    'rule_id': rule_id,
                    'total_executions': 0,
                    'success_rate': 0.0,
                    'avg_execution_time': 0.0,
                    'avg_signals_per_execution': 0.0,
                    'total_signals': 0
                }

            executions = len(metrics)
            successful = sum(1 for m in metrics if m[1])  # success column
            total_signals = sum(m[2] for m in metrics if m[2])  # signals_generated column
            avg_execution_time = sum(m[0] for m in metrics) / executions

            return {
                'rule_id': rule_id,
                'total_executions': executions,
                'success_rate': successful / executions if executions > 0 else 0,
                'avg_execution_time': avg_execution_time,
                'avg_signals_per_execution': total_signals / executions if executions > 0 else 0,
                'total_signals': total_signals
            }

        except Exception as e:
            self.logger.error(f"Failed to get rule performance summary: {e}")
            return {}

    def get_system_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get system performance summary."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT cpu_percent, memory_percent, memory_used_mb,
                           disk_usage_percent, network_connections, active_threads
                    FROM system_metrics
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                ''', (cutoff_time.isoformat(),))

                metrics = cursor.fetchall()

            if not metrics:
                return {
                    'avg_cpu_percent': 0.0,
                    'avg_memory_percent': 0.0,
                    'peak_memory_mb': 0.0,
                    'avg_disk_usage': 0.0,
                    'avg_network_connections': 0,
                    'avg_active_threads': 0,
                    'data_points': 0
                }

            cpu_avg = sum(m[0] for m in metrics) / len(metrics)
            memory_avg = sum(m[1] for m in metrics) / len(metrics)
            memory_peak = max(m[2] for m in metrics)
            disk_avg = sum(m[3] for m in metrics) / len(metrics)
            network_avg = sum(m[4] for m in metrics) / len(metrics)
            threads_avg = sum(m[5] for m in metrics) / len(metrics)

            return {
                'avg_cpu_percent': cpu_avg,
                'avg_memory_percent': memory_avg,
                'peak_memory_mb': memory_peak,
                'avg_disk_usage': disk_avg,
                'avg_network_connections': network_avg,
                'avg_active_threads': threads_avg,
                'data_points': len(metrics)
            }

        except Exception as e:
            self.logger.error(f"Failed to get system performance summary: {e}")
            return {}

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT alert_type, severity, message, rule_id, value, threshold, timestamp
                    FROM alerts
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

                alerts = []
                for row in cursor.fetchall():
                    alerts.append({
                        'type': row[0],
                        'severity': row[1],
                        'message': row[2],
                        'rule_id': row[3],
                        'value': row[4],
                        'threshold': row[5],
                        'timestamp': row[6]
                    })

                return alerts

        except Exception as e:
            self.logger.error(f"Failed to get recent alerts: {e}")
            return []

    def cleanup_old_data(self):
        """Clean up old performance data based on retention policy."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)

            with sqlite3.connect(self.db_path) as conn:
                # Clean up old rule metrics
                conn.execute('DELETE FROM rule_metrics WHERE timestamp < ?',
                           (cutoff_date.isoformat(),))

                # Clean up old system metrics
                conn.execute('DELETE FROM system_metrics WHERE timestamp < ?',
                           (cutoff_date.isoformat(),))

                # Clean up old alerts (keep alerts for 90 days)
                alert_cutoff = datetime.now() - timedelta(days=90)
                conn.execute('DELETE FROM alerts WHERE timestamp < ?',
                           (alert_cutoff.isoformat(),))

                deleted_count = conn.total_changes
                conn.commit()

            self.logger.info(f"Cleaned up {deleted_count} old performance records")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")

    def export_performance_report(self, output_file: str, days: int = 7):
        """Export comprehensive performance report."""
        try:
            report = {
                'generated_at': datetime.now().isoformat(),
                'period_days': days,
                'system_performance': self.get_system_performance_summary(hours=days*24),
                'rule_performance': {},
                'recent_alerts': self.get_recent_alerts(20),
                'summary': {}
            }

            # Get all unique rule IDs from recent metrics
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT DISTINCT rule_id
                    FROM rule_metrics
                    WHERE timestamp > ?
                ''', ((datetime.now() - timedelta(days=days)).isoformat(),))

                rule_ids = [row[0] for row in cursor.fetchall()]

            # Get performance for each rule
            for rule_id in rule_ids:
                report['rule_performance'][rule_id] = self.get_rule_performance_summary(rule_id, days)

            # Generate summary statistics
            rule_perfs = list(report['rule_performance'].values())
            if rule_perfs:
                total_executions = sum(r['total_executions'] for r in rule_perfs)
                avg_success_rate = sum(r['success_rate'] for r in rule_perfs) / len(rule_perfs)
                avg_execution_time = sum(r['avg_execution_time'] for r in rule_perfs) / len(rule_perfs)
                total_signals = sum(r['total_signals'] for r in rule_perfs)

                report['summary'] = {
                    'total_rules': len(rule_perfs),
                    'total_executions': total_executions,
                    'avg_success_rate': avg_success_rate,
                    'avg_execution_time': avg_execution_time,
                    'total_signals_generated': total_signals
                }

            # Write to file
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Performance report exported to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export performance report: {e}")
            return False
