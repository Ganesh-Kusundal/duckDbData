"""
Scanner CLI commands.
"""

import click
from datetime import date, time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import pandas as pd

# Import with fallback handling
try:
    from duckdb_financial_infra.infrastructure.logging import get_logger
    from duckdb_financial_infra.application.scanners.base_scanner import BaseScanner
    from duckdb_financial_infra.application.scanners.strategies.technical_scanner import TechnicalScanner
    from duckdb_financial_infra.application.scanners.strategies.relative_volume_scanner import RelativeVolumeScanner
    from duckdb_financial_infra.infrastructure.core.database import DuckDBManager
except ImportError:
    try:
        # Try relative imports for development
        from ...infrastructure.logging import get_logger
        from ...application.scanners.base_scanner import BaseScanner
        from ...application.scanners.strategies.technical_scanner import TechnicalScanner
        from ...application.scanners.strategies.relative_volume_scanner import RelativeVolumeScanner
        from ...infrastructure.core.database import DuckDBManager
    except ImportError:
        # Final fallback
        import logging
        get_logger = lambda name: logging.getLogger(name)
        BaseScanner = None
        TechnicalScanner = None
        RelativeVolumeScanner = None
        DuckDBManager = None

logger = get_logger(__name__)
console = Console()


@click.group()
@click.pass_context
def scanners(ctx):
    """Scanner execution and management commands."""
    pass


@scanners.command()
@click.option('--scanner-type', type=click.Choice(['technical', 'relative_volume', 'breakout']), default='technical',
              help='Type of scanner to run')
@click.option('--date', 'scan_date', type=click.DateTime(formats=['%Y-%m-%d']),
              default=lambda: date.today().strftime('%Y-%m-%d'), help='Date to scan (YYYY-MM-DD)')
@click.option('--cutoff-time', type=click.STRING, default='09:50',
              help='Cutoff time for scanning (HH:MM)')
@click.option('--output-format', type=click.Choice(['table', 'csv', 'json']), default='table',
              help='Output format')
@click.option('--output-file', type=click.Path(), help='Output file path')
@click.option('--limit', default=50, help='Maximum results to display')
@click.pass_context
def run(ctx, scanner_type, scan_date, cutoff_time, output_format, output_file, limit):
    """Run a scanner for the specified date."""
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        console.print(f"[bold blue]🔍 Running {scanner_type} scanner for {scan_date.date()}[/bold blue]")

    try:
        # Initialize scanner
        if scanner_type == 'technical':
            scanner = TechnicalScanner()
        elif scanner_type == 'relative_volume':
            scanner = RelativeVolumeScanner()
        else:
            raise click.BadParameter(f"Unsupported scanner type: {scanner_type}")

        # Run scanner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"🔍 Scanning with {scanner_type} scanner...", total=None)

            results_df = scanner.scan(
                scan_date=scan_date.date(),
                cutoff_time=cutoff_time
            )

            progress.update(task, completed=True)

        if results_df.empty:
            console.print("[yellow]⚠️  No results found from scanner[/yellow]")
            return

        # Limit results if specified
        if limit and len(results_df) > limit:
            results_df = results_df.head(limit)
            console.print(f"[yellow]⚠️  Showing first {limit} results[/yellow]")

        # Output results
        if output_file:
            if output_format == 'csv':
                results_df.to_csv(output_file, index=False)
            elif output_format == 'json':
                results_df.to_json(output_file, orient='records', indent=2)
            console.print(f"[green]✅ Results saved to: {output_file}[/green]")
        else:
            # Display as table
            display_scanner_results(results_df, scanner_type)

    except Exception as e:
        logger.error(f"Scanner execution failed: {e}")
        console.print(f"[red]❌ Scanner execution failed: {e}[/red]")
        raise click.Abort()


@scanners.command()
@click.option('--scanner-type', type=click.Choice(['technical', 'relative_volume']), default='technical')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), required=True)
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), required=True)
@click.option('--output-dir', type=click.Path(), default='scanner_results',
              help='Output directory for results')
@click.option('--parallel', is_flag=True, help='Run scans in parallel')
@click.pass_context
def backtest(ctx, scanner_type, start_date, end_date, output_dir, parallel):
    """Run scanner backtest over a date range."""
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        console.print(f"[bold blue]📈 Running {scanner_type} scanner backtest[/bold blue]")
        console.print(f"[blue]Period: {start_date.date()} to {end_date.date()}[/blue]")

    try:
        from ...application.scanners.backtests.backtester import Backtester

        # Initialize backtester
        backtester = Backtester(scanner_type=scanner_type)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Run backtest
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("📈 Running backtest...", total=None)

            results = backtester.run_backtest(
                start_date=start_date.date(),
                end_date=end_date.date(),
                output_dir=str(output_path),
                parallel=parallel
            )

            progress.update(task, completed=True)

        # Display summary
        console.print(f"[green]✅ Backtest completed![/green]")

        table = Table(title="📊 Backtest Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Days", str(results.get('total_days', 0)))
        table.add_row("Successful Scans", str(results.get('successful_scans', 0)))
        table.add_row("Average Signals/Day", ".2f")
        table.add_row("Output Directory", str(output_path))

        console.print(table)

    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        console.print(f"[red]❌ Backtest failed: {e}[/red]")
        raise click.Abort()


@scanners.command()
@click.option('--scanner-type', type=click.Choice(['technical', 'relative_volume']))
@click.pass_context
def optimize(ctx, scanner_type):
    """Optimize scanner parameters."""
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        console.print(f"[bold blue]🎯 Optimizing {scanner_type} scanner parameters[/bold blue]")

    try:
        from ...application.scanners.backtests.optimization_engine import OptimizationEngine

        # Initialize optimizer
        optimizer = OptimizationEngine(scanner_type=scanner_type)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🎯 Optimizing parameters...", total=None)

            results = optimizer.optimize()

            progress.update(task, completed=True)

        # Display optimization results
        console.print(f"[green]✅ Optimization completed![/green]")

        table = Table(title="🎯 Optimization Results")
        table.add_column("Parameter", style="cyan")
        table.add_column("Optimal Value", style="green")
        table.add_column("Score", style="magenta")

        for param, value in results.get('optimal_params', {}).items():
            table.add_row(param, str(value), "")

        console.print(table)

    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        console.print(f"[red]❌ Optimization failed: {e}[/red]")
        raise click.Abort()


@scanners.command()
@click.pass_context
def list(ctx):
    """List available scanners."""
    scanners_info = [
        {
            'name': 'technical',
            'description': 'Technical analysis scanner with RSI, MACD, Bollinger Bands',
            'status': '✅ Available'
        },
        {
            'name': 'relative_volume',
            'description': 'Relative volume analysis scanner',
            'status': '✅ Available'
        },
        {
            'name': 'breakout',
            'description': 'Advanced breakout pattern scanner with volume confirmation',
            'status': '✅ Available'
        }
    ]

    table = Table(title="🔍 Available Scanners")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    for scanner in scanners_info:
        table.add_row(
            scanner['name'],
            scanner['description'],
            scanner['status']
        )

    console.print(table)


def display_scanner_results(results_df, scanner_type):
    """Display scanner results in a formatted table."""
    if scanner_type == 'technical':
        table = Table(title=f"📊 Technical Scanner Results ({len(results_df)} symbols)")
        table.add_column("Symbol", style="cyan")
        table.add_column("Price", style="green")
        table.add_column("Change %", style="magenta")
        table.add_column("RSI", style="yellow")
        table.add_column("BB Position", style="blue")
        table.add_column("Trend", style="white")
        table.add_column("Score", style="red")

        for _, row in results_df.iterrows():
            change_color = "green" if row.get('price_change_pct', 0) > 0 else "red"
            table.add_row(
                str(row.get('symbol', '')),
                ".2f",
                ".2f",
                ".1f",
                str(row.get('bb_position', '')),
                str(row.get('trend_signal', '')),
                str(row.get('technical_score', ''))
            )
    else:
        # Generic display for other scanners
        table = Table(title=f"📊 Scanner Results ({len(results_df)} symbols)")
        for col in results_df.columns[:6]:  # Show first 6 columns
            table.add_column(col.replace('_', ' ').title(), style="cyan")

        for _, row in results_df.head(10).iterrows():
            table.add_row(*[str(row[col]) for col in results_df.columns[:6]])

    console.print(table)
