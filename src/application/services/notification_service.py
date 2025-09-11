"""
Notification Service - Application service for notifications.

Provides notification handling and delivery.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Application service for notification operations.

    Handles notification delivery and management.
    """

    def __init__(self, event_bus=None):
        """
        Initialize notification service.

        Args:
            event_bus: Optional event bus for notifications
        """
        self.event_bus = event_bus
        self.notifications = []

    async def send_notification(self, notification_type: str, recipient: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Send a notification.

        Args:
            notification_type: Type of notification
            recipient: Notification recipient
            message: Notification message
            **kwargs: Additional notification data

        Returns:
            Notification result
        """
        logger.info(f"Sending {notification_type} notification to {recipient}")

        notification = {
            'id': f"notif_{int(datetime.now().timestamp())}",
            'type': notification_type,
            'recipient': recipient,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'status': 'sent',
            'data': kwargs
        }

        self.notifications.append(notification)

        # In a real implementation, this would send actual notifications
        # (email, SMS, push notifications, etc.)

        return {
            'notification_id': notification['id'],
            'status': 'sent',
            'timestamp': notification['timestamp']
        }

    async def send_scanner_alert(self, scanner_type: str, results: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Send scanner alert notification.

        Args:
            scanner_type: Type of scanner
            results: Scanner results
            **kwargs: Additional alert data

        Returns:
            Alert result
        """
        message = f"Scanner {scanner_type} completed with {len(results)} results"

        return await self.send_notification(
            notification_type='scanner_alert',
            recipient='admin',
            message=message,
            scanner_type=scanner_type,
            results_count=len(results),
            **kwargs
        )

    async def send_system_alert(self, alert_type: str, severity: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Send system alert notification.

        Args:
            alert_type: Type of system alert
            severity: Alert severity (low, medium, high, critical)
            message: Alert message
            **kwargs: Additional alert data

        Returns:
            Alert result
        """
        return await self.send_notification(
            notification_type='system_alert',
            recipient='admin',
            message=f"[{severity.upper()}] {message}",
            alert_type=alert_type,
            severity=severity,
            **kwargs
        )

    def get_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent notifications.

        Args:
            limit: Maximum number of notifications to return

        Returns:
            List of notifications
        """
        return self.notifications[-limit:] if self.notifications else []

    def clear_notifications(self):
        """Clear all notifications."""
        self.notifications.clear()
        logger.info("Cleared all notifications")

    def get_notification_stats(self) -> Dict[str, Any]:
        """
        Get notification statistics.

        Returns:
            Notification statistics
        """
        if not self.notifications:
            return {
                'total_notifications': 0,
                'types': {},
                'recent_activity': []
            }

        # Count by type
        type_counts = {}
        for notification in self.notifications:
            notif_type = notification['type']
            type_counts[notif_type] = type_counts.get(notif_type, 0) + 1

        return {
            'total_notifications': len(self.notifications),
            'types': type_counts,
            'recent_activity': self.get_notifications(10)
        }

