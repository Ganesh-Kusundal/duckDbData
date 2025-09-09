"""
Notification Service
====================

Application service for handling notifications and alerts.
This service manages various types of notifications including
email, SMS, webhooks, and in-app notifications.

Features:
- Multi-channel notification delivery
- Notification templates and customization
- Alert prioritization and routing
- Notification history and tracking
- Integration with external notification services
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio

from ...application.ports.event_bus_port import EventBusPort
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    PUSH = "push"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationTemplate:
    """Notification template configuration."""
    name: str
    type: NotificationType
    subject_template: str
    body_template: str
    variables: List[str]


@dataclass
class NotificationRequest:
    """Notification request data."""
    type: NotificationType
    priority: NotificationPriority
    recipients: List[str]
    subject: str
    message: str
    template_name: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class NotificationResult:
    """Result from notification delivery."""
    notification_id: str
    success: bool
    delivered_to: List[str]
    failed_deliveries: List[str]
    timestamp: datetime
    delivery_time_seconds: float
    error_message: Optional[str] = None


class NotificationService:
    """
    Application service for notification management.

    This service handles various types of notifications and provides
    a unified interface for sending alerts and messages.
    """

    def __init__(self, event_bus: EventBusPort):
        """
        Initialize the notification service.

        Args:
            event_bus: Event bus for publishing notification events
        """
        self.event_bus = event_bus

        # Notification templates registry
        self.templates = {}

        # Notification history
        self.notification_history = []

        # Delivery channels
        self.delivery_channels = {
            NotificationType.EMAIL: self._deliver_email,
            NotificationType.SMS: self._deliver_sms,
            NotificationType.WEBHOOK: self._deliver_webhook,
            NotificationType.IN_APP: self._deliver_in_app,
            NotificationType.PUSH: self._deliver_push
        }

        logger.info("NotificationService initialized")

    def register_template(self, template: NotificationTemplate):
        """
        Register a notification template.

        Args:
            template: Template to register
        """
        self.templates[template.name] = template
        logger.info(f"Registered notification template: {template.name}")

    def send_notification(self, request: NotificationRequest) -> NotificationResult:
        """
        Send a notification.

        Args:
            request: Notification request

        Returns:
            NotificationResult with delivery status
        """
        start_time = datetime.now()
        notification_id = f"notif_{int(start_time.timestamp())}_{hash(str(request))}"

        logger.info(f"Sending {request.type.value} notification: {request.subject}")

        try:
            # Process template if specified
            if request.template_name:
                request = self._process_template(request)

            # Deliver notification
            delivery_result = self._deliver_notification(request)

            execution_time = (datetime.now() - start_time).total_seconds()

            result = NotificationResult(
                notification_id=notification_id,
                success=delivery_result['success'],
                delivered_to=delivery_result['delivered_to'],
                failed_deliveries=delivery_result['failed_deliveries'],
                timestamp=start_time,
                delivery_time_seconds=execution_time
            )

            # Store in history
            self._store_notification_history(result, request)

            # Publish event
            self._publish_notification_event(result, request)

            logger.info(f"Notification {notification_id} sent: {len(result.delivered_to)} delivered, "
                       f"{len(result.failed_deliveries)} failed")

            return result

        except Exception as e:
            logger.error(f"Notification delivery failed: {e}")

            execution_time = (datetime.now() - start_time).total_seconds()

            result = NotificationResult(
                notification_id=notification_id,
                success=False,
                delivered_to=[],
                failed_deliveries=request.recipients,
                timestamp=start_time,
                delivery_time_seconds=execution_time,
                error_message=str(e)
            )

            # Store failed notification
            self._store_notification_history(result, request)

            return result

    async def send_bulk_notifications(self, requests: List[NotificationRequest]) -> List[NotificationResult]:
        """
        Send multiple notifications in bulk.

        Args:
            requests: List of notification requests

        Returns:
            List of notification results
        """
        logger.info(f"Sending bulk notifications: {len(requests)} requests")

        # Create tasks for parallel processing
        tasks = []
        semaphore = asyncio.Semaphore(10)  # Limit concurrent notifications

        async def send_with_semaphore(request: NotificationRequest):
            async with semaphore:
                return self.send_notification(request)

        for request in requests:
            task = asyncio.create_task(send_with_semaphore(request))
            tasks.append(task)

        # Wait for all notifications to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Bulk notification {i} failed: {result}")
                # Create failed result
                failed_result = NotificationResult(
                    notification_id=f"bulk_failed_{i}",
                    success=False,
                    delivered_to=[],
                    failed_deliveries=requests[i].recipients,
                    timestamp=datetime.now(),
                    delivery_time_seconds=0.0,
                    error_message=str(result)
                )
                processed_results.append(failed_result)
            else:
                processed_results.append(result)

        logger.info(f"Bulk notifications completed: {len(processed_results)} total")
        return processed_results

    def send_alert(self, title: str, message: str, priority: NotificationPriority = NotificationPriority.MEDIUM,
                  recipients: Optional[List[str]] = None) -> NotificationResult:
        """
        Send a system alert notification.

        Args:
            title: Alert title
            message: Alert message
            priority: Alert priority
            recipients: Alert recipients (uses default if None)

        Returns:
            NotificationResult with delivery status
        """
        if not recipients:
            recipients = self._get_default_alert_recipients()

        request = NotificationRequest(
            type=NotificationType.EMAIL,
            priority=priority,
            recipients=recipients,
            subject=f"🚨 ALERT: {title}",
            message=message,
            metadata={'alert_type': 'system_alert'}
        )

        return self.send_notification(request)

    def send_scanner_results_notification(self, scanner_results: Dict[str, Any],
                                       recipients: Optional[List[str]] = None) -> NotificationResult:
        """
        Send scanner results notification.

        Args:
            scanner_results: Scanner execution results
            recipients: Notification recipients

        Returns:
            NotificationResult with delivery status
        """
        if not recipients:
            recipients = self._get_default_scanner_recipients()

        # Format scanner results
        total_stocks = scanner_results.get('summary', {}).get('total_records', 0)
        successful_scanners = scanner_results.get('summary', {}).get('successful_scanners', 0)

        subject = f"📊 Scanner Results: {total_stocks} stocks found"
        message = f"""
Scanner execution completed successfully!

📈 Results Summary:
• Total stocks found: {total_stocks}
• Successful scanners: {successful_scanners}
• Execution time: {scanner_results.get('execution_stats', {}).get('total_execution_time', 0):.2f}s

View detailed results in the application dashboard.
        """

        request = NotificationRequest(
            type=NotificationType.EMAIL,
            priority=NotificationPriority.MEDIUM,
            recipients=recipients,
            subject=subject,
            message=message,
            metadata={'notification_type': 'scanner_results'}
        )

        return self.send_notification(request)

    def get_notification_history(self, limit: int = 100, notification_type: Optional[NotificationType] = None) -> List[Dict[str, Any]]:
        """
        Get notification history.

        Args:
            limit: Maximum number of records to return
            notification_type: Filter by notification type

        Returns:
            List of notification records
        """
        history = self.notification_history

        if notification_type:
            history = [h for h in history if h.get('type') == notification_type.value]

        return history[-limit:]  # Return most recent

    def get_delivery_stats(self) -> Dict[str, Any]:
        """
        Get notification delivery statistics.

        Returns:
            Dictionary with delivery statistics
        """
        if not self.notification_history:
            return {'total_sent': 0, 'success_rate': 0.0}

        total_sent = len(self.notification_history)
        successful = sum(1 for h in self.notification_history if h.get('success', False))

        return {
            'total_sent': total_sent,
            'successful': successful,
            'failed': total_sent - successful,
            'success_rate': (successful / total_sent) * 100 if total_sent > 0 else 0.0
        }

    def _process_template(self, request: NotificationRequest) -> NotificationRequest:
        """
        Process notification template.

        Args:
            request: Original notification request

        Returns:
            Processed notification request
        """
        if not request.template_name or request.template_name not in self.templates:
            return request

        template = self.templates[request.template_name]

        # Replace template variables
        subject = self._replace_template_variables(template.subject_template, request.template_data or {})
        message = self._replace_template_variables(template.body_template, request.template_data or {})

        return NotificationRequest(
            type=template.type,
            priority=request.priority,
            recipients=request.recipients,
            subject=subject,
            message=message,
            template_name=request.template_name,
            template_data=request.template_data,
            metadata=request.metadata
        )

    def _deliver_notification(self, request: NotificationRequest) -> Dict[str, Any]:
        """
        Deliver notification through appropriate channel.

        Args:
            request: Notification request

        Returns:
            Dictionary with delivery results
        """
        if request.type not in self.delivery_channels:
            raise ValueError(f"Unsupported notification type: {request.type}")

        delivery_func = self.delivery_channels[request.type]
        return delivery_func(request)

    def _deliver_email(self, request: NotificationRequest) -> Dict[str, Any]:
        """
        Deliver email notification.

        Args:
            request: Email notification request

        Returns:
            Dictionary with delivery results
        """
        # This would integrate with an email service like SendGrid, SES, etc.
        logger.info(f"Sending email to {len(request.recipients)} recipients: {request.subject}")

        # Simulate email delivery
        delivered_to = []
        failed_deliveries = []

        for recipient in request.recipients:
            try:
                # Here you would integrate with actual email service
                logger.debug(f"Email sent to: {recipient}")
                delivered_to.append(recipient)
            except Exception as e:
                logger.error(f"Failed to send email to {recipient}: {e}")
                failed_deliveries.append(recipient)

        return {
            'success': len(delivered_to) > 0,
            'delivered_to': delivered_to,
            'failed_deliveries': failed_deliveries
        }

    def _deliver_sms(self, request: NotificationRequest) -> Dict[str, Any]:
        """
        Deliver SMS notification.

        Args:
            request: SMS notification request

        Returns:
            Dictionary with delivery results
        """
        # This would integrate with an SMS service like Twilio, AWS SNS, etc.
        logger.info(f"Sending SMS to {len(request.recipients)} recipients")

        # Simulate SMS delivery
        delivered_to = []
        failed_deliveries = []

        for recipient in request.recipients:
            try:
                # Here you would integrate with actual SMS service
                logger.debug(f"SMS sent to: {recipient}")
                delivered_to.append(recipient)
            except Exception as e:
                logger.error(f"Failed to send SMS to {recipient}: {e}")
                failed_deliveries.append(recipient)

        return {
            'success': len(delivered_to) > 0,
            'delivered_to': delivered_to,
            'failed_deliveries': failed_deliveries
        }

    def _deliver_webhook(self, request: NotificationRequest) -> Dict[str, Any]:
        """
        Deliver webhook notification.

        Args:
            request: Webhook notification request

        Returns:
            Dictionary with delivery results
        """
        # This would send HTTP POST requests to webhook URLs
        logger.info(f"Sending webhook to {len(request.recipients)} endpoints")

        delivered_to = []
        failed_deliveries = []

        for endpoint in request.recipients:
            try:
                # Here you would send actual HTTP requests
                logger.debug(f"Webhook sent to: {endpoint}")
                delivered_to.append(endpoint)
            except Exception as e:
                logger.error(f"Failed to send webhook to {endpoint}: {e}")
                failed_deliveries.append(endpoint)

        return {
            'success': len(delivered_to) > 0,
            'delivered_to': delivered_to,
            'failed_deliveries': failed_deliveries
        }

    def _deliver_in_app(self, request: NotificationRequest) -> Dict[str, Any]:
        """
        Deliver in-app notification.

        Args:
            request: In-app notification request

        Returns:
            Dictionary with delivery results
        """
        # This would store notifications in a database or cache for in-app display
        logger.info(f"Sending in-app notification to {len(request.recipients)} users")

        delivered_to = request.recipients  # Assume all succeed for in-app
        failed_deliveries = []

        return {
            'success': True,
            'delivered_to': delivered_to,
            'failed_deliveries': failed_deliveries
        }

    def _deliver_push(self, request: NotificationRequest) -> Dict[str, Any]:
        """
        Deliver push notification.

        Args:
            request: Push notification request

        Returns:
            Dictionary with delivery results
        """
        # This would integrate with push notification services like FCM, APNs, etc.
        logger.info(f"Sending push notification to {len(request.recipients)} devices")

        delivered_to = []
        failed_deliveries = []

        for device in request.recipients:
            try:
                # Here you would integrate with actual push service
                logger.debug(f"Push sent to: {device}")
                delivered_to.append(device)
            except Exception as e:
                logger.error(f"Failed to send push to {device}: {e}")
                failed_deliveries.append(device)

        return {
            'success': len(delivered_to) > 0,
            'delivered_to': delivered_to,
            'failed_deliveries': failed_deliveries
        }

    def _replace_template_variables(self, template: str, data: Dict[str, Any]) -> str:
        """
        Replace template variables in text.

        Args:
            template: Template string with variables
            data: Variable replacement data

        Returns:
            Processed template string
        """
        result = template
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))

        return result

    def _store_notification_history(self, result: NotificationResult, request: NotificationRequest):
        """
        Store notification in history.

        Args:
            result: Notification result
            request: Original request
        """
        history_record = {
            'notification_id': result.notification_id,
            'type': request.type.value,
            'priority': request.priority.value,
            'subject': request.subject,
            'recipients': request.recipients,
            'success': result.success,
            'delivered_to': result.delivered_to,
            'failed_deliveries': result.failed_deliveries,
            'timestamp': result.timestamp.isoformat(),
            'delivery_time': result.delivery_time_seconds,
            'error_message': result.error_message
        }

        self.notification_history.append(history_record)

        # Keep only last 1000 notifications
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]

    def _publish_notification_event(self, result: NotificationResult, request: NotificationRequest):
        """
        Publish notification event.

        Args:
            result: Notification result
            request: Original request
        """
        event_data = {
            'notification_id': result.notification_id,
            'type': request.type.value,
            'priority': request.priority.value,
            'success': result.success,
            'delivered_count': len(result.delivered_to),
            'failed_count': len(result.failed_deliveries),
            'timestamp': result.timestamp.isoformat()
        }

        try:
            self.event_bus.publish({
                'event_type': 'notification_sent',
                'data': event_data,
                'timestamp': datetime.now().isoformat()
            })
            logger.debug(f"Published notification event: {result.notification_id}")
        except Exception as e:
            logger.error(f"Failed to publish notification event: {e}")

    def _get_default_alert_recipients(self) -> List[str]:
        """
        Get default alert recipients.

        Returns:
            List of default alert recipients
        """
        # This would be configurable
        return ['admin@example.com']

    def _get_default_scanner_recipients(self) -> List[str]:
        """
        Get default scanner result recipients.

        Returns:
            List of default scanner recipients
        """
        # This would be configurable
        return ['trader@example.com']
