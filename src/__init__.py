"""
DuckDB Financial Infrastructure - Source Code
Main entry point for all modules
"""

# Import layers safely (infrastructure may have external dependencies)
from . import domain

try:
    from . import application, infrastructure
    INFRASTRUCTURE_AVAILABLE = True
except ImportError as e:
    # Infrastructure may not be available during testing
    application = None
    infrastructure = None
    INFRASTRUCTURE_AVAILABLE = False

# Make key components easily accessible
from .domain.market_data import MarketData, MarketDataBatch, OHLCV

__all__ = [
    'domain',
    'MarketData',
    'MarketDataBatch',
    'OHLCV'
]

if INFRASTRUCTURE_AVAILABLE:
    __all__.extend(['application', 'infrastructure'])
