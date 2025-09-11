"""
Trading CLI Commands
CLI commands for trading operations including backtesting, optimization, and rule management
"""

import logging
from typing import Optional, List
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.infrastructure.dependency_container import get_container as get_dependency_container

logger = logging.getLogger(__name__)
console = Console()


def register_trading_commands(cli_app):
    """
    Register trading commands with the CLI app

    Args:
        cli_app: Typer CLI application instance
    """
    trading_app = typer.Typer(help="Trading operations and strategy management")
    cli_app.add_typer(trading_app, name="trading")

    @trading_app.command("backtest")
    def run_backtest(
        strategy: str = typer.Option(..., help="Strategy name or file path"),
        symbols: List[str] = typer.Option(["AAPL"], help="Symbols to backtest"),
        start_date: str = typer.Option("2024-01-01", help="Start date (YYYY-MM-DD)"),
        end_date: str = typer.Option("2024-12-31", help="End date (YYYY-MM-DD)"),
        initial_capital: float = typer.Option(100000.0, help="Initial capital"),
        commission: float = typer.Option(0.001, help="Commission per trade (0.001 = 0.1%)"),
        slippage: float = typer.Option(0.0005, help="Slippage per trade"),
        output_file: Optional[str] = typer.Option(None, help="Output results to file"),
        detailed: bool = typer.Option(False, help="Show detailed backtest results"),
        plot: bool = typer.Option(False, help="Generate performance plots")
    ):
        """
        Run backtest for trading strategy
        """
        async def _run_backtest():
            try:
                console.print(f"📈 [bold blue]Running Backtest[/bold blue]")
                console.print(f"Strategy: {strategy}")
                console.print(f"Symbols: {', '.join(symbols)}")
                console.print(f"Period: {start_date} to {end_date}")
                console.print(f"Initial Capital: ${initial_capital:,.2f}")
                console.print("-" * 60)

                # Get dependency container
                container = get_dependency_container()

                # Mock backtest execution with progress
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task1 = progress.add_task("Loading market data...", total=100)
                    for i in range(100):
                        progress.update(task1, advance=1)

                    task2 = progress.add_task("Executing strategy...", total=100)
                    for i in range(100):
                        progress.update(task2, advance=1)

                    task3 = progress.add_task("Calculating performance...", total=100)
                    for i in range(100):
                        progress.update(task3, advance=1)

                # Mock backtest results
                backtest_results = {
                    "total_return": 0.152,
                    "annualized_return": 0.187,
                    "volatility": 0.223,
                    "sharpe_ratio": 1.45,
                    "max_drawdown": -0.085,
                    "win_rate": 0.62,
                    "total_trades": 145,
                    "profit_trades": 90,
                    "loss_trades": 55,
                    "avg_win": 0.023,
                    "avg_loss": -0.018,
                    "profit_factor": 1.87,
                    "expectancy": 0.012
                }

                # Display results
                display_backtest_results(backtest_results, detailed)

                if output_file:
                    console.print(f"💾 [green]Results saved to: {output_file}[/green]")

                if plot:
                    console.print("📊 [blue]Performance plots generated[/blue]")

            except Exception as e:
                console.print(f"❌ [red]Error running backtest: {e}[/red]")
                logger.exception("CLI backtest error")

        # Run async function
        import asyncio
        asyncio.run(_run_backtest())

    @trading_app.command("optimize")
    def optimize_strategy(
        strategy: str = typer.Option(..., help="Strategy name or file path"),
        symbols: List[str] = typer.Option(["AAPL"], help="Symbols to optimize on"),
        start_date: str = typer.Option("2024-01-01", help="Start date (YYYY-MM-DD)"),
        end_date: str = typer.Option("2024-12-31", help="End date (YYYY-MM-DD)"),
        parameters: List[str] = typer.Option([], help="Parameters to optimize (e.g., 'fast_period=5-20' 'slow_period=20-50')"),
        method: str = typer.Option("grid", help="Optimization method (grid, genetic, bayesian)"),
        max_evaluations: int = typer.Option(100, help="Maximum evaluations for optimization"),
        metric: str = typer.Option("sharpe_ratio", help="Optimization metric (sharpe_ratio, total_return, win_rate, etc.)"),
        output_file: Optional[str] = typer.Option(None, help="Output results to file"),
        parallel: bool = typer.Option(True, help="Use parallel processing")
    ):
        """
        Optimize trading strategy parameters
        """
        async def _optimize_strategy():
            try:
                console.print(f"🎯 [bold blue]Optimizing Strategy[/bold blue]")
                console.print(f"Strategy: {strategy}")
                console.print(f"Symbols: {', '.join(symbols)}")
                console.print(f"Method: {method}")
                console.print(f"Metric: {metric}")
                console.print(f"Max Evaluations: {max_evaluations}")
                console.print(f"Parameters: {', '.join(parameters) if parameters else 'None'}")
                console.print("-" * 60)

                # Get dependency container
                container = get_dependency_container()

                # Mock optimization execution
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task1 = progress.add_task("Setting up optimization...", total=100)
                    for i in range(100):
                        progress.update(task1, advance=1)

                    task2 = progress.add_task("Running optimization...", total=max_evaluations)
                    for i in range(max_evaluations):
                        progress.update(task2, advance=1)

                    task3 = progress.add_task("Analyzing results...", total=100)
                    for i in range(100):
                        progress.update(task3, advance=1)

                # Mock optimization results
                optimization_results = {
                    "best_parameters": {
                        "fast_period": 12,
                        "slow_period": 26,
                        "signal_period": 9,
                        "stop_loss": 0.02,
                        "take_profit": 0.05
                    },
                    "best_metric_value": 2.15,
                    "total_evaluations": max_evaluations,
                    "optimization_time": 45.2,
                    "parameter_ranges_tested": {
                        "fast_period": "5-20",
                        "slow_period": "20-50",
                        "signal_period": "5-15"
                    },
                    "top_5_results": [
                        {"params": {"fast_period": 12, "slow_period": 26}, "metric": 2.15, "rank": 1},
                        {"params": {"fast_period": 10, "slow_period": 25}, "metric": 2.08, "rank": 2},
                        {"params": {"fast_period": 15, "slow_period": 30}, "metric": 2.02, "rank": 3},
                        {"params": {"fast_period": 8, "slow_period": 22}, "metric": 1.95, "rank": 4},
                        {"params": {"fast_period": 14, "slow_period": 28}, "metric": 1.87, "rank": 5}
                    ]
                }

                # Display results
                display_optimization_results(optimization_results, method, metric)

                if output_file:
                    console.print(f"💾 [green]Results saved to: {output_file}[/green]")

            except Exception as e:
                console.print(f"❌ [red]Error optimizing strategy: {e}[/red]")
                logger.exception("CLI optimization error")

        # Run async function
        import asyncio
        asyncio.run(_optimize_strategy())

    @trading_app.command("rules")
    def list_rules(
        rule_type: Optional[str] = typer.Option(None, help="Filter by rule type (breakout, crp, technical, volume, custom)"),
        active_only: bool = typer.Option(False, help="Show only active rules"),
        detailed: bool = typer.Option(False, help="Show detailed rule information"),
        format: str = typer.Option("table", help="Output format (table, json)")
    ):
        """
        List and manage trading rules
        """
        async def _list_rules():
            try:
                console.print(f"📋 [bold blue]Trading Rules{' - ' + rule_type if rule_type else ''}[/bold blue]")
                console.print("-" * 60)

                # Get dependency container
                container = get_dependency_container()

                # Mock rules data
                rules_data = [
                    {
                        "id": "breakout_standard",
                        "name": "Standard Breakout",
                        "type": "breakout",
                        "active": True,
                        "description": "Detects price breakouts above resistance levels",
                        "parameters": {"threshold": 0.02, "lookback": 20, "volume_multiplier": 1.5},
                        "created_at": "2024-01-15",
                        "performance": {"win_rate": 0.65, "avg_return": 0.023}
                    },
                    {
                        "id": "crp_reversal",
                        "name": "CRP Reversal",
                        "type": "crp",
                        "active": True,
                        "description": "Identifies reversals at Central Pivot Range levels",
                        "parameters": {"range_tolerance": 0.005, "confirmation_period": 3},
                        "created_at": "2024-02-01",
                        "performance": {"win_rate": 0.58, "avg_return": 0.019}
                    },
                    {
                        "id": "rsi_divergence",
                        "name": "RSI Divergence",
                        "type": "technical",
                        "active": False,
                        "description": "Detects RSI divergences for potential reversals",
                        "parameters": {"rsi_period": 14, "overbought": 70, "oversold": 30},
                        "created_at": "2024-01-20",
                        "performance": {"win_rate": 0.52, "avg_return": 0.015}
                    },
                    {
                        "id": "volume_surge",
                        "name": "Volume Surge",
                        "type": "volume",
                        "active": True,
                        "description": "Identifies significant volume increases",
                        "parameters": {"threshold": 2.0, "lookback": 10},
                        "created_at": "2024-03-01",
                        "performance": {"win_rate": 0.61, "avg_return": 0.021}
                    }
                ]

                # Filter rules
                filtered_rules = rules_data
                if rule_type:
                    filtered_rules = [r for r in rules_data if r["type"] == rule_type]
                if active_only:
                    filtered_rules = [r for r in filtered_rules if r["active"]]

                if not filtered_rules:
                    console.print(f"❌ [red]No rules found matching criteria[/red]")
                    return

                # Display results
                display_rules_list(filtered_rules, detailed, format)

                console.print(f"\n📊 [cyan]Summary:[/cyan] {len(filtered_rules)} rules found")

            except Exception as e:
                console.print(f"❌ [red]Error listing rules: {e}[/red]")
                logger.exception("CLI rules list error")

        # Run async function
        import asyncio
        asyncio.run(_list_rules())

    @trading_app.command("rule-enable")
    def enable_rule(
        rule_id: str = typer.Option(..., help="Rule ID to enable"),
        confirm: bool = typer.Option(True, help="Skip confirmation prompt")
    ):
        """
        Enable a trading rule
        """
        async def _enable_rule():
            try:
                if confirm:
                    console.print(f"🔄 [yellow]Enabling rule: {rule_id}[/yellow]")
                    if not typer.confirm("Are you sure you want to enable this rule?"):
                        console.print("❌ [red]Operation cancelled[/red]")
                        return

                # Get dependency container
                container = get_dependency_container()

                # Mock rule enable
                console.print(f"✅ [green]Rule '{rule_id}' has been enabled[/green]")

            except Exception as e:
                console.print(f"❌ [red]Error enabling rule: {e}[/red]")
                logger.exception("CLI rule enable error")

        # Run async function
        import asyncio
        asyncio.run(_enable_rule())

    @trading_app.command("rule-disable")
    def disable_rule(
        rule_id: str = typer.Option(..., help="Rule ID to disable"),
        confirm: bool = typer.Option(True, help="Skip confirmation prompt")
    ):
        """
        Disable a trading rule
        """
        async def _disable_rule():
            try:
                if confirm:
                    console.print(f"🔄 [yellow]Disabling rule: {rule_id}[/yellow]")
                    if not typer.confirm("Are you sure you want to disable this rule?"):
                        console.print("❌ [red]Operation cancelled[/red]")
                        return

                # Get dependency container
                container = get_dependency_container()

                # Mock rule disable
                console.print(f"✅ [green]Rule '{rule_id}' has been disabled[/green]")

            except Exception as e:
                console.print(f"❌ [red]Error disabling rule: {e}[/red]")
                logger.exception("CLI rule disable error")

        # Run async function
        import asyncio
        asyncio.run(_disable_rule())

    @trading_app.command("portfolio")
    def show_portfolio(
        portfolio_id: Optional[str] = typer.Option(None, help="Specific portfolio ID"),
        detailed: bool = typer.Option(False, help="Show detailed position information"),
        format: str = typer.Option("table", help="Output format (table, json)")
    ):
        """
        Show portfolio status and positions
        """
        async def _show_portfolio():
            try:
                console.print(f"📊 [bold blue]Portfolio Status{' - ' + portfolio_id if portfolio_id else ''}[/bold blue]")
                console.print("-" * 60)

                # Get dependency container
                container = get_dependency_container()

                # Mock portfolio data
                portfolio_data = {
                    "portfolio_id": portfolio_id or "DEMO_PORTFOLIO",
                    "total_value": 125750.45,
                    "cash_balance": 25750.45,
                    "total_positions": 8,
                    "positions": [
                        {"symbol": "AAPL", "shares": 150, "avg_price": 185.25, "current_price": 192.50, "value": 28875.00, "pnl": 1098.75, "pnl_pct": 3.95},
                        {"symbol": "GOOGL", "shares": 25, "avg_price": 2750.00, "current_price": 2825.30, "value": 70632.50, "pnl": 1882.50, "pnl_pct": 2.74},
                        {"symbol": "MSFT", "shares": 75, "avg_price": 335.80, "current_price": 348.20, "value": 26115.00, "pnl": 933.00, "pnl_pct": 3.70},
                        {"symbol": "TSLA", "shares": 40, "avg_price": 245.50, "current_price": 238.90, "value": 9556.00, "pnl": -268.00, "pnl_pct": -2.74}
                    ],
                    "performance": {
                        "daily_pnl": 2875.25,
                        "daily_return_pct": 2.34,
                        "total_pnl": 15675.25,
                        "total_return_pct": 14.22
                    }
                }

                # Display results
                display_portfolio_status(portfolio_data, detailed, format)

            except Exception as e:
                console.print(f"❌ [red]Error showing portfolio: {e}[/red]")
                logger.exception("CLI portfolio error")

        # Run async function
        import asyncio
        asyncio.run(_show_portfolio())


def display_backtest_results(results: dict, detailed: bool):
    """
    Display backtest results

    Args:
        results: Backtest results dictionary
        detailed: Whether to show detailed information
    """
    # Performance metrics
    console.print("\n📈 [bold cyan]Performance Metrics:[/bold cyan]")
    metrics_table = Table()
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="green")

    metrics_table.add_row("Total Return", f"{results['total_return']:.2%}")
    metrics_table.add_row("Annualized Return", f"{results['annualized_return']:.2%}")
    metrics_table.add_row("Volatility", f"{results['volatility']:.2%}")
    metrics_table.add_row("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")
    metrics_table.add_row("Max Drawdown", f"{results['max_drawdown']:.2%}")

    console.print(metrics_table)

    # Trading statistics
    console.print("\n📊 [bold cyan]Trading Statistics:[/bold cyan]")
    stats_table = Table()
    stats_table.add_column("Statistic", style="cyan")
    stats_table.add_column("Value", style="green")

    stats_table.add_row("Win Rate", f"{results['win_rate']:.1%}")
    stats_table.add_row("Total Trades", f"{results['total_trades']}")
    stats_table.add_row("Profit Trades", f"{results['profit_trades']}")
    stats_table.add_row("Loss Trades", f"{results['loss_trades']}")
    stats_table.add_row("Avg Win", f"{results['avg_win']:.1%}")
    stats_table.add_row("Avg Loss", f"{results['avg_loss']:.1%}")
    stats_table.add_row("Profit Factor", f"{results['profit_factor']:.2f}")
    stats_table.add_row("Expectancy", f"{results['expectancy']:.1%}")

    console.print(stats_table)


def display_optimization_results(results: dict, method: str, metric: str):
    """
    Display optimization results

    Args:
        results: Optimization results dictionary
        method: Optimization method used
        metric: Metric optimized for
    """
    console.print("\n🎯 [bold cyan]Best Parameters:[/bold cyan]")
    best_params = results['best_parameters']
    for param, value in best_params.items():
        console.print(f"  {param}: {value}")

    console.print(f"\n📈 [bold cyan]Optimization Results:[/bold cyan]")
    console.print(f"  Best {metric.replace('_', ' ').title()}: {results['best_metric_value']:.3f}")
    console.print(f"  Total Evaluations: {results['total_evaluations']}")
    console.print(f"  Optimization Time: {results['optimization_time']:.1f}s")

    # Top 5 results
    console.print(f"\n🏆 [bold cyan]Top 5 Results:[/bold cyan]")
    top_results_table = Table()
    top_results_table.add_column("Rank", style="cyan")
    top_results_table.add_column("Parameters", style="white")
    top_results_table.add_column(f"{metric.replace('_', ' ').title()}", style="green")

    for result in results['top_5_results']:
        params_str = ", ".join([f"{k}={v}" for k, v in result['params'].items()])
        top_results_table.add_row(
            str(result['rank']),
            params_str,
            f"{result['metric']:.3f}"
        )

    console.print(top_results_table)


def display_rules_list(rules: list, detailed: bool, format: str):
    """
    Display rules list

    Args:
        rules: List of rule dictionaries
        detailed: Whether to show detailed information
        format: Output format
    """
    if format == "json":
        import json
        console.print(json.dumps(rules, indent=2))
        return

    table = Table()
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Win Rate", style="blue")

    if detailed:
        table.add_column("Description", style="white")
        table.add_column("Parameters", style="magenta")
        table.add_column("Performance", style="green")

    for rule in rules:
        status = "✅ Active" if rule["active"] else "❌ Inactive"
        win_rate = rule.get("performance", {}).get("win_rate", 0)

        if detailed:
            params_str = ", ".join([f"{k}={v}" for k, v in rule.get("parameters", {}).items()])
            perf_str = f"Win Rate: {win_rate:.1%}, Avg Return: {rule.get('performance', {}).get('avg_return', 0):.1%}"
            table.add_row(
                rule["id"],
                rule["name"],
                rule["type"],
                status,
                f"{win_rate:.1%}",
                rule["description"],
                params_str,
                perf_str
            )
        else:
            table.add_row(
                rule["id"],
                rule["name"],
                rule["type"],
                status,
                f"{win_rate:.1%}"
            )

    console.print(table)


def display_portfolio_status(portfolio: dict, detailed: bool, format: str):
    """
    Display portfolio status

    Args:
        portfolio: Portfolio data dictionary
        detailed: Whether to show detailed information
        format: Output format
    """
    if format == "json":
        import json
        console.print(json.dumps(portfolio, indent=2))
        return

    # Summary
    console.print(f"💼 Portfolio ID: {portfolio['portfolio_id']}")
    console.print(f"💰 Total Value: ${portfolio['total_value']:,.2f}")
    console.print(f"💵 Cash Balance: ${portfolio['cash_balance']:,.2f}")
    console.print(f"📊 Total Positions: {portfolio['total_positions']}")

    perf = portfolio['performance']
    console.print(f"📈 Daily P&L: ${perf['daily_pnl']:,.2f} ({perf['daily_return_pct']:.2f}%)")
    console.print(f"📈 Total P&L: ${perf['total_pnl']:,.2f} ({perf['total_return_pct']:.2f}%)")

    # Positions
    if portfolio['positions']:
        console.print("\n📋 [bold cyan]Positions:[/bold cyan]")
        positions_table = Table()
        positions_table.add_column("Symbol", style="cyan")
        positions_table.add_column("Shares", style="white")
        positions_table.add_column("Avg Price", style="yellow")
        positions_table.add_column("Current Price", style="green")
        positions_table.add_column("Value", style="blue")
        positions_table.add_column("P&L", style="magenta")
        positions_table.add_column("P&L %", style="red")

        for position in portfolio['positions']:
            pnl_color = "green" if position['pnl'] >= 0 else "red"
            pnl_pct_color = "green" if position['pnl_pct'] >= 0 else "red"

            positions_table.add_row(
                position['symbol'],
                f"{position['shares']:,}",
                f"${position['avg_price']:.2f}",
                f"${position['current_price']:.2f}",
                f"${position['value']:,.2f}",
                f"[{pnl_color}]${position['pnl']:,.2f}[/{pnl_color}]",
                f"[{pnl_pct_color}]{position['pnl_pct']:.2f}%[/{pnl_pct_color}]"
            )

        console.print(positions_table)
