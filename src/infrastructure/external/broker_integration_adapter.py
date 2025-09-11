"""
Broker Integration Adapters for External Broker APIs

Provides adapters for connecting to various broker APIs,
handling authentication, order execution, and data synchronization.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Protocol
from datetime import datetime
from decimal import Decimal
from abc import ABC, abstractmethod

from domain.broker_integration.entities.broker_connection import (
    BrokerConnection, ConnectionStatus, BrokerCredentials
)
from domain.broker_integration.entities.broker_account import BrokerAccount
from domain.broker_integration.value_objects.order_execution import (
    BrokerOrder, ExecutionReport, BrokerCapabilities
)
from infrastructure.adapters.dhan_broker_adapter import DhanBrokerAdapter
from ..monitoring.metrics_collector import get_metrics_collector, timed

logger = logging.getLogger(__name__)


class BrokerAPIAdapter(Protocol):
    """Protocol for broker API adapters."""

    @abstractmethod
    async def connect(self, credentials: BrokerCredentials) -> Dict[str, Any]:
        """Establish connection to broker API."""
        pass

    @abstractmethod
    async def authenticate(self, credentials: BrokerCredentials) -> Dict[str, Any]:
        """Authenticate with broker API."""
        pass

    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        pass

    @abstractmethod
    async def submit_order(self, order: BrokerOrder) -> Dict[str, Any]:
        """Submit order to broker."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status."""
        pass

    @abstractmethod
    async def get_capabilities(self) -> BrokerCapabilities:
        """Get broker capabilities."""
        pass


class InteractiveBrokersAdapter:
    """
    Interactive Brokers API adapter.

    Handles connection to Interactive Brokers TWS or IB Gateway.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self.authenticated = False
        self._connection = None

    @timed("broker.ib.connect")
    async def connect(self, credentials: BrokerCredentials) -> Dict[str, Any]:
        """Connect to Interactive Brokers."""
        try:
            # In a real implementation, this would connect to IB TWS/Gateway
            # For now, simulate connection
            await asyncio.sleep(0.5)  # Simulate network delay

            self.connected = True
            return {
                "success": True,
                "connection_id": f"ib_{self.client_id}",
                "server_version": "10.19.1",
                "connection_time": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"IB connection failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @timed("broker.ib.authenticate")
    async def authenticate(self, credentials: BrokerCredentials) -> Dict[str, Any]:
        """Authenticate with Interactive Brokers."""
        try:
            if not self.connected:
                return {"success": False, "error": "Not connected"}

            # In a real implementation, this would handle IB authentication
            # For now, simulate authentication
            await asyncio.sleep(0.3)  # Simulate auth delay

            self.authenticated = True
            return {
                "success": True,
                "session_token": "ib_session_12345",
                "account_id": credentials.api_key[:8],  # Mock account ID
                "permissions": ["READ", "TRADE", "OPTIONS"]
            }

        except Exception as e:
            logger.error(f"IB authentication failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @timed("broker.ib.get_account_info")
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from IB."""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}

            # Simulate account data retrieval
            await asyncio.sleep(0.2)

            return {
                "success": True,
                "account_number": "DU1234567",
                "account_type": "INDIVIDUAL",
                "currency": "USD",
                "cash_balance": 100000.00,
                "buying_power": 200000.00,
                "total_value": 150000.00,
                "margin_used": 25000.00,
                "available_margin": 175000.00
            }

        except Exception as e:
            logger.error(f"IB get account info failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.ib.get_positions")
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from IB."""
        try:
            if not self.authenticated:
                return []

            # Simulate positions data
            await asyncio.sleep(0.2)

            return [
                {
                    "symbol": "AAPL",
                    "quantity": 100,
                    "average_price": 150.25,
                    "current_price": 155.50,
                    "unrealized_pnl": 525.00,
                    "realized_pnl": 0.00,
                    "market_value": 15550.00
                },
                {
                    "symbol": "GOOGL",
                    "quantity": 25,
                    "average_price": 2800.00,
                    "current_price": 2850.00,
                    "unrealized_pnl": 1250.00,
                    "realized_pnl": 500.00,
                    "market_value": 71250.00
                }
            ]

        except Exception as e:
            logger.error(f"IB get positions failed: {e}")
            return []

    @timed("broker.ib.submit_order")
    async def submit_order(self, order: BrokerOrder) -> Dict[str, Any]:
        """Submit order to Interactive Brokers."""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}

            # Simulate order submission
            await asyncio.sleep(0.3)

            broker_order_id = f"IB_{order.symbol}_{int(datetime.now().timestamp())}"

            return {
                "success": True,
                "broker_order_id": broker_order_id,
                "status": "SUBMITTED",
                "estimated_fill_price": float(order.price) if order.price else 150.00,
                "commission_estimate": 1.25
            }

        except Exception as e:
            logger.error(f"IB submit order failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.ib.cancel_order")
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order on Interactive Brokers."""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}

            # Simulate order cancellation
            await asyncio.sleep(0.2)

            return {
                "success": True,
                "order_id": order_id,
                "status": "CANCELLED"
            }

        except Exception as e:
            logger.error(f"IB cancel order failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.ib.get_order_status")
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from Interactive Brokers."""
        try:
            if not self.authenticated:
                return {"success": False, "error": "Not authenticated"}

            # Simulate order status retrieval
            await asyncio.sleep(0.1)

            return {
                "success": True,
                "order_id": order_id,
                "status": "FILLED",
                "filled_quantity": 100,
                "remaining_quantity": 0,
                "average_price": 150.25,
                "last_update": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"IB get order status failed: {e}")
            return {"success": False, "error": str(e)}

    def get_capabilities(self) -> BrokerCapabilities:
        """Get Interactive Brokers capabilities."""
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
            max_orders_per_second=50
        )


class AlpacaAdapter:
    """
    Alpaca API adapter.

    Handles connection to Alpaca trading API.
    """

    def __init__(self, base_url: str = "https://api.alpaca.markets",
                 api_version: str = "v2"):
        self.base_url = base_url
        self.api_version = api_version
        self.session_token = None

    @timed("broker.alpaca.connect")
    async def connect(self, credentials: BrokerCredentials) -> Dict[str, Any]:
        """Connect to Alpaca API."""
        try:
            # In a real implementation, this would establish HTTP connection
            await asyncio.sleep(0.3)

            return {
                "success": True,
                "api_version": self.api_version,
                "connection_time": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.alpaca.authenticate")
    async def authenticate(self, credentials: BrokerCredentials) -> Dict[str, Any]:
        """Authenticate with Alpaca API."""
        try:
            # In a real implementation, this would make authentication request
            await asyncio.sleep(0.4)

            self.session_token = "alpaca_token_12345"

            return {
                "success": True,
                "token": self.session_token,
                "account_id": "ALPACA123",
                "permissions": ["TRADE", "DATA"]
            }

        except Exception as e:
            logger.error(f"Alpaca authentication failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.alpaca.get_account_info")
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from Alpaca."""
        try:
            if not self.session_token:
                return {"success": False, "error": "Not authenticated"}

            # Simulate API call
            await asyncio.sleep(0.2)

            return {
                "success": True,
                "account_number": "ALPACA123",
                "account_type": "PAPER_TRADING",
                "currency": "USD",
                "cash_balance": 50000.00,
                "buying_power": 100000.00,
                "total_value": 75000.00,
                "margin_used": 0.00,
                "available_margin": 100000.00
            }

        except Exception as e:
            logger.error(f"Alpaca get account info failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.alpaca.get_positions")
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from Alpaca."""
        try:
            if not self.session_token:
                return []

            # Simulate API call
            await asyncio.sleep(0.2)

            return [
                {
                    "symbol": "TSLA",
                    "quantity": 50,
                    "average_price": 250.00,
                    "current_price": 260.00,
                    "unrealized_pnl": 500.00,
                    "realized_pnl": 0.00,
                    "market_value": 13000.00
                },
                {
                    "symbol": "NVDA",
                    "quantity": 30,
                    "average_price": 450.00,
                    "current_price": 465.00,
                    "unrealized_pnl": 450.00,
                    "realized_pnl": 150.00,
                    "market_value": 13950.00
                }
            ]

        except Exception as e:
            logger.error(f"Alpaca get positions failed: {e}")
            return []

    @timed("broker.alpaca.submit_order")
    async def submit_order(self, order: BrokerOrder) -> Dict[str, Any]:
        """Submit order to Alpaca."""
        try:
            if not self.session_token:
                return {"success": False, "error": "Not authenticated"}

            # Simulate API call
            await asyncio.sleep(0.4)

            broker_order_id = f"ALPACA_{order.symbol}_{int(datetime.now().timestamp())}"

            return {
                "success": True,
                "broker_order_id": broker_order_id,
                "status": "ACCEPTED",
                "estimated_fill_price": float(order.price) if order.price else 250.00,
                "commission_estimate": 0.00  # Alpaca has free trading
            }

        except Exception as e:
            logger.error(f"Alpaca submit order failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.alpaca.cancel_order")
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order on Alpaca."""
        try:
            if not self.session_token:
                return {"success": False, "error": "Not authenticated"}

            # Simulate API call
            await asyncio.sleep(0.2)

            return {
                "success": True,
                "order_id": order_id,
                "status": "CANCELLED"
            }

        except Exception as e:
            logger.error(f"Alpaca cancel order failed: {e}")
            return {"success": False, "error": str(e)}

    @timed("broker.alpaca.get_order_status")
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from Alpaca."""
        try:
            if not self.session_token:
                return {"success": False, "error": "Not authenticated"}

            # Simulate API call
            await asyncio.sleep(0.1)

            return {
                "success": True,
                "order_id": order_id,
                "status": "FILLED",
                "filled_quantity": 50,
                "remaining_quantity": 0,
                "average_price": 252.50,
                "last_update": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Alpaca get order status failed: {e}")
            return {"success": False, "error": str(e)}

    def get_capabilities(self) -> BrokerCapabilities:
        """Get Alpaca capabilities."""
        return BrokerCapabilities(
            supports_market_orders=True,
            supports_limit_orders=True,
            supports_stop_orders=True,
            supports_stop_limit_orders=False,
            supports_options_trading=False,  # Alpaca doesn't support options yet
            supports_futures_trading=False,
            supports_margin_trading=True,
            realtime_data_available=True,
            historical_data_available=True,
            max_orders_per_second=200  # Alpaca has higher rate limits
        )


class BrokerAdapterFactory:
    """
    Factory for creating broker adapters.

    Creates appropriate adapter instances based on broker type.
    """

    @staticmethod
    def create_adapter(broker_type: str, **kwargs) -> BrokerAPIAdapter:
        """Create broker adapter instance."""
        if broker_type.upper() == "INTERACTIVE_BROKERS":
            return InteractiveBrokersAdapter(**kwargs)
        elif broker_type.upper() == "ALPACA":
            return AlpacaAdapter(**kwargs)
        elif broker_type.upper() in ["DHAN_HQ", "DHANHQ"]:
            return DhanBrokerAdapter()
        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")


class BrokerIntegrationManager:
    """
    Main broker integration manager.

    Orchestrates connections to multiple brokers and manages their lifecycle.
    """

    def __init__(self):
        self.adapters: Dict[str, BrokerAPIAdapter] = {}
        self.active_connections: Dict[str, BrokerConnection] = {}
        self.metrics = get_metrics_collector()

    async def connect_broker(self, connection: BrokerConnection) -> Dict[str, Any]:
        """Connect to a broker using the appropriate adapter."""
        try:
            # Create adapter if not exists
            if connection.id.value not in self.adapters:
                adapter = BrokerAdapterFactory.create_adapter(
                    connection.broker_type.value,
                    **connection.endpoints.__dict__ if connection.endpoints else {}
                )
                self.adapters[connection.id.value] = adapter

            adapter = self.adapters[connection.id.value]

            # Connect and authenticate
            connect_result = await adapter.connect(connection.credentials)
            if not connect_result["success"]:
                return connect_result

            auth_result = await adapter.authenticate(connection.credentials)
            if not auth_result["success"]:
                return auth_result

            # Store active connection
            self.active_connections[connection.id.value] = connection

            # Record metrics
            self.metrics.increment_counter("broker.connections.established",
                                         {"broker": connection.broker_type.value})

            return {
                "success": True,
                "connection_id": connection.id.value,
                "adapter_type": type(adapter).__name__
            }

        except Exception as e:
            logger.error(f"Failed to connect broker {connection.id.value}: {e}")
            self.metrics.increment_counter("broker.connections.failed",
                                         {"broker": connection.broker_type.value})
            return {"success": False, "error": str(e)}

    async def disconnect_broker(self, connection_id: str) -> Dict[str, Any]:
        """Disconnect from a broker."""
        try:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]

            if connection_id in self.adapters:
                del self.adapters[connection_id]

            self.metrics.increment_counter("broker.connections.disconnected")
            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to disconnect broker {connection_id}: {e}")
            return {"success": False, "error": str(e)}

    async def submit_order(self, connection_id: str, order: BrokerOrder) -> Dict[str, Any]:
        """Submit order through broker adapter."""
        try:
            if connection_id not in self.adapters:
                return {"success": False, "error": "Broker not connected"}

            adapter = self.adapters[connection_id]
            result = await adapter.submit_order(order)

            if result["success"]:
                self.metrics.increment_counter("broker.orders.submitted",
                                             {"broker": connection_id})
            else:
                self.metrics.increment_counter("broker.orders.failed",
                                             {"broker": connection_id})

            return result

        except Exception as e:
            logger.error(f"Failed to submit order to {connection_id}: {e}")
            self.metrics.increment_counter("broker.orders.error",
                                         {"broker": connection_id})
            return {"success": False, "error": str(e)}

    async def get_account_summary(self, connection_id: str) -> Dict[str, Any]:
        """Get account summary from broker."""
        try:
            if connection_id not in self.adapters:
                return {"success": False, "error": "Broker not connected"}

            adapter = self.adapters[connection_id]
            account_info = await adapter.get_account_info()
            positions = await adapter.get_positions()

            self.metrics.increment_counter("broker.account.queries",
                                         {"broker": connection_id})

            return {
                "success": True,
                "account": account_info,
                "positions": positions,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get account summary from {connection_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_connected_brokers(self) -> List[str]:
        """Get list of connected broker IDs."""
        return list(self.active_connections.keys())

    def get_broker_capabilities(self, connection_id: str) -> Optional[BrokerCapabilities]:
        """Get capabilities of connected broker."""
        if connection_id in self.adapters:
            return self.adapters[connection_id].get_capabilities()
        return None

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "available_adapters": len(self.adapters),
            "connected_brokers": list(self.active_connections.keys())
        }


# Global broker integration manager instance
_broker_manager: Optional[BrokerIntegrationManager] = None


def get_broker_integration_manager() -> BrokerIntegrationManager:
    """Get global broker integration manager instance."""
    global _broker_manager
    if _broker_manager is None:
        _broker_manager = BrokerIntegrationManager()
    return _broker_manager


def reset_broker_integration_manager():
    """Reset global broker integration manager (mainly for testing)."""
    global _broker_manager
    _broker_manager = None
