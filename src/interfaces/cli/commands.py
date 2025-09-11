"""
CLI Command Registration
Register all commands from different modules into the unified CLI
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typer import Typer

logger = logging.getLogger(__name__)


def register_commands(cli_app):
    """
    Register all CLI commands from different modules

    Args:
        cli_app: Typer CLI application instance
    """
    logger.info("Registering CLI commands...")

    try:
        # Import command registration functions
        from .commands.market_data_commands import register_market_data_commands
        from .commands.analytics_commands import register_analytics_commands
        from .commands.scanner_commands import register_scanner_commands
        from .commands.system_commands import register_system_commands

        # Register market data commands
        register_market_data_commands(cli_app)
        logger.info("✅ Market data commands registered")

        # Register analytics commands
        register_analytics_commands(cli_app)
        logger.info("✅ Analytics commands registered")

        # Register scanner commands
        register_scanner_commands(cli_app)
        logger.info("✅ Scanner commands registered")

        # Register system commands
        register_system_commands(cli_app)
        logger.info("✅ System commands registered")

        logger.info("🎉 All CLI commands registered successfully")

    except Exception as e:
        logger.error(f"Failed to register CLI commands: {e}")
        raise


def get_command_groups():
    """
    Get information about available command groups

    Returns:
        Dictionary of command groups and their descriptions
    """
    return {
        "market-data": {
            "description": "Market data operations (get, update, import)",
            "commands": ["get", "update", "import", "export", "validate"]
        },
        "analytics": {
            "description": "Analytics and technical analysis",
            "commands": ["indicators", "anomalies", "statistics", "backtest"]
        },
        "scanner": {
            "description": "Market scanner and rule-based analysis",
            "commands": ["scan", "rules", "backtest", "optimize"]
        },
        "system": {
            "description": "System management and utilities",
            "commands": ["status", "health", "config", "logs", "backup"]
        }
    }


def get_command_help():
    """
    Get comprehensive help information for all commands

    Returns:
        Formatted help text
    """
    groups = get_command_groups()

    help_text = """
🎯 Trading System CLI - Unified Interface

This CLI provides a unified interface to all trading system functionality,
consolidating commands from analytics, scanner, trade_engine, and sync modules.

📚 Available Command Groups:
"""

    for group_name, group_info in groups.items():
        help_text += f"\n🔹 {group_name.upper()}\n"
        help_text += f"   {group_info['description']}\n"
        help_text += f"   Commands: {', '.join(group_info['commands'])}\n"

    help_text += """

🚀 Quick Start Examples:

  # Get current market data
  trading-system market-data get AAPL

  # Run technical analysis
  trading-system analytics indicators AAPL --indicators SMA EMA RSI

  # Scan market for patterns
  trading-system scanner scan --symbols AAPL MSFT GOOGL

  # Check system health
  trading-system system health

  # Get help for specific command
  trading-system market-data --help

📖 For detailed help on any command, use: trading-system <group> <command> --help

🔧 Global Options:
  --verbose, -v    Enable verbose logging
  --debug          Enable debug logging
  --help           Show this help message
"""

    return help_text
