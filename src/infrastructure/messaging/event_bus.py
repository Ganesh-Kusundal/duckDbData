"""Event bus implementation using RxPy for reactive event handling."""

from typing import Any, Dict, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from rx.subject import Subject
    from rx import Observable
    from rx.operators import filter, map
    HAS_RX = True
except ImportError:
    # Fallback for when rx is not available
    HAS_RX = False
    Subject = None
    Observable = None
    filter = None
    map = None

from ...domain.events import DomainEvent


@dataclass(frozen=True)
class EventEnvelope:
    """Envelope for wrapping events with metadata."""

    event: DomainEvent
    timestamp: datetime
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate envelope after initialization."""
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})


class EventBus:
    """Reactive event bus for handling domain events."""

    def __init__(self):
        """Initialize the event bus."""
        if HAS_RX and Subject:
            self._subject = Subject()
        else:
            # Fallback implementation without RxPy
            self._subject = None
            self._fallback_handlers: Dict[str, List[Callable]] = {}

        self._handlers: Dict[str, List[Callable]] = {}
        self._middleware: List[Callable] = []

    def publish(self, event: DomainEvent, correlation_id: Optional[str] = None) -> None:
        """Publish an event to the bus."""
        envelope = EventEnvelope(
            event=event,
            timestamp=datetime.now(),
            correlation_id=correlation_id,
        )

        # Apply middleware
        processed_envelope = envelope
        for middleware in self._middleware:
            processed_envelope = middleware(processed_envelope)

        # Publish to subject
        self._subject.on_next(processed_envelope)

    def subscribe(
        self,
        event_type: Optional[str] = None,
        handler: Optional[Callable] = None
    ) -> Observable:
        """Subscribe to events on the bus."""
        observable = self._subject

        # Filter by event type if specified
        if event_type:
            observable = observable.pipe(
                filter(lambda envelope: envelope.event.event_type == event_type)
            )

        # Map to event if handler is provided
        if handler:
            observable = observable.pipe(
                map(lambda envelope: handler(envelope.event, envelope))
            )

        return observable

    def subscribe_to_type(
        self,
        event_type: str,
        handler: Callable[[DomainEvent, EventEnvelope], None]
    ):
        """Subscribe to a specific event type."""
        subscription = self.subscribe(event_type, handler)
        return subscription.subscribe()

    def add_middleware(self, middleware: Callable[[EventEnvelope], EventEnvelope]):
        """Add middleware to the event bus."""
        self._middleware.append(middleware)

    def get_event_stream(self) -> Observable:
        """Get the raw event stream."""
        return self._subject

    def get_events_by_type(self, event_type: str) -> Observable:
        """Get events filtered by type."""
        return self._subject.pipe(
            filter(lambda envelope: envelope.event.event_type == event_type),
            map(lambda envelope: envelope.event)
        )

    def get_events_by_correlation_id(self, correlation_id: str) -> Observable:
        """Get events filtered by correlation ID."""
        return self._subject.pipe(
            filter(lambda envelope: envelope.correlation_id == correlation_id)
        )


# Global event bus instance
_event_bus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish_event(event: DomainEvent, correlation_id: Optional[str] = None) -> None:
    """Publish an event to the global event bus."""
    bus = get_event_bus()
    bus.publish(event, correlation_id)


def subscribe_to_event(
    event_type: str,
    handler: Callable[[DomainEvent, EventEnvelope], None]
):
    """Subscribe to events on the global event bus."""
    bus = get_event_bus()
    return bus.subscribe_to_type(event_type, handler)


def add_event_middleware(middleware: Callable[[EventEnvelope], EventEnvelope]):
    """Add middleware to the global event bus."""
    bus = get_event_bus()
    bus.add_middleware(middleware)
