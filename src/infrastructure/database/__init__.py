"""
Unified DuckDB Database Infrastructure
====================================

Provides a consolidated, efficient DuckDB integration layer that eliminates
multiple connection flows and provides unified access to database operations.
"""

from .unified_duckdb import (
    UnifiedDuckDBManager,
    DuckDBConfig,
    ConnectionPool,
    SchemaManager,
    QueryExecutor,
)

__all__ = [
    'UnifiedDuckDBManager',
    'DuckDBConfig',
    'ConnectionPool',
    'SchemaManager',
    'QueryExecutor',
]
