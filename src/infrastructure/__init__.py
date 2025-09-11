"""
Infrastructure Layer
Provides technical capabilities and external integrations
"""

# Import key components for easy access
from .database import BaseRepository, DuckDBAdapter, MarketDataRepositoryImpl
from .external import BaseExternalAdapter, BrokerAdapter, DhanBrokerAdapter
from .messaging import DomainEvent, IntegrationEvent
from .dependency_container import DependencyContainer, get_container, ServiceLocator, inject

__all__ = [
    # Database
    'BaseRepository',
    'DuckDBAdapter',
    'MarketDataRepositoryImpl',

    # External
    'BaseExternalAdapter',
    'BrokerAdapter',
    'DhanBrokerAdapter',

    # Messaging
    'DomainEvent',
    'IntegrationEvent',

    # Dependency Injection
    'DependencyContainer',
    'get_container',
    'ServiceLocator',
    'inject'
]
