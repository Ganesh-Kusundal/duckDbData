"""
Monitoring Dashboard Package
=============================

This package provides a comprehensive monitoring dashboard for the DuckDB Financial Infrastructure
with Panel/Bokeh, dark mode, test monitoring, logging framework, and performance metrics.
"""

# Dashboard functions are imported when needed to avoid circular imports
from .config.database import monitoring_db
from .logging import get_logger, set_correlation_id
from .test_monitor import test_monitor
from .metrics import metrics_collector

__version__ = "1.0.0"

def create_dashboard_app():
    """Create the monitoring dashboard application."""
    from .dashboard.app import create_dashboard_app as _create_app
    return _create_app()


def run_dashboard(port=None, host=None):
    """Run the monitoring dashboard."""
    from .dashboard.app import run_dashboard as _run_dashboard
    _run_dashboard(port=port, host=host)


__all__ = [
    # Main functions
    'create_dashboard_app',
    'run_dashboard',

    # Core components
    'monitoring_db',
    'get_logger',
    'set_correlation_id',
    'test_monitor',
    'metrics_collector'
]
