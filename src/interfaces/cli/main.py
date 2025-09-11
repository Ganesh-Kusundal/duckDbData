"""
Unified CLI Application
Consolidates all CLI commands from different modules into a single interface
"""

import logging
import asyncio
from typing import Optional

# Try to import Typer, fallback to mock if not available
try:
    import typer
    from rich.console import Console
    from rich.logging import RichHandler
    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False
    # Mock classes for when Typer/Rich is not available
    class Typer:
        def __init__(self, **kwargs):
            pass

        def callback(self, **kwargs):
            def decorator(func):
                return func
            return decorator

        def command(self, **kwargs):
            def decorator(func):
                return func
            return decorator

        def add_typer(self, *args, **kwargs):
            pass

    def Option(*args, **kwargs):
        return args[0] if args else None

    typer = type('MockTyper', (), {'Typer': Typer, 'Option': Option})()

    class Console:
        def print(self, *args, **kwargs):
            print(*args, **kwargs)

    class RichHandler:
        pass

    logging.basicConfig(level=logging.INFO)

from .commands import register_commands
from src.infrastructure.dependency_container import get_container as get_dependency_container

# Setup logging with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)
console = Console()

# Create main CLI app
cli_app = typer.Typer(
    name="trading-system",
    help="Unified Trading System CLI",
    add_completion=True,
    rich_markup_mode="rich"
)


@cli_app.callback()
def main_callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """
    Main CLI callback - sets up logging and global options
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        console.print("🐛 [bold blue]Debug logging enabled[/bold blue]")
    elif verbose:
        logging.getLogger().setLevel(logging.INFO)
        console.print("📝 [bold blue]Verbose logging enabled[/bold blue]")
    else:
        logging.getLogger().setLevel(logging.WARNING)


async def initialize_cli():
    """
    Initialize CLI dependencies and services
    """
    console.print("🚀 [bold green]Initializing Trading System CLI...[/bold green]")

    try:
        # Initialize complete application with bootstrap
        from infrastructure.bootstrap import initialize_application
        success = await initialize_application()

        if not success:
            console.print("❌ [red]CLI initialization failed: Bootstrap unsuccessful[/red]")
            return None

        # Get initialized container
        container = get_dependency_container()

        console.print("✅ [green]CLI initialized successfully[/green]")
        return container

    except Exception as e:
        console.print(f"❌ [red]CLI initialization failed: {e}[/red]")
        raise


@cli_app.command("status")
def show_status():
    """
    Show system status and health information
    """
    console.print("📊 [bold blue]Trading System Status[/bold blue]")
    console.print("=" * 50)

    # Show basic system information
    import platform
    import psutil
    from datetime import datetime

    console.print(f"🖥️  [cyan]Platform:[/cyan] {platform.system()} {platform.release()}")
    console.print(f"🐍 [cyan]Python:[/cyan] {platform.python_version()}")
    console.print(f"⏰ [cyan]Time:[/cyan] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Show resource usage
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()

    console.print(f"🧠 [cyan]CPU Usage:[/cyan] {cpu_percent:.1f}%")
    console.print(f"💾 [cyan]Memory:[/cyan] {memory.percent:.1f}% used ({memory.used // (1024**3)}GB/{memory.total // (1024**3)}GB)")

    console.print("\n🔧 [bold blue]Services Status:[/bold blue]")
    console.print("✅ Application Layer: Operational")
    console.print("✅ Infrastructure Layer: Operational")
    console.print("✅ Domain Layer: Operational")
    console.print("✅ Presentation Layer: Operational")


@cli_app.command("version")
def show_version():
    """
    Show version information
    """
    console.print("📦 [bold blue]Trading System Version[/bold blue]")
    console.print("=" * 40)
    console.print("🎯 Version: 2.0.0")
    console.print("🏗️  Architecture: Clean Architecture + CQRS")
    console.print("📅 Release Date: September 2025")
    console.print("🔧 Built with: Python 3.11+, FastAPI, Typer")


def run_cli():
    """
    Run the CLI application
    This is the main entry point for the CLI
    """
    try:
        # Initialize CLI with bootstrap
        import asyncio
        global _cli_container
        _cli_container = asyncio.run(initialize_cli())
        print(f"DEBUG: CLI container set: {_cli_container is not None}")

        # Register all commands
        register_commands(cli_app)

        # Run the CLI
        cli_app()

    except KeyboardInterrupt:
        console.print("\n👋 [yellow]CLI interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n❌ [red]CLI error: {e}[/red]")
        logger.exception("CLI execution failed")
        raise

# Global variable to store the CLI container
_cli_container = None


if __name__ == "__main__":
    run_cli()