"""
Compatibility shim to expose DuckDBAdapter under src/infrastructure/adapters.

This consolidates imports while `database/adapters/duckdb_adapter.py` remains
in place. Downstream code can import
`src.infrastructure.adapters.duckdb_adapter.DuckDBAdapter`.
"""

from infrastructure.database.duckdb_adapter import DuckDBAdapter  # type: ignore F401

__all__ = ["DuckDBAdapter"]

