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

from src.infrastructure.config.settings import get_settings

# Import with fallback handling
try:
    from src.infrastructure.logging import get_logger
    from src.application.scanners.strategies.technical_scanner import TechnicalScanner
    from src.application.scanners.strategies.relative_volume_scanner import RelativeVolumeScanner
except ImportError:
    try:
        # Try relative imports for development
        from ...infrastructure.logging import get_logger
        from ...application.scanners.strategies.technical_scanner import TechnicalScanner
        from ...application.scanners.strategies.relative_volume_scanner import RelativeVolumeScanner
    except ImportError:
        # Final fallback
        import logging
        get_logger = lambda name: logging.getLogger(name)
        TechnicalScanner = None
        RelativeVolumeScanner = None

logger = get_logger(__name__)
console = Console()


@click.group()
@click.pass_context
def scanners(ctx):
    """Scanner execution and management commands."""
    pass


@scanners.command()
@click.option('--scanner-type', type=click.Choice(['technical', 'relative_volume', 'breakout', 'crp']), default='technical',
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
        # Initialize scanner with proper port injection
        db_path = get_settings().database.path
        if scanner_type == 'technical':
            scanner = TechnicalScanner(db_path=db_path)
        elif scanner_type == 'relative_volume':
            scanner = RelativeVolumeScanner(db_path=db_path)
        elif scanner_type == 'crp':
            # Use composition root helper for CRP scanner with port injection
            from src.app.startup import get_scanner
            scanner = get_scanner('crp', db_path=db_path)
        elif scanner_type == 'breakout':
            # Use composition root helper for breakout scanner with port injection
            from src.app.startup import get_scanner
            scanner = get_scanner('breakout', db_path=db_path)
        else:
            raise click.BadParameter(f"Unsupported scanner type: {scanner_type}")

        # Convert cutoff_time string to time object
        if isinstance(cutoff_time, str):
            try:
                if not cutoff_time.strip():
                    raise ValueError("Empty time string")

                parts = cutoff_time.split(':')
                if len(parts) != 2:
                    raise ValueError(f"Expected HH:MM format, got {len(parts)} parts")

                hours, minutes = map(int, parts)

                # Validate ranges
                if not (0 <= hours <= 23):
                    raise ValueError(f"Hour must be 0-23, got {hours}")
                if not (0 <= minutes <= 59):
                    raise ValueError(f"Minute must be 0-59, got {minutes}")

                cutoff_time = time(hours, minutes)
                logger.debug(f"Converted time string '{cutoff_time}' to {cutoff_time}")
            except ValueError as e:
                console.print(f"[red]❌ Invalid cutoff time format: {cutoff_time}. Expected HH:MM format. Error: {e}[/red]")
                raise click.Abort()

        # Run scanner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"🔍 Scanning with {scanner_type} scanner...", total=None)

            results_list = scanner.scan(
                scan_date=scan_date.date(),
                cutoff_time=cutoff_time
            )

            progress.update(task, completed=True)

        if not results_list:
            console.print("[yellow]⚠️  No results found from scanner[/yellow]")
            return

        # Convert to DataFrame for easier handling
        import pandas as pd
        results_df = pd.DataFrame(results_list)

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
@click.option('--scanner-type', type=click.Choice(['technical', 'relative_volume', 'crp']), default='technical')
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
@click.option('--scanner-type', type=click.Choice(['technical', 'relative_volume', 'crp']))
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
        },
        {
            'name': 'crp',
            'description': 'CRP (Close, Range, Pattern) scanner for intraday opportunities',
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
                f"{row.get('breakout_price', 0):.2f}",
                f"{row.get('breakout_price', 0):.2f}",
                ".1f",
                str(row.get('bb_position', '')),
                str(row.get('trend_signal', '')),
                str(row.get('technical_score', ''))
            )
    elif scanner_type == 'breakout':
        # Specific display for breakout scanner with new daily performance columns
        table = Table(title=f"📊 Breakout Scanner Results ({len(results_df)} symbols)")
        table.add_column("Symbol", style="cyan")
        table.add_column("Breakout Price", style="green")
        table.add_column("Price@09:50", style="yellow")
        table.add_column("Price@15:15", style="blue")
        table.add_column("Daily Perf %", style="magenta")
        table.add_column("Breakout %", style="red")
        table.add_column("Volume", style="white")

        for _, row in results_df.iterrows():
            # Format daily performance percentage with color
            daily_perf = row.get('daily_performance_pct')
            if daily_perf is not None:
                daily_perf_color = "green" if daily_perf > 0 else "red"
                daily_perf_str = f"{daily_perf:.2f}"
            else:
                daily_perf_color = "white"
                daily_perf_str = "N/A"

            table.add_row(
                str(row.get('symbol', '')),
                f"{row.get('breakout_price', 0):.2f}",
                f"{row.get('price_at_0950', 0):.2f}" if row.get('price_at_0950') else "N/A",
                f"{row.get('price_at_1515', 0):.2f}" if row.get('price_at_1515') else "N/A",
                daily_perf_str,
                f"{row.get('breakout_pct', 0):.2f}",
                f"{row.get('current_volume', 0):,.0f}"
            )
    else:
        # Generic display for other scanners
        table = Table(title=f"📊 Scanner Results ({len(results_df)} symbols)")
        for col in results_df.columns[:8]:  # Show first 8 columns for other scanners
            table.add_column(col.replace('_', ' ').title(), style="cyan")

        for _, row in results_df.head(10).iterrows():
            table.add_row(*[str(row[col]) for col in results_df.columns[:8]])

    console.print(table)
