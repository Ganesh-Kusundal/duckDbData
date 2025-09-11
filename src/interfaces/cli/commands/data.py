"""
Data management CLI commands.
"""

import click
from pathlib import Path
from datetime import date
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Import with proper path handling
import sys
from pathlib import Path

# Ensure the src directory is in the path
src_path = Path(__file__).parent.parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from src.infrastructure.logging import get_logger
    from src.infrastructure.external.data_ingestion_pipeline import DataIngestionPipeline
    from src.infrastructure.core.singleton_database import DuckDBConnectionManager, create_db_manager
except ImportError:
    # Fallback for when running as installed package
    try:
        from duckdb_financial_infra.infrastructure.logging import get_logger
        from duckdb_financial_infra.infrastructure.external.data_ingestion_pipeline import DataIngestionPipeline
        from duckdb_financial_infra.infrastructure.core.singleton_database import DuckDBConnectionManager, create_db_manager
    except ImportError:
        import logging
        get_logger = lambda name: logging.getLogger(name)
        DataIngestionPipeline = None
        DuckDBConnectionManager = None
        create_db_manager = None

logger = get_logger(__name__)
console = Console()


@click.group()
@click.pass_context
def data(ctx):
    """Data ingestion and management commands."""
    pass


@data.command()
@click.option('--limit', default=15, help='Number of top symbols to show')
@click.pass_context
def latest(ctx, limit):
    """Show latest available date and top symbols from market_data_unified."""
    try:
        db_manager = create_db_manager()
        with db_manager.get_connection() as conn:
            latest_df = conn.execute("SELECT MAX(date_partition) AS max_date FROM market_data_unified").fetchdf()
            if latest_df.empty or latest_df.iloc[0]['max_date'] is None:
                console.print("[yellow]⚠️  No data found in market_data_unified[/yellow]")
                return
            max_date = latest_df.iloc[0]['max_date']

            top_sql = f"""
            SELECT symbol, COUNT(*) AS rows
            FROM market_data_unified
            WHERE date_partition = ?
            GROUP BY 1
            ORDER BY rows DESC
            LIMIT {int(limit)}
            """
            top_df = conn.execute(top_sql, [max_date]).fetchdf()

            console.print(f"[green]✅ Latest date: {max_date}[/green]")

            if top_df.empty:
                console.print("[yellow]⚠️  No rows found for latest date[/yellow]")
                return

            table = Table(title=f"🏆 Top {limit} symbols on {max_date}")
            table.add_column("Symbol", style="cyan")
            table.add_column("Rows", style="magenta")
            for _, row in top_df.iterrows():
                table.add_row(str(row['symbol']), str(int(row['rows'])))
            console.print(table)
    except Exception as e:
        logger.error(f"Failed to get latest data: {e}")
        console.print(f"[red]❌ Failed to get latest data: {e}[/red]")
        raise click.Abort()

@data.command()
@click.argument('data_directory', type=click.Path(exists=True))
@click.option('--symbol-pattern', default='*.parquet', help='File pattern for symbols')
@click.option('--batch-size', default=1000, help='Batch size for processing')
@click.option('--dry-run', is_flag=True, help='Show what would be processed without executing')
@click.pass_context
def ingest(ctx, data_directory, symbol_pattern, batch_size, dry_run):
    """Ingest market data from Parquet files."""
    verbose = ctx.obj.get('verbose', False)

    if verbose:
        console.print(f"[bold blue]📊 Starting data ingestion from: {data_directory}[/bold blue]")

    try:
        # Initialize components
        db_manager = create_db_manager()
        pipeline = DataIngestionPipeline()

        if dry_run:
            console.print("[yellow]🔍 DRY RUN MODE - No data will be ingested[/yellow]")

            # Count files that would be processed
            data_path = Path(data_directory)
            parquet_files = list(data_path.rglob(symbol_pattern))
            total_files = len(parquet_files)

            table = Table(title="📋 Files to be processed")
            table.add_column("Directory", style="cyan")
            table.add_column("File Count", style="magenta")

            # Group by directory
            dir_counts = {}
            for file_path in parquet_files:
                dir_name = str(file_path.parent.relative_to(data_path))
                dir_counts[dir_name] = dir_counts.get(dir_name, 0) + 1

            for directory, count in sorted(dir_counts.items()):
                table.add_row(directory, str(count))

            console.print(table)
            console.print(f"[green]✅ Total files to process: {total_files}[/green]")
            return

        # Execute ingestion
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("📥 Ingesting market data...", total=None)

            result = pipeline.ingest_from_parquet_files(
                data_directory=str(data_directory),
                symbol_pattern=symbol_pattern,
                batch_size=batch_size
            )

            progress.update(task, completed=True)

        # Display results
        table = Table(title="📊 Ingestion Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Files Processed", str(result.get('files_processed', 0)))
        table.add_row("Records Ingested", str(result.get('records_ingested', 0)))
        table.add_row("Symbols Processed", str(result.get('symbols_processed', 0)))
        table.add_row("Duration", ".2f")

        console.print(table)
        console.print("[green]✅ Data ingestion completed successfully![/green]")

    except Exception as e:
        logger.error(f"Data ingestion failed: {e}")
        console.print(f"[red]❌ Data ingestion failed: {e}[/red]")
        raise click.Abort()


@data.command()
@click.option('--symbol', help='Filter by symbol')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), help='End date (YYYY-MM-DD)')
@click.option('--limit', default=100, help='Maximum records to display')
@click.pass_context
def list(ctx, symbol, start_date, end_date, limit):
    """List market data records."""
    verbose = ctx.obj.get('verbose', False)

    try:
        db_manager = create_db_manager()

        # Build query
        query = """
        SELECT
            symbol,
            timestamp,
            open,
            high,
            low,
            close,
            volume,
            date_partition
        FROM market_data_unified
        WHERE 1=1
        """

        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if start_date:
            query += " AND date_partition >= ?"
            params.append(start_date.date())

        if end_date:
            query += " AND date_partition <= ?"
            params.append(end_date.date())

        query += f" ORDER BY timestamp DESC LIMIT {limit}"

        # Execute query
        with db_manager.get_connection() as conn:
            df = conn.execute(query, params).fetchdf()

        # Display results
        if df.empty:
            console.print("[yellow]⚠️  No data found matching criteria[/yellow]")
            return

        table = Table(title=f"📊 Market Data ({len(df)} records)")
        table.add_column("Symbol", style="cyan")
        table.add_column("Timestamp", style="white")
        table.add_column("Open", style="green")
        table.add_column("High", style="green")
        table.add_column("Low", style="red")
        table.add_column("Close", style="green")
        table.add_column("Volume", style="magenta")

        for _, row in df.iterrows():
            table.add_row(
                str(row['symbol']),
                str(row['timestamp']),
                ".2f",
                ".2f",
                ".2f",
                ".2f",
                str(int(row['volume']))
            )

        console.print(table)

        if len(df) == limit:
            console.print(f"[yellow]⚠️  Showing first {limit} records. Use --limit to see more.[/yellow]")

    except Exception as e:
        logger.error(f"Failed to list data: {e}")
        console.print(f"[red]❌ Failed to list data: {e}[/red]")
        raise click.Abort()


@data.command()
@click.pass_context
def stats(ctx):
    """Show data statistics."""
    verbose = ctx.obj.get('verbose', False)

    try:
        db_manager = create_db_manager()

        # Get comprehensive statistics
        query = """
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            COUNT(DISTINCT date_partition) as total_days,
            MIN(date_partition) as earliest_date,
            MAX(date_partition) as latest_date,
            AVG(volume) as avg_volume,
            SUM(volume) as total_volume
        FROM market_data_unified
        """

        with db_manager.get_connection() as conn:
            stats_df = conn.execute(query).fetchdf()

            if stats_df.empty:
                console.print("[yellow]⚠️  No data found in database[/yellow]")
                return

            stats_row = stats_df.iloc[0]

            table = Table(title="📈 Data Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Records", f"{int(stats_row['total_records']):,}")
            table.add_row("Unique Symbols", f"{int(stats_row['unique_symbols']):,}")
            table.add_row("Total Trading Days", f"{int(stats_row['total_days']):,}")
            table.add_row("Date Range", f"{stats_row['earliest_date']} to {stats_row['latest_date']}")
            table.add_row("Average Volume", f"{int(stats_row['avg_volume']):,}")
            table.add_row("Total Volume", f"{int(stats_row['total_volume']):,}")

            console.print(table)

            # Symbol breakdown
            symbol_query = """
            SELECT
                symbol,
                COUNT(*) as record_count,
                MIN(date_partition) as first_date,
                MAX(date_partition) as last_date
            FROM market_data_unified
            GROUP BY symbol
            ORDER BY record_count DESC
            LIMIT 10
            """

            symbol_df = conn.execute(symbol_query).fetchdf()

        if not symbol_df.empty:
            symbol_table = Table(title="🏆 Top 10 Symbols by Record Count")
            symbol_table.add_column("Symbol", style="cyan")
            symbol_table.add_column("Records", style="magenta")
            symbol_table.add_column("Date Range", style="white")

            for _, row in symbol_df.iterrows():
                symbol_table.add_row(
                    str(row['symbol']),
                    f"{int(row['record_count']):,}",
                    f"{row['first_date']} to {row['last_date']}"
                )

            console.print()
            console.print(symbol_table)

    except Exception as e:
        logger.error(f"Failed to get data stats: {e}")
        console.print(f"[red]❌ Failed to get data stats: {e}[/red]")
        raise click.Abort()


@data.command()
@click.option('--source', type=click.Choice(['table', 'parquet']), default='table',
              help='Read from DuckDB table or directly from Parquet files')
@click.option('--parquet-glob', default='data/*/*/*/*_minute_*.parquet',
              help='Glob pattern for Parquet files when using source=parquet')
@click.pass_context
def coverage(ctx, source, parquet_glob):
    """Show latest date coverage and day counts per symbol."""
    try:
        db_manager = create_db_manager()

        # Build source relation
        if source == 'table':
            src_rel = 'market_data'
        else:
            # Directly read Parquet files
            # Note: DuckDB evaluates the glob at query time
            src_rel = f"read_parquet('{parquet_glob}')"

        # Summary metrics
        summary_sql = f"""
        WITH per_symbol AS (
          SELECT symbol,
                 MAX(COALESCE(date_partition, CAST(timestamp AS DATE))) AS latest_date,
                 COUNT(DISTINCT COALESCE(date_partition, CAST(timestamp AS DATE))) AS days
          FROM {src_rel}
          GROUP BY symbol
        ), mm AS (
          SELECT MIN(latest_date) AS common_latest,
                 MAX(latest_date) AS max_latest
          FROM per_symbol
        )
        SELECT
          (SELECT COUNT(*) FROM per_symbol)             AS total_symbols,
          (SELECT common_latest FROM mm)                AS common_latest,
          (SELECT max_latest FROM mm)                   AS max_latest,
          (SELECT COUNT(*) FROM per_symbol
             WHERE latest_date = (SELECT common_latest FROM mm)) AS symbols_at_common,
          (SELECT MIN(days) FROM per_symbol)            AS min_days,
          (SELECT MAX(days) FROM per_symbol)            AS max_days,
          (SELECT AVG(days) FROM per_symbol)            AS avg_days,
          (SELECT MEDIAN(days) FROM per_symbol)         AS median_days
        ;
        """

        laggards_sql = f"""
        SELECT symbol,
               MAX(COALESCE(date_partition, CAST(timestamp AS DATE))) AS latest_date
        FROM {src_rel}
        GROUP BY symbol
        ORDER BY latest_date ASC, symbol ASC
        LIMIT 10;
        """

        toppers_sql = f"""
        SELECT symbol,
               COUNT(DISTINCT COALESCE(date_partition, CAST(timestamp AS DATE))) AS days
        FROM {src_rel}
        GROUP BY symbol
        ORDER BY days DESC, symbol ASC
        LIMIT 10;
        """

        with db_manager.get_connection() as conn:
            summary = conn.execute(summary_sql).fetchdf()
            lag = conn.execute(laggards_sql).fetchdf()
            top = conn.execute(toppers_sql).fetchdf()

        if summary.empty:
            console.print("[yellow]⚠️  No data found for coverage computation[/yellow]")
            return

        row = summary.iloc[0]
        console.print(Panel.fit(
            f"Source: {source}\n"
            f"Total symbols: {int(row['total_symbols'])}\n"
            f"Common latest date: {row['common_latest']}\n"
            f"Most advanced latest date: {row['max_latest']}\n"
            f"Symbols at common latest date: {int(row['symbols_at_common'])}\n"
            f"Days per symbol — min: {int(row['min_days'])}, max: {int(row['max_days'])}, "
            f"avg: {float(row['avg_days']):.2f}, median: {float(row['median_days'])}",
            title="📅 Coverage Summary",
        ))

        # Print laggards
        if not lag.empty:
            lag_table = Table(title="🐢 Top 10 laggards (earliest latest_date)")
            lag_table.add_column("Symbol", style="cyan")
            lag_table.add_column("Latest Date", style="magenta")
            for _, r in lag.iterrows():
                lag_table.add_row(str(r['symbol']), str(r['latest_date']))
            console.print(lag_table)

        # Print top by days
        if not top.empty:
            top_table = Table(title="🏆 Top 10 by days of data")
            top_table.add_column("Symbol", style="cyan")
            top_table.add_column("Days", style="green")
            for _, r in top.iterrows():
                top_table.add_row(str(r['symbol']), str(int(r['days'])))
            console.print(top_table)

    except Exception as e:
        logger.error(f"Failed to compute coverage: {e}")
        console.print(f"[red]❌ Failed to compute coverage: {e}[/red]")
        raise click.Abort()


@data.command("create-parquet-view")
@click.option('--view-name', default='market_data_parquet', help='Name of the DuckDB view to create')
@click.option('--parquet-glob', default='data/*/*/*/*_minute_*.parquet',
              help='Glob pattern for Parquet files')
@click.pass_context
def create_parquet_view(ctx, view_name, parquet_glob):
    """Create or replace a DuckDB view over Parquet files.

    This lets the app query Parquet via DuckDB as a logical table/view.
    """
    try:
        db_manager = create_db_manager()
        sql = f"""
        CREATE OR REPLACE VIEW {view_name} AS
        SELECT
          symbol,
          timestamp,
          open,
          high,
          low,
          close,
          volume,
          CAST(timestamp AS DATE) AS date_partition
        FROM read_parquet('{parquet_glob}');
        """

        with db_manager.get_connection() as conn:
            conn.execute(sql)

        console.print(f"[green]✅ Created view '{view_name}' over Parquet: {parquet_glob}[/green]")
        console.print("You can now run: data coverage --source=parquet or query the view directly.")

    except Exception as e:
        logger.error(f"Failed to create parquet view: {e}")
        console.print(f"[red]❌ Failed to create parquet view: {e}[/red]")
        raise click.Abort()
