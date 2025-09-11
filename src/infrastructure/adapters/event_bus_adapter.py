"""
Event Bus Adapter for infrastructure layer.

Provides an event bus implementation for decoupling components
and enabling asynchronous communication.
"""

import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EventMessage:
    """Event message structure."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    source: str
    correlation_id: Optional[str] = None


class EventBusAdapter:
    """
    Event bus adapter for handling domain events and integration events.

    Provides publish-subscribe pattern for decoupling components.
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Handler function to call when event is published
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to event type: {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable):
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Unsubscribed handler from event type: {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event type: {event_type}")

    async def publish(self, event_type: str, payload: Dict[str, Any], source: str = "unknown", correlation_id: Optional[str] = None):
        """
        Publish an event.

        Args:
            event_type: Type of event to publish
            payload: Event payload data
            source: Source of the event
            correlation_id: Optional correlation ID for tracking
        """
        event = EventMessage(
            event_type=event_type,
            payload=payload,
            timestamp=datetime.now(),
            source=source,
            correlation_id=correlation_id
        )

        await self._queue.put(event)
        logger.debug(f"Published event: {event_type} from {source}")

    async def start(self):
        """Start the event processing loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self):
        """Stop the event processing loop."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Event bus stopped")

    async def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._handle_event(event)
                self._queue.task_done()

            except asyncio.TimeoutError:
                # No event received, continue loop
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def _handle_event(self, event: EventMessage):
        """Handle a single event."""
        event_type = event.event_type

        if event_type in self._handlers:
            handlers = self._handlers[event_type]
            logger.debug(f"Handling event {event_type} with {len(handlers)} handlers")

            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        # Run sync handler in thread pool
                        await asyncio.get_event_loop().run_in_executor(None, handler, event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
        else:
            logger.debug(f"No handlers for event type: {event_type}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'running': self._running,
            'queue_size': self._queue.qsize(),
            'subscribed_event_types': len(self._handlers),
            'total_handlers': sum(len(handlers) for handlers in self._handlers.values())
        }

    async def wait_for_empty_queue(self, timeout: float = 10.0):
        """
        Wait for the event queue to be empty.

        Args:
            timeout: Maximum time to wait in seconds
        """
        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for empty queue after {timeout} seconds")

    def clear_handlers(self):
        """Clear all event handlers."""
        self._handlers.clear()
        logger.info("Cleared all event handlers")

