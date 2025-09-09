"""
Main CLI entry point for DuckDB Financial Infrastructure.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Try to import logging, fallback to basic logging if not available
try:
    from duckdb_financial_infra.infrastructure.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    try:
        # Try relative import for development
        from ..infrastructure.logging import get_logger
        logger = get_logger(__name__)
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

console = Console()


def create_cli_app():
    """Create and configure the main CLI application."""

    @click.group()
    @click.version_option(version="1.0.0")
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
    @click.pass_context
    def cli(ctx, verbose):
        """DuckDB Financial Infrastructure CLI

        A comprehensive command-line interface for managing the financial data platform.
        """
        # Store verbose flag in context for subcommands
        ctx.ensure_object(dict)
        ctx.obj['verbose'] = verbose

        if verbose:
            logger.info("CLI started with verbose logging")

        # Display welcome message
        welcome_text = Text("🚀 DuckDB Financial Infrastructure CLI", style="bold blue")
        console.print(Panel.fit(welcome_text, border_style="blue"))

    # Import and register subcommands with error handling
    try:
        from .commands import data, scanners, system, config
        cli.add_command(data.data)
        cli.add_command(scanners.scanners)
        cli.add_command(system.system)
        cli.add_command(config.config)
    except ImportError as e:
        logger.warning(f"Some CLI commands could not be loaded: {e}")
        # Try with alternative imports for development
        try:
            from .commands.data import data
            from .commands.scanners import scanners
            from .commands.system import system
            from .commands.config import config
            cli.add_command(data)
            cli.add_command(scanners)
            cli.add_command(system)
            cli.add_command(config)
        except ImportError:
            # Add basic help command
            @cli.command()
            def help():
                """Show help information."""
                console.print("[yellow]CLI commands are not fully available due to import issues.[/yellow]")
                console.print("Please ensure the package is properly installed or run from the correct directory.")

    return cli


# Create the main CLI app
app = create_cli_app()


if __name__ == "__main__":
    app()
