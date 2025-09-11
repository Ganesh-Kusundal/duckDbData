"""
Trading Domain Repository Implementations

Provides concrete repository implementations for trading domain entities
following DDD repository patterns.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from domain.trading.entities.order import Order, OrderStatus
from domain.trading.entities.position import Position
from domain.trading.repositories.order_repository import OrderRepository
from domain.trading.repositories.position_repository import PositionRepository
from ..database.duckdb_adapter import DuckDBAdapter
from ..database.base_repository import RepositoryResult, QueryBuilder

logger = logging.getLogger(__name__)


class DuckDBOrderRepository(OrderRepository):
    """
    DuckDB implementation of OrderRepository.

    Provides persistence operations for Order entities.
    """

    def __init__(self, db_path: str = "data/financial_data.duckdb"):
        self.db = DuckDBAdapter(db_path)
        self._initialized = False

    async def initialize(self):
        """Initialize the repository database schema."""
        if self._initialized:
            return

        schema_sql = """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            order_type TEXT NOT NULL,
            price DECIMAL(10,4),
            stop_price DECIMAL(10,4),
            time_in_force TEXT NOT NULL DEFAULT 'DAY',
            status TEXT NOT NULL DEFAULT 'PENDING',
            strategy_id TEXT,
            risk_profile_id TEXT,
            submitted_at TIMESTAMP,
            filled_at TIMESTAMP,
            cancelled_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_strategy ON orders(strategy_id);
        CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
        """

        try:
            await self.db.execute_query(schema_sql)
            self._initialized = True
            logger.info("Order repository initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize order repository: {e}")
            raise

    async def save(self, order: Order) -> RepositoryResult:
        """Save or update an order."""
        await self.initialize()

        try:
            # Check if order exists
            existing = await self.find_by_id(order.id)
            if existing.success and existing.data:
                # Update existing order
                return await self._update_order(order)
            else:
                # Insert new order
                return await self._insert_order(order)

        except Exception as e:
            logger.error(f"Failed to save order {order.id}: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def _insert_order(self, order: Order) -> RepositoryResult:
        """Insert a new order."""
        insert_sql = """
        INSERT INTO orders (
            id, symbol, side, quantity, order_type, price, stop_price,
            time_in_force, status, strategy_id, risk_profile_id,
            submitted_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            order.id,
            order.symbol,
            order.side,
            order.quantity,
            order.order_type,
            float(order.price) if order.price else None,
            float(order.stop_price) if order.stop_price else None,
            order.time_in_force,
            order.status.value,
            order.strategy_id,
            order.risk_profile_id,
            order.submitted_at,
            order.created_at,
            order.updated_at
        )

        await self.db.execute_query(insert_sql, params)
        return RepositoryResult(success=True, data=order)

    async def _update_order(self, order: Order) -> RepositoryResult:
        """Update an existing order."""
        update_sql = """
        UPDATE orders SET
            symbol = ?, side = ?, quantity = ?, order_type = ?,
            price = ?, stop_price = ?, time_in_force = ?, status = ?,
            strategy_id = ?, risk_profile_id = ?, submitted_at = ?,
            filled_at = ?, cancelled_at = ?, updated_at = ?
        WHERE id = ?
        """

        params = (
            order.symbol, order.side, order.quantity, order.order_type,
            float(order.price) if order.price else None,
            float(order.stop_price) if order.stop_price else None,
            order.time_in_force, order.status.value, order.strategy_id,
            order.risk_profile_id, order.submitted_at, order.filled_at,
            order.cancelled_at, datetime.now(), order.id
        )

        await self.db.execute_query(update_sql, params)
        return RepositoryResult(success=True, data=order)

    async def find_by_id(self, order_id: str) -> RepositoryResult:
        """Find order by ID."""
        await self.initialize()

        try:
            query = "SELECT * FROM orders WHERE id = ?"
            result = await self.db.execute_query(query, (order_id,))

            if result:
                order_data = result[0]
                order = self._row_to_order(order_data)
                return RepositoryResult(success=True, data=order)
            else:
                return RepositoryResult(success=True, data=None)

        except Exception as e:
            logger.error(f"Failed to find order {order_id}: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def find_by_symbol(self, symbol: str, limit: int = 100) -> RepositoryResult:
        """Find orders by symbol."""
        await self.initialize()

        try:
            query = "SELECT * FROM orders WHERE symbol = ? ORDER BY created_at DESC LIMIT ?"
            result = await self.db.execute_query(query, (symbol, limit))

            orders = [self._row_to_order(row) for row in result]
            return RepositoryResult(success=True, data=orders)

        except Exception as e:
            logger.error(f"Failed to find orders for symbol {symbol}: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def find_by_status(self, status: OrderStatus, limit: int = 100) -> RepositoryResult:
        """Find orders by status."""
        await self.initialize()

        try:
            query = "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ?"
            result = await self.db.execute_query(query, (status.value, limit))

            orders = [self._row_to_order(row) for row in result]
            return RepositoryResult(success=True, data=orders)

        except Exception as e:
            logger.error(f"Failed to find orders by status {status.value}: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def find_executed_trades(self, filters: Dict[str, Any] = None, limit: int = 100) -> RepositoryResult:
        """Find executed trades with optional filters."""
        await self.initialize()

        try:
            query_builder = QueryBuilder("orders").where("status = ?", status="FILLED")

            if filters:
                if "symbol" in filters:
                    query_builder.where("symbol = ?", symbol=filters["symbol"])
                if "start_date" in filters:
                    query_builder.where("filled_at >= ?", start_date=filters["start_date"])
                if "end_date" in filters:
                    query_builder.where("filled_at <= ?", end_date=filters["end_date"])
                if "strategy_id" in filters:
                    query_builder.where("strategy_id = ?", strategy_id=filters["strategy_id"])

            query_builder.order_by("filled_at", desc=True).limit(limit)

            query, params = query_builder.build_select()
            result = await self.db.execute_query(query, params)

            orders = [self._row_to_order(row) for row in result]
            return RepositoryResult(success=True, data=orders)

        except Exception as e:
            logger.error(f"Failed to find executed trades: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def update_status(self, order_id: str, status: OrderStatus) -> RepositoryResult:
        """Update order status."""
        await self.initialize()

        try:
            update_sql = "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?"

            now = datetime.now()
            params = (status.value, now, order_id)

            await self.db.execute_query(update_sql, params)
            return RepositoryResult(success=True)

        except Exception as e:
            logger.error(f"Failed to update order {order_id} status: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def delete(self, order_id: str) -> RepositoryResult:
        """Delete an order."""
        await self.initialize()

        try:
            delete_sql = "DELETE FROM orders WHERE id = ?"
            await self.db.execute_query(delete_sql, (order_id,))
            return RepositoryResult(success=True)

        except Exception as e:
            logger.error(f"Failed to delete order {order_id}: {e}")
            return RepositoryResult(success=False, error=str(e))

    def _row_to_order(self, row: Dict[str, Any]) -> Order:
        """Convert database row to Order entity."""
        return Order(
            id=row['id'],
            symbol=row['symbol'],
            side=row['side'],
            quantity=row['quantity'],
            order_type=row['order_type'],
            price=Decimal(str(row['price'])) if row['price'] else None,
            stop_price=Decimal(str(row['stop_price'])) if row['stop_price'] else None,
            time_in_force=row['time_in_force'],
            status=OrderStatus(row['status']),
            strategy_id=row['strategy_id'],
            risk_profile_id=row['risk_profile_id'],
            submitted_at=row['submitted_at'],
            filled_at=row['filled_at'],
            cancelled_at=row['cancelled_at'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


class DuckDBPositionRepository(PositionRepository):
    """
    DuckDB implementation of PositionRepository.

    Provides persistence operations for Position entities.
    """

    def __init__(self, db_path: str = "data/financial_data.duckdb"):
        self.db = DuckDBAdapter(db_path)
        self._initialized = False

    async def initialize(self):
        """Initialize the repository database schema."""
        if self._initialized:
            return

        schema_sql = """
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            quantity DECIMAL(15,4) NOT NULL,
            average_price DECIMAL(10,4) NOT NULL,
            current_price DECIMAL(10,4),
            market_value DECIMAL(15,4),
            unrealized_pnl DECIMAL(15,4) DEFAULT 0,
            realized_pnl DECIMAL(15,4) DEFAULT 0,
            total_pnl DECIMAL(15,4) DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'OPEN',
            portfolio_id TEXT,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
        CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
        CREATE INDEX IF NOT EXISTS idx_positions_portfolio ON positions(portfolio_id);
        """

        try:
            await self.db.execute_query(schema_sql)
            self._initialized = True
            logger.info("Position repository initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize position repository: {e}")
            raise

    async def save(self, position: Position) -> RepositoryResult:
        """Save or update a position."""
        await self.initialize()

        try:
            # Check if position exists
            existing = await self.find_by_id(position.id)
            if existing.success and existing.data:
                # Update existing position
                return await self._update_position(position)
            else:
                # Insert new position
                return await self._insert_position(position)

        except Exception as e:
            logger.error(f"Failed to save position {position.id}: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def _insert_position(self, position: Position) -> RepositoryResult:
        """Insert a new position."""
        insert_sql = """
        INSERT INTO positions (
            id, symbol, quantity, average_price, current_price, market_value,
            unrealized_pnl, realized_pnl, total_pnl, status, portfolio_id,
            opened_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            position.id, position.symbol, float(position.quantity),
            float(position.average_price),
            float(position.current_price) if position.current_price else None,
            float(position.market_value) if position.market_value else None,
            float(position.unrealized_pnl), float(position.realized_pnl),
            float(position.total_pnl), position.status, position.portfolio_id,
            position.opened_at, position.created_at, position.updated_at
        )

        await self.db.execute_query(insert_sql, params)
        return RepositoryResult(success=True, data=position)

    async def _update_position(self, position: Position) -> RepositoryResult:
        """Update an existing position."""
        update_sql = """
        UPDATE positions SET
            symbol = ?, quantity = ?, average_price = ?, current_price = ?,
            market_value = ?, unrealized_pnl = ?, realized_pnl = ?, total_pnl = ?,
            status = ?, portfolio_id = ?, closed_at = ?, updated_at = ?
        WHERE id = ?
        """

        params = (
            position.symbol, float(position.quantity), float(position.average_price),
            float(position.current_price) if position.current_price else None,
            float(position.market_value) if position.market_value else None,
            float(position.unrealized_pnl), float(position.realized_pnl),
            float(position.total_pnl), position.status, position.portfolio_id,
            position.closed_at, datetime.now(), position.id
        )

        await self.db.execute_query(update_sql, params)
        return RepositoryResult(success=True, data=position)

    async def find_by_id(self, position_id: str) -> RepositoryResult:
        """Find position by ID."""
        await self.initialize()

        try:
            query = "SELECT * FROM positions WHERE id = ?"
            result = await self.db.execute_query(query, (position_id,))

            if result:
                position_data = result[0]
                position = self._row_to_position(position_data)
                return RepositoryResult(success=True, data=position)
            else:
                return RepositoryResult(success=True, data=None)

        except Exception as e:
            logger.error(f"Failed to find position {position_id}: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def find_by_symbol(self, symbol: str) -> RepositoryResult:
        """Find positions by symbol."""
        await self.initialize()

        try:
            query = "SELECT * FROM positions WHERE symbol = ? AND status = 'OPEN'"
            result = await self.db.execute_query(query, (symbol,))

            positions = [self._row_to_position(row) for row in result]
            return RepositoryResult(success=True, data=positions)

        except Exception as e:
            logger.error(f"Failed to find positions for symbol {symbol}: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def find_by_portfolio(self, portfolio_id: str) -> RepositoryResult:
        """Find positions by portfolio."""
        await self.initialize()

        try:
            query = "SELECT * FROM positions WHERE portfolio_id = ? ORDER BY opened_at DESC"
            result = await self.db.execute_query(query, (portfolio_id,))

            positions = [self._row_to_position(row) for row in result]
            return RepositoryResult(success=True, data=positions)

        except Exception as e:
            logger.error(f"Failed to find positions for portfolio {portfolio_id}: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def find_all(self) -> RepositoryResult:
        """Find all positions."""
        await self.initialize()

        try:
            query = "SELECT * FROM positions ORDER BY opened_at DESC"
            result = await self.db.execute_query(query)

            positions = [self._row_to_position(row) for row in result]
            return RepositoryResult(success=True, data=positions)

        except Exception as e:
            logger.error(f"Failed to find all positions: {e}")
            return RepositoryResult(success=False, error=str(e))

    async def update(self, position: Position) -> RepositoryResult:
        """Update a position."""
        return await self.save(position)

    async def delete(self, position_id: str) -> RepositoryResult:
        """Delete a position."""
        await self.initialize()

        try:
            delete_sql = "DELETE FROM positions WHERE id = ?"
            await self.db.execute_query(delete_sql, (position_id,))
            return RepositoryResult(success=True)

        except Exception as e:
            logger.error(f"Failed to delete position {position_id}: {e}")
            return RepositoryResult(success=False, error=str(e))

    def _row_to_position(self, row: Dict[str, Any]) -> Position:
        """Convert database row to Position entity."""
        return Position(
            id=row['id'],
            symbol=row['symbol'],
            quantity=Decimal(str(row['quantity'])),
            average_price=Decimal(str(row['average_price'])),
            current_price=Decimal(str(row['current_price'])) if row['current_price'] else None,
            market_value=Decimal(str(row['market_value'])) if row['market_value'] else None,
            unrealized_pnl=Decimal(str(row['unrealized_pnl'])),
            realized_pnl=Decimal(str(row['realized_pnl'])),
            total_pnl=Decimal(str(row['total_pnl'])),
            status=row['status'],
            portfolio_id=row['portfolio_id'],
            opened_at=row['opened_at'],
            closed_at=row['closed_at'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
