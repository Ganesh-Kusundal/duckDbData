"""
Broker Integration Domain Query Handlers

Query handlers for broker integration operations that retrieve
broker data and connection information efficiently.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from application.queries.base_query import QueryHandler, QueryResult
from application.queries.broker_integration_queries import (
    GetBrokerConnectionByIdQuery, GetBrokerConnectionsQuery,
    GetBrokerAccountsQuery, GetOrderExecutionHistoryQuery
)
from domain.broker_integration.repositories.broker_connection_repository import BrokerConnectionRepository
from domain.broker_integration.repositories.order_execution_repository import OrderExecutionRepository
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class GetBrokerConnectionByIdQueryHandler(QueryHandler):
    """
    Handler for GetBrokerConnectionByIdQuery.

    Retrieves a specific broker connection by its ID.
    """

    def __init__(self, broker_connection_repository: Optional[BrokerConnectionRepository] = None):
        self.broker_connection_repository = broker_connection_repository

    @property
    def handled_query_type(self) -> str:
        return "GetBrokerConnectionById"

    async def handle(self, query: GetBrokerConnectionByIdQuery) -> QueryResult:
        """Handle get broker connection by ID query."""
        try:
            logger.info(f"Retrieving broker connection {query.connection_id}")

            if not self.broker_connection_repository:
                raise DomainException("Broker connection repository not available")

            connection = await self.broker_connection_repository.find_by_id(query.connection_id)
            if not connection:
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None
                )

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "connection": {
                        "id": connection.id.value,
                        "broker_type": connection.broker_type.value,
                        "name": connection.name,
                        "status": connection.status.value if hasattr(connection, 'status') else "unknown",
                        "last_connected_at": getattr(connection, 'last_connected_at', None),
                        "created_at": getattr(connection, 'created_at', datetime.utcnow()),
                        "is_active": getattr(connection, 'is_active', True)
                    }
                }
            )

        except Exception as e:
            logger.error(f"Get broker connection by ID failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetBrokerConnectionsQueryHandler(QueryHandler):
    """
    Handler for GetBrokerConnectionsQuery.

    Retrieves broker connections with filtering and pagination.
    """

    def __init__(self, broker_connection_repository: Optional[BrokerConnectionRepository] = None):
        self.broker_connection_repository = broker_connection_repository

    @property
    def handled_query_type(self) -> str:
        return "GetBrokerConnections"

    async def handle(self, query: GetBrokerConnectionsQuery) -> QueryResult:
        """Handle get broker connections query."""
        try:
            logger.info("Retrieving broker connections")

            if not self.broker_connection_repository:
                raise DomainException("Broker connection repository not available")

            # Build filters
            filters = {}
            if query.broker_type:
                filters["broker_type"] = query.broker_type
            if query.status:
                filters["status"] = query.status
            if query.is_active is not None:
                filters["is_active"] = query.is_active

            # Add date range filter
            if query.start_date or query.end_date:
                if query.start_date:
                    filters["start_date"] = query.start_date
                if query.end_date:
                    filters["end_date"] = query.end_date

            result = await self.broker_connection_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            connections = result.data if result.success and result.data else []

            # Calculate summary statistics
            total_connections = len(connections)
            active_connections = sum(1 for c in connections if getattr(c, 'is_active', True))
            by_broker_type = {}
            for c in connections:
                broker_type = c.broker_type.value if hasattr(c, 'broker_type') else "unknown"
                by_broker_type[broker_type] = by_broker_type.get(broker_type, 0) + 1

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "connections": [
                        {
                            "id": c.id.value,
                            "broker_type": c.broker_type.value if hasattr(c, 'broker_type') else "unknown",
                            "name": c.name,
                            "status": c.status.value if hasattr(c, 'status') else "unknown",
                            "is_active": getattr(c, 'is_active', True),
                            "last_connected_at": getattr(c, 'last_connected_at', None)
                        }
                        for c in connections
                    ],
                    "summary": {
                        "total_connections": total_connections,
                        "active_connections": active_connections,
                        "inactive_connections": total_connections - active_connections,
                        "connections_by_type": by_broker_type
                    },
                    "filters_applied": filters
                }
            )

        except Exception as e:
            logger.error(f"Get broker connections failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetBrokerAccountsQueryHandler(QueryHandler):
    """
    Handler for GetBrokerAccountsQuery.

    Retrieves broker accounts for a specific connection.
    """

    def __init__(self, broker_connection_repository: Optional[BrokerConnectionRepository] = None):
        self.broker_connection_repository = broker_connection_repository

    @property
    def handled_query_type(self) -> str:
        return "GetBrokerAccounts"

    async def handle(self, query: GetBrokerAccountsQuery) -> QueryResult:
        """Handle get broker accounts query."""
        try:
            logger.info(f"Retrieving broker accounts for connection {query.connection_id}")

            if not self.broker_connection_repository:
                raise DomainException("Broker connection repository not available")

            # In a real implementation, this would query for accounts associated with the connection
            # For now, return mock account data
            accounts = [
                {
                    "id": f"account_1_{query.connection_id}",
                    "connection_id": query.connection_id,
                    "account_number": "DEMO123456",
                    "account_type": "MARGIN",
                    "currency": "USD",
                    "is_active": True,
                    "created_at": datetime.utcnow()
                },
                {
                    "id": f"account_2_{query.connection_id}",
                    "connection_id": query.connection_id,
                    "account_number": "DEMO789012",
                    "account_type": "CASH",
                    "currency": "USD",
                    "is_active": True,
                    "created_at": datetime.utcnow()
                }
            ]

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "accounts": accounts,
                    "total_count": len(accounts),
                    "connection_id": query.connection_id
                }
            )

        except Exception as e:
            logger.error(f"Get broker accounts failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetOrderExecutionHistoryQueryHandler(QueryHandler):
    """
    Handler for GetOrderExecutionHistoryQuery.

    Retrieves order execution history for monitoring and analysis.
    """

    def __init__(self, order_execution_repository: Optional[OrderExecutionRepository] = None):
        self.order_execution_repository = order_execution_repository

    @property
    def handled_query_type(self) -> str:
        return "GetOrderExecutionHistory"

    async def handle(self, query: GetOrderExecutionHistoryQuery) -> QueryResult:
        """Handle get order execution history query."""
        try:
            logger.info(f"Retrieving order execution history for connection {query.connection_id}")

            # Build filters
            filters = {"connection_id": query.connection_id}
            if query.status:
                filters["status"] = query.status
            if query.symbol:
                filters["symbol"] = query.symbol

            # Add date range filter
            if query.start_date or query.end_date:
                if query.start_date:
                    filters["start_date"] = query.start_date
                if query.end_date:
                    filters["end_date"] = query.end_date

            executions = []
            if self.order_execution_repository:
                result = await self.order_execution_repository.find_by_criteria(
                    filters, limit=query.limit, offset=query.offset
                )
                executions = result.data if result.success and result.data else []
            else:
                # Mock execution history
                executions = [
                    {
                        "id": f"exec_1_{query.connection_id}",
                        "broker_order_id": f"BRK_001_{query.connection_id}",
                        "symbol": query.symbol or "AAPL",
                        "side": "BUY",
                        "quantity": 100,
                        "price": 150.25,
                        "status": "FILLED",
                        "executed_at": datetime.utcnow(),
                        "commission": 5.00
                    },
                    {
                        "id": f"exec_2_{query.connection_id}",
                        "broker_order_id": f"BRK_002_{query.connection_id}",
                        "symbol": query.symbol or "GOOGL",
                        "side": "SELL",
                        "quantity": 50,
                        "price": 2800.00,
                        "status": "FILLED",
                        "executed_at": datetime.utcnow() - timedelta(minutes=30),
                        "commission": 7.00
                    }
                ]

            # Calculate summary statistics
            total_executions = len(executions)
            filled_executions = sum(1 for e in executions if e.get("status") == "FILLED")
            total_value = sum(e.get("quantity", 0) * e.get("price", 0) for e in executions)
            total_commission = sum(e.get("commission", 0) for e in executions)

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "executions": executions,
                    "summary": {
                        "total_executions": total_executions,
                        "filled_executions": filled_executions,
                        "success_rate": (filled_executions / max(1, total_executions)) * 100,
                        "total_value": total_value,
                        "total_commission": total_commission,
                        "net_value": total_value - total_commission
                    },
                    "connection_id": query.connection_id,
                    "filters_applied": filters
                }
            )

        except Exception as e:
            logger.error(f"Get order execution history failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )
