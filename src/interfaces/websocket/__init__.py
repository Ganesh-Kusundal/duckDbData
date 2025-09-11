"""
Unified WebSocket Interface Layer
Consolidates websocket servers from scanner and other modules for real-time data streaming
"""

from .main import create_websocket_app, run_websocket_server
from .connections import WebSocketConnectionManager
from .handlers import register_websocket_handlers

__all__ = [
    'create_websocket_app',
    'run_websocket_server',
    'WebSocketConnectionManager',
    'register_websocket_handlers'
]
