"""
Real-time Client
===============

Client for real-time data streaming operations.
"""

import asyncio
import websockets
import json
import threading
from typing import Dict, List, Optional, Any, Callable
import logging


class RealtimeClient:
    """
    Client for real-time data streaming.

    Provides WebSocket connections for live market data.
    """

    def __init__(self, client):
        """Initialize real-time client."""
        self.client = client
        self.websocket = None
        self.is_connected = False
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket_url: Optional[str] = None) -> None:
        """
        Connect to real-time data stream.

        Args:
            websocket_url: WebSocket URL (defaults to API base URL)
        """
        if websocket_url is None:
            # Convert HTTP URL to WebSocket URL
            ws_url = self.client.base_url.replace('http://', 'ws://').replace('https://', 'wss://')
            websocket_url = f"{ws_url}/realtime"

        try:
            self.websocket = await websockets.connect(websocket_url)
            self.is_connected = True
            self.logger.info(f"Connected to real-time stream: {websocket_url}")

            # Start message handling loop
            asyncio.create_task(self._message_handler())

        except Exception as e:
            self.logger.error(f"Failed to connect to real-time stream: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from real-time data stream."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.is_connected = False
            self.logger.info("Disconnected from real-time stream")

    async def subscribe(self, symbol: str, callback: Callable) -> None:
        """
        Subscribe to real-time data for a symbol.

        Args:
            symbol: Trading symbol
            callback: Function to call when data is received
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to real-time stream")

        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []

        self.subscriptions[symbol].append(callback)

        # Send subscription message
        await self.websocket.send(json.dumps({
            'action': 'subscribe',
            'symbol': symbol
        }))

        self.logger.info(f"Subscribed to real-time data for {symbol}")

    async def unsubscribe(self, symbol: str, callback: Optional[Callable] = None) -> None:
        """
        Unsubscribe from real-time data for a symbol.

        Args:
            symbol: Trading symbol
            callback: Specific callback to remove (None for all)
        """
        if symbol in self.subscriptions:
            if callback:
                if callback in self.subscriptions[symbol]:
                    self.subscriptions[symbol].remove(callback)
                    if not self.subscriptions[symbol]:
                        del self.subscriptions[symbol]
            else:
                del self.subscriptions[symbol]

            # Send unsubscription message
            await self.websocket.send(json.dumps({
                'action': 'unsubscribe',
                'symbol': symbol
            }))

            self.logger.info(f"Unsubscribed from real-time data for {symbol}")

    async def _message_handler(self) -> None:
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)

                    if data.get('type') == 'market_data':
                        symbol = data.get('symbol')
                        if symbol in self.subscriptions:
                            for callback in self.subscriptions[symbol]:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(data)
                                    else:
                                        callback(data)
                                except Exception as e:
                                    self.logger.error(f"Error in callback: {e}")

                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Real-time connection closed")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")
            self.is_connected = False

    def subscribe_sync(self, symbol: str, callback: Callable) -> None:
        """
        Synchronous version of subscribe (for use outside async context).

        Args:
            symbol: Trading symbol
            callback: Function to call when data is received
        """
        # This would need to be run in an event loop
        # For now, store the subscription for later connection
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []
        self.subscriptions[symbol].append(callback)

    def get_subscriptions(self) -> List[str]:
        """
        Get list of currently subscribed symbols.

        Returns:
            List of subscribed symbols
        """
        return list(self.subscriptions.keys())

    def is_symbol_subscribed(self, symbol: str) -> bool:
        """
        Check if a symbol is currently subscribed.

        Args:
            symbol: Trading symbol

        Returns:
            True if subscribed, False otherwise
        """
        return symbol in self.subscriptions

    async def get_connection_status(self) -> Dict:
        """
        Get real-time connection status.

        Returns:
            Connection status information
        """
        return {
            'connected': self.is_connected,
            'subscriptions': len(self.subscriptions),
            'subscribed_symbols': list(self.subscriptions.keys())
        }

    # Context manager support
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
