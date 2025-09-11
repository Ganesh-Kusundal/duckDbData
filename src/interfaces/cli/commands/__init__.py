"""
CLI Commands
Consolidated command definitions from all modules
"""

from .market_data_commands import register_market_data_commands
from .analytics_commands import register_analytics_commands
from .scanner_commands import register_scanner_commands
from .system_commands import register_system_commands
from .trading_commands import register_trading_commands


def register_commands(cli_app):
    """
    Register all CLI commands with the main application

    Args:
        cli_app: Typer CLI application instance
    """
    # Register all command modules
    try:
        register_market_data_commands(cli_app)
    except Exception as e:
        print(f"Warning: Failed to register market data commands: {e}")

    try:
        register_analytics_commands(cli_app)
    except Exception as e:
        print(f"Warning: Failed to register analytics commands: {e}")

    try:
        register_scanner_commands(cli_app)
    except Exception as e:
        print(f"Warning: Failed to register scanner commands: {e}")

    try:
        register_system_commands(cli_app)
    except Exception as e:
        print(f"Warning: Failed to register system commands: {e}")

    try:
        register_trading_commands(cli_app)
    except Exception as e:
        print(f"Warning: Failed to register trading commands: {e}")


__all__ = [
    'register_commands',
    'register_market_data_commands',
    'register_analytics_commands',
    'register_scanner_commands',
    'register_system_commands',
    'register_trading_commands'
]