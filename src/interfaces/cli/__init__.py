"""
Unified CLI Interface Layer
Consolidates all CLI commands from analytics, scanner, trade_engine, and sync modules
"""

from .main import cli_app, run_cli
from .commands import register_commands

__all__ = [
    'cli_app',
    'run_cli',
    'register_commands'
]