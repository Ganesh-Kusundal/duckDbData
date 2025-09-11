"""
Unified WebSocket Application
Consolidates websocket servers for real-time market data streaming
"""

import logging
import asyncio
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .connections import WebSocketConnectionManager
from .handlers import register_websocket_handlers

logger = logging.getLogger(__name__)


def create_websocket_app() -> FastAPI:
    """
    Create and configure the unified websocket application

    Returns:
        Configured FastAPI application with WebSocket support
    """
    app = FastAPI(
        title="Trading System WebSocket Server",
        description="Real-time WebSocket server for market data and trading signals",
        version="2.0.0"
    )

    # Setup CORS for WebSocket connections
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize WebSocket connection manager
    connection_manager = WebSocketConnectionManager()

    # Store connection manager in app state
    app.state.connection_manager = connection_manager

    # Register WebSocket handlers
    register_websocket_handlers(app, connection_manager)

    # Health check endpoint
    @app.get("/health")
    async def websocket_health():
        """WebSocket server health check"""
        active_connections = await connection_manager.get_active_connections_count()

        return {
            "status": "healthy",
            "service": "websocket_server",
            "active_connections": active_connections,
            "version": "2.0.0"
        }

    # Connection statistics endpoint
    @app.get("/stats")
    async def websocket_stats():
        """WebSocket server statistics"""
        stats = await connection_manager.get_connection_stats()

        return {
            "timestamp": "2024-09-05T10:30:00Z",  # Would be dynamic
            "total_connections": stats.get("total_connections", 0),
            "active_connections": stats.get("active_connections", 0),
            "messages_sent": stats.get("messages_sent", 0),
            "messages_received": stats.get("messages_received", 0),
            "uptime": "2h 15m 30s"  # Would be dynamic
        }

    logger.info("✅ Unified WebSocket Application created")
    return app


def run_websocket_server(
    host: str = "0.0.0.0",
    port: int = 8081,
    reload: bool = False
):
    """
    Run the WebSocket server with uvicorn

    Args:
        host: Server host
        port: Server port
        reload: Enable auto-reload for development
    """
    app = create_websocket_app()

    logger.info(f"🚀 Starting WebSocket server on {host}:{port}")

    uvicorn.run(
        "src.interfaces.websocket.main:create_websocket_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
        log_level="info"
    )


async def start_background_tasks(app: FastAPI):
    """
    Start background tasks for the WebSocket server

    Args:
        app: FastAPI application instance
    """
    connection_manager = app.state.connection_manager

    # Start background data streaming
    asyncio.create_task(stream_market_data(connection_manager))

    logger.info("✅ Background tasks started")


async def stream_market_data(connection_manager: WebSocketConnectionManager):
    """
    Background task to stream market data to connected clients

    Args:
        connection_manager: WebSocket connection manager
    """
    logger.info("🎯 Starting market data streaming")

    while True:
        try:
            # Mock market data updates - in real implementation, this would
            # get data from the CQRS query system or external feeds
            mock_updates = [
                {
                    "type": "market_data",
                    "symbol": "AAPL",
                    "price": 152.34 + (0.1 * (0.5 - 0)),  # Small random variation
                    "volume": 45000000,
                    "timestamp": "2024-09-05T10:30:00Z"
                },
                {
                    "type": "market_data",
                    "symbol": "MSFT",
                    "price": 305.67 + (0.15 * (0.5 - 0)),
                    "volume": 32000000,
                    "timestamp": "2024-09-05T10:30:00Z"
                }
            ]

            # Send updates to all connected clients
            for update in mock_updates:
                await connection_manager.broadcast_to_symbol(
                    update["symbol"],
                    update
                )

            # Wait before next update
            await asyncio.sleep(5)  # Update every 5 seconds

        except Exception as e:
            logger.error(f"Error in market data streaming: {e}")
            await asyncio.sleep(10)  # Wait longer on error


if __name__ == "__main__":
    run_websocket_server()
