"""
DuckDB Advanced Framework for Financial Data Analysis
====================================================

This framework provides:
- Advanced query building and optimization
- Analytical functions for financial data
- Scanner framework for pattern recognition
- Real-time trading infrastructure
"""

from .query_builder import QueryBuilder, AdvancedQueryBuilder
from .analytics import FinancialAnalytics, TechnicalIndicators
from .scanner import ScannerFramework, SignalEngine
from .realtime import RealtimeManager, OrderManager

__all__ = [
    'QueryBuilder',
    'AdvancedQueryBuilder',
    'FinancialAnalytics',
    'TechnicalIndicators',
    'ScannerFramework',
    'SignalEngine',
    'RealtimeManager',
    'OrderManager'
]
