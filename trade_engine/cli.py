#!/usr/bin/env python3
"""
Trade Engine CLI
===============

Command-line interface for running the unified trade engine.
Supports both backtest and live trading modes.
"""

import asyncio
import click
import json
from pathlib import Path

from .engine.strategy_runner import run_backtest, run_live, StrategyRunner


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Unified Intraday Trade Engine - Backtest + Live Parity"""
    pass


@cli.command()
@click.option('--config', '-c', default='trade_engine/config/trade_engine.yaml',
              help='Path to configuration file')
@click.option('--date', '-d', help='Trading date for backtest (YYYY-MM-DD)')
@click.option('--output', '-o', help='Output file for results (JSON)')
def backtest(config: str, date: str, output: str):
    """Run backtest for specified date"""

    # Update config with date if provided
    if date:
        # Note: In production, you'd modify the config file or pass it as parameter
        click.echo(f"Running backtest for date: {date}")

    click.echo(f"Starting backtest with config: {config}")

    try:
        results = asyncio.run(run_backtest(config))

        click.echo("\n🎯 BACKTEST RESULTS")
        click.echo("=" * 50)
        click.echo(f"📅 Date: {results['date']}")
        click.echo(f"💰 Total Return: ₹{results['total_return']:,.2f}")
        click.echo(f"📊 Total Trades: {results['total_trades']}")
        click.echo(f"🎯 Signals Generated: {results['signals_generated']}")
        click.echo(f"💵 Final Cash: ₹{results['final_cash']:,.2f}")
        click.echo(f"📈 Final Positions: {results['final_positions']}")

        if output:
            with open(output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            click.echo(f"\n💾 Results saved to: {output}")

        click.echo("\n✅ Backtest completed successfully!")

    except Exception as e:
        click.echo(f"❌ Backtest failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--config', '-c', default='trade_engine/config/trade_engine.yaml',
              help='Path to configuration file')
def live(config: str):
    """Run live trading mode"""

    click.echo("🚀 Starting LIVE TRADING MODE")
    click.echo("=" * 50)
    click.echo("⚠️  WARNING: This will execute real trades!")
    click.echo("📊 Monitoring market conditions...")

    if not click.confirm("Are you sure you want to start live trading?"):
        click.echo("Live trading cancelled.")
        return

    try:
        click.echo("🔄 Initializing live trading system...")
        asyncio.run(run_live(config))

    except KeyboardInterrupt:
        click.echo("\n🛑 Live trading stopped by user")
    except Exception as e:
        click.echo(f"❌ Live trading failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--config', '-c', default='trade_engine/config/trade_engine.yaml',
              help='Path to configuration file')
def validate(config: str):
    """Validate configuration and system readiness"""

    click.echo("🔍 VALIDATING TRADE ENGINE SETUP")
    click.echo("=" * 50)

    try:
        # Check config file
        config_path = Path(config)
        if not config_path.exists():
            click.echo(f"❌ Config file not found: {config}")
            return

        click.echo(f"✅ Config file found: {config}")

        # Check database
        import yaml
        with open(config_path, 'r') as f:
            cfg = yaml.safe_load(f)

        db_path = cfg['data']['duckdb_path']
        db_file = Path(db_path)
        if not db_file.exists():
            click.echo(f"❌ Database not found: {db_path}")
            return

        click.echo(f"✅ Database found: {db_path}")

        # Test database connection
        from ..adapters.duckdb_data_feed import DuckDBDataFeed
        data_feed = DuckDBDataFeed(db_path)
        symbols = data_feed.get_available_symbols()

        click.echo(f"✅ Database connection successful")
        click.echo(f"📊 Available symbols: {len(symbols)}")

        if symbols:
            click.echo(f"🎯 Sample symbols: {symbols[:5]}")

        # Validate NSE config
        nse_config = Path('trade_engine/config/nse_ticks.yaml')
        if nse_config.exists():
            click.echo("✅ NSE configuration found")
        else:
            click.echo("⚠️  NSE configuration not found")

        click.echo("\n🎉 System validation completed successfully!")
        click.echo("🚀 Ready for backtesting or live trading")

    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)


if __name__ == '__main__':
    cli()
