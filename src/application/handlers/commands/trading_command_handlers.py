"""
Trading Domain Command Handlers

Command handlers for trading operations that orchestrate domain logic
and coordinate with repositories and external services.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from application.commands.base_command import CommandHandler, CommandResult
from application.commands.trading_commands import (
    SubmitOrderCommand, CancelOrderCommand, ModifyOrderCommand,
    ClosePositionCommand, CreateTradingStrategyCommand
)
from domain.trading.entities.order import Order, OrderStatus
from domain.trading.entities.position import Position
from domain.trading.repositories.order_repository import OrderRepository
from domain.trading.repositories.position_repository import PositionRepository
from domain.trading.services.order_execution_service import OrderExecutionService
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class SubmitOrderCommandHandler(CommandHandler):
    """
    Handler for SubmitOrderCommand.

    Orchestrates the creation and submission of trading orders.
    """

    def __init__(self, order_repository: Optional[OrderRepository] = None,
                 position_repository: Optional[PositionRepository] = None,
                 order_execution_service: Optional[OrderExecutionService] = None):
        self.order_repository = order_repository
        self.position_repository = position_repository
        self.order_execution_service = order_execution_service

    @property
    def handled_command_type(self) -> str:
        return "SubmitOrder"

    async def handle(self, command: SubmitOrderCommand) -> CommandResult:
        """Handle order submission command."""
        try:
            logger.info(f"Processing order submission for {command.symbol}")

            # Create order entity
            order = Order(
                symbol=command.symbol,
                side=command.side,
                quantity=command.quantity,
                order_type=command.order_type,
                price=command.price,
                stop_price=command.stop_price,
                time_in_force=command.time_in_force,
                strategy_id=command.strategy_id,
                risk_profile_id=command.risk_profile_id
            )

            # Validate order
            await self._validate_order(order)

            # Save order to repository
            if self.order_repository:
                await self.order_repository.save(order)

            # Submit order for execution
            if self.order_execution_service:
                execution_result = await self.order_execution_service.submit_order(order)
            else:
                execution_result = {"success": True, "message": "Order submitted (mock)"}

            # Update order status
            order.status = OrderStatus.SUBMITTED
            order.submitted_at = datetime.utcnow()

            if self.order_repository:
                await self.order_repository.update(order)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "order_id": order.id,
                    "status": order.status.value,
                    "execution_result": execution_result
                }
            )

        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )

    async def _validate_order(self, order: Order) -> None:
        """Validate order before submission."""
        # Check risk limits
        if self.position_repository:
            existing_positions = await self.position_repository.find_by_symbol(order.symbol)
            # Add risk validation logic here

        # Check account balance/position limits
        # Add additional validation logic here

        pass


class CancelOrderCommandHandler(CommandHandler):
    """
    Handler for CancelOrderCommand.

    Orchestrates the cancellation of existing orders.
    """

    def __init__(self, order_repository: Optional[OrderRepository] = None,
                 order_execution_service: Optional[OrderExecutionService] = None):
        self.order_repository = order_repository
        self.order_execution_service = order_execution_service

    @property
    def handled_command_type(self) -> str:
        return "CancelOrder"

    async def handle(self, command: CancelOrderCommand) -> CommandResult:
        """Handle order cancellation command."""
        try:
            logger.info(f"Processing order cancellation for {command.order_id}")

            # Find order
            if not self.order_repository:
                raise DomainException("Order repository not available")

            order = await self.order_repository.find_by_id(command.order_id)
            if not order:
                raise DomainException(f"Order not found: {command.order_id}")

            # Check if order can be cancelled
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                raise DomainException(f"Order cannot be cancelled (status: {order.status.value})")

            # Cancel order through execution service
            if self.order_execution_service:
                cancel_result = await self.order_execution_service.cancel_order(order)
            else:
                cancel_result = {"success": True, "message": "Order cancelled (mock)"}

            # Update order status
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = datetime.utcnow()
            order.cancellation_reason = command.reason

            await self.order_repository.update(order)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "order_id": order.id,
                    "status": order.status.value,
                    "cancellation_result": cancel_result
                }
            )

        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class ModifyOrderCommandHandler(CommandHandler):
    """
    Handler for ModifyOrderCommand.

    Orchestrates the modification of existing orders.
    """

    def __init__(self, order_repository: Optional[OrderRepository] = None,
                 order_execution_service: Optional[OrderExecutionService] = None):
        self.order_repository = order_repository
        self.order_execution_service = order_execution_service

    @property
    def handled_command_type(self) -> str:
        return "ModifyOrder"

    async def handle(self, command: ModifyOrderCommand) -> CommandResult:
        """Handle order modification command."""
        try:
            logger.info(f"Processing order modification for {command.order_id}")

            # Find order
            if not self.order_repository:
                raise DomainException("Order repository not available")

            order = await self.order_repository.find_by_id(command.order_id)
            if not order:
                raise DomainException(f"Order not found: {command.order_id}")

            # Check if order can be modified
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                raise DomainException(f"Order cannot be modified (status: {order.status.value})")

            # Apply modifications
            modifications_applied = []
            for key, value in command.modifications.items():
                if hasattr(order, key):
                    setattr(order, key, value)
                    modifications_applied.append(key)
                else:
                    logger.warning(f"Unknown order attribute: {key}")

            # Modify order through execution service
            if self.order_execution_service:
                modify_result = await self.order_execution_service.modify_order(order, command.modifications)
            else:
                modify_result = {"success": True, "message": "Order modified (mock)"}

            # Update order
            order.modified_at = datetime.utcnow()
            await self.order_repository.update(order)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "order_id": order.id,
                    "modifications_applied": modifications_applied,
                    "modify_result": modify_result
                }
            )

        except Exception as e:
            logger.error(f"Order modification failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class ClosePositionCommandHandler(CommandHandler):
    """
    Handler for ClosePositionCommand.

    Orchestrates the closing of existing positions.
    """

    def __init__(self, position_repository: Optional[PositionRepository] = None,
                 order_execution_service: Optional[OrderExecutionService] = None):
        self.position_repository = position_repository
        self.order_execution_service = order_execution_service

    @property
    def handled_command_type(self) -> str:
        return "ClosePosition"

    async def handle(self, command: ClosePositionCommand) -> CommandResult:
        """Handle position closing command."""
        try:
            logger.info(f"Processing position closure for {command.position_id}")

            # Find position
            if not self.position_repository:
                raise DomainException("Position repository not available")

            position = await self.position_repository.find_by_id(command.position_id)
            if not position:
                raise DomainException(f"Position not found: {command.position_id}")

            # Determine quantity to close
            quantity_to_close = command.quantity or position.quantity

            if quantity_to_close > position.quantity:
                raise DomainException(f"Cannot close more than position size: {position.quantity}")

            # Create closing order
            closing_order = Order(
                symbol=position.symbol,
                side="SELL" if position.side == "BUY" else "BUY",
                quantity=quantity_to_close,
                order_type=command.order_type,
                price=command.price
            )

            # Submit closing order
            if self.order_execution_service:
                order_result = await self.order_execution_service.submit_order(closing_order)
            else:
                order_result = {"success": True, "message": "Closing order submitted (mock)"}

            # Update position
            if quantity_to_close == position.quantity:
                position.status = "CLOSED"
                position.closed_at = datetime.utcnow()
            else:
                position.quantity -= quantity_to_close

            await self.position_repository.update(position)

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "position_id": position.id,
                    "closing_order_id": closing_order.id if hasattr(closing_order, 'id') else None,
                    "quantity_closed": quantity_to_close,
                    "position_status": position.status,
                    "order_result": order_result
                }
            )

        except Exception as e:
            logger.error(f"Position closure failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )


class CreateTradingStrategyCommandHandler(CommandHandler):
    """
    Handler for CreateTradingStrategyCommand.

    Orchestrates the creation of trading strategies.
    """

    def __init__(self, strategy_repository=None):  # Would be injected
        self.strategy_repository = strategy_repository

    @property
    def handled_command_type(self) -> str:
        return "CreateTradingStrategy"

    async def handle(self, command: CreateTradingStrategyCommand) -> CommandResult:
        """Handle trading strategy creation command."""
        try:
            logger.info(f"Creating trading strategy: {command.name}")

            # Create strategy entity (would use domain entity)
            strategy_data = {
                "id": f"strategy_{command.command_id}",
                "name": command.name,
                "description": command.description,
                "strategy_type": command.strategy_type,
                "parameters": command.parameters,
                "risk_profile_id": command.risk_profile_id,
                "is_active": command.is_active,
                "created_at": datetime.utcnow()
            }

            # Save strategy (mock implementation)
            if self.strategy_repository:
                await self.strategy_repository.save(strategy_data)
            else:
                logger.info(f"Strategy would be saved: {strategy_data}")

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "strategy_id": strategy_data["id"],
                    "status": "created"
                }
            )

        except Exception as e:
            logger.error(f"Strategy creation failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )
