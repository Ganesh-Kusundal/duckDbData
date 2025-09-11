"""
Infrastructure Layer - External Service Adapters
Provides adapters for external APIs and services following adapter pattern
"""

from .broker_adapter import BrokerAdapter, DhanBrokerAdapter
from .base_external_adapter import BaseExternalAdapter

__all__ = [
    'BrokerAdapter',
    'DhanBrokerAdapter',
    'BaseExternalAdapter'
]
