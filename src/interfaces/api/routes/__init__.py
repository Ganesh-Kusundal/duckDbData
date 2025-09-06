"""
API Routes
==========

FastAPI route modules for the DuckDB Financial Infrastructure API.
"""

from .health import router as health_router
from .market_data import router as market_data_router
from .scanners import router as scanner_router
from .plugins import router as plugin_router
from .system import router as system_router
from .metrics import router as metrics_router

__all__ = [
    'health_router',
    'market_data_router',
    'scanner_router',
    'plugin_router',
    'system_router',
    'metrics_router'
]
