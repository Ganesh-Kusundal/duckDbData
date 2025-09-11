#!/usr/bin/env python3
"""
DhanHQ Broker Adapter for Domain Layer Integration

This module provides a DhanBrokerAdapter that bridges the existing DhanHQ broker module
with the domain-driven broker integration layer, enabling seamless integration without
modifying the original broker implementation.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import sys
import os

# Add broker module to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
broker_path = os.path.join(project_root, 'broker')
sys.path.insert(0, broker_path)

from broker import get_broker
from domain.broker_integration.entities.broker_connection import BrokerCredentials
from domain.broker_integration.value_objects.order_execution import (
    BrokerOrder, ExecutionReport, BrokerCapabilities
)
from infrastructure.monitoring.metrics_collector import get_metrics_collector, timed

logger = logging.getLogger(__name__)


class DhanBrokerAdapter:
    """
    DhanHQ Broker Adapter for Domain Layer Integration

    This adapter provides a clean interface between the domain layer and the existing
    DhanHQ broker module, implementing the BrokerAPIAdapter protocol while leveraging
    the full functionality of the broker module.
    """

    def __init__(self):
        self.broker = None
        self.connected = False
        self.authenticated = False
        self.metrics = get_metrics_collector()
        self._last_health_check = None
        self._health_check_interval = 60  # seconds

    @timed("broker.dhan.connect")
    async def connect(self, credentials: BrokerCredentials) -> Dict[str, Any]:
        """
        Establish connection to DhanHQ broker.

        Uses the existing broker module's singleton pattern and connection management.
        """
        try:
            # Set environment variables for broker authentication
            if credentials.api_key:
                os.environ['DHAN_CLIENT_ID'] = credentials.api_key
            if credentials.access_token:
                os.environ['DHAN_API_TOKEN'] = credentials.access_token

            # Initialize broker using existing module
            self.broker = get_broker()

            # Test connection
            try:
                # Test basic connectivity
                balance = await self._run_in_executor(self.broker.get_balance)
                self.connected = True

                logger.info("✅ DhanHQ broker connection established successfully")
                self.metrics.increment_counter("broker.dhan.connections.established")

                return {
                    "success": True,
                    "connection_id": f"dhan_{credentials.api_key[:8] if credentials.api_key else 'unknown'}",
                    "broker_version": "v2.1.0",
                    "connection_time": datetime.now().isoformat(),
                    "balance_info": balance
                }

            except Exception as e:
                logger.error(f"❌ DhanHQ broker authentication failed: {e}")
                return {
                    "success": False,
                    "error": f"Authentication failed: {str(e)}"
                }

        except Exception as e:
            logger.error(f"❌ DhanHQ broker connection failed: {e}")
            self.metrics.increment_counter("broker.dhan.connections.failed")
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }

    @timed("broker.dhan.authenticate")
    async def authenticate(self, credentials: BrokerCredentials) -> Dict[str, Any]:
        """
        Authenticate with DhanHQ broker.

        Since authentication is handled during connection in the broker module,
        this method validates the existing authentication.
        """
        try:
            if not self.connected or not self.broker:
                return {"success": False, "error": "Not connected"}

            # Test authentication by attempting to get account info
            balance = await self._run_in_executor(self.broker.get_balance)

            if balance:
                self.authenticated = True

                # Handle different response formats from broker
                if isinstance(balance, dict):
                    account_id = balance.get('clientId', credentials.api_key[:8] if credentials.api_key else 'unknown')
                elif isinstance(balance, (int, float)):
                    # If balance is just a number, use API key as account ID
                    account_id = credentials.api_key[:8] if credentials.api_key else 'unknown'
                else:
                    account_id = str(credentials.api_key[:8]) if credentials.api_key else 'unknown'

                logger.info(f"✅ DhanHQ broker authentication successful for account: {account_id}")

                return {
                    "success": True,
                    "account_id": account_id,
                    "permissions": ["READ", "TRADE", "DATA"],
                    "balance": balance
                }
            else:
                return {"success": False, "error": "Authentication validation failed"}

        except Exception as e:
            logger.error(f"❌ DhanHQ broker authentication failed: {e}")
            return {
                "success": False,
                "error": f"Authentication failed: {str(e)}"
            }

    @timed("broker.dhan.get_account_info")
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from DhanHQ."""
        try:
            if not self.authenticated or not self.broker:
                return {"success": False, "error": "Not authenticated"}

            balance = await self._run_in_executor(self.broker.get_balance)

            if balance:
                # Handle different response formats from broker
                if isinstance(balance, dict):
                    account_number = balance.get('clientId', 'unknown')
                    cash_balance = float(balance.get('net', 0))
                elif isinstance(balance, (int, float)):
                    # If balance is just a number, treat it as the cash balance
                    account_number = 'unknown'
                    cash_balance = float(balance)
                else:
                    account_number = 'unknown'
                    cash_balance = 0.0

                return {
                    "success": True,
                    "account_number": account_number,
                    "account_type": "TRADING",
                    "currency": "INR",
                    "cash_balance": cash_balance,
                    "buying_power": cash_balance,
                    "total_value": cash_balance,
                    "margin_used": 0.0,  # DhanHQ provides net balance
                    "available_margin": cash_balance
                }
            else:
                return {"success": False, "error": "Failed to retrieve account info"}

        except Exception as e:
            logger.error(f"❌ DhanHQ get account info failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.dhan.get_positions")
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from DhanHQ."""
        try:
            if not self.authenticated or not self.broker:
                return []

            # DhanHQ broker module doesn't have a direct positions method
            # We'll return empty list for now, but this could be extended
            # if DhanHQ provides positions data through other endpoints
            positions = []

            logger.info(f"📊 Retrieved {len(positions)} positions from DhanHQ")

            return positions

        except Exception as e:
            logger.error(f"❌ DhanHQ get positions failed: {e}")
            return []

    @timed("broker.dhan.submit_order")
    async def submit_order(self, order: BrokerOrder) -> Dict[str, Any]:
        """Submit order to DhanHQ broker."""
        try:
            if not self.authenticated or not self.broker:
                return {"success": False, "error": "Not authenticated"}

            # Map domain order to broker module parameters
            order_params = self._map_order_to_broker_params(order)

            # Submit order using broker module
            if order.order_type.upper() == 'BRACKET':
                result = await self._run_in_executor(
                    self.broker.place_bracket_order,
                    **order_params
                )
            else:
                # For other order types, we'd need to extend the broker module
                # or use the appropriate DhanHQ API endpoint
                return {
                    "success": False,
                    "error": f"Order type {order.order_type} not yet supported"
                }

            if result:
                broker_order_id = str(result)
                logger.info(f"✅ DhanHQ order submitted successfully: {broker_order_id}")

                return {
                    "success": True,
                    "broker_order_id": broker_order_id,
                    "status": "SUBMITTED",
                    "estimated_fill_price": float(order.price) if order.price else None,
                    "commission_estimate": 0.0  # To be calculated based on DhanHQ fees
                }
            else:
                return {"success": False, "error": "Order submission failed"}

        except Exception as e:
            logger.error(f"❌ DhanHQ submit order failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.dhan.cancel_order")
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order on DhanHQ."""
        try:
            if not self.authenticated or not self.broker:
                return {"success": False, "error": "Not authenticated"}

            # DhanHQ broker module doesn't have a direct cancel method yet
            # This would need to be implemented in the broker module
            return {
                "success": False,
                "error": "Order cancellation not yet implemented in broker module"
            }

        except Exception as e:
            logger.error(f"❌ DhanHQ cancel order failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.dhan.get_order_status")
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from DhanHQ."""
        try:
            if not self.authenticated or not self.broker:
                return {"success": False, "error": "Not authenticated"}

            # Get super orders from broker module
            orders = await self._run_in_executor(self.broker.get_super_orders)

            # Find the specific order
            for order in orders:
                if str(order.get('orderId', '')) == order_id:
                    return {
                        "success": True,
                        "order_id": order_id,
                        "status": order.get('orderStatus', 'UNKNOWN'),
                        "filled_quantity": order.get('filledQty', 0),
                        "remaining_quantity": order.get('remainingQty', 0),
                        "average_price": float(order.get('avgPrice', 0)),
                        "last_update": datetime.now().isoformat()
                    }

            return {"success": False, "error": f"Order {order_id} not found"}

        except Exception as e:
            logger.error(f"❌ DhanHQ get order status failed: {e}")
            return {"success": False, "error": str(e)}

    def get_capabilities(self) -> BrokerCapabilities:
        """Get DhanHQ broker capabilities."""
        return BrokerCapabilities(
            supports_market_orders=True,
            supports_limit_orders=True,
            supports_stop_orders=True,
            supports_stop_limit_orders=True,
            supports_options_trading=True,
            supports_futures_trading=True,
            supports_margin_trading=True,
            realtime_data_available=True,
            historical_data_available=True,
            max_orders_per_second=10  # Conservative limit for DhanHQ
        )

    async def get_quote_data(self, symbol: str) -> Dict[str, Any]:
        """Get market quote data from DhanHQ."""
        try:
            if not self.authenticated or not self.broker:
                return {"success": False, "error": "Not authenticated"}

            quote = await self._run_in_executor(self.broker.get_quote_data, symbol)

            if quote:
                return {
                    "success": True,
                    "symbol": symbol,
                    "quote": quote,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": "Failed to get quote"}

        except Exception as e:
            logger.error(f"❌ DhanHQ get quote failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_historical_data(self, symbol: str, timeframe: str = "1",
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get historical data from DhanHQ."""
        try:
            if not self.authenticated or not self.broker:
                return {"success": False, "error": "Not authenticated"}

            # Call broker method with correct named parameters using lambda
            # Since run_in_executor doesn't support kwargs, use lambda to wrap the call
            data = await self._run_in_executor(
                lambda: self.broker.get_historical_data(
                    tradingsymbol=symbol,
                    timeframe=timeframe,
                    exchange="NSE",
                    start_date=start_date,
                    end_date=end_date
                )
            )

            # Handle both DataFrame and list responses from broker
            if data is not None and ((hasattr(data, 'empty') and not data.empty) or (hasattr(data, '__len__') and len(data) > 0)):
                return {
                    "success": True,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data": data,
                    "record_count": len(data),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": "No historical data available or symbol not found"}

        except Exception as e:
            logger.error(f"❌ DhanHQ get historical data failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_20_level_depth(self, symbol: str) -> Dict[str, Any]:
        """Get 20-level market depth from DhanHQ."""
        try:
            if not self.authenticated or not self.broker:
                return {"success": False, "error": "Not authenticated"}

            depth = await self._run_in_executor(
                self.broker.get_20_level_depth,
                symbol,
                exchange_segment=1  # NSE_EQ
            )

            if depth:
                return {
                    "success": True,
                    "symbol": symbol,
                    "depth": depth,
                    "level_count": 20,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": "Failed to get depth"}

        except Exception as e:
            logger.error(f"❌ DhanHQ get 20-level depth failed: {e}")
            return {"success": False, "error": str(e)}

    async def start_market_data_stream(self, symbols: List[str],
                                     callback: Optional[callable] = None) -> Dict[str, Any]:
        """Start real-time market data streaming from DhanHQ."""
        try:
            if not self.authenticated or not self.broker:
                return {"success": False, "error": "Not authenticated"}

            # Start 20-level depth streaming
            success = await self._run_in_executor(
                self.broker.start_20_level_depth_stream,
                symbols,
                callback=callback
            )

            if success:
                return {
                    "success": True,
                    "symbols": symbols,
                    "stream_type": "20_level_depth",
                    "status": "STARTED",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": "Failed to start stream"}

        except Exception as e:
            logger.error(f"❌ DhanHQ start stream failed: {e}")
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on DhanHQ connection."""
        try:
            if not self.broker:
                return {
                    "status": "disconnected",
                    "last_check": datetime.now().isoformat()
                }

            # Test connection with a simple operation
            balance = await self._run_in_executor(self.broker.get_balance)

            self._last_health_check = datetime.now()

            if balance:
                return {
                    "status": "healthy",
                    "last_check": self._last_health_check.isoformat(),
                    "account_balance": balance.get('net', 0)
                }
            else:
                return {
                    "status": "unhealthy",
                    "last_check": datetime.now().isoformat(),
                    "error": "Failed to get account balance"
                }

        except Exception as e:
            return {
                "status": "error",
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            }

    def _map_order_to_broker_params(self, order: BrokerOrder) -> Dict[str, Any]:
        """Map domain order to broker module parameters."""
        params = {
            'tradingsymbol': order.symbol,
            'exchange': 'NSE',
            'transaction_type': order.side,
            'quantity': order.quantity
        }

        if order.order_type.upper() == 'BRACKET':
            params.update({
                'entry_price': float(order.price) if order.price else None,
                'target_price': float(order.price) * 1.05 if order.price else None,  # 5% target
                'stop_loss_price': float(order.price) * 0.95 if order.price else None,  # 5% stop
                'trailing_jump': 5.0  # Default trailing jump
            })

        return params

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run synchronous broker function in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self.connected and self.broker is not None

    def is_authenticated(self) -> bool:
        """Check if broker is authenticated."""
        return self.authenticated and self.is_connected()
