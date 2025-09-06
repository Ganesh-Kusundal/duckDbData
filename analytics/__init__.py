#!/usr/bin/env python3
"""
Analytics Module
================

A comprehensive analytics dashboard for DuckDB-based stock data analysis.
"""

__version__ = "1.0.0"
__description__ = "Analytics dashboard for stock data analysis"

# Make this a proper Python package
from .core import DuckDBAnalytics, PatternAnalyzer
from .rules import RuleEngine, TradingRule
from .utils import DataProcessor, AnalyticsVisualizer

__all__ = [
    'DuckDBAnalytics',
    'PatternAnalyzer',
    'RuleEngine',
    'TradingRule',
    'DataProcessor',
    'AnalyticsVisualizer'
]
