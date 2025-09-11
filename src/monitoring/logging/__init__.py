"""
Monitoring Logging Package
==========================

This package provides a sophisticated logging framework with:
- Structured JSON logging
- Log aggregation and filtering
- Advanced search capabilities
- Correlation ID tracking
- Database storage
"""

from .structured_logger import (
    StructuredLogger,
    get_logger,
    set_correlation_id,
    get_correlation_id,
    LogEntry
)
from .aggregator import (
    LogAggregator,
    LogFilter,
    LogStats,
    log_aggregator
)
from .filters import (
    LogFilterEngine,
    AdvancedFilter,
    CompositeFilter,
    LogQuery,
    FilterOperator,
    filter_engine
)

__all__ = [
    # Structured Logger
    'StructuredLogger',
    'get_logger',
    'set_correlation_id',
    'get_correlation_id',
    'LogEntry',

    # Aggregator
    'LogAggregator',
    'LogFilter',
    'LogStats',
    'log_aggregator',

    # Filters
    'LogFilterEngine',
    'AdvancedFilter',
    'CompositeFilter',
    'LogQuery',
    'FilterOperator',
    'filter_engine'
]
