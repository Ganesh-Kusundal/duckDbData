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
from ..config.config_manager import ConfigManager
from ...domain.exceptions import BrokerAPIError
from ...infrastructure.utils.retry import retry_api_call
import asyncio
from functools import wraps
from typing import Callable, Any, Optional
from ..logging import get_logger

logger = get_logger(__name__)


class BrokerAdapter(ABC):
    """Abstract adapter for integrating brokers with DDD architecture."""

    def __init__(self, config_manager: Optional[ConfigManager] = None, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize broker adapter with centralized configuration."""
        self.config_manager = config_manager
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

    @abstractmethod
    async def async_subscribe_symbols(self, symbols: List[str]) -> bool:
        """
        Async method to subscribe to real-time symbols via websocket.
        
        Args:
            symbols: List of symbols to subscribe to
            
        Returns:
            True if subscription successful
        """
        pass

    @abstractmethod
    async def async_get_tick_data(self, symbol: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Async method to get tick data for a symbol.
        
        Args:
            symbol: Symbol to get tick data for
            timeout: Timeout for the request
            
        Returns:
            Tick data dictionary or None if failed
        """
        pass

    @abstractmethod
    async def async_unsubscribe_symbols(self, symbols: List[str]) -> bool:
        """
        Async method to unsubscribe from real-time symbols.
        
        Args:
            symbols: List of symbols to unsubscribe from
            
        Returns:
            True if unsubscription successful
        """
        pass

    def get_credentials(self, broker_name: str) -> Optional[Dict]:
        """
        Get broker credentials using ConfigManager or fallback to legacy method.
        
        Args:
            broker_name: Name of the broker (e.g., 'dhan', 'tradehull')
            
        Returns:
            Dictionary containing api_key, api_secret, access_token
        """
        if self.config_manager:
            try:
                brokers_config = self.config_manager.get_config('brokers')
                brokers = brokers_config.get('brokers', {})
                if broker_name in brokers:
                    credentials = brokers[broker_name]
                    # Handle SecretStr from Pydantic
                    return {
                        'api_key': str(credentials.get('api_key', '')),
                        'api_secret': str(credentials.get('api_secret', '')),
                        'access_token': str(credentials.get('access_token', ''))
                    }
                else:
                    logger.warning(f"Broker {broker_name} not found in config")
            except Exception as e:
                logger.error(f"Failed to load broker credentials from config: {e}")
        
        # Fallback to legacy credential loading (subclasses can override)
        return self._get_legacy_credentials(broker_name)
    
    def _get_legacy_credentials(self, broker_name: str) -> Optional[Dict]:
        """Legacy credential loading method - override in subclasses."""
        logger.warning(f"Using legacy credentials for {broker_name} - please update to use ConfigManager")
        return None

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

    def __init__(self, legacy_broker, config_manager: Optional[ConfigManager] = None, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize with existing broker instance and config manager."""
        super().__init__(config_manager, market_data_repo)
        self.legacy_broker = legacy_broker
        
        # Load credentials using ConfigManager if available
        if self.config_manager:
            credentials = self.get_credentials('dhan')  # Default broker
            if credentials:
                # Configure legacy broker with new credentials if it supports it
                if hasattr(self.legacy_broker, 'set_credentials'):
                    self.legacy_broker.set_credentials(**credentials)

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
            error_msg = f"Failed to place order for {symbol}: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'order_placement',
                'symbol': symbol,
                'side': side.value,
                'quantity': quantity,
                'order_type': order_type.value
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'order_placement', symbol, context=context)
            logger.error("Order placement failed", extra=exc.to_dict())
            raise exc

        return None

    @retry_api_call()
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order using legacy broker."""
        try:
            if hasattr(self.legacy_broker, 'cancel_order'):
                result = self.legacy_broker.cancel_order(order_id)
                return result is not None
        except Exception as e:
            error_msg = f"Failed to cancel order {order_id}: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'cancel_order',
                'order_id': order_id
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'cancel_order', context=context)
            logger.error("Order cancellation failed", extra=exc.to_dict())
            raise exc
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
                            logger.warning(f"Error converting order: {e}")
                            continue
        except Exception as e:
            error_msg = f"Failed to retrieve orders: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'get_orderbook'
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'get_orderbook', context=context)
            logger.error("Failed to get orders", extra=exc.to_dict())
            raise exc
        return orders

    @retry_api_call()
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
                            logger.warning(f"Error converting position: {e}")
                            continue
        except Exception as e:
            error_msg = f"Failed to retrieve positions: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'get_positions'
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'get_positions', context=context)
            logger.error("Failed to get positions", extra=exc.to_dict())
            raise exc
        return positions

    @retry_api_call()
    def get_account_info(self) -> Optional[Account]:
        """Get account info from legacy broker."""
        try:
            if hasattr(self.legacy_broker, 'get_balance'):
                legacy_account = self.legacy_broker.get_balance()
                if legacy_account:
                    return self.convert_legacy_account_to_domain(legacy_account)
        except Exception as e:
            error_msg = f"Failed to retrieve account info: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'get_balance'
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'get_balance', context=context)
            logger.error("Failed to get account info", extra=exc.to_dict())
            raise exc
        return None

    @retry_api_call()
    def get_market_depth(self, symbol: str, depth_level: int = 5) -> Optional[MarketDepth]:
        """Get market depth from legacy broker."""
        try:
            if hasattr(self.legacy_broker, 'get_quote_data'):
                legacy_depth = self.legacy_broker.get_quote_data(symbol)
                if legacy_depth:
                    return self.convert_legacy_depth_to_domain(symbol, legacy_depth)
        except Exception as e:
            error_msg = f"Failed to get market depth for {symbol}: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'get_quote_data',
                'symbol': symbol,
                'depth_level': depth_level
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'get_quote_data', symbol, context=context)
            logger.error("Failed to get market depth", extra=exc.to_dict())
            raise exc
        return None

    async def async_subscribe_symbols(self, symbols: List[str]) -> bool:
        """Async implementation for subscribing to symbols."""
        try:
            # Use asyncio.to_thread to wrap sync subscription if available
            if hasattr(self.legacy_broker, 'subscribe_symbols'):
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self.legacy_broker.subscribe_symbols,
                    symbols
                )
                return result is True
            else:
                # Mock implementation for compatibility
                logger.info(f"Mock async subscription for {len(symbols)} symbols")
                await asyncio.sleep(0.1)  # Simulate async operation
                return True
        except Exception as e:
            error_msg = f"Failed to async subscribe to {len(symbols)} symbols: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'async_subscribe_symbols',
                'symbols_count': len(symbols)
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'async_subscribe_symbols', context=context)
            logger.error("Async subscription failed", extra=exc.to_dict())
            raise exc

    async def async_get_tick_data(self, symbol: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Async implementation for getting tick data."""
        try:
            async def _get_tick_wrapper():
                # Try different legacy methods for tick data
                if hasattr(self.legacy_broker, 'get_tick_data'):
                    return self.legacy_broker.get_tick_data(symbol)
                elif hasattr(self.legacy_broker, 'get_quote_data'):
                    return self.legacy_broker.get_quote_data(symbol)
                else:
                    # Mock tick data for compatibility
                    return {
                        'symbol': symbol,
                        'last_price': 100.0 + (hash(symbol) % 100),
                        'volume': 1000 + (hash(symbol) % 10000),
                        'timestamp': datetime.now().isoformat()
                    }
            
            loop = asyncio.get_event_loop()
            # Use wait_for to handle timeout
            tick_data = await asyncio.wait_for(
                loop.run_in_executor(None, _get_tick_wrapper),
                timeout=timeout
            )
            
            if tick_data:
                return {
                    'symbol': symbol,
                    'data': tick_data,
                    'timestamp': datetime.now()
                }
            return None
            
        except asyncio.TimeoutError:
            error_msg = f"Async tick data timeout for {symbol}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'async_get_tick_data',
                'symbol': symbol,
                'timeout': timeout
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'async_get_tick_data', symbol, context=context)
            logger.error("Async tick data timeout", extra=exc.to_dict())
            raise exc
        except Exception as e:
            error_msg = f"Failed to async get tick data for {symbol}: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'async_get_tick_data',
                'symbol': symbol
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'async_get_tick_data', symbol, context=context)
            logger.error("Async tick data failed", extra=exc.to_dict())
            raise exc

    async def async_unsubscribe_symbols(self, symbols: List[str]) -> bool:
        """Async implementation for unsubscribing from symbols."""
        try:
            if hasattr(self.legacy_broker, 'unsubscribe_symbols'):
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self.legacy_broker.unsubscribe_symbols,
                    symbols
                )
                return result is True
            else:
                # Mock implementation for compatibility
                logger.info(f"Mock async unsubscription for {len(symbols)} symbols")
                await asyncio.sleep(0.05)  # Simulate async operation
                return True
        except Exception as e:
            error_msg = f"Failed to async unsubscribe from {len(symbols)} symbols: {str(e)}"
            context = {
                'broker_name': self.get_broker_name(),
                'endpoint': 'async_unsubscribe_symbols',
                'symbols_count': len(symbols)
            }
            exc = BrokerAPIError(error_msg, self.get_broker_name(), 'async_unsubscribe_symbols', context=context)
            logger.error("Async unsubscription failed", extra=exc.to_dict())
            raise exc


class BrokerService:
    """Service for managing broker operations."""

    def __init__(self, config_manager: Optional[ConfigManager] = None, market_data_repo: Optional[MarketDataRepository] = None):
        """Initialize broker service with centralized configuration."""
        self.config_manager = config_manager
        self.market_data_repo = market_data_repo or DuckDBMarketDataRepository()
        self.adapters: Dict[str, BrokerAdapter] = {}

    def register_broker(self, name: str, adapter: BrokerAdapter):
        """Register a broker adapter."""
        # Ensure adapter has access to config_manager
        if self.config_manager and not adapter.config_manager:
            adapter.config_manager = self.config_manager
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
