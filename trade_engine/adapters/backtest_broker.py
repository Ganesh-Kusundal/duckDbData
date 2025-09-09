"""
Backtest Broker Adapter
=====================

Simulates broker behavior for backtesting with realistic
slippage, fees, and execution timing.
"""

from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import asyncio

from ..domain.models import OrderIntent, Order, Fill, Position, AccountState, Side, OrderStatus
from ..ports.broker import BrokerPort
from ..domain.nse_utils import nse_utils


class BacktestBroker(BrokerPort):
    """Backtest broker that simulates realistic execution"""

    def __init__(self, config: dict, initial_capital: Decimal = Decimal('100000')):
        self.config = config
        self.cash = initial_capital
        self.margin_used = Decimal('0')
        self.positions: Dict[str, Position] = {}
        self.pending_orders: Dict[str, Order] = {}
        self.order_counter = 0

    async def place_order(self, order_intent: OrderIntent) -> Order:
        """Place order with simulated execution"""
        # Apply slippage and fees
        adjusted_intent = self.apply_slippage_and_fees(order_intent, order_intent.price)

        order = Order(
            id=f"BT_{self.order_counter}",
            symbol=order_intent.symbol,
            side=order_intent.side,
            quantity=order_intent.quantity,
            order_type=order_intent.order_type,
            status=OrderStatus.SUBMITTED,
            price=adjusted_intent.price,
            stop_price=adjusted_intent.stop_price,
            timestamp=datetime.now()
        )

        self.pending_orders[order.id] = order
        self.order_counter += 1

        # Simulate immediate fill for backtesting
        await asyncio.sleep(0.001)  # Micro delay for realism
        return await self._simulate_fill(order)

    async def amend_order(self, order_id: str, price: Optional[Decimal] = None,
                         quantity: Optional[int] = None) -> Order:
        """Amend order (simplified for backtest)"""
        if order_id not in self.pending_orders:
            raise ValueError(f"Order {order_id} not found")

        order = self.pending_orders[order_id]
        if price:
            order.price = price
        if quantity:
            order.quantity = quantity

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if order_id in self.pending_orders:
            order = self.pending_orders[order_id]
            order.status = OrderStatus.CANCELLED
            del self.pending_orders[order_id]
            return True
        return False

    async def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get order status"""
        return self.pending_orders.get(order_id)

    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        return list(self.positions.values())

    async def get_account_state(self) -> AccountState:
        """Get account state"""
        total_pnl = sum(p.unrealized_pnl + p.realized_pnl for p in self.positions.values())

        return AccountState(
            timestamp=datetime.now(),
            cash=self.cash,
            margin_used=self.margin_used,
            margin_available=self.cash - self.margin_used,
            day_pnl=total_pnl,
            total_pnl=total_pnl,
            positions=list(self.positions.values())
        )

    def apply_slippage_and_fees(self, order_intent: OrderIntent,
                               market_price: Decimal) -> OrderIntent:
        """Apply slippage and fees to order"""
        # Apply slippage
        slippage_adjustment = nse_utils.apply_slippage(market_price, self.config['sizing']['slippage_bps'])

        # Adjust price based on slippage
        if order_intent.side == Side.BUY:
            adjusted_price = market_price + slippage_adjustment
        else:
            adjusted_price = market_price - slippage_adjustment

        # Round to tick size
        adjusted_price = nse_utils.round_to_tick(adjusted_price)

        return OrderIntent(
            symbol=order_intent.symbol,
            side=order_intent.side,
            quantity=order_intent.quantity,
            order_type=order_intent.order_type,
            price=adjusted_price,
            stop_price=order_intent.stop_price,
            time_in_force=order_intent.time_in_force,
            metadata={**order_intent.metadata, 'slippage_applied': True}
        )

    async def _simulate_fill(self, order: Order) -> Order:
        """Simulate order fill"""
        # Calculate fees
        trade_value = order.price * order.quantity
        fees = nse_utils.calculate_fees(trade_value, order.side == Side.SELL)

        # Create fill
        fill = Fill(
            timestamp=datetime.now(),
            quantity=order.quantity,
            price=order.price,
            fee=fees['total']
        )

        order.fills.append(fill)
        order.avg_fill_price = order.price
        order.filled_quantity = order.quantity
        order.status = OrderStatus.FILLED

        # Update cash and positions
        if order.side == Side.BUY:
            self.cash -= (trade_value + fees['total'])
            self._update_position(order.symbol, order.quantity, order.price)
        else:
            self.cash += (trade_value - fees['total'])
            self._update_position(order.symbol, -order.quantity, order.price)

        # Remove from pending
        if order.id in self.pending_orders:
            del self.pending_orders[order.id]

        return order

    def _update_position(self, symbol: str, quantity: int, price: Decimal):
        """Update position after fill"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=0,
                avg_cost=Decimal('0'),
                entry_timestamp=datetime.now()
            )

        position = self.positions[symbol]

        if position.quantity == 0:
            # New position
            position.quantity = quantity
            position.avg_cost = price
        else:
            # Update existing position
            total_cost = (position.avg_cost * position.quantity) + (price * quantity)
            position.quantity += quantity
            if position.quantity != 0:
                position.avg_cost = total_cost / abs(position.quantity)

        # Update P&L
        if position.current_price:
            position.unrealized_pnl = (position.current_price - position.avg_cost) * position.quantity
