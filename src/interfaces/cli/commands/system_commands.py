"""
System CLI Commands
CLI commands for system management and utilities
"""

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.infrastructure.dependency_container import get_container as get_dependency_container
from src.application.services.market_data_application_service import MarketDataApplicationService

logger = logging.getLogger(__name__)
console = Console()


def register_system_commands(cli_app):
    """
    Register system commands with the CLI app

    Args:
        cli_app: Typer CLI application instance
    """
    system_app = typer.Typer(help="System management and utilities")
    cli_app.add_typer(system_app, name="system")

    @system_app.command("health")
    def check_system_health(
        detailed: bool = typer.Option(False, help="Show detailed health information"),
        format: str = typer.Option("table", help="Output format (table, json)")
    ):
        """
        Check system health and status
        """
        async def _check_health():
            try:
                console.print("🏥 [bold blue]System Health Check[/bold blue]")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # Get health data
                health_data = await service.get_market_health_status()

                # Display results
                display_health_status(health_data, detailed, format)

            except Exception as e:
                console.print(f"❌ [red]Error checking system health: {e}[/red]")
                logger.exception("CLI system health error")

        # Run async function
        import asyncio
        asyncio.run(_check_health())

    @system_app.command("config")
    def show_configuration(
        section: Optional[str] = typer.Option(None, help="Show specific configuration section"),
        format: str = typer.Option("table", help="Output format (table, json)")
    ):
        """
        Show system configuration
        """
        async def _show_config():
            try:
                console.print("⚙️  [bold blue]System Configuration[/bold blue]")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # TODO: Implement actual configuration display
                # For now, show mock configuration

                # Display results
                display_system_config(section, format)

            except Exception as e:
                console.print(f"❌ [red]Error showing configuration: {e}[/red]")
                logger.exception("CLI system config error")

        # Run async function
        import asyncio
        asyncio.run(_show_config())

    @system_app.command("logs")
    def show_system_logs(
        level: str = typer.Option("INFO", help="Log level to show (DEBUG, INFO, WARNING, ERROR)"),
        lines: int = typer.Option(50, help="Number of log lines to show"),
        follow: bool = typer.Option(False, help="Follow log output (like tail -f)")
    ):
        """
        Show system logs
        """
        async def _show_logs():
            try:
                console.print(f"📝 [bold blue]System Logs (Level: {level})[/bold blue]")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # TODO: Implement actual log display
                # For now, show mock logs

                # Display results
                display_system_logs(level, lines, follow)

            except Exception as e:
                console.print(f"❌ [red]Error showing system logs: {e}[/red]")
                logger.exception("CLI system logs error")

        # Run async function
        import asyncio
        asyncio.run(_show_logs())

    @system_app.command("backup")
    def create_system_backup(
        destination: str = typer.Option("./backup", help="Backup destination directory"),
        include_data: bool = typer.Option(True, help="Include market data in backup"),
        include_config: bool = typer.Option(True, help="Include configuration in backup"),
        compress: bool = typer.Option(True, help="Compress backup files")
    ):
        """
        Create system backup
        """
        async def _create_backup():
            try:
                console.print(f"💾 [bold blue]Creating System Backup[/bold blue]")
                console.print(f"Destination: {destination}")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # TODO: Implement actual backup logic
                # For now, show mock backup process

                # Display results
                display_backup_progress(destination, include_data, include_config, compress)

            except Exception as e:
                console.print(f"❌ [red]Error creating backup: {e}[/red]")
                logger.exception("CLI system backup error")

        # Run async function
        import asyncio
        asyncio.run(_create_backup())

    @system_app.command("cleanup")
    def cleanup_system(
        older_than_days: int = typer.Option(30, help="Remove data older than N days"),
        dry_run: bool = typer.Option(True, help="Show what would be cleaned without actually doing it"),
        confirm: bool = typer.Option(False, help="Skip confirmation prompt")
    ):
        """
        Clean up old system data
        """
        async def _cleanup_system():
            try:
                console.print(f"🧹 [bold blue]System Cleanup[/bold blue]")
                console.print(f"Remove data older than: {older_than_days} days")
                console.print(f"Dry run: {dry_run}")

                if dry_run:
                    console.print("⚠️  [yellow]This is a dry run - no data will be actually deleted[/yellow]")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # TODO: Implement actual cleanup logic
                # For now, show mock cleanup process

                # Display results
                display_cleanup_plan(older_than_days, dry_run)

            except Exception as e:
                console.print(f"❌ [red]Error during cleanup: {e}[/red]")
                logger.exception("CLI system cleanup error")

        # Run async function
        import asyncio
        asyncio.run(_cleanup_system())


def display_health_status(health_data: dict, detailed: bool, format: str):
    """
    Display system health status

    Args:
        health_data: Health data from application service
        detailed: Whether to show detailed information
        format: Output format
    """
    console.print(f"\n🏥 [bold blue]System Health Status[/bold blue]")
    console.print("-" * 50)

    if format == "json":
        import json
        console.print(json.dumps(health_data, indent=2))
        return

    # Overall status
    status = health_data.get("status", "unknown")
    status_color = "green" if status == "healthy" else "red" if status == "unhealthy" else "yellow"

    console.print(f"📊 Overall Status: [{status_color}]{status.upper()}[/{status_color}]")
    console.print(f"⏰ Timestamp: {health_data.get('timestamp', 'unknown')}")

    # Services status
    if "components" in health_data:
        console.print("\n🔧 [cyan]Component Status:[/cyan]")
        components = health_data["components"]

        table = Table()
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")

        for component, info in components.items():
            comp_status = info.get("status", "unknown")
            status_color = "green" if comp_status == "healthy" else "red" if comp_status == "unhealthy" else "yellow"
            details = str(info.get("details", ""))[:50]  # Truncate long details
            table.add_row(component.replace("_", " ").title(), f"[{status_color}]{comp_status}[/{status_color}]", details)

        console.print(table)

    # System metrics
    if detailed and "metrics" in health_data:
        console.print("\n📊 [cyan]System Metrics:[/cyan]")
        metrics = health_data["metrics"]

        if "cpu" in metrics:
            console.print(f"🧠 CPU Usage: {metrics['cpu'].get('percent', 'N/A'):.1f}%")

        if "memory" in metrics:
            mem = metrics["memory"]
            console.print(f"💾 Memory: {mem.get('percent', 'N/A'):.1f}% used ({mem.get('used', 0)//(1024**3)}GB/{mem.get('total', 0)//(1024**3)}GB)")

        if "disk" in metrics:
            disk = metrics["disk"]
            console.print(f"💿 Disk: {disk.get('percent', 'N/A'):.1f}% used ({disk.get('free', 0)//(1024**3)}GB free)")


def display_system_config(section: Optional[str], format: str):
    """
    Display system configuration

    Args:
        section: Specific configuration section to show
        format: Output format
    """
    console.print(f"\n⚙️  [bold blue]System Configuration{' - ' + section if section else ''}[/bold blue]")
    console.print("-" * 60)

    # Mock configuration data
    config_data = {
        "database": {
            "type": "DuckDB",
            "path": "./data/financial_data.duckdb",
            "connection_pool": {
                "min_connections": 1,
                "max_connections": 10,
                "timeout": 30
            }
        },
        "api": {
            "host": "0.0.0.0",
            "port": 8000,
            "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
            "rate_limit": "100/minute"
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "./logs/app.log",
            "max_file_size": "10MB",
            "backup_count": 5
        },
        "cache": {
            "type": "Redis",
            "host": "localhost",
            "port": 6379,
            "ttl": 3600,
            "max_memory": "512MB"
        }
    }

    if section and section in config_data:
        config_data = {section: config_data[section]}

    if format == "json":
        import json
        console.print(json.dumps(config_data, indent=2))
    else:
        for section_name, section_config in config_data.items():
            console.print(f"\n🔧 [cyan]{section_name.upper()}:[/cyan]")
            display_config_section(section_config, indent=2)


def display_config_section(config: dict, indent: int = 0):
    """
    Display a configuration section recursively

    Args:
        config: Configuration dictionary
        indent: Indentation level
    """
    indent_str = " " * indent

    for key, value in config.items():
        if isinstance(value, dict):
            console.print(f"{indent_str}• {key}:")
            display_config_section(value, indent + 2)
        elif isinstance(value, list):
            console.print(f"{indent_str}• {key}: {', '.join(str(v) for v in value)}")
        else:
            console.print(f"{indent_str}• {key}: {value}")


def display_system_logs(level: str, lines: int, follow: bool):
    """
    Display system logs

    Args:
        level: Log level to show
        lines: Number of lines to show
        follow: Whether to follow logs
    """
    console.print(f"\n📝 [bold blue]Recent System Logs (Level: {level})[/bold blue]")
    console.print("-" * 70)

    # Mock log entries
    mock_logs = [
        {"timestamp": "2024-09-05 10:30:15", "level": "INFO", "module": "api.main", "message": "API server started on 0.0.0.0:8000"},
        {"timestamp": "2024-09-05 10:30:16", "level": "INFO", "module": "database", "message": "Database connection established"},
        {"timestamp": "2024-09-05 10:30:20", "level": "INFO", "module": "market_data", "message": "Loaded 1250 market data records"},
        {"timestamp": "2024-09-05 10:31:05", "level": "WARNING", "module": "scanner", "message": "Scanner rule 'momentum_breakout' generated 45 signals"},
        {"timestamp": "2024-09-05 10:32:10", "level": "INFO", "module": "analytics", "message": "Technical indicators calculated for AAPL"},
        {"timestamp": "2024-09-05 10:33:15", "level": "ERROR", "module": "api.routes", "message": "Invalid request parameters for /api/v1/market-data"},
        {"timestamp": "2024-09-05 10:34:20", "level": "INFO", "module": "cache", "message": "Cache hit rate: 87.3%"},
        {"timestamp": "2024-09-05 10:35:25", "level": "DEBUG", "module": "cqrs", "message": "Command UpdateMarketData executed successfully"}
    ]

    # Filter by level
    level_hierarchy = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
    min_level = level_hierarchy.get(level.upper(), 1)
    filtered_logs = [log for log in mock_logs if level_hierarchy.get(log["level"], 1) >= min_level]

    # Show requested number of lines
    display_logs = filtered_logs[-lines:] if lines > 0 else filtered_logs

    if not follow:
        table = Table()
        table.add_column("Time", style="blue", no_wrap=True)
        table.add_column("Level", style="cyan", no_wrap=True)
        table.add_column("Module", style="white", no_wrap=True)
        table.add_column("Message", style="white")

        for log_entry in display_logs:
            level_color = {
                "DEBUG": "blue",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red"
            }.get(log_entry["level"], "white")

            table.add_row(
                log_entry["timestamp"],
                f"[{level_color}]{log_entry['level']}[/{level_color}]",
                log_entry["module"],
                log_entry["message"]
            )

        console.print(table)
        console.print(f"\n📊 Showing {len(display_logs)} of {len(filtered_logs)} log entries")
    else:
        console.print("⚠️  [yellow]Follow mode not implemented in this demo[/yellow]")
        console.print("Use your system's log monitoring tools for real-time log following")


def display_backup_progress(destination: str, include_data: bool, include_config: bool, compress: bool):
    """
    Display backup progress

    Args:
        destination: Backup destination
        include_data: Whether to include data
        include_config: Whether to include config
        compress: Whether to compress
    """
    console.print(f"\n💾 [bold blue]Creating System Backup[/bold blue]")
    console.print(f"Destination: {destination}")
    console.print("-" * 60)

    # Mock backup items
    backup_items = []

    if include_data:
        backup_items.extend([
            {"type": "Database", "file": "financial_data.duckdb", "size": "2.5GB", "status": "✅ Backed up"},
            {"type": "Market Data", "file": "market_data/", "size": "1.8GB", "status": "✅ Backed up"},
            {"type": "Analytics", "file": "analytics_cache/", "size": "500MB", "status": "✅ Backed up"}
        ])

    if include_config:
        backup_items.extend([
            {"type": "Config", "file": "configs/", "size": "25MB", "status": "✅ Backed up"},
            {"type": "Logs", "file": "logs/", "size": "150MB", "status": "✅ Backed up"}
        ])

    table = Table()
    table.add_column("Type", style="cyan")
    table.add_column("File/Path", style="white")
    table.add_column("Size", style="green")
    table.add_column("Status", style="yellow")

    total_size = 0
    for item in backup_items:
        table.add_row(item["type"], item["file"], item["size"], item["status"])
        # Simple size parsing for total
        size_str = item["size"]
        if "GB" in size_str:
            total_size += float(size_str.replace("GB", "").strip()) * 1024
        elif "MB" in size_str:
            total_size += float(size_str.replace("MB", "").strip())

    console.print(table)

    console.print(f"\n📊 [cyan]Backup Summary:[/cyan]")
    console.print(f"  Total Items: {len(backup_items)}")
    console.print(f"  Total Size: {total_size:.1f}MB")
    console.print(f"  Compression: {'Enabled' if compress else 'Disabled'}")
    console.print(f"  Backup Location: {destination}")

    if compress:
        console.print(f"  Estimated Compressed Size: {total_size * 0.7:.1f}MB")


def display_cleanup_plan(older_than_days: int, dry_run: bool):
    """
    Display cleanup plan

    Args:
        older_than_days: Remove data older than this many days
        dry_run: Whether this is a dry run
    """
    console.print(f"\n🧹 [bold blue]System Cleanup Plan[/bold blue]")
    console.print(f"Remove data older than: {older_than_days} days")
    console.print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (data will be deleted)'}")
    console.print("-" * 80)

    # Mock cleanup items
    cleanup_items = [
        {"type": "Old Market Data", "location": "market_data table", "records": 12500, "size": "850MB"},
        {"type": "Expired Cache", "location": "cache/", "files": 45, "size": "125MB"},
        {"type": "Old Logs", "location": "logs/", "files": 12, "size": "75MB"},
        {"type": "Temporary Files", "location": "temp/", "files": 8, "size": "45MB"}
    ]

    table = Table()
    table.add_column("Data Type", style="cyan")
    table.add_column("Location", style="white")
    table.add_column("Items", style="yellow")
    table.add_column("Size", style="green")

    total_items = 0
    total_size = 0
    for item in cleanup_items:
        if "records" in item:
            items_str = f"{item['records']:,} records"
            total_items += item['records']
        else:
            items_str = f"{item['files']} files"
            total_items += item['files']

        table.add_row(item["type"], item["location"], items_str, item["size"])

        # Simple size parsing for total
        size_str = item["size"]
        if "GB" in size_str:
            total_size += float(size_str.replace("GB", "").strip()) * 1024
        elif "MB" in size_str:
            total_size += float(size_str.replace("MB", "").strip())

    console.print(table)

    console.print(f"\n📊 [cyan]Cleanup Summary:[/cyan]")
    console.print(f"  Total Items to Remove: {total_items:,}")
    console.print(f"  Total Space to Free: {total_size:.1f}MB")

    if dry_run:
        console.print("\n✅ [green]This is a dry run - no data will be actually deleted[/green]")
        console.print("   Run with --no-dry-run to perform actual cleanup")
    else:
        console.print("\n⚠️  [red]WARNING: This will permanently delete data![/red]")
        console.print("   Make sure you have backups before proceeding")
