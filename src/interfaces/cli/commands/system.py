"""
System monitoring and management CLI commands.
"""

import click
from datetime import datetime, timedelta
import psutil
import platform
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Import with fallback handling
try:
    from duckdb_financial_infra.infrastructure.logging import get_logger
    from duckdb_financial_infra.infrastructure.core.database import DuckDBManager
except ImportError:
    try:
        # Try relative imports for development
        from ...infrastructure.logging import get_logger
        from ...infrastructure.core.database import DuckDBManager
    except ImportError:
        # Final fallback
        import logging
        get_logger = lambda name: logging.getLogger(name)
        DuckDBManager = None

logger = get_logger(__name__)
console = Console()


@click.group()
@click.pass_context
def system(ctx):
    """System monitoring and management commands."""
    pass


@system.command()
@click.option('--detailed', is_flag=True, help='Show detailed system information')
@click.pass_context
def status(ctx, detailed):
    """Show system status and health."""
    verbose = ctx.obj.get('verbose', False)

    try:
        # Get system information
        system_info = get_system_info()

        # Get database status
        db_status = get_database_status()

        # Get process information
        process_info = get_process_info()

        # Display system status
        if detailed:
            display_detailed_status(system_info, db_status, process_info)
        else:
            display_brief_status(system_info, db_status, process_info)

    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        console.print(f"[red]❌ Failed to get system status: {e}[/red]")
        raise click.Abort()


@system.command()
@click.option('--lines', default=50, help='Number of log lines to display')
@click.option('--level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), help='Filter by log level')
@click.option('--service', type=click.Choice(['pipeline', 'api', 'scanner']), help='Filter by service')
@click.pass_context
def logs(ctx, lines, level, service):
    """Display recent system logs."""
    verbose = ctx.obj.get('verbose', False)

    try:
        log_files = {
            'pipeline': 'logs/pipeline_monitor.log',
            'api': 'logs/api.log',
            'scanner': 'logs/scanner.log'
        }

        if service:
            log_file = log_files.get(service, 'logs/duckdb_financial.log')
        else:
            log_file = 'logs/duckdb_financial.log'

        log_path = Path(log_file)

        if not log_path.exists():
            console.print(f"[yellow]⚠️  Log file not found: {log_file}[/yellow]")
            return

        # Read and filter logs
        with open(log_path, 'r') as f:
            all_lines = f.readlines()

        # Apply filters
        filtered_lines = []
        for line in reversed(all_lines):  # Start from most recent
            if len(filtered_lines) >= lines:
                break

            if level and level not in line:
                continue

            filtered_lines.append(line.strip())

        # Display logs
        console.print(f"[bold blue]📋 Recent logs from {log_file}[/bold blue]")

        for line in reversed(filtered_lines):  # Show in chronological order
            if 'ERROR' in line:
                console.print(f"[red]{line}[/red]")
            elif 'WARNING' in line:
                console.print(f"[yellow]{line}[/yellow]")
            elif 'INFO' in line:
                console.print(f"[blue]{line}[/blue]")
            else:
                console.print(line)

    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        console.print(f"[red]❌ Failed to read logs: {e}[/red]")
        raise click.Abort()


@system.command()
@click.option('--hours', default=24, help='Hours of history to display')
@click.pass_context
def monitor(ctx, hours):
    """Monitor system performance in real-time."""
    verbose = ctx.obj.get('verbose', False)

    try:
        console.print(f"[bold blue]📊 Monitoring system for {hours} hours...[/bold blue]")
        console.print("[dim]Press Ctrl+C to stop monitoring[/dim]\n")

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=hours)

        while datetime.now() < end_time:
            # Clear screen and show current status
            console.clear()

            # Get current metrics
            system_info = get_system_info()
            db_status = get_database_status()

            # Display header
            console.print(f"[bold green]🔍 System Monitor - {datetime.now().strftime('%H:%M:%S')}[/bold green]\n")

            # System metrics
            table = Table(title="💻 System Metrics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Status", style="magenta")

            cpu_percent = system_info['cpu_percent']
            memory_percent = system_info['memory_percent']
            disk_percent = system_info['disk_percent']

            table.add_row("CPU Usage", ".1f", get_status_indicator(cpu_percent, 80))
            table.add_row("Memory Usage", ".1f", get_status_indicator(memory_percent, 85))
            table.add_row("Disk Usage", ".1f", get_status_indicator(disk_percent, 90))

            console.print(table)

            # Database metrics
            if db_status['status'] == 'healthy':
                db_table = Table(title="🗄️  Database Status")
                db_table.add_column("Metric", style="cyan")
                db_table.add_column("Value", style="green")

                db_table.add_row("Status", "[green]Healthy[/green]")
                db_table.add_row("Records", f"{db_status.get('total_records', 0):,}")
                db_table.add_row("Symbols", f"{db_status.get('total_symbols', 0):,}")

                console.print(db_table)

            # Wait before next update
            import time
            time.sleep(5)

    except KeyboardInterrupt:
        console.print("\n[blue]👋 Monitoring stopped by user[/blue]")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        console.print(f"[red]❌ Monitoring failed: {e}[/red]")
        raise click.Abort()


@system.command()
@click.pass_context
def cleanup(ctx):
    """Clean up temporary files and optimize database."""
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        console.print("[bold blue]🧹 Starting system cleanup[/bold blue]")

    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Database optimization
            task1 = progress.add_task("🗄️  Optimizing database...", total=None)
            db_manager = DuckDBManager()

            with db_manager.get_connection() as conn:
                # Run optimization queries
                conn.execute("VACUUM")
                conn.execute("ANALYZE market_data")

            progress.update(task1, completed=True)

            # Clean up temporary files
            task2 = progress.add_task("🗂️  Cleaning temporary files...", total=None)

            temp_files = [
                "data/temp/*",
                "logs/*.tmp",
                "__pycache__",
                "*.pyc"
            ]

            cleaned_count = 0
            for pattern in temp_files:
                for path in Path(".").glob(pattern):
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                        elif path.is_dir():
                            import shutil
                            shutil.rmtree(path)
                        cleaned_count += 1

            progress.update(task2, completed=True)

        console.print("[green]✅ System cleanup completed![/green]")
        console.print(f"[blue]🗑️  Cleaned up {cleaned_count} temporary items[/blue]")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        console.print(f"[red]❌ Cleanup failed: {e}[/red]")
        raise click.Abort()


def get_system_info():
    """Get basic system information."""
    return {
        'platform': platform.system(),
        'cpu_count': psutil.cpu_count(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_total': psutil.virtual_memory().total,
        'memory_used': psutil.virtual_memory().used,
        'memory_percent': psutil.virtual_memory().percent,
        'disk_total': psutil.disk_usage('/').total,
        'disk_used': psutil.disk_usage('/').used,
        'disk_percent': psutil.disk_usage('/').percent,
    }


def get_database_status():
    """Get database health status."""
    try:
        db_manager = DuckDBManager()

        with db_manager.get_connection() as conn:
            # Get basic stats
            result = conn.execute("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT symbol) as total_symbols,
                    MAX(timestamp) as latest_record
                FROM market_data
            """).fetchone()

            return {
                'status': 'healthy',
                'total_records': result[0] if result else 0,
                'total_symbols': result[1] if result else 0,
                'latest_record': result[2] if result else None
            }
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def get_process_info():
    """Get information about the current process."""
    process = psutil.Process()
    return {
        'pid': process.pid,
        'cpu_percent': process.cpu_percent(),
        'memory_percent': process.memory_percent(),
        'memory_mb': process.memory_info().rss / 1024 / 1024,
        'threads': process.num_threads(),
        'status': process.status()
    }


def display_brief_status(system_info, db_status, process_info):
    """Display brief system status."""
    # Overall health
    health_status = "healthy"
    if system_info['cpu_percent'] > 90 or system_info['memory_percent'] > 90:
        health_status = "warning"
    if db_status.get('status') != 'healthy':
        health_status = "critical"

    status_color = {
        'healthy': 'green',
        'warning': 'yellow',
        'critical': 'red'
    }[health_status]

    console.print(f"[bold {status_color}]🔍 System Status: {health_status.upper()}[/bold {status_color}]")

    # Quick metrics
    table = Table()
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")

    table.add_row("CPU", get_status_indicator(system_info['cpu_percent'], 80),
                  ".1f")
    table.add_row("Memory", get_status_indicator(system_info['memory_percent'], 85),
                  ".1f")
    table.add_row("Disk", get_status_indicator(system_info['disk_percent'], 90),
                  ".1f")
    table.add_row("Database", "✅" if db_status.get('status') == 'healthy' else "❌",
                  f"{db_status.get('total_records', 0):,} records")

    console.print(table)


def display_detailed_status(system_info, db_status, process_info):
    """Display detailed system status."""
    # System Information
    sys_table = Table(title="💻 System Information")
    sys_table.add_column("Property", style="cyan")
    sys_table.add_column("Value", style="green")

    sys_table.add_row("Platform", system_info['platform'])
    sys_table.add_row("CPU Cores", str(system_info['cpu_count']))
    sys_table.add_row("CPU Usage", ".1f")
    sys_table.add_row("Memory Total", ".1f")
    sys_table.add_row("Memory Used", ".1f")
    sys_table.add_row("Memory Usage", ".1f")
    sys_table.add_row("Disk Total", ".1f")
    sys_table.add_row("Disk Used", ".1f")
    sys_table.add_row("Disk Usage", ".1f")

    console.print(sys_table)

    # Database Information
    if db_status.get('status') == 'healthy':
        db_table = Table(title="🗄️  Database Information")
        db_table.add_column("Property", style="cyan")
        db_table.add_column("Value", style="green")

        db_table.add_row("Status", "[green]Healthy[/green]")
        db_table.add_row("Total Records", f"{db_status.get('total_records', 0):,}")
        db_table.add_row("Total Symbols", f"{db_status.get('total_symbols', 0):,}")
        db_table.add_row("Latest Record", str(db_status.get('latest_record', 'N/A')))

        console.print(db_table)
    else:
        console.print(f"[red]❌ Database Status: {db_status.get('error', 'Unknown error')}[/red]")

    # Process Information
    proc_table = Table(title="⚙️  Process Information")
    proc_table.add_column("Property", style="cyan")
    proc_table.add_column("Value", style="green")

    proc_table.add_row("PID", str(process_info['pid']))
    proc_table.add_row("CPU Usage", ".1f")
    proc_table.add_row("Memory Usage", ".1f")
    proc_table.add_row("Memory (MB)", ".1f")
    proc_table.add_row("Threads", str(process_info['threads']))
    proc_table.add_row("Status", process_info['status'])

    console.print(proc_table)


def get_status_indicator(value, threshold):
    """Get status indicator based on value and threshold."""
    if value > threshold:
        return f"[red]⚠️  {value:.1f}%[/red]"
    elif value > threshold * 0.8:
        return f"[yellow]⚡ {value:.1f}%[/yellow]"
    else:
        return f"[green]✅ {value:.1f}%[/green]"
