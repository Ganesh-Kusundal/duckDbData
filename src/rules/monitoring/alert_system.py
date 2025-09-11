#!/usr/bin/env python3
"""
Alert System - Comprehensive Alerting and Notification System

This module provides a flexible alerting system that can send notifications
through various channels (email, Slack, webhooks, etc.) based on performance
metrics and system health.
"""

import json
import smtplib
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging


@dataclass
class AlertConfig:
    """Configuration for alert channels."""
    email_enabled: bool = False
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: List[str] = None

    slack_enabled: bool = False
    slack_webhook_url: str = ""
    slack_channel: str = "#alerts"

    webhook_enabled: bool = False
    webhook_urls: List[str] = None

    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []
        if self.webhook_urls is None:
            self.webhook_urls = []


class AlertChannel:
    """Base class for alert channels."""

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send an alert through this channel."""
        raise NotImplementedError

    def format_alert_message(self, alert: Dict[str, Any]) -> str:
        """Format alert for this channel."""
        severity_emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }

        emoji = severity_emoji.get(alert.get('severity', 'info'), 'ℹ️')

        message = f"{emoji} **{alert['severity'].upper()} ALERT**\n\n"
        message += f"**Type:** {alert['type']}\n"
        message += f"**Message:** {alert['message']}\n"

        if alert.get('rule_id'):
            message += f"**Rule ID:** {alert['rule_id']}\n"

        if alert.get('value') is not None:
            message += f"**Value:** {alert['value']:.2f}\n"

        if alert.get('threshold') is not None:
            message += f"**Threshold:** {alert['threshold']:.2f}\n"

        message += f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return message


class EmailAlertChannel(AlertChannel):
    """Email alert channel."""

    def __init__(self, config: AlertConfig):
        self.config = config

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert via email."""
        if not self.config.email_enabled or not self.config.email_recipients:
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_username
            msg['To'] = ', '.join(self.config.email_recipients)
            msg['Subject'] = f"Trading System Alert: {alert['type']} - {alert['severity'].upper()}"

            body = self.format_alert_message(alert)
            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_username, self.config.email_password)
            text = msg.as_string()
            server.sendmail(self.config.email_username, self.config.email_recipients, text)
            server.quit()

            return True

        except Exception as e:
            logging.error(f"Failed to send email alert: {e}")
            return False


class SlackAlertChannel(AlertChannel):
    """Slack alert channel."""

    def __init__(self, config: AlertConfig):
        self.config = config

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert via Slack webhook."""
        if not self.config.slack_enabled or not self.config.slack_webhook_url:
            return False

        try:
            payload = {
                "channel": self.config.slack_channel,
                "username": "Trading System Monitor",
                "text": self.format_alert_message(alert),
                "icon_emoji": ":chart_with_upwards_trend:"
            }

            response = requests.post(
                self.config.slack_webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )

            return response.status_code == 200

        except Exception as e:
            logging.error(f"Failed to send Slack alert: {e}")
            return False


class WebhookAlertChannel(AlertChannel):
    """Webhook alert channel."""

    def __init__(self, config: AlertConfig):
        self.config = config

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert via webhooks."""
        if not self.config.webhook_enabled or not self.config.webhook_urls:
            return False

        success_count = 0

        for webhook_url in self.config.webhook_urls:
            try:
                payload = {
                    "alert_type": alert['type'],
                    "severity": alert['severity'],
                    "message": alert['message'],
                    "rule_id": alert.get('rule_id'),
                    "value": alert.get('value'),
                    "threshold": alert.get('threshold'),
                    "timestamp": datetime.now().isoformat(),
                    "source": "trading_system_monitor"
                }

                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

                if response.status_code == 200:
                    success_count += 1

            except Exception as e:
                logging.error(f"Failed to send webhook alert to {webhook_url}: {e}")

        return success_count > 0


class ConsoleAlertChannel(AlertChannel):
    """Console alert channel for development and debugging."""

    def __init__(self, config: AlertConfig = None):
        """Initialize console alert channel."""
        self.config = config or AlertConfig()

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Print alert to console."""
        message = self.format_alert_message(alert)
        print(f"\n{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        return True


class AlertManager:
    """Main alert management system."""

    def __init__(self, config: AlertConfig):
        self.config = config
        self.channels: List[AlertChannel] = []
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_filters: Dict[str, datetime] = {}  # Prevent alert spam

        # Setup channels
        self._setup_channels()

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def _setup_channels(self):
        """Setup alert channels based on configuration."""
        self.channels = []

        # Always add console channel for logging
        self.channels.append(ConsoleAlertChannel(self.config))

        # Add configured channels
        if self.config.email_enabled:
            self.channels.append(EmailAlertChannel(self.config))

        if self.config.slack_enabled:
            self.channels.append(SlackAlertChannel(self.config))

        if self.config.webhook_enabled:
            self.channels.append(WebhookAlertChannel(self.config))

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send an alert through all configured channels."""
        # Check if we should filter this alert to prevent spam
        if self._should_filter_alert(alert):
            return True

        success_count = 0

        # Send through all channels
        for channel in self.channels:
            try:
                if channel.send_alert(alert):
                    success_count += 1
            except Exception as e:
                self.logger.error(f"Alert channel error: {e}")

        # Record alert in history
        alert_record = alert.copy()
        alert_record['timestamp'] = datetime.now()
        alert_record['channels_sent'] = success_count
        self.alert_history.append(alert_record)

        # Keep only recent alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]

        return success_count > 0

    def _should_filter_alert(self, alert: Dict[str, Any]) -> bool:
        """Check if alert should be filtered to prevent spam."""
        alert_key = f"{alert['type']}_{alert.get('rule_id', 'system')}"
        now = datetime.now()

        # If we've sent this alert type recently (within 5 minutes), filter it
        if alert_key in self.alert_filters:
            last_sent = self.alert_filters[alert_key]
            if (now - last_sent).total_seconds() < 300:  # 5 minutes
                return True

        # Update filter timestamp
        self.alert_filters[alert_key] = now

        # Clean up old filter entries
        cutoff_time = now.replace(minute=now.minute - 10)  # Keep last 10 minutes
        self.alert_filters = {
            k: v for k, v in self.alert_filters.items()
            if v > cutoff_time
        }

        return False

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alert history."""
        return self.alert_history[-limit:] if self.alert_history else []

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics."""
        if not self.alert_history:
            return {
                'total_alerts': 0,
                'critical_count': 0,
                'warning_count': 0,
                'error_count': 0,
                'info_count': 0,
                'alerts_by_severity': {},
                'alerts_by_type': {},
                'recent_alerts': []
            }

        # Count by severity
        severity_count = {}
        type_count = {}

        for alert in self.alert_history:
            severity = alert.get('severity', 'unknown')
            alert_type = alert.get('type', 'unknown')

            severity_count[severity] = severity_count.get(severity, 0) + 1
            type_count[alert_type] = type_count.get(alert_type, 0) + 1

        return {
            'total_alerts': len(self.alert_history),
            'critical_count': severity_count.get('critical', 0),
            'warning_count': severity_count.get('warning', 0),
            'error_count': severity_count.get('error', 0),
            'info_count': severity_count.get('info', 0),
            'alerts_by_severity': severity_count,
            'alerts_by_type': type_count,
            'recent_alerts': self.get_alert_history(10)
        }


class AlertTemplates:
    """Pre-defined alert templates for common scenarios."""

    @staticmethod
    def high_cpu_usage(cpu_percent: float, threshold: float = 80.0) -> Dict[str, Any]:
        """Template for high CPU usage alerts."""
        return {
            'type': 'system_cpu_high',
            'severity': 'warning',
            'message': f'System CPU usage is high: {cpu_percent:.1f}% (threshold: {threshold:.1f}%)',
            'value': cpu_percent,
            'threshold': threshold
        }

    @staticmethod
    def high_memory_usage(memory_percent: float, threshold: float = 85.0) -> Dict[str, Any]:
        """Template for high memory usage alerts."""
        return {
            'type': 'system_memory_high',
            'severity': 'critical',
            'message': f'System memory usage is high: {memory_percent:.1f}% (threshold: {threshold:.1f}%)',
            'value': memory_percent,
            'threshold': threshold
        }

    @staticmethod
    def slow_rule_execution(rule_id: str, execution_time: float, threshold: float = 5.0) -> Dict[str, Any]:
        """Template for slow rule execution alerts."""
        return {
            'type': 'rule_execution_slow',
            'severity': 'warning',
            'message': f'Rule {rule_id} execution is slow: {execution_time:.2f}s (threshold: {threshold:.1f}s)',
            'rule_id': rule_id,
            'value': execution_time,
            'threshold': threshold
        }

    @staticmethod
    def rule_failure(rule_id: str, error_message: str) -> Dict[str, Any]:
        """Template for rule execution failure alerts."""
        return {
            'type': 'rule_execution_failed',
            'severity': 'error',
            'message': f'Rule {rule_id} execution failed: {error_message}',
            'rule_id': rule_id
        }

    @staticmethod
    def low_success_rate(rule_id: str, success_rate: float, threshold: float = 0.7) -> Dict[str, Any]:
        """Template for low rule success rate alerts."""
        return {
            'type': 'rule_success_rate_low',
            'severity': 'error',
            'message': f'Rule {rule_id} success rate is low: {success_rate:.1f}% (threshold: {threshold*100:.1f}%)',
            'rule_id': rule_id,
            'value': success_rate,
            'threshold': threshold
        }

    @staticmethod
    def database_connection_error(error_message: str) -> Dict[str, Any]:
        """Template for database connection errors."""
        return {
            'type': 'database_connection_error',
            'severity': 'critical',
            'message': f'Database connection error: {error_message}'
        }

    @staticmethod
    def system_restart_required(reason: str) -> Dict[str, Any]:
        """Template for system restart alerts."""
        return {
            'type': 'system_restart_required',
            'severity': 'critical',
            'message': f'System restart required: {reason}'
        }
