"""
Broker Integration Domain

This domain handles broker connectivity, order execution, and account management
for trading operations. It provides a unified interface for interacting with
multiple broker APIs while maintaining domain integrity.
"""

from .entities import BrokerConnection, ConnectionStatus, BrokerCredentials
from .entities import BrokerAccount

from .value_objects.order_execution import (
    ExecutionParameters, BrokerOrder, ExecutionReport, OrderStatusUpdate, BrokerCapabilities
)

from .repositories.broker_connection_repository import (
    BrokerConnectionRepository, InMemoryBrokerConnectionRepository,
    BrokerAccountRepository, InMemoryBrokerAccountRepository
)
from .repositories.order_execution_repository import (
    OrderExecutionRepository, InMemoryOrderExecutionRepository,
    ExecutionReportRepository, InMemoryExecutionReportRepository,
    OrderStatusRepository, InMemoryOrderStatusRepository
)

from .services.broker_connection_service import (
    BrokerConnectionService, BrokerAuthenticationService, BrokerConnectionManager
)
from .services.order_execution_service import (
    OrderExecutionService, OrderRoutingService, ExecutionMonitoringService, OrderExecutionManager
)

__all__ = [
    # Entities
    'BrokerConnection', 'ConnectionStatus', 'BrokerCredentials',
    'BrokerAccount',

    # Value Objects
    'ExecutionParameters', 'BrokerOrder', 'ExecutionReport',
    'OrderStatusUpdate', 'BrokerCapabilities',

    # Repositories
    'BrokerConnectionRepository', 'InMemoryBrokerConnectionRepository',
    'BrokerAccountRepository', 'InMemoryBrokerAccountRepository',
    'OrderExecutionRepository', 'InMemoryOrderExecutionRepository',
    'ExecutionReportRepository', 'InMemoryExecutionReportRepository',
    'OrderStatusRepository', 'InMemoryOrderStatusRepository',

    # Services
    'BrokerConnectionService', 'BrokerAuthenticationService', 'BrokerConnectionManager',
    'OrderExecutionService', 'OrderRoutingService', 'ExecutionMonitoringService', 'OrderExecutionManager'
]
