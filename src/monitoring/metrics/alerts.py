"""
Alerting System for Performance Monitoring
==========================================

This module provides alerting capabilities for performance metrics,
including threshold monitoring, alert generation, and notification management.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import threading
import json

from ..config.database import monitoring_db
from ..config.settings import config
from ..logging import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """Alert rule definition."""
    rule_id: str
    name: str
    description: str
    metric_name: str
    operator: str  # 'gt', 'lt', 'gte', 'lte', 'eq', 'ne'
    threshold: float
    severity: AlertSeverity
    component: str
    enabled: bool = True
    cooldown_minutes: int = 5  # Minimum time between alerts for same rule
    tags: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self, metric_value: float) -> bool:
        """Evaluate if the alert condition is met."""
        if not self.enabled:
            return False

        if self.operator == 'gt':
            return metric_value > self.threshold
        elif self.operator == 'lt':
            return metric_value < self.threshold
        elif self.operator == 'gte':
            return metric_value >= self.threshold
        elif self.operator == 'lte':
            return metric_value <= self.threshold
        elif self.operator == 'eq':
            return metric_value == self.threshold
        elif self.operator == 'ne':
            return metric_value != self.threshold

        return False


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_id: str
    title: str
    message: str
    severity: AlertSeverity
    component: str
    metric_name: str
    threshold_value: float
    actual_value: float
    status: AlertStatus
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """Manages alert rules and alert generation."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._alert_rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_handlers: List[Callable[[Alert], Awaitable[None]]] = []
        self._rule_cooldowns: Dict[str, datetime] = {}
        self._lock = threading.Lock()

        # Initialize default alert rules
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """Initialize default alert rules based on configuration."""
        rules = [
            AlertRule(
                rule_id="cpu_high",
                name="High CPU Usage",
                description="CPU usage exceeded threshold",
                metric_name="cpu_percent",
                operator="gt",
                threshold=config.metrics.cpu_threshold,
                severity=AlertSeverity.HIGH,
                component="system",
                cooldown_minutes=10
            ),
            AlertRule(
                rule_id="memory_high",
                name="High Memory Usage",
                description="Memory usage exceeded threshold",
                metric_name="memory_percent",
                operator="gt",
                threshold=config.metrics.memory_threshold,
                severity=AlertSeverity.HIGH,
                component="system",
                cooldown_minutes=5
            ),
            AlertRule(
                rule_id="disk_high",
                name="High Disk Usage",
                description="Disk usage exceeded threshold",
                metric_name="disk_percent",
                operator="gt",
                threshold=config.metrics.disk_threshold,
                severity=AlertSeverity.MEDIUM,
                component="system",
                cooldown_minutes=60  # Only alert once per hour
            ),
            AlertRule(
                rule_id="db_size_large",
                name="Large Database Size",
                description="Database size exceeds 1GB",
                metric_name="database_size_mb",
                operator="gt",
                threshold=1024,  # 1GB
                severity=AlertSeverity.MEDIUM,
                component="database",
                cooldown_minutes=1440  # Only alert once per day
            )
        ]

        for rule in rules:
            self.add_alert_rule(rule)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            self._alert_rules[rule.rule_id] = rule
            self.logger.info("Added alert rule", extra={
                'rule_id': rule.rule_id,
                'rule_name': rule.name,
                'metric': rule.metric_name,
                'threshold': rule.threshold
            })

    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        with self._lock:
            if rule_id in self._alert_rules:
                del self._alert_rules[rule_id]
                return True
        return False

    def get_alert_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        with self._lock:
            return list(self._alert_rules.values())

    def add_alert_handler(self, handler: Callable[[Alert], Awaitable[None]]) -> None:
        """Add an alert notification handler."""
        self._alert_handlers.append(handler)

    async def evaluate_metric(self, metric_name: str, metric_value: float, component: str = "system") -> None:
        """Evaluate metric against alert rules and generate alerts if needed."""
        triggered_rules = []

        with self._lock:
            for rule in self._alert_rules.values():
                if (rule.metric_name == metric_name and
                    rule.component == component and
                    rule.evaluate(metric_value)):

                    # Check cooldown
                    now = datetime.now()
                    last_alert = self._rule_cooldowns.get(rule.rule_id)
                    if (last_alert and
                        (now - last_alert).seconds < (rule.cooldown_minutes * 60)):
                        continue

                    triggered_rules.append(rule)
                    self._rule_cooldowns[rule.rule_id] = now

        # Generate alerts for triggered rules
        for rule in triggered_rules:
            await self._generate_alert(rule, metric_value)

    async def _generate_alert(self, rule: AlertRule, actual_value: float) -> None:
        """Generate an alert for a triggered rule."""
        alert_id = f"{rule.rule_id}_{int(datetime.now().timestamp())}"

        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            title=f"{rule.name}: {actual_value:.2f} (threshold: {rule.threshold:.2f})",
            message=rule.description,
            severity=rule.severity,
            component=rule.component,
            metric_name=rule.metric_name,
            threshold_value=rule.threshold,
            actual_value=actual_value,
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(),
            tags=rule.tags.copy()
        )

        # Store alert
        self._store_alert(alert)

        # Add to active alerts
        with self._lock:
            self._active_alerts[alert_id] = alert

        # Notify handlers
        for handler in self._alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                self.logger.error("Alert handler failed", extra={
                    'handler': str(handler),
                    'error': str(e),
                    'alert_id': alert_id
                })

        self.logger.warning("Alert generated", extra={
            'alert_id': alert_id,
            'rule_id': rule.rule_id,
            'severity': rule.severity.value,
            'metric': rule.metric_name,
            'value': actual_value,
            'threshold': rule.threshold
        })

    def _store_alert(self, alert: Alert) -> None:
        """Store alert in database."""
        try:
            with monitoring_db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO alerts (
                        alert_type, severity, title, message, component,
                        metric_name, threshold_value, actual_value, status,
                        created_at, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.rule_id,
                    alert.severity.value,
                    alert.title,
                    alert.message,
                    alert.component,
                    alert.metric_name,
                    alert.threshold_value,
                    alert.actual_value,
                    alert.status.value,
                    alert.created_at,
                    json.dumps(alert.tags)
                ))
        except Exception as e:
            self.logger.error("Failed to store alert", extra={
                'alert_id': alert.alert_id,
                'error': str(e)
            })

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = user

                self._update_alert_status(alert)
                return True
        return False

    def resolve_alert(self, alert_id: str, user: str) -> bool:
        """Resolve an alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                alert.resolved_by = user

                self._update_alert_status(alert)
                del self._active_alerts[alert_id]
                return True
        return False

    def _update_alert_status(self, alert: Alert) -> None:
        """Update alert status in database."""
        try:
            with monitoring_db.get_connection() as conn:
                update_fields = ["status = ?"]
                params = [alert.status.value]

                if alert.acknowledged_at:
                    update_fields.append("acknowledged_at = ?")
                    params.append(alert.acknowledged_at)

                if alert.resolved_at:
                    update_fields.append("resolved_at = ?")
                    params.append(alert.resolved_at)

                if alert.acknowledged_by:
                    update_fields.append("acknowledged_by = ?")
                    params.append(alert.acknowledged_by)

                if alert.resolved_by:
                    update_fields.append("resolved_by = ?")
                    params.append(alert.resolved_by)

                query = f"""
                    UPDATE alerts
                    SET {', '.join(update_fields)}
                    WHERE id = (SELECT id FROM alerts WHERE alert_type = ? ORDER BY created_at DESC LIMIT 1)
                """
                params.extend([alert.rule_id])

                conn.execute(query, params)

        except Exception as e:
            self.logger.error("Failed to update alert status", extra={
                'alert_id': alert.alert_id,
                'error': str(e)
            })

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        with self._lock:
            return list(self._active_alerts.values())

    def get_alert_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get alert history."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            with monitoring_db.get_connection() as conn:
                results = conn.execute("""
                    SELECT
                        id,
                        alert_type,
                        severity,
                        title,
                        message,
                        component,
                        metric_name,
                        threshold_value,
                        actual_value,
                        status,
                        created_at,
                        acknowledged_at,
                        resolved_at,
                        acknowledged_by,
                        resolved_by
                    FROM alerts
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 100
                """, [cutoff_date]).fetchall()

            alerts = []
            for row in results:
                alerts.append({
                    'id': row[0],
                    'alert_type': row[1],
                    'severity': row[2],
                    'title': row[3],
                    'message': row[4],
                    'component': row[5],
                    'metric_name': row[6],
                    'threshold_value': row[7],
                    'actual_value': row[8],
                    'status': row[9],
                    'created_at': row[10],
                    'acknowledged_at': row[11],
                    'resolved_at': row[12],
                    'acknowledged_by': row[13],
                    'resolved_by': row[14],
                    'tags': {}  # Default empty tags since not stored in DB
                })

            return alerts

        except Exception as e:
            self.logger.error("Failed to get alert history", extra={'error': str(e)})
            return []

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary for dashboard."""
        active_alerts = self.get_active_alerts()

        # Count by severity
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = 0

        for alert in active_alerts:
            severity_counts[alert.severity.value] += 1

        # Recent alerts (last 24 hours)
        recent_alerts = []
        try:
            with monitoring_db.get_connection() as conn:
                results = conn.execute("""
                    SELECT
                        alert_type,
                        severity,
                        title,
                        created_at
                    FROM alerts
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 10
                """, [datetime.now() - timedelta(hours=24)]).fetchall()

                for row in results:
                    recent_alerts.append({
                        'alert_type': row[0],
                        'severity': row[1],
                        'title': row[2],
                        'created_at': row[3]
                    })

        except Exception as e:
            self.logger.error("Failed to get recent alerts", extra={'error': str(e)})

        return {
            'active_count': len(active_alerts),
            'severity_counts': severity_counts,
            'recent_alerts': recent_alerts,
            'most_common_type': max(severity_counts, key=severity_counts.get) if severity_counts else None
        }


# Global instance will be created when needed
def _get_alert_manager() -> AlertManager:
    """Get the alert manager instance."""
    return AlertManager()
