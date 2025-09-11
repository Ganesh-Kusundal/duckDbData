"""
Trading Domain Query Handlers

Query handlers for trading data retrieval that coordinate with
repositories and return read-only data.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from application.queries.base_query import QueryHandler, QueryResult
from application.queries.trading_queries import (
    GetOrderByIdQuery, GetOrdersBySymbolQuery, GetPortfolioSummaryQuery,
    GetTradingHistoryQuery, GetPositionByIdQuery
)
from domain.trading.repositories.order_repository import OrderRepository
from domain.trading.repositories.position_repository import PositionRepository
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class GetOrderByIdQueryHandler(QueryHandler):
    """
    Handler for GetOrderByIdQuery.

    Retrieves detailed information about a specific order.
    """

    def __init__(self, order_repository: Optional[OrderRepository] = None):
        self.order_repository = order_repository

    @property
    def handled_query_type(self) -> str:
        return "GetOrderById"

    async def handle(self, query: GetOrderByIdQuery) -> QueryResult:
        """Handle order retrieval by ID."""
        try:
            logger.info(f"Retrieving order: {query.order_id}")

            if not self.order_repository:
                # Mock response for demonstration
                mock_order = {
                    "id": query.order_id,
                    "symbol": "AAPL",
                    "side": "BUY",
                    "quantity": 100,
                    "order_type": "LIMIT",
                    "price": 150.00,
                    "status": "FILLED",
                    "created_at": datetime.utcnow().isoformat()
                }
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=mock_order
                )

            order = await self.order_repository.find_by_id(query.order_id)
            if not order:
                return QueryResult(
                    success=False,
                    query_id=query.query_id,
                    error_message=f"Order not found: {query.order_id}"
                )

            # Convert order to dict for response
            order_data = {
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "quantity": order.quantity,
                "order_type": order.order_type,
                "price": float(order.price) if order.price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None,
                "status": order.status.value,
                "time_in_force": order.time_in_force,
                "strategy_id": order.strategy_id,
                "risk_profile_id": order.risk_profile_id,
                "created_at": order.created_at.isoformat(),
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None
            }

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data=order_data
            )

        except Exception as e:
            logger.error(f"Order retrieval failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetOrdersBySymbolQueryHandler(QueryHandler):
    """
    Handler for GetOrdersBySymbolQuery.

    Retrieves orders for a specific symbol with filtering options.
    """

    def __init__(self, order_repository: Optional[OrderRepository] = None):
        self.order_repository = order_repository

    @property
    def handled_query_type(self) -> str:
        return "GetOrdersBySymbol"

    async def handle(self, query: GetOrdersBySymbolQuery) -> QueryResult:
        """Handle orders retrieval by symbol."""
        try:
            logger.info(f"Retrieving orders for symbol: {query.symbol}")

            if not self.order_repository:
                # Mock response
                mock_orders = [
                    {
                        "id": f"order_{i}",
                        "symbol": query.symbol,
                        "side": "BUY",
                        "quantity": 100,
                        "order_type": "LIMIT",
                        "price": 150.00 + i,
                        "status": "FILLED",
                        "created_at": datetime.utcnow().isoformat()
                    } for i in range(min(query.limit, 5))
                ]
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=mock_orders,
                    metadata={"total_count": len(mock_orders)}
                )

            # Build filter criteria
            filters = {"symbol": query.symbol}

            if query.status_filter:
                filters["status"] = query.status_filter

            if query.start_date:
                filters["created_after"] = query.start_date

            if query.end_date:
                filters["created_before"] = query.end_date

            orders = await self.order_repository.find_by_filters(filters, limit=query.limit)

            # Convert orders to dict format
            orders_data = []
            for order in orders:
                order_data = {
                    "id": order.id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.quantity,
                    "order_type": order.order_type,
                    "price": float(order.price) if order.price else None,
                    "status": order.status.value,
                    "created_at": order.created_at.isoformat()
                }
                orders_data.append(order_data)

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data=orders_data,
                metadata={"total_count": len(orders_data)}
            )

        except Exception as e:
            logger.error(f"Orders retrieval failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetPortfolioSummaryQueryHandler(QueryHandler):
    """
    Handler for GetPortfolioSummaryQuery.

    Retrieves comprehensive portfolio information.
    """

    def __init__(self,
                 position_repository: Optional[PositionRepository] = None,
                 order_repository: Optional[OrderRepository] = None):
        self.position_repository = position_repository
        self.order_repository = order_repository

    @property
    def handled_query_type(self) -> str:
        return "GetPortfolioSummary"

    async def handle(self, query: GetPortfolioSummaryQuery) -> QueryResult:
        """Handle portfolio summary retrieval."""
        try:
            logger.info("Retrieving portfolio summary")

            portfolio_data = {
                "portfolio_id": "portfolio_001",
                "total_value": 100000.00,
                "cash_balance": 25000.00,
                "total_positions": 0,
                "total_orders": 0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 1500.00,
                "day_pnl": 250.00,
                "positions": [],
                "orders": [],
                "last_updated": datetime.utcnow().isoformat()
            }

            # Get positions if requested
            if query.include_positions:
                if self.position_repository:
                    positions = await self.position_repository.find_all()
                    portfolio_data["positions"] = [
                        {
                            "id": pos.id,
                            "symbol": pos.symbol,
                            "quantity": pos.quantity,
                            "average_price": float(pos.average_price),
                            "current_price": 155.00,  # Mock current price
                            "unrealized_pnl": 500.00,  # Mock P&L
                            "market_value": pos.quantity * 155.00
                        } for pos in positions
                    ]
                    portfolio_data["total_positions"] = len(positions)
                else:
                    # Mock positions
                    portfolio_data["positions"] = [
                        {
                            "id": "pos_1",
                            "symbol": "AAPL",
                            "quantity": 100,
                            "average_price": 150.00,
                            "current_price": 155.00,
                            "unrealized_pnl": 500.00,
                            "market_value": 15500.00
                        }
                    ]
                    portfolio_data["total_positions"] = 1

            # Get orders if requested
            if query.include_orders:
                if self.order_repository:
                    orders = await self.order_repository.find_by_filters({"status": ["PENDING", "SUBMITTED"]})
                    portfolio_data["orders"] = [
                        {
                            "id": order.id,
                            "symbol": order.symbol,
                            "side": order.side,
                            "quantity": order.quantity,
                            "order_type": order.order_type,
                            "price": float(order.price) if order.price else None,
                            "status": order.status.value
                        } for order in orders
                    ]
                    portfolio_data["total_orders"] = len(orders)
                else:
                    # Mock orders
                    portfolio_data["orders"] = [
                        {
                            "id": "order_1",
                            "symbol": "GOOGL",
                            "side": "BUY",
                            "quantity": 50,
                            "order_type": "LIMIT",
                            "price": 2800.00,
                            "status": "PENDING"
                        }
                    ]
                    portfolio_data["total_orders"] = 1

            # Calculate totals
            positions_value = sum(pos["market_value"] for pos in portfolio_data["positions"])
            portfolio_data["total_value"] = portfolio_data["cash_balance"] + positions_value
            portfolio_data["unrealized_pnl"] = sum(pos["unrealized_pnl"] for pos in portfolio_data["positions"])

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data=portfolio_data
            )

        except Exception as e:
            logger.error(f"Portfolio summary retrieval failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetTradingHistoryQueryHandler(QueryHandler):
    """
    Handler for GetTradingHistoryQuery.

    Retrieves historical trading activity.
    """

    def __init__(self, order_repository: Optional[OrderRepository] = None):
        self.order_repository = order_repository

    @property
    def handled_query_type(self) -> str:
        return "GetTradingHistory"

    async def handle(self, query: GetTradingHistoryQuery) -> QueryResult:
        """Handle trading history retrieval."""
        try:
            logger.info(f"Retrieving trading history from {query.start_date} to {query.end_date}")

            if not self.order_repository:
                # Mock trading history
                mock_trades = [
                    {
                        "id": f"trade_{i}",
                        "symbol": "AAPL",
                        "side": "BUY" if i % 2 == 0 else "SELL",
                        "quantity": 100,
                        "price": 150.00 + i * 0.5,
                        "executed_at": (query.start_date.replace(hour=i % 24)).isoformat(),
                        "commission": 5.00,
                        "pnl": 250.00 if i % 2 == 1 else 0.0
                    } for i in range(min(query.limit, 10))
                ]
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=mock_trades,
                    metadata={"total_count": len(mock_trades)}
                )

            # Build filter criteria
            filters = {
                "executed_after": query.start_date,
                "executed_before": query.end_date
            }

            if query.symbol_filter:
                filters["symbol"] = query.symbol_filter

            if query.strategy_filter:
                filters["strategy_id"] = query.strategy_filter

            trades = await self.order_repository.find_executed_trades(filters, limit=query.limit)

            # Convert trades to dict format
            trades_data = []
            for trade in trades:
                trade_data = {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": float(trade.price),
                    "executed_at": trade.executed_at.isoformat(),
                    "commission": float(trade.commission) if trade.commission else 0.0,
                    "pnl": float(trade.realized_pnl) if trade.realized_pnl else 0.0
                }
                trades_data.append(trade_data)

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data=trades_data,
                metadata={"total_count": len(trades_data)}
            )

        except Exception as e:
            logger.error(f"Trading history retrieval failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetPositionByIdQueryHandler(QueryHandler):
    """
    Handler for GetPositionByIdQuery.

    Retrieves detailed position information.
    """

    def __init__(self, position_repository: Optional[PositionRepository] = None):
        self.position_repository = position_repository

    @property
    def handled_query_type(self) -> str:
        return "GetPositionById"

    async def handle(self, query: GetPositionByIdQuery) -> QueryResult:
        """Handle position retrieval by ID."""
        try:
            logger.info(f"Retrieving position: {query.position_id}")

            if not self.position_repository:
                # Mock position data
                mock_position = {
                    "id": query.position_id,
                    "symbol": "AAPL",
                    "quantity": 100,
                    "average_price": 150.00,
                    "current_price": 155.00,
                    "market_value": 15500.00,
                    "unrealized_pnl": 500.00,
                    "realized_pnl": 250.00,
                    "total_pnl": 750.00,
                    "status": "OPEN",
                    "opened_at": datetime.utcnow().isoformat(),
                    "last_updated": datetime.utcnow().isoformat()
                }
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=mock_position
                )

            position = await self.position_repository.find_by_id(query.position_id)
            if not position:
                return QueryResult(
                    success=False,
                    query_id=query.query_id,
                    error_message=f"Position not found: {query.position_id}"
                )

            # Convert position to dict format
            position_data = {
                "id": position.id,
                "symbol": position.symbol,
                "quantity": position.quantity,
                "average_price": float(position.average_price),
                "current_price": float(position.current_price) if position.current_price else None,
                "market_value": float(position.market_value) if position.market_value else None,
                "unrealized_pnl": float(position.unrealized_pnl) if position.unrealized_pnl else 0.0,
                "realized_pnl": float(position.realized_pnl) if position.realized_pnl else 0.0,
                "total_pnl": float(position.total_pnl) if position.total_pnl else 0.0,
                "status": position.status,
                "opened_at": position.opened_at.isoformat(),
                "closed_at": position.closed_at.isoformat() if position.closed_at else None,
                "last_updated": position.last_updated.isoformat()
            }

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data=position_data
            )

        except Exception as e:
            logger.error(f"Position retrieval failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )
