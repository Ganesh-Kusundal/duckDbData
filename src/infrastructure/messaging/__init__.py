"""
Infrastructure Layer - Messaging
Provides event-driven communication between bounded contexts
"""

from .event_types import DomainEvent, IntegrationEvent

__all__ = [
    'DomainEvent',
    'IntegrationEvent'
]
