"""
REST API Interface
==================

FastAPI-based REST API for the DuckDB Financial Infrastructure.
Provides programmatic access to all platform features.
"""

from .app import app

__all__ = ['app']
