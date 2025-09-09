"""
Event Bus Port (abstraction) for Dependency Inversion.

Defines minimal contract used by application/services to publish events
without depending on infrastructure implementation (Rx, asyncio, etc.).
"""

from typing import Protocol, Optional


class EventBusPort(Protocol):
    """Port for publishing domain/application events."""

    def publish(self, event: object, correlation_id: Optional[str] = None) -> None:  # pragma: no cover - protocol
        ...

