"""Event bus implementation using RxPy for reactive event handling."""

import logging
logger = logging.getLogger(__name__)

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

import asyncio
from typing import List, Optional, Awaitable

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


class AsyncEventBus:
    """Async event bus using asyncio.Queue for non-blocking publish/subscribe."""
    
    def __init__(self):
        """Initialize the async event bus."""
        self._queues: Dict[str, asyncio.Queue] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._is_running = False
        self._main_task: Optional[asyncio.Task] = None
        
        logger.info("Async event bus initialized")
    
    async def start(self):
        """Start the async event bus."""
        if self._is_running:
            return
        
        self._is_running = True
        self._main_task = asyncio.create_task(self._event_loop())
        logger.info("Async event bus started")
    
    async def stop(self):
        """Stop the async event bus."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel main task
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        
        # Clear queues
        for queue in self._queues.values():
            queue.put_nowait(None)  # Sentinel to wake up consumers
        
        logger.info("Async event bus stopped")
    
    async def _event_loop(self):
        """Main event loop for processing events."""
        while self._is_running:
            try:
                # Wait for any event in any queue
                done, pending = await asyncio.wait(
                    [self._process_queue(event_type) for event_type in self._queues.keys()],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    
            except Exception as e:
                logger.error(f"Error in async event loop: {e}")
                await asyncio.sleep(1)
    
    async def _process_queue(self, event_type: str):
        """Process events from a specific queue."""
        queue = self._queues.get(event_type)
        if not queue:
            return
        
        while self._is_running:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                if event is None:  # Stop signal
                    break
                
                # Notify subscribers
                if event_type in self._subscribers:
                    for subscriber in self._subscribers[event_type]:
                        try:
                            if asyncio.iscoroutinefunction(subscriber):
                                await subscriber(event)
                            else:
                                # Run sync subscriber in executor
                                loop = asyncio.get_event_loop()
                                await loop.run_in_executor(None, subscriber, event)
                        except Exception as e:
                            logger.error(f"Error in subscriber for {event_type}: {e}")
                
                queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing queue {event_type}: {e}")
    
    async def async_publish(self, event: DomainEvent, event_type: Optional[str] = None, correlation_id: Optional[str] = None) -> None:
        """Async publish event to the bus."""
        event_type = event_type or event.event_type
        
        # Create envelope
        envelope = EventEnvelope(
            event=event,
            timestamp=datetime.now(),
            correlation_id=correlation_id,
        )
        
        # Ensure queue exists
        if event_type not in self._queues:
            self._queues[event_type] = asyncio.Queue()
        
        # Publish to queue
        await self._queues[event_type].put(envelope)
        logger.debug(f"Async published event: {event_type}")
    
    async def async_subscribe(self, event_type: str, handler: Callable) -> None:
        """Async subscribe to events."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        logger.debug(f"Async subscribed to event type: {event_type}")
    
    async def async_unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Async unsubscribe from events."""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Async unsubscribed from event type: {event_type}")
    
    def get_queue_size(self, event_type: str) -> int:
        """Get queue size for event type."""
        queue = self._queues.get(event_type)
        return queue.qsize() if queue else 0


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

# Global async event bus instance
_async_event_bus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def get_async_event_bus() -> AsyncEventBus:
    """Get the global async event bus instance."""
    global _async_event_bus
    if _async_event_bus is None:
        _async_event_bus = AsyncEventBus()
        # Start the async bus
        asyncio.create_task(_async_event_bus.start())
    return _async_event_bus


async def async_publish_event(event: DomainEvent, correlation_id: Optional[str] = None) -> None:
    """Async publish event to both sync and async buses."""
    # Publish to sync bus
    publish_event(event, correlation_id)
    
    # Publish to async bus
    try:
        async_bus = get_async_event_bus()
        await async_bus.async_publish(event, correlation_id=correlation_id)
    except Exception as e:
        logger.error(f"Failed to publish to async bus: {e}")


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
