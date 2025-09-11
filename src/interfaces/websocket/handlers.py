"""
WebSocket Message Handlers
Handle WebSocket messages and route them appropriately
"""

import logging
import json
from typing import Dict, Any
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

from .connections import WebSocketConnectionManager

logger = logging.getLogger(__name__)


def register_websocket_handlers(app, connection_manager: WebSocketConnectionManager):
    """
    Register WebSocket handlers with the FastAPI app

    Args:
        app: FastAPI application instance
        connection_manager: WebSocket connection manager
    """

    @app.websocket("/ws/market-data")
    async def market_data_websocket(websocket: WebSocket):
        """
        WebSocket endpoint for market data streaming
        """
        client_id = f"client_{id(websocket)}"  # Simple client ID generation

        await handle_market_data_connection(websocket, client_id, connection_manager)

    @app.websocket("/ws/scanner")
    async def scanner_websocket(websocket: WebSocket):
        """
        WebSocket endpoint for scanner signals
        """
        client_id = f"scanner_{id(websocket)}"

        await handle_scanner_connection(websocket, client_id, connection_manager)

    @app.websocket("/ws/system")
    async def system_websocket(websocket: WebSocket):
        """
        WebSocket endpoint for system monitoring
        """
        client_id = f"system_{id(websocket)}"

        await handle_system_connection(websocket, client_id, connection_manager)


async def handle_market_data_connection(
    websocket: WebSocket,
    client_id: str,
    connection_manager: WebSocketConnectionManager
):
    """
    Handle market data WebSocket connection

    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
        connection_manager: WebSocket connection manager
    """
    # Accept connection
    if not await connection_manager.connect(websocket, client_id):
        return

    try:
        # Send welcome message
        welcome_message = {
            "type": "welcome",
            "client_id": client_id,
            "message": "Connected to market data stream",
            "timestamp": datetime.now().isoformat(),
            "available_symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]  # Mock data
        }
        await connection_manager.send_personal_message(client_id, welcome_message)

        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Update connection metadata
                if client_id in connection_manager.connection_metadata:
                    connection_manager.connection_metadata[client_id]["messages_received"] += 1
                    connection_manager.connection_metadata[client_id]["last_activity"] = datetime.now()

                # Handle message
                await handle_market_data_message(client_id, message, connection_manager)

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
                await connection_manager.send_personal_message(client_id, {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnect for client {client_id}")
    except Exception as e:
        logger.error(f"Error handling market data connection for {client_id}: {e}")
    finally:
        # Clean up connection
        await connection_manager.disconnect(client_id)


async def handle_scanner_connection(
    websocket: WebSocket,
    client_id: str,
    connection_manager: WebSocketConnectionManager
):
    """
    Handle scanner WebSocket connection

    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
        connection_manager: WebSocket connection manager
    """
    # Accept connection
    if not await connection_manager.connect(websocket, client_id):
        return

    try:
        # Send welcome message
        welcome_message = {
            "type": "welcome",
            "client_id": client_id,
            "message": "Connected to scanner signal stream",
            "timestamp": datetime.now().isoformat(),
            "available_rules": ["momentum_breakout", "volume_surge", "rsi_divergence"]
        }
        await connection_manager.send_personal_message(client_id, welcome_message)

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Update metadata
                if client_id in connection_manager.connection_metadata:
                    connection_manager.connection_metadata[client_id]["messages_received"] += 1
                    connection_manager.connection_metadata[client_id]["last_activity"] = datetime.now()

                # Handle message
                await handle_scanner_message(client_id, message, connection_manager)

            except json.JSONDecodeError:
                await connection_manager.send_personal_message(client_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })

    except WebSocketDisconnect:
        logger.info(f"Scanner WebSocket disconnect for client {client_id}")
    except Exception as e:
        logger.error(f"Error handling scanner connection for {client_id}: {e}")
    finally:
        await connection_manager.disconnect(client_id)


async def handle_system_connection(
    websocket: WebSocket,
    client_id: str,
    connection_manager: WebSocketConnectionManager
):
    """
    Handle system monitoring WebSocket connection

    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
        connection_manager: WebSocket connection manager
    """
    # Accept connection
    if not await connection_manager.connect(websocket, client_id):
        return

    try:
        # Send welcome message
        welcome_message = {
            "type": "welcome",
            "client_id": client_id,
            "message": "Connected to system monitoring stream",
            "timestamp": datetime.now().isoformat()
        }
        await connection_manager.send_personal_message(client_id, welcome_message)

        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Update metadata
                if client_id in connection_manager.connection_metadata:
                    connection_manager.connection_metadata[client_id]["messages_received"] += 1
                    connection_manager.connection_metadata[client_id]["last_activity"] = datetime.now()

                # Handle message
                await handle_system_message(client_id, message, connection_manager)

            except json.JSONDecodeError:
                await connection_manager.send_personal_message(client_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })

    except WebSocketDisconnect:
        logger.info(f"System WebSocket disconnect for client {client_id}")
    except Exception as e:
        logger.error(f"Error handling system connection for {client_id}: {e}")
    finally:
        await connection_manager.disconnect(client_id)


async def handle_market_data_message(
    client_id: str,
    message: Dict[str, Any],
    connection_manager: WebSocketConnectionManager
):
    """
    Handle market data WebSocket message

    Args:
        client_id: Client identifier
        message: Message from client
        connection_manager: WebSocket connection manager
    """
    message_type = message.get("type", "unknown")

    if message_type == "subscribe":
        # Handle symbol subscription
        symbols = message.get("symbols", [])
        for symbol in symbols:
            await connection_manager.subscribe_to_symbol(client_id, symbol)

        await connection_manager.send_personal_message(client_id, {
            "type": "subscription_confirmed",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        })

    elif message_type == "unsubscribe":
        # Handle symbol unsubscription
        symbols = message.get("symbols", [])
        for symbol in symbols:
            await connection_manager.unsubscribe_from_symbol(client_id, symbol)

        await connection_manager.send_personal_message(client_id, {
            "type": "unsubscription_confirmed",
            "symbols": symbols,
            "timestamp": datetime.now().isoformat()
        })

    elif message_type == "ping":
        # Handle ping/pong for connection health
        await connection_manager.send_personal_message(client_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })

    else:
        logger.warning(f"Unknown message type from client {client_id}: {message_type}")
        await connection_manager.send_personal_message(client_id, {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.now().isoformat()
        })


async def handle_scanner_message(
    client_id: str,
    message: Dict[str, Any],
    connection_manager: WebSocketConnectionManager
):
    """
    Handle scanner WebSocket message

    Args:
        client_id: Client identifier
        message: Message from client
        connection_manager: WebSocket connection manager
    """
    message_type = message.get("type", "unknown")

    if message_type == "start_scan":
        # Start scanner for specific symbols/rules
        symbols = message.get("symbols", [])
        rules = message.get("rules", [])

        # Mock scanner start - in real implementation, this would trigger scanner
        await connection_manager.send_personal_message(client_id, {
            "type": "scan_started",
            "symbols": symbols,
            "rules": rules,
            "scan_id": f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        })

    elif message_type == "stop_scan":
        # Stop scanner
        scan_id = message.get("scan_id")
        await connection_manager.send_personal_message(client_id, {
            "type": "scan_stopped",
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat()
        })

    elif message_type == "ping":
        await connection_manager.send_personal_message(client_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })

    else:
        await connection_manager.send_personal_message(client_id, {
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        })


async def handle_system_message(
    client_id: str,
    message: Dict[str, Any],
    connection_manager: WebSocketConnectionManager
):
    """
    Handle system monitoring WebSocket message

    Args:
        client_id: Client identifier
        message: Message from client
        connection_manager: WebSocket connection manager
    """
    message_type = message.get("type", "unknown")

    if message_type == "subscribe_metrics":
        # Subscribe to system metrics
        metrics = message.get("metrics", ["cpu", "memory", "disk"])

        await connection_manager.send_personal_message(client_id, {
            "type": "metrics_subscription_confirmed",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        })

    elif message_type == "ping":
        await connection_manager.send_personal_message(client_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })

    else:
        await connection_manager.send_personal_message(client_id, {
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        })
