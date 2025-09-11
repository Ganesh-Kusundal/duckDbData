"""
Trading Application Service

High-level application service that orchestrates trading operations
across multiple domains using CQRS pattern.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal

from .cqrs_registry import get_cqrs_registry
from ..commands.trading_commands import (
    SubmitOrderCommand, CancelOrderCommand, ClosePositionCommand,
    CreateTradingStrategyCommand, ExecuteTradingStrategyCommand
)
from ..queries.trading_queries import (
    GetPortfolioSummaryQuery, GetTradingHistoryQuery,
    GetOrderByIdQuery, GetPositionByIdQuery
)
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class TradingApplicationService:
    """
    Application service for trading operations.

    Provides high-level orchestration of trading activities including
    order management, position management, and strategy execution.
    """

    def __init__(self):
        self.cqrs_registry = get_cqrs_registry()

    async def submit_market_order(self, symbol: str, side: str, quantity: int,
                                 strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit a market order.

        Args:
            symbol: Trading symbol
            side: "BUY" or "SELL"
            quantity: Order quantity
            strategy_id: Optional strategy identifier

        Returns:
            Order submission result
        """
        try:
            command = SubmitOrderCommand(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type="MARKET",
                strategy_id=strategy_id
            )

            result = await self.cqrs_registry.execute_command(command)

            if result.success:
                return {
                    "success": True,
                    "order_id": result.data["order_id"],
                    "status": result.data["status"],
                    "message": "Market order submitted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Market order submission failed"
                }

        except Exception as e:
            logger.error(f"Market order submission failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Market order submission failed"
            }

    async def submit_limit_order(self, symbol: str, side: str, quantity: int,
                                price: Decimal, strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit a limit order.

        Args:
            symbol: Trading symbol
            side: "BUY" or "SELL"
            quantity: Order quantity
            price: Limit price
            strategy_id: Optional strategy identifier

        Returns:
            Order submission result
        """
        try:
            command = SubmitOrderCommand(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type="LIMIT",
                price=price,
                strategy_id=strategy_id
            )

            result = await self.cqrs_registry.execute_command(command)

            if result.success:
                return {
                    "success": True,
                    "order_id": result.data["order_id"],
                    "status": result.data["status"],
                    "message": f"Limit order submitted successfully at {price}"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Limit order submission failed"
                }

        except Exception as e:
            logger.error(f"Limit order submission failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Limit order submission failed"
            }

    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel an existing order.

        Args:
            order_id: Order identifier
            reason: Optional cancellation reason

        Returns:
            Order cancellation result
        """
        try:
            command = CancelOrderCommand(
                order_id=order_id,
                reason=reason
            )

            result = await self.cqrs_registry.execute_command(command)

            if result.success:
                return {
                    "success": True,
                    "order_id": order_id,
                    "status": result.data["status"],
                    "message": "Order cancelled successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Order cancellation failed"
                }

        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Order cancellation failed"
            }

    async def close_position(self, position_id: str, quantity: Optional[int] = None) -> Dict[str, Any]:
        """
        Close an existing position.

        Args:
            position_id: Position identifier
            quantity: Optional quantity to close (None = close entire position)

        Returns:
            Position closure result
        """
        try:
            command = ClosePositionCommand(
                position_id=position_id,
                quantity=quantity
            )

            result = await self.cqrs_registry.execute_command(command)

            if result.success:
                return {
                    "success": True,
                    "position_id": position_id,
                    "quantity_closed": result.data["quantity_closed"],
                    "closing_order_id": result.data.get("closing_order_id"),
                    "message": f"Position closed successfully ({result.data['quantity_closed']} shares)"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Position closure failed"
                }

        except Exception as e:
            logger.error(f"Position closure failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Position closure failed"
            }

    async def create_trading_strategy(self, name: str, description: str,
                                     strategy_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new trading strategy.

        Args:
            name: Strategy name
            description: Strategy description
            strategy_type: Type of strategy
            parameters: Strategy parameters

        Returns:
            Strategy creation result
        """
        try:
            command = CreateTradingStrategyCommand(
                name=name,
                description=description,
                strategy_type=strategy_type,
                parameters=parameters
            )

            result = await self.cqrs_registry.execute_command(command)

            if result.success:
                return {
                    "success": True,
                    "strategy_id": result.data["strategy_id"],
                    "message": f"Trading strategy '{name}' created successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Strategy creation failed"
                }

        except Exception as e:
            logger.error(f"Strategy creation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Strategy creation failed"
            }

    async def execute_trading_strategy(self, strategy_id: str, symbol: str) -> Dict[str, Any]:
        """
        Execute a trading strategy.

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol

        Returns:
            Strategy execution result
        """
        try:
            command = ExecuteTradingStrategyCommand(
                strategy_id=strategy_id,
                symbol=symbol,
                timeframe="1D"  # Default timeframe
            )

            result = await self.cqrs_registry.execute_command(command)

            if result.success:
                return {
                    "success": True,
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "message": "Strategy executed successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Strategy execution failed"
                }

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Strategy execution failed"
            }

    async def get_portfolio_summary(self, include_positions: bool = True,
                                   include_orders: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary.

        Args:
            include_positions: Include position details
            include_orders: Include order details

        Returns:
            Portfolio summary data
        """
        try:
            query = GetPortfolioSummaryQuery(
                include_positions=include_positions,
                include_orders=include_orders
            )

            result = await self.cqrs_registry.execute_query(query)

            if result.success:
                return {
                    "success": True,
                    "portfolio": result.data,
                    "message": "Portfolio summary retrieved successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Portfolio summary retrieval failed"
                }

        except Exception as e:
            logger.error(f"Portfolio summary retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Portfolio summary retrieval failed"
            }

    async def get_trading_history(self, start_date: datetime, end_date: datetime,
                                 symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get trading history within date range.

        Args:
            start_date: Start date for history
            end_date: End date for history
            symbol: Optional symbol filter

        Returns:
            Trading history data
        """
        try:
            query = GetTradingHistoryQuery(
                start_date=start_date,
                end_date=end_date,
                symbol_filter=symbol
            )

            result = await self.cqrs_registry.execute_query(query)

            if result.success:
                return {
                    "success": True,
                    "trades": result.data,
                    "total_count": result.metadata.get("total_count", 0),
                    "message": f"Retrieved {len(result.data)} trades"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Trading history retrieval failed"
                }

        except Exception as e:
            logger.error(f"Trading history retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Trading history retrieval failed"
            }

    async def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific order.

        Args:
            order_id: Order identifier

        Returns:
            Order details
        """
        try:
            query = GetOrderByIdQuery(order_id=order_id)

            result = await self.cqrs_registry.execute_query(query)

            if result.success:
                return {
                    "success": True,
                    "order": result.data,
                    "message": "Order details retrieved successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Order details retrieval failed"
                }

        except Exception as e:
            logger.error(f"Order details retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Order details retrieval failed"
            }

    async def get_position_details(self, position_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific position.

        Args:
            position_id: Position identifier

        Returns:
            Position details
        """
        try:
            query = GetPositionByIdQuery(position_id=position_id)

            result = await self.cqrs_registry.execute_query(query)

            if result.success:
                return {
                    "success": True,
                    "position": result.data,
                    "message": "Position details retrieved successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Position details retrieval failed"
                }

        except Exception as e:
            logger.error(f"Position details retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Position details retrieval failed"
            }

    async def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open orders
        """
        try:
            from ..queries.trading_queries import GetOpenOrdersQuery

            query = GetOpenOrdersQuery(symbol_filter=symbol)
            result = await self.cqrs_registry.execute_query(query)

            if result.success:
                return {
                    "success": True,
                    "orders": result.data,
                    "count": len(result.data),
                    "message": f"Retrieved {len(result.data)} open orders"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": "Open orders retrieval failed"
                }

        except Exception as e:
            logger.error(f"Open orders retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Open orders retrieval failed"
            }

    async def get_positions_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get all positions for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of positions for the symbol
        """
        try:
            from ..queries.trading_queries import GetPositionsBySymbolQuery

            query = GetPositionsBySymbolQuery(symbol=symbol)
            result = await self.cqrs_registry.execute_query(query)

            if result.success:
                return {
                    "success": True,
                    "positions": result.data,
                    "symbol": symbol,
                    "message": f"Retrieved {len(result.data)} positions for {symbol}"
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message,
                    "message": f"Positions retrieval failed for {symbol}"
                }

        except Exception as e:
            logger.error(f"Positions retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Positions retrieval failed for {symbol}"
            }
