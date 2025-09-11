"""
API Routes
Consolidated route definitions for all API endpoints
"""

from .market_data_routes import router as market_data_router
from .analytics_routes import router as analytics_router
from .scanner_routes import router as scanner_router
from .health_routes import router as health_router

# Import setup_routes from the routes.py file (same level)
try:
    from ..routes import setup_routes
    SETUP_ROUTES_AVAILABLE = True
except ImportError:
    SETUP_ROUTES_AVAILABLE = False
    def setup_routes(*args, **kwargs):
        pass

__all__ = [
    'market_data_router',
    'analytics_router',
    'scanner_router',
    'health_router',
    'setup_routes'
]