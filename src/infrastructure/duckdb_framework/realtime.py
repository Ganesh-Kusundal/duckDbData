"""
Real-time Trading Infrastructure
==============================

Provides:
- Live data streaming
- Order management system
- Risk monitoring
- Market data ingestion
- Alert system
"""

import asyncio
import websockets
import json
import pandas as pd
import threading
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor


class OrderType(Enum):
    """Types of orders."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(Enum):
    """Order sides."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order statuses."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    """Trading order."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = None
    filled_quantity: int = 0
    average_fill_price: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Position:
    """Portfolio position."""
    symbol: str
    quantity: int
    average_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float


@dataclass
class MarketData:
    """Real-time market data."""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None


class RealtimeManager:
    """
    Real-time market data manager.
    """

    def __init__(self, connection, config: Optional[Dict[str, Any]] = None):
        self.connection = connection
        self.config = config or self.get_default_config()
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger(__name__)

    def get_default_config(self) -> Dict[str, Any]:
        return {
            'update_interval': 1.0,  # seconds
            'max_symbols': 100,
            'data_retention_hours': 24,
            'websocket_url': 'wss://websocket.example.com/marketdata',
            'api_key': None,
            'api_secret': None
        }

    async def start_streaming(self):
        """Start real-time data streaming."""
        self.is_running = True
        self.logger.info("Starting real-time data streaming")

        try:
            # Connect to websocket
            async with websockets.connect(self.config['websocket_url']) as websocket:
                # Subscribe to symbols
                await self._subscribe_to_symbols(websocket)

                while self.is_running:
                    try:
                        # Receive market data
                        message = await websocket.recv()
                        data = json.loads(message)

                        # Process market data
                        await self._process_market_data(data)

                    except websockets.exceptions.ConnectionClosed:
                        self.logger.warning("WebSocket connection closed, reconnecting...")
                        await asyncio.sleep(5)
                        break

        except Exception as e:
            self.logger.error(f"Error in real-time streaming: {e}")

    def stop_streaming(self):
        """Stop real-time data streaming."""
        self.is_running = False
        self.logger.info("Stopped real-time data streaming")

    def subscribe(self, symbol: str, callback: Callable):
        """Subscribe to real-time data for a symbol."""
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []
        self.subscriptions[symbol].append(callback)

    def unsubscribe(self, symbol: str, callback: Callable):
        """Unsubscribe from real-time data for a symbol."""
        if symbol in self.subscriptions:
            self.subscriptions[symbol].remove(callback)
            if not self.subscriptions[symbol]:
                del self.subscriptions[symbol]

    async def _subscribe_to_symbols(self, websocket):
        """Subscribe to market data for all symbols."""
        symbols = list(self.subscriptions.keys())
        if symbols:
            subscription_message = {
                'type': 'subscribe',
                'symbols': symbols
            }
            await websocket.send(json.dumps(subscription_message))
            self.logger.info(f"Subscribed to {len(symbols)} symbols")

    async def _process_market_data(self, data: Dict[str, Any]):
        """Process incoming market data."""
        try:
            market_data = MarketData(
                symbol=data['symbol'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                price=data['price'],
                volume=data['volume'],
                bid=data.get('bid'),
                ask=data.get('ask'),
                bid_size=data.get('bid_size'),
                ask_size=data.get('ask_size')
            )

            # Store in database
            await self._store_market_data(market_data)

            # Notify subscribers
            await self._notify_subscribers(market_data)

        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")

    async def _store_market_data(self, data: MarketData):
        """Store market data in database."""
        query = """
        INSERT INTO market_data (symbol, timestamp, timeframe, open, high, low, close, volume, date_partition)
        VALUES (?, ?, '1m', ?, ?, ?, ?, ?, ?)
        """

        # Use thread pool for database operations
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._execute_query,
            query,
            (
                data.symbol,
                data.timestamp,
                data.price,  # open
                data.price,  # high
                data.price,  # low
                data.price,  # close
                data.volume,
                data.timestamp.date()
            )
        )

    def _execute_query(self, query: str, params: Tuple):
        """Execute database query in thread pool."""
        try:
            self.connection.execute(query, params)
            self.connection.commit()
        except Exception as e:
            self.logger.error(f"Database error: {e}")

    async def _notify_subscribers(self, data: MarketData):
        """Notify subscribers of new market data."""
        if data.symbol in self.subscriptions:
            for callback in self.subscriptions[data.symbol]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    self.logger.error(f"Error in subscriber callback: {e}")

    def get_real_time_price(self, symbol: str) -> Optional[float]:
        """Get the most recent price for a symbol."""
        query = """
        SELECT close
        FROM market_data
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """

        try:
            df = self.connection.execute(query, (symbol,)).fetchdf()
            if not df.empty:
                return df.iloc[0]['close']
        except Exception as e:
            self.logger.error(f"Error getting real-time price: {e}")

        return None


class OrderManager:
    """
    Order management system for trading.
    """

    def __init__(self, connection, realtime_manager: Optional[RealtimeManager] = None):
        self.connection = connection
        self.realtime_manager = realtime_manager
        self.active_orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.logger = logging.getLogger(__name__)

    def create_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                    quantity: int, price: Optional[float] = None,
                    stop_price: Optional[float] = None) -> Order:
        """Create a new order."""
        import uuid
        order_id = str(uuid.uuid4())

        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )

        self.active_orders[order_id] = order
        self._save_order(order)

        self.logger.info(f"Created order: {order_id} for {symbol}")
        return order

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order."""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order.status = OrderStatus.CANCELLED
            self._update_order(order)
            self.logger.info(f"Cancelled order: {order_id}")
            return True

        return False

    def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get the status of an order."""
        return self.active_orders.get(order_id)

    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all active orders, optionally filtered by symbol."""
        orders = list(self.active_orders.values())
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        return orders

    def update_position(self, symbol: str, quantity: int, price: float):
        """Update position after a trade execution."""
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=0,
                average_cost=0.0,
                current_price=price,
                market_value=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0
            )

        position = self.positions[symbol]

        if position.quantity == 0:
            # Opening position
            position.quantity = quantity
            position.average_cost = price
        elif (position.quantity > 0 and quantity > 0) or (position.quantity < 0 and quantity < 0):
            # Adding to position
            total_quantity = position.quantity + quantity
            total_cost = (position.quantity * position.average_cost) + (quantity * price)
            position.average_cost = total_cost / total_quantity
            position.quantity = total_quantity
        else:
            # Reducing or closing position
            if abs(quantity) >= abs(position.quantity):
                # Closing position
                realized_pnl = (price - position.average_cost) * position.quantity
                position.realized_pnl += realized_pnl
                position.quantity = 0
                position.average_cost = 0.0
            else:
                # Partial close
                realized_pnl = (price - position.average_cost) * quantity
                position.realized_pnl += realized_pnl
                position.quantity += quantity

        position.current_price = price
        position.market_value = position.quantity * price
        position.unrealized_pnl = (price - position.average_cost) * position.quantity

        self._save_position(position)

    def get_positions(self) -> Dict[str, Position]:
        """Get all current positions."""
        return self.positions.copy()

    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value."""
        total_value = 0.0
        for position in self.positions.values():
            total_value += position.market_value
        return total_value

    def _save_order(self, order: Order):
        """Save order to database."""
        query = """
        INSERT INTO orders (order_id, symbol, side, order_type, quantity, price, stop_price, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            self.connection.execute(query, (
                order.order_id,
                order.symbol,
                order.side.value,
                order.order_type.value,
                order.quantity,
                order.price,
                order.stop_price,
                order.status.value,
                order.timestamp
            ))
            self.connection.commit()
        except Exception as e:
            self.logger.error(f"Error saving order: {e}")

    def _update_order(self, order: Order):
        """Update order in database."""
        query = """
        UPDATE orders
        SET status = ?, filled_quantity = ?, average_fill_price = ?
        WHERE order_id = ?
        """

        try:
            self.connection.execute(query, (
                order.status.value,
                order.filled_quantity,
                order.average_fill_price,
                order.order_id
            ))
            self.connection.commit()
        except Exception as e:
            self.logger.error(f"Error updating order: {e}")

    def _save_position(self, position: Position):
        """Save position to database."""
        query = """
        INSERT OR REPLACE INTO positions (symbol, quantity, average_cost, current_price, market_value, unrealized_pnl, realized_pnl, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        try:
            self.connection.execute(query, (
                position.symbol,
                position.quantity,
                position.average_cost,
                position.current_price,
                position.market_value,
                position.unrealized_pnl,
                position.realized_pnl,
                datetime.now()
            ))
            self.connection.commit()
        except Exception as e:
            self.logger.error(f"Error saving position: {e}")


class RiskManager:
    """
    Risk management system for real-time trading.
    """

    def __init__(self, order_manager: OrderManager, config: Optional[Dict[str, Any]] = None):
        self.order_manager = order_manager
        self.config = config or self.get_default_config()
        self.logger = logging.getLogger(__name__)

    def get_default_config(self) -> Dict[str, Any]:
        return {
            'max_position_size': 0.1,      # 10% of portfolio
            'max_portfolio_risk': 0.05,    # 5% max drawdown
            'max_single_stock': 0.05,      # 5% max single stock
            'max_sector_exposure': 0.3,    # 30% max sector exposure
            'stop_loss_threshold': 0.02,   # 2% stop loss
            'max_daily_trades': 10,        # Max trades per day
            'max_concurrent_orders': 5     # Max concurrent orders
        }

    def validate_order(self, order: Order) -> Tuple[bool, str]:
        """Validate an order against risk limits."""
        # Check position size limits
        portfolio_value = self.order_manager.get_portfolio_value()
        if portfolio_value > 0:
            position_size = (order.quantity * order.price) / portfolio_value
            if position_size > self.config['max_position_size']:
                return False, f"Position size {position_size:.2%} exceeds limit {self.config['max_position_size']:.2%}"

        # Check single stock exposure
        current_position = self.order_manager.positions.get(order.symbol)
        if current_position:
            current_exposure = abs(current_position.market_value / portfolio_value)
            new_exposure = current_exposure + ((order.quantity * order.price) / portfolio_value)
            if new_exposure > self.config['max_single_stock']:
                return False, f"Single stock exposure {new_exposure:.2%} exceeds limit {self.config['max_single_stock']:.2%}"

        # Check concurrent orders limit
        active_orders = len(self.order_manager.get_active_orders())
        if active_orders >= self.config['max_concurrent_orders']:
            return False, f"Too many concurrent orders: {active_orders}"

        return True, "Order validated"

    def check_portfolio_risk(self) -> Dict[str, Any]:
        """Check overall portfolio risk metrics."""
        positions = self.order_manager.get_positions()
        portfolio_value = self.order_manager.get_portfolio_value()

        risk_metrics = {
            'total_exposure': 0.0,
            'largest_position': 0.0,
            'concentration_ratio': 0.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0,
            'warnings': []
        }

        if portfolio_value > 0:
            for position in positions.values():
                exposure = abs(position.market_value / portfolio_value)
                risk_metrics['total_exposure'] += exposure
                risk_metrics['largest_position'] = max(risk_metrics['largest_position'], exposure)
                risk_metrics['unrealized_pnl'] += position.unrealized_pnl
                risk_metrics['realized_pnl'] += position.realized_pnl

            if positions:
                risk_metrics['concentration_ratio'] = risk_metrics['largest_position'] / risk_metrics['total_exposure']

        # Check risk thresholds
        if risk_metrics['largest_position'] > self.config['max_single_stock']:
            risk_metrics['warnings'].append(f"Largest position {risk_metrics['largest_position']:.2%} exceeds limit")

        if risk_metrics['unrealized_pnl'] < -portfolio_value * self.config['max_portfolio_risk']:
            risk_metrics['warnings'].append("Portfolio drawdown exceeds threshold")

        return risk_metrics

    def emergency_stop(self, reason: str):
        """Execute emergency stop - cancel all orders."""
        self.logger.warning(f"Emergency stop triggered: {reason}")

        active_orders = self.order_manager.get_active_orders()
        for order in active_orders:
            self.order_manager.cancel_order(order.order_id)

        self.logger.info(f"Cancelled {len(active_orders)} active orders")
