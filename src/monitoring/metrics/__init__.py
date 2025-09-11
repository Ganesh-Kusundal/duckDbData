"""
Metrics Package
===============

This package provides comprehensive performance monitoring capabilities:
- System and database metrics collection
- Alerting system with configurable rules
- Metrics storage and retrieval with aggregation
- Real-time performance monitoring
"""

from .collector import (
    MetricsCollector,
    SystemMetrics,
    DatabaseMetrics,
    ApplicationMetrics,
    metrics_collector
)
from .alerts import (
    AlertManager,
    AlertRule,
    Alert,
    AlertSeverity,
    AlertStatus
)
from .storage import (
    MetricsStorage,
    MetricData,
    metrics_storage
)

def _get_alert_manager():
    """Get alert manager instance."""
    from .alerts import _get_alert_manager
    return _get_alert_manager()

# For backward compatibility
alert_manager = _get_alert_manager()

__all__ = [
    # Collector
    'MetricsCollector',
    'SystemMetrics',
    'DatabaseMetrics',
    'ApplicationMetrics',
    'metrics_collector',

    # Alerts
    'AlertManager',
    'AlertRule',
    'Alert',
    'AlertSeverity',
    'AlertStatus',
    'alert_manager',

    # Storage
    'MetricsStorage',
    'MetricData',
    'metrics_storage'
]
