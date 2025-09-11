"""
WebSocket Connection Manager
Manages WebSocket connections and message routing
"""

import logging
from typing import Dict, List, Set, Optional
from datetime import datetime

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages WebSocket connections and message broadcasting
    """

    def __init__(self):
        # Active connections by client ID
        self.active_connections: Dict[str, WebSocket] = {}

        # Connections grouped by subscribed symbols
        self.symbol_subscriptions: Dict[str, Set[str]] = {}

        # Client subscriptions (which symbols each client is subscribed to)
        self.client_subscriptions: Dict[str, Set[str]] = {}

        # Connection metadata
        self.connection_metadata: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        Accept a new WebSocket connection

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier

        Returns:
            True if connection accepted, False otherwise
        """
        try:
            await websocket.accept()

            # Store connection
            self.active_connections[client_id] = websocket

            # Initialize client subscriptions
            self.client_subscriptions[client_id] = set()

            # Store connection metadata
            self.connection_metadata[client_id] = {
                "connected_at": datetime.now(),
                "last_activity": datetime.now(),
                "messages_sent": 0,
                "messages_received": 0
            }

            logger.info(f"✅ WebSocket client {client_id} connected")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to accept WebSocket connection for {client_id}: {e}")
            return False

    async def disconnect(self, client_id: str):
        """
        Remove a WebSocket connection

        Args:
            client_id: Client identifier to disconnect
        """
        if client_id in self.active_connections:
            # Remove from all symbol subscriptions
            if client_id in self.client_subscriptions:
                for symbol in self.client_subscriptions[client_id]:
                    if symbol in self.symbol_subscriptions:
                        self.symbol_subscriptions[symbol].discard(client_id)
                        if not self.symbol_subscriptions[symbol]:
                            del self.symbol_subscriptions[symbol]

                del self.client_subscriptions[client_id]

            # Remove connection and metadata
            del self.active_connections[client_id]
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]

            logger.info(f"👋 WebSocket client {client_id} disconnected")

    async def subscribe_to_symbol(self, client_id: str, symbol: str):
        """
        Subscribe a client to market data for a symbol

        Args:
            client_id: Client identifier
            symbol: Trading symbol to subscribe to
        """
        if client_id not in self.active_connections:
            logger.warning(f"Client {client_id} not connected, cannot subscribe to {symbol}")
            return

        # Add to client's subscriptions
        if client_id not in self.client_subscriptions:
            self.client_subscriptions[client_id] = set()
        self.client_subscriptions[client_id].add(symbol)

        # Add to symbol's subscribers
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = set()
        self.symbol_subscriptions[symbol].add(client_id)

        logger.info(f"📡 Client {client_id} subscribed to {symbol}")

    async def unsubscribe_from_symbol(self, client_id: str, symbol: str):
        """
        Unsubscribe a client from market data for a symbol

        Args:
            client_id: Client identifier
            symbol: Trading symbol to unsubscribe from
        """
        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].discard(symbol)

        if symbol in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol].discard(client_id)
            if not self.symbol_subscriptions[symbol]:
                del self.symbol_subscriptions[symbol]

        logger.info(f"🚫 Client {client_id} unsubscribed from {symbol}")

    async def send_personal_message(self, client_id: str, message: dict):
        """
        Send a message to a specific client

        Args:
            client_id: Target client identifier
            message: Message to send
        """
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)

                # Update metadata
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["messages_sent"] += 1
                    self.connection_metadata[client_id]["last_activity"] = datetime.now()

                logger.debug(f"📤 Sent message to client {client_id}")

            except Exception as e:
                logger.error(f"Failed to send message to client {client_id}: {e}")
                # Client might be disconnected, remove them
                await self.disconnect(client_id)

    async def broadcast_to_symbol(self, symbol: str, message: dict):
        """
        Broadcast a message to all clients subscribed to a symbol

        Args:
            symbol: Symbol to broadcast to
            message: Message to broadcast
        """
        if symbol not in self.symbol_subscriptions:
            return

        subscribers = self.symbol_subscriptions[symbol].copy()
        disconnected_clients = []

        for client_id in subscribers:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)

                    # Update metadata
                    if client_id in self.connection_metadata:
                        self.connection_metadata[client_id]["messages_sent"] += 1
                        self.connection_metadata[client_id]["last_activity"] = datetime.now()

                except Exception as e:
                    logger.error(f"Failed to send message to client {client_id}: {e}")
                    disconnected_clients.append(client_id)
            else:
                # Client no longer connected, remove from subscriptions
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

        if subscribers:
            logger.debug(f"📡 Broadcasted message to {len(subscribers)} clients for {symbol}")

    async def broadcast_to_all(self, message: dict):
        """
        Broadcast a message to all connected clients

        Args:
            message: Message to broadcast
        """
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)

                # Update metadata
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["messages_sent"] += 1
                    self.connection_metadata[client_id]["last_activity"] = datetime.now()

            except Exception as e:
                logger.error(f"Failed to send message to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

        logger.debug(f"📢 Broadcasted message to all {len(self.active_connections)} clients")

    async def get_active_connections_count(self) -> int:
        """
        Get the number of active connections

        Returns:
            Number of active connections
        """
        return len(self.active_connections)

    async def get_connection_stats(self) -> Dict:
        """
        Get connection statistics

        Returns:
            Dictionary with connection statistics
        """
        total_messages_sent = sum(
            meta.get("messages_sent", 0)
            for meta in self.connection_metadata.values()
        )

        total_messages_received = sum(
            meta.get("messages_received", 0)
            for meta in self.connection_metadata.values()
        )

        return {
            "total_connections": len(self.connection_metadata),
            "active_connections": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.client_subscriptions.values()),
            "unique_symbols": len(self.symbol_subscriptions),
            "messages_sent": total_messages_sent,
            "messages_received": total_messages_received
        }

    async def get_client_info(self, client_id: str) -> Optional[Dict]:
        """
        Get information about a specific client

        Args:
            client_id: Client identifier

        Returns:
            Client information dictionary or None if not found
        """
        if client_id not in self.connection_metadata:
            return None

        metadata = self.connection_metadata[client_id]
        subscriptions = list(self.client_subscriptions.get(client_id, set()))

        return {
            "client_id": client_id,
            "connected_at": metadata["connected_at"].isoformat(),
            "last_activity": metadata["last_activity"].isoformat(),
            "messages_sent": metadata["messages_sent"],
            "messages_received": metadata["messages_received"],
            "subscriptions": subscriptions,
            "is_active": client_id in self.active_connections
        }

    async def cleanup_inactive_connections(self, max_inactive_seconds: int = 300):
        """
        Clean up connections that have been inactive for too long

        Args:
            max_inactive_seconds: Maximum seconds of inactivity before cleanup
        """
        current_time = datetime.now()
        inactive_clients = []

        for client_id, metadata in self.connection_metadata.items():
            last_activity = metadata["last_activity"]
            inactive_seconds = (current_time - last_activity).total_seconds()

            if inactive_seconds > max_inactive_seconds:
                inactive_clients.append(client_id)

        # Disconnect inactive clients
        for client_id in inactive_clients:
            logger.info(f"🧹 Cleaning up inactive client {client_id}")
            await self.disconnect(client_id)

        if inactive_clients:
            logger.info(f"🧹 Cleaned up {len(inactive_clients)} inactive connections")
