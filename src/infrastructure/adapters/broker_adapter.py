"""Adapter to integrate existing brokers with the new DDD architecture."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from abc import ABC, abstractmethod

from ...domain.entities.trading import (
    Order, OrderType, OrderSide, OrderStatus,
    Position, PositionType,
    Trade, Account, MarketDepth
)
from ...domain.repositories.market_data_repo import MarketDataRepository
from ...infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository


class BrokerAdapter(ABC):
    """Abstract adapter for integrating brokers with DDD architecture."""

    def __init__(self, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize broker adapter."""
        self.market_data_repo = market_data_repo or DuckDBMarketDataRepository()

    @abstractmethod
    def get_broker_name(self) -> str:
        """Get broker name."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        pass

    @abstractmethod
    def place_order(self,
                   symbol: str,
                   side: OrderSide,
                   quantity: int,
                   order_type: OrderType = OrderType.MARKET,
                   price: Optional[Decimal] = None,
                   trigger_price: Optional[Decimal] = None) -> Optional[Order]:
        """Place an order and return domain entity."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    def get_orders(self) -> List[Order]:
        """Get all orders."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all positions."""
        pass

    @abstractmethod
    def get_account_info(self) -> Optional[Account]:
        """Get account information."""
        pass

    @abstractmethod
    def get_market_depth(self, symbol: str, depth_level: int = 5) -> Optional[MarketDepth]:
        """Get market depth for symbol."""
        pass

    def convert_legacy_order_to_domain(self, legacy_order: Dict[str, Any]) -> Order:
        """Convert legacy order format to domain Order entity."""
        # Map legacy order status to domain enum
        status_mapping = {
            'PENDING': OrderStatus.PENDING,
            'OPEN': OrderStatus.OPEN,
            'COMPLETE': OrderStatus.FILLED,
            'CANCELLED': OrderStatus.CANCELLED,
            'REJECTED': OrderStatus.REJECTED,
        }

        # Map legacy order type
        type_mapping = {
            'MARKET': OrderType.MARKET,
            'LIMIT': OrderType.LIMIT,
            'SL-M': OrderType.SL_MARKET,
            'SL-L': OrderType.SL_LIMIT,
        }

        # Map legacy side
        side_mapping = {
            'BUY': OrderSide.BUY,
            'SELL': OrderSide.SELL,
        }

        return Order(
            order_id=str(legacy_order.get('orderid', legacy_order.get('order_id', ''))),
            symbol=legacy_order.get('symbol', legacy_order.get('tradingsymbol', '')),
            side=side_mapping.get(legacy_order.get('transactiontype', legacy_order.get('side', '')).upper(), OrderSide.BUY),
            order_type=type_mapping.get(legacy_order.get('ordertype', legacy_order.get('order_type', '')).upper(), OrderType.MARKET),
            quantity=int(legacy_order.get('quantity', 0)),
            price=Decimal(str(legacy_order.get('price', 0))) if legacy_order.get('price') else None,
            trigger_price=Decimal(str(legacy_order.get('triggerprice', 0))) if legacy_order.get('triggerprice') else None,
            status=status_mapping.get(legacy_order.get('status', '').upper(), OrderStatus.PENDING),
            timestamp=datetime.now(),  # Use current time if not provided
            exchange=legacy_order.get('exchange', 'NSE'),
            product_type=legacy_order.get('producttype', 'INTRADAY'),
            metadata=legacy_order
        )

    def convert_legacy_position_to_domain(self, legacy_position: Dict[str, Any]) -> Position:
        """Convert legacy position format to domain Position entity."""
        position_type = PositionType.LONG if legacy_position.get('netqty', 0) > 0 else PositionType.SHORT

        return Position(
            symbol=legacy_position.get('symbol', legacy_position.get('tradingsymbol', '')),
            position_type=position_type,
            quantity=abs(int(legacy_position.get('netqty', 0))),
            average_price=Decimal(str(legacy_position.get('avgnetprice', legacy_position.get('average_price', 0)))),
            current_price=Decimal(str(legacy_position.get('ltp', 0))) if legacy_position.get('ltp') else None,
            unrealized_pnl=Decimal(str(legacy_position.get('unrealised', 0))) if legacy_position.get('unrealised') else None,
            realized_pnl=Decimal(str(legacy_position.get('realised', 0))),
            timestamp=datetime.now(),
            exchange=legacy_position.get('exchange', 'NSE'),
            metadata=legacy_position
        )

    def convert_legacy_account_to_domain(self, legacy_account: Dict[str, Any]) -> Account:
        """Convert legacy account format to domain Account entity."""
        return Account(
            account_id=str(legacy_account.get('clientid', legacy_account.get('client_id', ''))),
            balance=Decimal(str(legacy_account.get('net', legacy_account.get('balance', 0)))),
            margin_available=Decimal(str(legacy_account.get('availablecash', legacy_account.get('margin_available', 0)))),
            margin_used=Decimal(str(legacy_account.get('usedmargin', legacy_account.get('margin_used', 0)))),
            timestamp=datetime.now(),
            metadata=legacy_account
        )

    def convert_legacy_depth_to_domain(self, symbol: str, legacy_depth: Dict[str, Any]) -> MarketDepth:
        """Convert legacy depth format to domain MarketDepth entity."""
        bids = []
        asks = []

        # Convert bids
        if 'bids' in legacy_depth:
            for bid in legacy_depth['bids'][:20]:  # Limit to 20 levels
                bids.append({
                    'price': Decimal(str(bid.get('price', 0))),
                    'quantity': int(bid.get('quantity', 0))
                })

        # Convert asks
        if 'asks' in legacy_depth:
            for ask in legacy_depth['asks'][:20]:  # Limit to 20 levels
                asks.append({
                    'price': Decimal(str(ask.get('price', 0))),
                    'quantity': int(ask.get('quantity', 0))
                })

        return MarketDepth(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.now(),
            depth_level=len(bids) if bids else 5,
            exchange=legacy_depth.get('exchange', 'NSE'),
            metadata=legacy_depth
        )


class LegacyBrokerAdapter(BrokerAdapter):
    """Adapter for existing broker implementations."""

    def __init__(self, legacy_broker, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize with existing broker instance."""
        super().__init__(market_data_repo)
        self.legacy_broker = legacy_broker

    def get_broker_name(self) -> str:
        """Get broker name from legacy broker."""
        return getattr(self.legacy_broker, 'broker_name', 'LegacyBroker')

    def is_connected(self) -> bool:
        """Check if legacy broker is connected."""
        if hasattr(self.legacy_broker, 'is_connected'):
            return self.legacy_broker.is_connected()
        if hasattr(self.legacy_broker, 'is_available'):
            return self.legacy_broker.is_available()
        return True  # Assume connected if no method available

    def place_order(self,
                   symbol: str,
                   side: OrderSide,
                   quantity: int,
                   order_type: OrderType = OrderType.MARKET,
                   price: Optional[Decimal] = None,
                   trigger_price: Optional[Decimal] = None) -> Optional[Order]:
        """Place order using legacy broker."""
        try:
            # Map domain enums to legacy format
            legacy_side = side.value
            legacy_type = order_type.value

            # Call legacy broker method
            if hasattr(self.legacy_broker, 'order_placement'):
                result = self.legacy_broker.order_placement(
                    tradingsymbol=symbol,
                    exchange="NSE",
                    quantity=quantity,
                    price=float(price) if price else 0,
                    trigger_price=float(trigger_price) if trigger_price else 0,
                    order_type=legacy_type,
                    transaction_type=legacy_side,
                    trade_type="MIS",  # Default to intraday
                    product_type="INTRADAY"
                )

                if result:
                    # Create domain order from result
                    return Order(
                        order_id=str(result),
                        symbol=symbol,
                        side=side,
                        order_type=order_type,
                        quantity=quantity,
                        price=price,
                        trigger_price=trigger_price,
                        status=OrderStatus.PENDING,
                        timestamp=datetime.now()
                    )

        except Exception as e:
            print(f"Error placing order: {e}")

        return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order using legacy broker."""
        try:
            if hasattr(self.legacy_broker, 'cancel_order'):
                result = self.legacy_broker.cancel_order(order_id)
                return result is not None
        except Exception as e:
            print(f"Error canceling order: {e}")
        return False

    def get_orders(self) -> List[Order]:
        """Get orders from legacy broker."""
        orders = []
        try:
            if hasattr(self.legacy_broker, 'get_orderbook'):
                legacy_orders = self.legacy_broker.get_orderbook()
                if legacy_orders:
                    for legacy_order in legacy_orders:
                        try:
                            domain_order = self.convert_legacy_order_to_domain(legacy_order)
                            orders.append(domain_order)
                        except Exception as e:
                            print(f"Error converting order: {e}")
        except Exception as e:
            print(f"Error getting orders: {e}")
        return orders

    def get_positions(self) -> List[Position]:
        """Get positions from legacy broker."""
        positions = []
        try:
            if hasattr(self.legacy_broker, 'get_positions'):
                legacy_positions = self.legacy_broker.get_positions()
                if legacy_positions:
                    for legacy_pos in legacy_positions:
                        try:
                            domain_pos = self.convert_legacy_position_to_domain(legacy_pos)
                            positions.append(domain_pos)
                        except Exception as e:
                            print(f"Error converting position: {e}")
        except Exception as e:
            print(f"Error getting positions: {e}")
        return positions

    def get_account_info(self) -> Optional[Account]:
        """Get account info from legacy broker."""
        try:
            if hasattr(self.legacy_broker, 'get_balance'):
                legacy_account = self.legacy_broker.get_balance()
                if legacy_account:
                    return self.convert_legacy_account_to_domain(legacy_account)
        except Exception as e:
            print(f"Error getting account info: {e}")
        return None

    def get_market_depth(self, symbol: str, depth_level: int = 5) -> Optional[MarketDepth]:
        """Get market depth from legacy broker."""
        try:
            if hasattr(self.legacy_broker, 'get_quote_data'):
                legacy_depth = self.legacy_broker.get_quote_data(symbol)
                if legacy_depth:
                    return self.convert_legacy_depth_to_domain(symbol, legacy_depth)
        except Exception as e:
            print(f"Error getting market depth: {e}")
        return None


class BrokerService:
    """Service for managing broker operations."""

    def __init__(self, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize broker service."""
        self.market_data_repo = market_data_repo or DuckDBMarketDataRepository()
        self.adapters: Dict[str, BrokerAdapter] = {}

    def register_broker(self, name: str, adapter: BrokerAdapter):
        """Register a broker adapter."""
        self.adapters[name] = adapter

    def get_broker(self, name: str) -> Optional[BrokerAdapter]:
        """Get a registered broker."""
        return self.adapters.get(name)

    def get_available_brokers(self) -> List[str]:
        """Get list of available brokers."""
        return list(self.adapters.keys())

    def execute_order(self,
                     broker_name: str,
                     symbol: str,
                     side: OrderSide,
                     quantity: int,
                     order_type: OrderType = OrderType.MARKET,
                     price: Optional[Decimal] = None,
                     trigger_price: Optional[Decimal] = None) -> Optional[Order]:
        """Execute order on specified broker."""
        broker = self.get_broker(broker_name)
        if broker:
            return broker.place_order(symbol, side, quantity, order_type, price, trigger_price)
        return None

    def get_all_orders(self, broker_name: str) -> List[Order]:
        """Get all orders from specified broker."""
        broker = self.get_broker(broker_name)
        if broker:
            return broker.get_orders()
        return []

    def get_all_positions(self, broker_name: str) -> List[Position]:
        """Get all positions from specified broker."""
        broker = self.get_broker(broker_name)
        if broker:
            return broker.get_positions()
        return []

    def get_account_balance(self, broker_name: str) -> Optional[Account]:
        """Get account balance from specified broker."""
        broker = self.get_broker(broker_name)
        if broker:
            return broker.get_account_info()
        return None
