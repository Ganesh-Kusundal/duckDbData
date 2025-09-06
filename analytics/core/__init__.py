"""
DuckDB Analytics Dashboard Core Module
====================================

Core components for breakout pattern analysis and discovery.
"""

__version__ = "1.0.0"
__author__ = "DuckDB Financial Analytics"

from .duckdb_connector import DuckDBAnalytics
from .pattern_analyzer import PatternAnalyzer

__all__ = ['DuckDBAnalytics', 'PatternAnalyzer']
