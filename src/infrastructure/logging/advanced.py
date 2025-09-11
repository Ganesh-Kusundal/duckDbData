"""
Advanced Logging and Monitoring
==============================

Enhanced logging with metrics integration, alerting, and performance monitoring.
"""

import logging
import time
import threading
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import structlog

from . import get_logger

logger = get_logger(__name__)


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime
    level: str
    logger: str
    message: str
    context: Dict[str, Any]
    performance_data: Optional[Dict[str, Any]] = None


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    condition: Callable[[LogEntry], bool]
    severity: str
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None


class AdvancedLogger:
    """
    Advanced logger with metrics and alerting capabilities.
    """

    def __init__(self):
        self.entries: List[LogEntry] = []
        self.alert_rules: List[AlertRule] = []
        self.performance_metrics: Dict[str, Any] = {}
        self.max_entries = 10000
        self.lock = threading.Lock()

        # Start performance monitoring
        self._start_performance_monitoring()

    def log_with_metrics(self,
                        level: str,
                        message: str,
                        context: Optional[Dict[str, Any]] = None,
                        logger_name: str = "advanced") -> None:
        """
        Log message with performance metrics.

        Args:
            level: Log level
            message: Log message
            context: Additional context
            logger_name: Logger name
        """
        # Collect performance metrics
        metrics = self._collect_performance_metrics()

        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level.upper(),
            logger=logger_name,
            message=message,
            context=context or {},
            performance_data=metrics
        )

        # Store entry
        with self.lock:
            self.entries.append(entry)
            if len(self.entries) > self.max_entries:
                self.entries.pop(0)

        # Check alert rules
        self._check_alerts(entry)

        # Log with structured format
        log_data = {
            'timestamp': entry.timestamp.isoformat(),
            'level': entry.level,
            'logger': entry.logger,
            'message': entry.message,
            'context': entry.context,
            'performance': entry.performance_data
        }

        # Use appropriate logging level
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message, **log_data)

    def add_alert_rule(self,
                      name: str,
                      condition: Callable[[LogEntry], bool],
                      severity: str = "WARNING",
                      cooldown_minutes: int = 5) -> None:
        """
        Add alert rule.

        Args:
            name: Alert rule name
            condition: Function that returns True if alert should trigger
            severity: Alert severity (INFO, WARNING, ERROR, CRITICAL)
            cooldown_minutes: Minutes to wait before triggering same alert
        """
        rule = AlertRule(
            name=name,
            condition=condition,
            severity=severity,
            cooldown_minutes=cooldown_minutes
        )

        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {name}")

    def _check_alerts(self, entry: LogEntry) -> None:
        """Check if any alert rules should trigger."""
        for rule in self.alert_rules:
            try:
                # Check cooldown
                if rule.last_triggered:
                    time_since_last = datetime.now() - rule.last_triggered
                    if time_since_last < timedelta(minutes=rule.cooldown_minutes):
                        continue

                # Check condition
                if rule.condition(entry):
                    rule.last_triggered = datetime.now()
                    self._trigger_alert(rule, entry)

            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")

    def _trigger_alert(self, rule: AlertRule, entry: LogEntry) -> None:
        """Trigger alert for rule."""
        alert_message = f"ALERT [{rule.severity}]: {rule.name} - {entry.message}"

        # Log alert
        self.log_with_metrics(
            "warning",
            alert_message,
            {
                'alert_rule': rule.name,
                'alert_severity': rule.severity,
                'triggered_by': entry.logger
            },
            "alerts"
        )

        # Could send email, Slack, etc. here
        logger.warning(alert_message)

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
            return {}

    def _start_performance_monitoring(self) -> None:
        """Start background performance monitoring."""
        def monitor_performance():
            while True:
                try:
                    metrics = self._collect_performance_metrics()
                    self.performance_metrics = metrics

                    # Check for performance alerts
                    if metrics.get('cpu_percent', 0) > 90:
                        self.log_with_metrics(
                            "warning",
                            "High CPU usage detected",
                            {'cpu_percent': metrics['cpu_percent']},
                            "performance"
                        )

                    if metrics.get('memory_percent', 0) > 90:
                        self.log_with_metrics(
                            "warning",
                            "High memory usage detected",
                            {'memory_percent': metrics['memory_percent']},
                            "performance"
                        )

                    time.sleep(60)  # Check every minute

                except Exception as e:
                    logger.error(f"Performance monitoring error: {e}")
                    time.sleep(60)

        # Start monitoring thread
        thread = threading.Thread(target=monitor_performance, daemon=True)
        thread.start()

    def get_recent_entries(self,
                          level: Optional[str] = None,
                          logger_name: Optional[str] = None,
                          limit: int = 100) -> List[LogEntry]:
        """
        Get recent log entries with optional filtering.

        Args:
            level: Filter by log level
            logger_name: Filter by logger name
            limit: Maximum entries to return

        Returns:
            List of log entries
        """
        with self.lock:
            entries = self.entries.copy()

        # Apply filters
        if level:
            entries = [e for e in entries if e.level == level.upper()]
        if logger_name:
            entries = [e for e in entries if e.logger == logger_name]

        return entries[-limit:]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        return {
            'current_metrics': self.performance_metrics,
            'alert_rules_count': len(self.alert_rules),
            'total_log_entries': len(self.entries),
            'active_monitoring': True
        }

    def export_logs(self,
                   filepath: str,
                   format: str = "json",
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> None:
        """
        Export logs to file.

        Args:
            filepath: Export file path
            format: Export format (json, csv)
            start_time: Start time filter
            end_time: End time filter
        """
        with self.lock:
            entries = self.entries.copy()

        # Apply time filters
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        # Export based on format
        if format.lower() == "json":
            self._export_json(filepath, entries)
        elif format.lower() == "csv":
            self._export_csv(filepath, entries)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self, filepath: str, entries: List[LogEntry]) -> None:
        """Export logs as JSON."""
        data = []
        for entry in entries:
            data.append({
                'timestamp': entry.timestamp.isoformat(),
                'level': entry.level,
                'logger': entry.logger,
                'message': entry.message,
                'context': entry.context,
                'performance_data': entry.performance_data
            })

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def _export_csv(self, filepath: str, entries: List[LogEntry]) -> None:
        """Export logs as CSV."""
        import csv

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'level', 'logger', 'message',
                'context', 'cpu_percent', 'memory_percent'
            ])

            for entry in entries:
                perf = entry.performance_data or {}
                writer.writerow([
                    entry.timestamp.isoformat(),
                    entry.level,
                    entry.logger,
                    entry.message,
                    json.dumps(entry.context),
                    perf.get('cpu_percent', ''),
                    perf.get('memory_percent', '')
                ])


# Global advanced logger instance
advanced_logger = AdvancedLogger()


def get_advanced_logger() -> AdvancedLogger:
    """Get the global advanced logger instance."""
    return advanced_logger


# Convenience functions for easy logging
def log_performance(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Log performance-related message."""
    advanced_logger.log_with_metrics("info", message, context, "performance")


def log_error_with_context(message: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Log error with context and performance data."""
    context = context or {}
    context['error_type'] = type(error).__name__
    context['error_message'] = str(error)

    advanced_logger.log_with_metrics("error", message, context, "errors")


def setup_performance_alerts() -> None:
    """Set up default performance alert rules."""
    # High CPU usage alert
    advanced_logger.add_alert_rule(
        name="high_cpu_usage",
        condition=lambda entry: (
            entry.performance_data and
            entry.performance_data.get('cpu_percent', 0) > 90
        ),
        severity="WARNING",
        cooldown_minutes=10
    )

    # High memory usage alert
    advanced_logger.add_alert_rule(
        name="high_memory_usage",
        condition=lambda entry: (
            entry.performance_data and
            entry.performance_data.get('memory_percent', 0) > 90
        ),
        severity="WARNING",
        cooldown_minutes=10
    )

    # Database connection errors
    advanced_logger.add_alert_rule(
        name="database_connection_error",
        condition=lambda entry: (
            'connection' in entry.message.lower() and
            entry.level == 'ERROR'
        ),
        severity="ERROR",
        cooldown_minutes=5
    )

    logger.info("Performance alert rules configured")
