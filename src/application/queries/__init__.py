"""
Application Layer - Queries
CQRS Query definitions for read operations
"""

from .base_query import Query, QueryResult
from .market_data_queries import (
    GetMarketDataQuery,
    GetMarketDataHistoryQuery,
    GetMarketDataSummaryQuery,
    GetTechnicalIndicatorsQuery,
    GetMarketAnomaliesQuery
)

__all__ = [
    'Query',
    'QueryResult',
    'GetMarketDataQuery',
    'GetMarketDataHistoryQuery',
    'GetMarketDataSummaryQuery',
    'GetTechnicalIndicatorsQuery',
    'GetMarketAnomaliesQuery'
]
