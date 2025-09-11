"""
DuckDB Infrastructure for Financial Data

This package provides a comprehensive infrastructure for managing financial market data
using DuckDB as the backend database. It supports efficient querying of OHLCV data
organized by symbol and date with advanced resampling and analytical capabilities.

Main components:
- DuckDBManager: Core database management
- DataLoader: Bulk data loading utilities  
- QueryAPI: High-level query interface with resampling
- API Server: REST API for external access

Features:
- Data resampling to higher timeframes (5min, 15min, 1hour, daily, etc.)
- Technical indicators calculation
- Complex analytical queries
- Volume profile analysis
- Correlation analysis
- Market summary statistics
- Custom SQL query execution
"""

from .database import DuckDBManager
from .data_loader import DataLoader
from .query_api import QueryAPI, TimeFrame

# Only import API server if FastAPI is available
try:
    from .api_server import app
    __all__ = ["DuckDBManager", "DataLoader", "QueryAPI", "TimeFrame", "app"]
except ImportError:
    __all__ = ["DuckDBManager", "DataLoader", "QueryAPI", "TimeFrame"]

__version__ = "1.0.0"
