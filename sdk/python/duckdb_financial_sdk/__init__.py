"""
DuckDB Financial SDK
===================

Python SDK for DuckDB Financial Infrastructure API.

Provides easy-to-use Python client for:
- Market data operations
- Scanner execution
- System monitoring
- Real-time data streaming

Example:
    from duckdb_financial_sdk import FinancialClient

    client = FinancialClient("http://localhost:8000")
    data = client.get_market_data("AAPL", "2024-01-01", "2024-12-31")
"""

from .client import FinancialClient
from .market_data import MarketDataClient
from .scanners import ScannerClient
from .system import SystemClient
from .realtime import RealtimeClient
from .exceptions import APIError, AuthenticationError, ValidationError

__version__ = "1.0.0"
__all__ = [
    'FinancialClient',
    'MarketDataClient',
    'ScannerClient',
    'SystemClient',
    'RealtimeClient',
    'APIError',
    'AuthenticationError',
    'ValidationError'
]
