#!/usr/bin/env python3
"""
Broker Health Monitor for DhanHQ Integration

This module provides comprehensive monitoring and health checking capabilities
for DhanHQ broker connections, including real-time status monitoring, alerting,
and performance metrics collection.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from infrastructure.adapters.dhan_broker_adapter import DhanBrokerAdapter
from infrastructure.external.broker_integration_adapter import get_broker_integration_manager
from infrastructure.monitoring.metrics_collector import get_metrics_collector
from domain.broker_integration.services.sync_verification_service import (
    get_sync_verification_service, SyncVerificationType
)

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthMetric:
    """Health metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


@dataclass
class HealthAlert:
    """Health alert information."""
    alert_id: str
    connection_id: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    details: Dict[str, Any] = None

    def resolve(self):
        """Mark alert as resolved."""
        self.resolved = True
        self.resolved_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'connection_id': self.connection_id,
            'severity': self.severity.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'details': self.details or {}
        }


@dataclass
class ConnectionHealth:
    """Connection health status."""
    connection_id: str
    status: HealthStatus
    last_check: datetime
    response_time_ms: Optional[float]
    error_message: Optional[str]
    metrics: Dict[str, Any]

    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return self.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'status': self.status.value,
            'last_check': self.last_check.isoformat(),
            'response_time_ms': self.response_time_ms,
            'error_message': self.error_message,
            'metrics': self.metrics
        }


class BrokerHealthMonitor:
    """
    Comprehensive health monitor for DhanHQ broker connections.

    Features:
    - Real-time health checking
    - Performance metrics collection
    - Alert generation and management
    - Connection status monitoring
    - Automated recovery suggestions
    """

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds
        self.metrics_collector = get_metrics_collector()
        self.broker_manager = get_broker_integration_manager()
        self.sync_verifier = get_sync_verification_service()

        # Health state
        self.connection_health: Dict[str, ConnectionHealth] = {}
        self.active_alerts: Dict[str, HealthAlert] = {}
        self.health_history: List[HealthMetric] = []
        self.alert_history: List[HealthAlert] = []

        # Monitoring tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._alerting_task: Optional[asyncio.Task] = None
        self._is_monitoring = False

        # Alert callbacks
        self._alert_callbacks: List[Callable[[HealthAlert], None]] = []

        # Health thresholds
        self.thresholds = {
            'max_response_time_ms': 5000,  # 5 seconds
            'max_error_rate': 0.1,  # 10%
            'min_sync_consistency': 0.8,  # 80%
            'max_consecutive_failures': 3
        }

        logger.info("BrokerHealthMonitor initialized")

    async def start_monitoring(self):
        """Start the health monitoring process."""
        if self._is_monitoring:
            logger.warning("Health monitoring already running")
            return

        self._is_monitoring = True
        logger.info("Starting broker health monitoring")

        # Start monitoring tasks
        self._monitoring_task = asyncio.create_task(self._health_check_loop())
        self._alerting_task = asyncio.create_task(self._alert_check_loop())

    async def stop_monitoring(self):
        """Stop the health monitoring process."""
        if not self._is_monitoring:
            return

        self._is_monitoring = False
        logger.info("Stopping broker health monitoring")

        # Cancel monitoring tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._alerting_task:
            self._alerting_task.cancel()

        # Wait for tasks to complete
        try:
            if self._monitoring_task:
                await self._monitoring_task
            if self._alerting_task:
                await self._alerting_task
        except asyncio.CancelledError:
            pass

    async def _health_check_loop(self):
        """Main health check loop."""
        while self._is_monitoring:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(self.check_interval)

    async def _alert_check_loop(self):
        """Alert checking and management loop."""
        while self._is_monitoring:
            try:
                await self._check_alerts()
                await asyncio.sleep(30)  # Check alerts every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert check loop error: {e}")
                await asyncio.sleep(30)

    async def _perform_health_checks(self):
        """Perform health checks on all active connections."""
        active_connections = self.broker_manager.get_connected_brokers()

        for connection_id in active_connections:
            try:
                health = await self._check_connection_health(connection_id)
                self.connection_health[connection_id] = health

                # Record metrics
                self._record_health_metrics(health)

                # Check for alerts
                await self._evaluate_health_alerts(health)

            except Exception as e:
                logger.error(f"Health check failed for {connection_id}: {e}")
                # Create unhealthy status
                health = ConnectionHealth(
                    connection_id=connection_id,
                    status=HealthStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    response_time_ms=None,
                    error_message=str(e),
                    metrics={}
                )
                self.connection_health[connection_id] = health
                await self._evaluate_health_alerts(health)

    async def _check_connection_health(self, connection_id: str) -> ConnectionHealth:
        """Check health of a specific connection."""
        start_time = time.time()

        try:
            # Get adapter for this connection
            adapter = self.broker_manager.adapters.get(connection_id)
            if not adapter:
                return ConnectionHealth(
                    connection_id=connection_id,
                    status=HealthStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    response_time_ms=None,
                    error_message="Adapter not found",
                    metrics={}
                )

            # Perform health check
            health_result = await adapter.health_check()
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Determine health status
            if health_result.get('status') == 'healthy':
                status = HealthStatus.HEALTHY
                error_message = None
            elif health_result.get('status') == 'degraded':
                status = HealthStatus.DEGRADED
                error_message = health_result.get('error')
            else:
                status = HealthStatus.UNHEALTHY
                error_message = health_result.get('error', 'Unknown error')

            # Collect additional metrics
            metrics = {
                'account_balance': health_result.get('account_balance'),
                'response_time_ms': response_time,
                'health_status': health_result.get('status'),
                'last_check': datetime.now().isoformat()
            }

            return ConnectionHealth(
                connection_id=connection_id,
                status=status,
                last_check=datetime.now(),
                response_time_ms=response_time,
                error_message=error_message,
                metrics=metrics
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectionHealth(
                connection_id=connection_id,
                status=HealthStatus.CRITICAL,
                last_check=datetime.now(),
                response_time_ms=response_time,
                error_message=str(e),
                metrics={}
            )

    def _record_health_metrics(self, health: ConnectionHealth):
        """Record health metrics."""
        # Record response time
        if health.response_time_ms is not None:
            metric = HealthMetric(
                name="broker_response_time_ms",
                value=health.response_time_ms,
                timestamp=health.last_check,
                tags={"connection_id": health.connection_id}
            )
            self.health_history.append(metric)
            self.metrics_collector.record_metric(
                "broker.health.response_time",
                health.response_time_ms,
                {"connection_id": health.connection_id}
            )

        # Record health status as gauge
        status_value = {
            HealthStatus.HEALTHY: 1,
            HealthStatus.DEGRADED: 0.5,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.CRITICAL: -1,
            HealthStatus.UNKNOWN: -2
        }.get(health.status, -2)

        self.metrics_collector.record_gauge(
            "broker.health.status",
            status_value,
            {"connection_id": health.connection_id}
        )

    async def _evaluate_health_alerts(self, health: ConnectionHealth):
        """Evaluate health status and generate alerts if needed."""
        connection_id = health.connection_id

        # Check response time threshold
        if (health.response_time_ms and
            health.response_time_ms > self.thresholds['max_response_time_ms']):
            await self._create_alert(
                connection_id=connection_id,
                severity=AlertSeverity.WARNING,
                message=f"High response time: {health.response_time_ms:.0f}ms",
                details={
                    'response_time_ms': health.response_time_ms,
                    'threshold_ms': self.thresholds['max_response_time_ms']
                }
            )

        # Check unhealthy status
        if health.status == HealthStatus.UNHEALTHY:
            await self._create_alert(
                connection_id=connection_id,
                severity=AlertSeverity.ERROR,
                message=f"Broker connection unhealthy: {health.error_message}",
                details=health.to_dict()
            )

        # Check critical status
        if health.status == HealthStatus.CRITICAL:
            await self._create_alert(
                connection_id=connection_id,
                severity=AlertSeverity.CRITICAL,
                message=f"Broker connection critical: {health.error_message}",
                details=health.to_dict()
            )

    async def _create_alert(self, connection_id: str, severity: AlertSeverity,
                          message: str, details: Dict[str, Any]):
        """Create a new health alert."""
        alert_id = f"alert_{connection_id}_{int(datetime.now().timestamp())}"

        # Check if similar alert already exists
        existing_alert = self._find_similar_alert(connection_id, message)
        if existing_alert:
            logger.debug(f"Similar alert already exists: {alert_id}")
            return

        alert = HealthAlert(
            alert_id=alert_id,
            connection_id=connection_id,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            details=details
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        logger.warning(f"Health alert created: {alert_id} - {message}")

        # Notify alert callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    async def _check_alerts(self):
        """Check and resolve alerts based on current health status."""
        alerts_to_resolve = []

        for alert_id, alert in self.active_alerts.items():
            if alert.resolved:
                continue

            # Get current health status
            health = self.connection_health.get(alert.connection_id)
            if not health:
                continue

            # Resolve alerts based on health status
            should_resolve = False

            if "response time" in alert.message.lower():
                if (health.response_time_ms and
                    health.response_time_ms <= self.thresholds['max_response_time_ms']):
                    should_resolve = True

            elif "unhealthy" in alert.message.lower():
                if health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                    should_resolve = True

            if should_resolve:
                alert.resolve()
                logger.info(f"Alert resolved: {alert_id}")
                alerts_to_resolve.append(alert_id)

        # Clean up resolved alerts after some time
        for alert_id in alerts_to_resolve:
            # Keep resolved alerts for 1 hour before cleanup
            if (datetime.now() - self.active_alerts[alert_id].resolved_at) > timedelta(hours=1):
                del self.active_alerts[alert_id]

    def _find_similar_alert(self, connection_id: str, message: str) -> Optional[HealthAlert]:
        """Find similar active alert."""
        for alert in self.active_alerts.values():
            if (alert.connection_id == connection_id and
                alert.message == message and
                not alert.resolved):
                return alert
        return None

    def add_alert_callback(self, callback: Callable[[HealthAlert], None]):
        """Add callback for alert notifications."""
        self._alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable[[HealthAlert], None]):
        """Remove alert callback."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)

    def get_connection_health(self, connection_id: str) -> Optional[ConnectionHealth]:
        """Get health status for a specific connection."""
        return self.connection_health.get(connection_id)

    def get_all_connection_health(self) -> Dict[str, ConnectionHealth]:
        """Get health status for all connections."""
        return self.connection_health.copy()

    def get_active_alerts(self, connection_id: Optional[str] = None) -> List[HealthAlert]:
        """Get active alerts, optionally filtered by connection."""
        alerts = [alert for alert in self.active_alerts.values() if not alert.resolved]

        if connection_id:
            alerts = [alert for alert in alerts if alert.connection_id == connection_id]

        return alerts

    def get_alert_history(self, connection_id: Optional[str] = None,
                         hours: int = 24) -> List[HealthAlert]:
        """Get alert history, optionally filtered by connection and time."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        alerts = [alert for alert in self.alert_history
                 if alert.timestamp >= cutoff_time]

        if connection_id:
            alerts = [alert for alert in alerts if alert.connection_id == connection_id]

        return alerts

    def get_health_metrics(self, connection_id: Optional[str] = None,
                          hours: int = 24) -> List[HealthMetric]:
        """Get health metrics history."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        metrics = [metric for metric in self.health_history
                  if metric.timestamp >= cutoff_time]

        if connection_id:
            metrics = [metric for metric in metrics
                      if metric.tags.get('connection_id') == connection_id]

        return metrics

    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        total_connections = len(self.connection_health)
        healthy_connections = len([h for h in self.connection_health.values() if h.is_healthy()])
        active_alerts = len([a for a in self.active_alerts.values() if not a.resolved])

        overall_status = HealthStatus.HEALTHY
        if active_alerts > 0:
            overall_status = HealthStatus.DEGRADED
        if healthy_connections == 0 and total_connections > 0:
            overall_status = HealthStatus.CRITICAL

        return {
            'overall_status': overall_status.value,
            'total_connections': total_connections,
            'healthy_connections': healthy_connections,
            'active_alerts': active_alerts,
            'last_check': datetime.now().isoformat(),
            'connections': {cid: health.to_dict() for cid, health in self.connection_health.items()}
        }

    async def perform_sync_verification(self, connection_id: str) -> Dict[str, Any]:
        """Perform sync verification for a connection."""
        try:
            result = await self.sync_verifier.verify_full_sync_integrity(connection_id)

            # Create alert if sync verification fails
            if not result.is_successful():
                await self._create_alert(
                    connection_id=connection_id,
                    severity=AlertSeverity.ERROR,
                    message=f"Sync verification failed: {len(result.issues_found)} issues found",
                    details=result.get_summary()
                )

            return result.get_summary()

        except Exception as e:
            logger.error(f"Sync verification failed for {connection_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global broker health monitor instance
_broker_health_monitor: Optional[BrokerHealthMonitor] = None


def get_broker_health_monitor() -> BrokerHealthMonitor:
    """Get global broker health monitor instance."""
    global _broker_health_monitor
    if _broker_health_monitor is None:
        _broker_health_monitor = BrokerHealthMonitor()
    return _broker_health_monitor


def reset_broker_health_monitor():
    """Reset global broker health monitor (mainly for testing)."""
    global _broker_health_monitor
    _broker_health_monitor = None
