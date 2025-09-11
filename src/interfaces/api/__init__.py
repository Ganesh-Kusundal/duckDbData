"""
Unified API Interface Layer
Consolidates all API endpoints from analytics, scanner, trade_engine, and sync modules
"""

from .main import create_api_app
from .middleware import setup_middleware
from .routes import setup_routes
from .dependencies import get_application_service

__all__ = [
    'create_api_app',
    'setup_middleware',
    'setup_routes',
    'get_application_service'
]