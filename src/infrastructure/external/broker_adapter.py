"""
Broker Adapter Implementation
Provides adapter pattern for broker integrations
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .base_external_adapter import BaseExternalAdapter, ExternalServiceResult

logger = logging.getLogger(__name__)


@dataclass
class BrokerCredentials:
    """Broker authentication credentials"""
    client_id: str
    access_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    session_token: Optional[str] = None


@dataclass
class OrderRequest:
    """Order placement request"""
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: int
    order_type: str  # 'MARKET', 'LIMIT', 'SL', 'SL-M'
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    exchange: str = "NSE"
    product_type: str = "INTRADAY"


@dataclass
class OrderResponse:
    """Order placement response"""
    order_id: str
    status: str
    message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class OrderStatus:
    """Order status information"""
    order_id: str
    status: str
    symbol: str
    side: str
    quantity: int
    filled_quantity: int
    price: Optional[float] = None
    average_price: Optional[float] = None
    order_type: str = "MARKET"
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Position:
    """Position information"""
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    unrealized_pnl: float
    exchange: str = "NSE"
    product_type: str = "INTRADAY"


@dataclass
class MarketData:
    """Market data from broker"""
    symbol: str
    last_price: float
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    volume: Optional[int] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BrokerAdapter(ABC):
    """
    Abstract Broker Adapter
    Defines interface for broker integrations
    """

    @abstractmethod
    async def authenticate(self, credentials: BrokerCredentials) -> bool:
        """Authenticate with broker"""
        pass

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel an order"""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status"""
        pass

    @abstractmethod
    async def get_all_orders(self) -> List[OrderStatus]:
        """Get all orders"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions"""
        pass

    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get market data for symbol"""
        pass

    @abstractmethod
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance information"""
        pass

    @abstractmethod
    async def is_authenticated(self) -> bool:
        """Check if authenticated"""
        pass

    @abstractmethod
    async def logout(self) -> bool:
        """Logout from broker"""
        pass


class DhanBrokerAdapter(BaseExternalAdapter, BrokerAdapter):
    """
    Dhan Broker Adapter Implementation
    Integrates with Dhan trading platform
    """

    def __init__(self,
                 client_id: str,
                 access_token: str,
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.dhan.co"):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            max_retries=3,
            rate_limit_per_minute=60
        )

        self.client_id = client_id
        self.access_token = access_token
        self.authenticated = False

        # Dhan specific mappings
        self.exchange_codes = {
            'NSE': 'NSE',
            'BSE': 'BSE'
        }

        self.order_types = {
            'MARKET': 'MARKET',
            'LIMIT': 'LIMIT',
            'SL': 'SL',
            'SL-M': 'SL-M'
        }

        self.product_types = {
            'INTRADAY': 'INTRADAY',
            'DELIVERY': 'CNC',
            'MARGIN': 'MARGIN'
        }

    async def authenticate(self, credentials: BrokerCredentials) -> bool:
        """Authenticate with Dhan broker"""
        try:
            # Test authentication with a simple API call
            result = await self._make_request('GET', 'v2/fundlimit')

            if result.success:
                self.authenticated = True
                self.logger.info("Successfully authenticated with Dhan broker")
                return True
            else:
                self.authenticated = False
                self.logger.error(f"Authentication failed: {result.error}")
                return False

        except Exception as e:
            self.authenticated = False
            self.logger.error(f"Authentication error: {e}")
            return False

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order with Dhan broker"""
        if not self.is_authenticated():
            return OrderResponse(
                order_id="",
                status="REJECTED",
                message="Not authenticated"
            )

        try:
            # Prepare order payload for Dhan API
            payload = {
                "dhanClientId": self.client_id,
                "transactionType": order.side.upper(),
                "exchangeSegment": self.exchange_codes.get(order.exchange, order.exchange),
                "productType": self.product_types.get(order.product_type, order.product_type),
                "orderType": self.order_types.get(order.order_type, order.order_type),
                "validity": "DAY",
                "securityId": order.symbol,
                "quantity": order.quantity
            }

            # Add price fields based on order type
            if order.price:
                payload["price"] = order.price

            if order.trigger_price:
                payload["triggerPrice"] = order.trigger_price

            # Place order
            result = await self._make_request('POST', 'v2/orders', json_data=payload)

            if result.success and result.data:
                order_id = result.data.get('orderId', '')
                status = result.data.get('orderStatus', 'UNKNOWN')

                self.logger.info(f"Order placed: {order_id} - {status}")

                return OrderResponse(
                    order_id=order_id,
                    status=status,
                    message=result.data.get('message'),
                    timestamp=datetime.now()
                )
            else:
                return OrderResponse(
                    order_id="",
                    status="REJECTED",
                    message=result.error or "Order placement failed",
                    timestamp=datetime.now()
                )

        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return OrderResponse(
                order_id="",
                status="ERROR",
                message=str(e),
                timestamp=datetime.now()
            )

    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel order with Dhan broker"""
        if not self.is_authenticated():
            return OrderResponse(
                order_id=order_id,
                status="REJECTED",
                message="Not authenticated"
            )

        try:
            result = await self._make_request('DELETE', f'v2/orders/{order_id}')

            if result.success:
                self.logger.info(f"Order cancelled: {order_id}")
                return OrderResponse(
                    order_id=order_id,
                    status="CANCELLED",
                    message="Order cancelled successfully",
                    timestamp=datetime.now()
                )
            else:
                return OrderResponse(
                    order_id=order_id,
                    status="REJECTED",
                    message=result.error or "Cancellation failed",
                    timestamp=datetime.now()
                )

        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return OrderResponse(
                order_id=order_id,
                status="ERROR",
                message=str(e),
                timestamp=datetime.now()
            )

    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status from Dhan broker"""
        if not self.is_authenticated():
            return None

        try:
            result = await self._make_request('GET', f'v2/orders/{order_id}')

            if result.success and result.data:
                data = result.data
                return OrderStatus(
                    order_id=data.get('orderId', order_id),
                    status=data.get('orderStatus', 'UNKNOWN'),
                    symbol=data.get('securityId', ''),
                    side=data.get('transactionType', ''),
                    quantity=data.get('quantity', 0),
                    filled_quantity=data.get('filledQty', 0),
                    price=data.get('price'),
                    average_price=data.get('averagePrice'),
                    order_type=data.get('orderType', 'MARKET'),
                    timestamp=datetime.now()
                )
            else:
                self.logger.warning(f"Could not get order status for {order_id}: {result.error}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting order status for {order_id}: {e}")
            return None

    async def get_all_orders(self) -> List[OrderStatus]:
        """Get all orders from Dhan broker"""
        if not self.is_authenticated():
            return []

        try:
            result = await self._make_request('GET', 'v2/orders')

            if result.success and result.data:
                orders = []
                for order_data in result.data:
                    order = OrderStatus(
                        order_id=order_data.get('orderId', ''),
                        status=order_data.get('orderStatus', 'UNKNOWN'),
                        symbol=order_data.get('securityId', ''),
                        side=order_data.get('transactionType', ''),
                        quantity=order_data.get('quantity', 0),
                        filled_quantity=order_data.get('filledQty', 0),
                        price=order_data.get('price'),
                        average_price=order_data.get('averagePrice'),
                        order_type=order_data.get('orderType', 'MARKET'),
                        timestamp=datetime.now()
                    )
                    orders.append(order)

                self.logger.info(f"Retrieved {len(orders)} orders")
                return orders
            else:
                self.logger.warning(f"Could not get orders: {result.error}")
                return []

        except Exception as e:
            self.logger.error(f"Error getting all orders: {e}")
            return []

    async def get_positions(self) -> List[Position]:
        """Get current positions from Dhan broker"""
        if not self.is_authenticated():
            return []

        try:
            result = await self._make_request('GET', 'v2/positions')

            if result.success and result.data:
                positions = []
                for pos_data in result.data:
                    # Get current market price for P&L calculation
                    current_price = await self._get_current_price(pos_data.get('securityId', ''))

                    position = Position(
                        symbol=pos_data.get('securityId', ''),
                        quantity=pos_data.get('netQty', 0),
                        average_price=pos_data.get('avgPrice', 0.0),
                        current_price=current_price or pos_data.get('ltp', 0.0),
                        unrealized_pnl=pos_data.get('unrealizedProfit', 0.0),
                        exchange=pos_data.get('exchangeSegment', 'NSE'),
                        product_type=pos_data.get('productType', 'INTRADAY')
                    )
                    positions.append(position)

                self.logger.info(f"Retrieved {len(positions)} positions")
                return positions
            else:
                self.logger.warning(f"Could not get positions: {result.error}")
                return []

        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []

    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get market data for symbol from Dhan"""
        try:
            # Use Dhan's quote API
            result = await self._make_request('GET', f'v2/marketfeed/quote', params={'securityId': symbol})

            if result.success and result.data:
                data = result.data[0] if isinstance(result.data, list) else result.data
                return MarketData(
                    symbol=symbol,
                    last_price=data.get('lastPrice', 0.0),
                    bid_price=data.get('bidPrice'),
                    ask_price=data.get('askPrice'),
                    volume=data.get('volume'),
                    timestamp=datetime.now()
                )
            else:
                self.logger.warning(f"Could not get market data for {symbol}: {result.error}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None

    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance information"""
        if not self.is_authenticated():
            return {'error': 'Not authenticated'}

        try:
            result = await self._make_request('GET', 'v2/fundlimit')

            if result.success and result.data:
                self.logger.info("Retrieved account balance")
                return result.data
            else:
                self.logger.warning(f"Could not get account balance: {result.error}")
                return {'error': result.error}

        except Exception as e:
            self.logger.error(f"Error getting account balance: {e}")
            return {'error': str(e)}

    async def is_authenticated(self) -> bool:
        """Check if authenticated with Dhan"""
        if not self.authenticated:
            return False

        # Perform a quick health check
        try:
            result = await self._make_request('GET', 'v2/fundlimit')
            return result.success
        except Exception:
            self.authenticated = False
            return False

    async def logout(self) -> bool:
        """Logout from Dhan broker"""
        try:
            # Note: Dhan might not have explicit logout, so we just clear authentication
            self.authenticated = False
            self.logger.info("Logged out from Dhan broker")
            return True
        except Exception as e:
            self.logger.error(f"Error during logout: {e}")
            return False

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol (helper method)"""
        try:
            market_data = await self.get_market_data(symbol)
            return market_data.last_price if market_data else None
        except Exception:
            return None

    async def _perform_health_check(self) -> ExternalServiceResult:
        """Dhan-specific health check"""
        if not self.is_authenticated():
            return ExternalServiceResult(success=False, error="Not authenticated")

        # Try to get account balance as health check
        return await self._make_request('GET', 'v2/fundlimit')
