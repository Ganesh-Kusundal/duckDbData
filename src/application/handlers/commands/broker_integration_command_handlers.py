"""
Broker Integration Domain Command Handlers

Command handlers for broker integration operations that orchestrate
broker connections, order execution, and account management.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from application.commands.base_command import CommandHandler, CommandResult
from application.commands.broker_integration_commands import (
    EstablishBrokerConnectionCommand, SubmitBrokerOrderCommand,
    CancelBrokerOrderCommand, GetBrokerAccountInfoCommand
)
from domain.broker_integration.entities.broker_connection import BrokerConnection
from domain.broker_integration.entities.broker_account import BrokerAccount
from domain.broker_integration.repositories.broker_connection_repository import BrokerConnectionRepository
from domain.broker_integration.repositories.order_execution_repository import OrderExecutionRepository
from domain.broker_integration.services.broker_connection_service import BrokerConnectionManager
from domain.broker_integration.services.order_execution_service import OrderExecutionService
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class EstablishBrokerConnectionCommandHandler(CommandHandler):
    """
    Handler for EstablishBrokerConnectionCommand.

    Orchestrates broker connection establishment and authentication.
    """

    def __init__(self, broker_connection_repository: Optional[BrokerConnectionRepository] = None,
                 broker_connection_service: Optional[BrokerConnectionManager] = None):
        self.broker_connection_repository = broker_connection_repository
        self.broker_connection_service = broker_connection_service

    @property
    def handled_command_type(self) -> str:
        return "EstablishBrokerConnection"

    async def handle(self, command: EstablishBrokerConnectionCommand) -> CommandResult:
        """Handle broker connection establishment command."""
        try:
            logger.info(f"Establishing broker connection: {command.connection_id}")

            # Create broker connection entity
            connection = BrokerConnection(
                id=command.connection_id,
                broker_type=command.broker_type,
                credentials=command.credentials,
                endpoints=command.endpoints,
                name=command.broker_name
            )

            # Establish connection
            connection_result = {}
            if self.broker_connection_service:
                result = await self.broker_connection_service.establish_connection(connection)
                connection_result = result
            else:
                # Mock connection establishment
                connection.status = "CONNECTED"
                connection.last_connected_at = datetime.utcnow()
                connection_result = {
                    "success": True,
                    "connection_id": command.connection_id,
                    "status": "connected",
                    "session_id": f"session_{command.connection_id}",
                    "api_version": "v1"
                }

            # Save connection to repository
            if self.broker_connection_repository:
                await self.broker_connection_repository.save(connection)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "connection_id": command.connection_id,
                    "broker_type": command.broker_type,
                    "status": connection.status.value if hasattr(connection, 'status') else "connected",
                    "connection_result": connection_result,
                    "established_at": datetime.utcnow()
                }
            )

        except Exception as e:
            logger.error(f"Broker connection establishment failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class SubmitBrokerOrderCommandHandler(CommandHandler):
    """
    Handler for SubmitBrokerOrderCommand.

    Orchestrates order submission to broker APIs.
    """

    def __init__(self, order_execution_repository: Optional[OrderExecutionRepository] = None,
                 order_execution_service: Optional[OrderExecutionService] = None):
        self.order_execution_repository = order_execution_repository
        self.order_execution_service = order_execution_service

    @property
    def handled_command_type(self) -> str:
        return "SubmitBrokerOrder"

    async def handle(self, command: SubmitBrokerOrderCommand) -> CommandResult:
        """Handle broker order submission command."""
        try:
            logger.info(f"Submitting order to broker {command.broker_connection_id}")

            # Create broker order
            broker_order = {
                "id": f"order_{command.command_id}",
                "broker_connection_id": command.broker_connection_id,
                "symbol": command.symbol,
                "side": command.side,
                "quantity": command.quantity,
                "order_type": command.order_type,
                "price": command.price,
                "time_in_force": command.time_in_force,
                "parameters": command.parameters,
                "submitted_at": datetime.utcnow()
            }

            # Submit order through service
            submission_result = {}
            if self.order_execution_service:
                result = await self.order_execution_service.submit_order(broker_order)
                submission_result = result
            else:
                # Mock order submission
                submission_result = {
                    "success": True,
                    "broker_order_id": f"BRK_{broker_order['id']}",
                    "status": "SUBMITTED",
                    "estimated_fill_price": command.price or 150.00,
                    "commission_estimate": 5.00
                }

            # Save order execution record
            if self.order_execution_repository:
                execution_record = {
                    "id": broker_order["id"],
                    "broker_order_id": submission_result.get("broker_order_id"),
                    "status": "SUBMITTED",
                    "submission_result": submission_result,
                    "created_at": datetime.utcnow()
                }
                await self.order_execution_repository.save(execution_record)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "order_id": broker_order["id"],
                    "broker_order_id": submission_result.get("broker_order_id"),
                    "status": submission_result.get("status", "SUBMITTED"),
                    "submission_result": submission_result,
                    "submitted_at": broker_order["submitted_at"]
                }
            )

        except Exception as e:
            logger.error(f"Broker order submission failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class CancelBrokerOrderCommandHandler(CommandHandler):
    """
    Handler for CancelBrokerOrderCommand.

    Orchestrates order cancellation through broker APIs.
    """

    def __init__(self, order_execution_service: Optional[OrderExecutionService] = None):
        self.order_execution_service = order_execution_service

    @property
    def handled_command_type(self) -> str:
        return "CancelBrokerOrder"

    async def handle(self, command: CancelBrokerOrderCommand) -> CommandResult:
        """Handle broker order cancellation command."""
        try:
            logger.info(f"Cancelling broker order {command.broker_order_id}")

            # Cancel order through service
            cancellation_result = {}
            if self.order_execution_service:
                result = await self.order_execution_service.cancel_order(
                    command.broker_order_id, command.broker_connection_id
                )
                cancellation_result = result
            else:
                # Mock order cancellation
                cancellation_result = {
                    "success": True,
                    "order_id": command.broker_order_id,
                    "status": "CANCELLED",
                    "cancelled_at": datetime.utcnow()
                }

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "broker_order_id": command.broker_order_id,
                    "status": cancellation_result.get("status", "CANCELLED"),
                    "cancellation_result": cancellation_result,
                    "cancelled_at": datetime.utcnow()
                }
            )

        except Exception as e:
            logger.error(f"Broker order cancellation failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class GetBrokerAccountInfoCommandHandler(CommandHandler):
    """
    Handler for GetBrokerAccountInfoCommand.

    Orchestrates retrieval of broker account information.
    """

    def __init__(self, broker_connection_service: Optional[BrokerConnectionManager] = None):
        self.broker_connection_service = broker_connection_service

    @property
    def handled_command_type(self) -> str:
        return "GetBrokerAccountInfo"

    async def handle(self, command: GetBrokerAccountInfoCommand) -> CommandResult:
        """Handle broker account info retrieval command."""
        try:
            logger.info(f"Retrieving account info for broker {command.broker_connection_id}")

            # Get account information
            account_result = {}
            if self.broker_connection_service:
                result = await self.broker_connection_service.get_account_info(
                    command.broker_connection_id, command.account_number
                )
                account_result = result
            else:
                # Mock account information
                account_result = {
                    "success": True,
                    "account_number": command.account_number or "DEMO123",
                    "account_type": "MARGIN",
                    "currency": "USD",
                    "cash_balance": 50000.00,
                    "buying_power": 100000.00,
                    "total_value": 75000.00,
                    "margin_used": 0.00,
                    "available_margin": 100000.00,
                    "positions_count": 5,
                    "last_updated": datetime.utcnow()
                }

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "broker_connection_id": command.broker_connection_id,
                    "account_info": account_result,
                    "retrieved_at": datetime.utcnow()
                }
            )

        except Exception as e:
            logger.error(f"Broker account info retrieval failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )
