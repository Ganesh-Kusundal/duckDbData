"""
EventBus adapter that implements the EventBusPort by delegating to the
existing infrastructure event bus implementation.
"""

from typing import Optional

from src.application.ports.event_bus_port import EventBusPort
from src.infrastructure.messaging.event_bus import get_event_bus


class EventBusAdapter(EventBusPort):
    """Adapter that wraps the global EventBus to satisfy the port."""

    def __init__(self):
        self._bus = get_event_bus()

    def publish(self, event: object, correlation_id: Optional[str] = None) -> None:
        self._bus.publish(event, correlation_id)

