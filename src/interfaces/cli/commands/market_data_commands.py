"""
Market Data CLI Commands
CLI commands for market data operations
"""

import logging
from typing import List, Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.infrastructure.dependency_container import get_container as get_dependency_container
from src.application.services.market_data_application_service import MarketDataApplicationService

logger = logging.getLogger(__name__)
console = Console()


def register_market_data_commands(cli_app):
    """
    Register market data commands with the CLI app

    Args:
        cli_app: Typer CLI application instance
    """
    market_data_app = typer.Typer(help="Market data operations")
    cli_app.add_typer(market_data_app, name="market-data")

    @market_data_app.command("get")
    def get_market_data(
        symbol: str = typer.Argument(..., help="Trading symbol (e.g., AAPL, RELIANCE)"),
        timeframe: str = typer.Option("1D", help="Data timeframe (1D, 1H, etc.)"),
        days: int = typer.Option(1, help="Number of days of data to retrieve"),
        format: str = typer.Option("table", help="Output format (table, json, csv)")
    ):
        """
        Get market data for a symbol
        """
        async def _get_data():
            try:
                console.print(f"📊 [bold blue]Getting market data for {symbol}[/bold blue]")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # Get current data
                if days == 1:
                    result = await service.get_current_market_data(symbol, timeframe)
                    if result.success and result.data:
                        display_market_data([result.data], format)
                    else:
                        console.print(f"❌ [red]No current data found for {symbol}[/red]")
                else:
                    # Get historical data
                    result = await service.get_market_data_history(symbol, timeframe, days)
                    if result.success and result.data:
                        display_market_data(result.data, format)
                        console.print(f"✅ [green]Retrieved {len(result.data)} records[/green]")
                    else:
                        console.print(f"❌ [red]No historical data found for {symbol}[/red]")

            except Exception as e:
                console.print(f"❌ [red]Error getting market data: {e}[/red]")
                logger.exception(f"CLI market data get error for {symbol}")

        # Run async function
        import asyncio
        asyncio.run(_get_data())

    @market_data_app.command("update")
    def update_market_data(
        symbol: str = typer.Argument(..., help="Trading symbol"),
        open_price: float = typer.Option(..., help="Opening price"),
        high_price: float = typer.Option(..., help="High price"),
        low_price: float = typer.Option(..., help="Low price"),
        close_price: float = typer.Option(..., help="Closing price"),
        volume: int = typer.Option(..., help="Trading volume"),
        timestamp: str = typer.Option(None, help="Data timestamp (ISO format)")
    ):
        """
        Update market data for a symbol
        """
        async def _update_data():
            try:
                console.print(f"📝 [bold blue]Updating market data for {symbol}[/bold blue]")

                # Parse timestamp
                if timestamp:
                    parsed_timestamp = datetime.fromisoformat(timestamp)
                else:
                    parsed_timestamp = datetime.now()

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # Create market data
                market_data = await service.create_market_data_from_raw(
                    symbol=symbol,
                    timestamp=parsed_timestamp,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume
                )

                # Update market data
                result = await service.update_market_data(symbol, market_data)

                if result.success:
                    console.print(f"✅ [green]Successfully updated market data for {symbol}[/green]")
                else:
                    console.print(f"❌ [red]Failed to update market data: {result.error_message}[/red]")

            except Exception as e:
                console.print(f"❌ [red]Error updating market data: {e}[/red]")
                logger.exception(f"CLI market data update error for {symbol}")

        # Run async function
        import asyncio
        asyncio.run(_update_data())

    @market_data_app.command("import")
    def import_market_data(
        file_path: str = typer.Argument(..., help="Path to data file (CSV, JSON)"),
        symbol: Optional[str] = typer.Option(None, help="Symbol to import (if not in file)"),
        format: str = typer.Option("csv", help="File format (csv, json)"),
        batch_size: int = typer.Option(1000, help="Batch size for processing")
    ):
        """
        Import market data from file
        """
        async def _import_data():
            try:
                console.print(f"📥 [bold blue]Importing market data from {file_path}[/bold blue]")

                # TODO: Implement file import logic
                # This would read the file and use the application service
                # to process batches of market data

                console.print("⚠️  [yellow]Import functionality not yet implemented[/yellow]")
                console.print("📝 This will import market data from CSV/JSON files")

            except Exception as e:
                console.print(f"❌ [red]Error importing market data: {e}[/red]")
                logger.exception(f"CLI market data import error for {file_path}")

        # Run async function
        import asyncio
        asyncio.run(_import_data())

    @market_data_app.command("validate")
    def validate_market_data(
        symbol: str = typer.Argument(..., help="Trading symbol to validate"),
        days: int = typer.Option(30, help="Number of days to validate")
    ):
        """
        Validate market data quality
        """
        async def _validate_data():
            try:
                console.print(f"🔍 [bold blue]Validating market data for {symbol}[/bold blue]")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # Validate data quality
                start_date = datetime.now().replace(day=1)  # Start of month
                end_date = datetime.now()

                quality_report = await service.validate_market_data_quality(
                    symbol, start_date, end_date
                )

                # Display validation results
                console.print("\n📊 [bold blue]Data Quality Report[/bold blue]")
                console.print(f"Symbol: {quality_report['symbol']}")
                console.print(f"Quality Score: {quality_report['quality_score']:.2f}")
                console.print(f"Total Records: {quality_report['total_records']}")

                if quality_report['issues']:
                    console.print("\n⚠️  [yellow]Issues Found:[/yellow]")
                    for issue in quality_report['issues']:
                        console.print(f"  • {issue}")
                else:
                    console.print("✅ [green]No issues found[/green]")

            except Exception as e:
                console.print(f"❌ [red]Error validating market data: {e}[/red]")
                logger.exception(f"CLI market data validation error for {symbol}")

        # Run async function
        import asyncio
        asyncio.run(_validate_data())

    @market_data_app.command("summary")
    def get_market_summary(
        symbol: str = typer.Argument(..., help="Trading symbol"),
        days: int = typer.Option(30, help="Analysis period in days")
    ):
        """
        Get market data summary and analytics
        """
        async def _get_summary():
            try:
                console.print(f"📈 [bold blue]Getting market summary for {symbol}[/bold blue]")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # Get market summary
                result = await service.get_market_data_summary(symbol, days)

                if result.success:
                    # Display summary in a nice format
                    console.print("\n📊 [bold blue]Market Summary[/bold blue]")
                    console.print(f"Symbol: {symbol}")
                    console.print(f"Analysis Period: {days} days")

                    # This would display actual summary data when implemented
                    console.print("📝 Summary data would be displayed here")

                else:
                    console.print(f"❌ [red]Failed to get summary: {result.error_message}[/red]")

            except Exception as e:
                console.print(f"❌ [red]Error getting market summary: {e}[/red]")
                logger.exception(f"CLI market summary error for {symbol}")

        # Run async function
        import asyncio
        asyncio.run(_get_summary())


def display_market_data(data, format_type: str = "table"):
    """
    Display market data in the specified format

    Args:
        data: List of market data records
        format_type: Output format (table, json, csv)
    """
    if format_type == "table":
        table = Table(title="Market Data")
        table.add_column("Symbol", style="cyan")
        table.add_column("Date", style="white")
        table.add_column("Open", style="green")
        table.add_column("High", style="green")
        table.add_column("Low", style="red")
        table.add_column("Close", style="green")
        table.add_column("Volume", style="yellow")

        for record in data:
            table.add_row(
                record.symbol,
                record.parsed_timestamp.strftime("%Y-%m-%d"),
                f"{record.ohlcv.open:.2f}",
                f"{record.ohlcv.high:.2f}",
                f"{record.ohlcv.low:.2f}",
                f"{record.ohlcv.close:.2f}",
                f"{record.ohlcv.volume:,}"
            )

        console.print(table)

    elif format_type == "json":
        import json
        # Convert data to JSON-serializable format
        json_data = []
        for record in data:
            json_data.append({
                "symbol": record.symbol,
                "timestamp": record.parsed_timestamp.isoformat(),
                "open": record.ohlcv.open,
                "high": record.ohlcv.high,
                "low": record.ohlcv.low,
                "close": record.ohlcv.close,
                "volume": record.ohlcv.volume
            })

        console.print(json.dumps(json_data, indent=2))

    elif format_type == "csv":
        # Output CSV format
        console.print("symbol,timestamp,open,high,low,close,volume")
        for record in data:
            console.print(
                f"{record.symbol},"
                f"{record.parsed_timestamp.strftime('%Y-%m-%d %H:%M:%S')},"
                f"{record.ohlcv.open:.2f},"
                f"{record.ohlcv.high:.2f},"
                f"{record.ohlcv.low:.2f},"
                f"{record.ohlcv.close:.2f},"
                f"{record.ohlcv.volume}"
            )
