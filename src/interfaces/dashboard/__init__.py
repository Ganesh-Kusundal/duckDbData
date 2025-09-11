"""
Unified Dashboard Interface Layer
Consolidates dashboard components from analytics, trade_engine, and scanner modules
"""

from .main import create_dashboard_app, run_dashboard_server
from .components import register_components
from .routes import setup_dashboard_routes

__all__ = [
    'create_dashboard_app',
    'run_dashboard_server',
    'register_components',
    'setup_dashboard_routes'
]
