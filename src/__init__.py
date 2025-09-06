"""DuckDB Financial Infrastructure - Main Package."""

__version__ = "0.1.0"
__author__ = "Financial Data Team"
__description__ = "A comprehensive, event-driven financial data platform"

# Initialize core infrastructure
from .infrastructure.config.settings import get_settings
from .infrastructure.logging import setup_logging
from .infrastructure.messaging.event_bus import get_event_bus

# Initialize settings
settings = get_settings()

# Set up logging
# setup_logging()

# Initialize event bus
event_bus = get_event_bus()

# Export main components
__all__ = [
    'settings',
    'event_bus',
    'get_settings',
    'get_event_bus',
]
