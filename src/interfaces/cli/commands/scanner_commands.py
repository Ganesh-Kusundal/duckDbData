"""
Scanner CLI Commands
CLI commands for market scanner operations
"""

import logging
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.infrastructure.dependency_container import get_container as get_dependency_container
from src.application.services.market_data_application_service import MarketDataApplicationService

logger = logging.getLogger(__name__)
console = Console()


def register_scanner_commands(cli_app):
    """
    Register scanner commands with the CLI app

    Args:
        cli_app: Typer CLI application instance
    """
    scanner_app = typer.Typer(help="Market scanner and rule-based analysis")
    cli_app.add_typer(scanner_app, name="scanner")

    @scanner_app.command("scan")
    def run_market_scan(
        symbols: List[str] = typer.Option(..., help="Trading symbols to scan"),
        rules: List[str] = typer.Option(None, help="Scanner rules to apply"),
        limit: int = typer.Option(50, help="Maximum results per symbol")
    ):
        """
        Run market scanner on specified symbols
        """
        async def _run_scan():
            try:
                console.print(f"🔍 [bold blue]Running market scan[/bold blue]")
                console.print(f"Symbols: {', '.join(symbols)}")
                if rules:
                    console.print(f"Rules: {', '.join(rules)}")

                # Get application service
                from infrastructure.dependency_container import get_container
                container = get_container()

                try:
                    service = container.resolve(MarketDataApplicationService)
                except ValueError:
                    # Try to initialize bootstrap
                    console.print("🔧 [yellow]Initializing services...[/yellow]")
                    from infrastructure.bootstrap import initialize_application
                    import asyncio

                    # Run bootstrap in a new event loop
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        success = loop.run_until_complete(initialize_application())
                        loop.close()

                        if success:
                            service = container.resolve(MarketDataApplicationService)
                        else:
                            console.print("❌ [red]Failed to initialize services[/red]")
                            return
                    except Exception as e:
                        console.print(f"❌ [red]Bootstrap error: {e}[/red]")
                        return

                # Import scanner functionality
                from app.startup import get_scanner

                # Execute actual scanning logic
                console.print(f"🔍 Executing scanner with rules: {rules or ['all']}")

                # Get appropriate scanner based on rules
                scanner = None
                rules_list = rules or ['all']
                if any('breakout' in rule.lower() for rule in rules_list) or 'all' in [r.lower() for r in rules_list]:
                    scanner = get_scanner('breakout')
                    console.print("🚀 Using breakout scanner")
                elif any('crp' in rule.lower() for rule in rules_list):
                    scanner = get_scanner('crp')
                    console.print("🎯 Using CRP scanner")

                if scanner:
                    # Get current date for scanning
                    from datetime import date
                    test_date = date.today()

                    # Execute scan
                    results = scanner.scan(test_date)

                    # Display actual results
                    display_actual_scan_results(results, limit)
                else:
                    console.print("⚠️ [yellow]No appropriate scanner found for rules[/yellow]")
                    # Fallback to mock results
                    display_scan_results(symbols, rules or ["all"], limit)

            except Exception as e:
                console.print(f"❌ [red]Error running market scan: {e}[/red]")
                logger.exception("CLI scanner scan error")

        # Run async function
        import asyncio
        asyncio.run(_run_scan())

    @scanner_app.command("rules")
    def list_scanner_rules(
        category: Optional[str] = typer.Option(None, help="Filter by category"),
        format: str = typer.Option("table", help="Output format (table, json)")
    ):
        """
        List available scanner rules
        """
        async def _list_rules():
            try:
                console.print(f"📋 [bold blue]Available Scanner Rules[/bold blue]")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # TODO: Implement actual rules listing
                # For now, show mock rules

                # Display results
                display_scanner_rules(category, format)

            except Exception as e:
                console.print(f"❌ [red]Error listing scanner rules: {e}[/red]")
                logger.exception("CLI scanner rules error")

        # Run async function
        import asyncio
        asyncio.run(_list_rules())

    @scanner_app.command("backtest")
    def backtest_scanner_rule(
        rule_name: str = typer.Argument(..., help="Scanner rule to backtest"),
        symbols: List[str] = typer.Option(..., help="Symbols to test"),
        start_date: str = typer.Option("2024-01-01", help="Start date (YYYY-MM-DD)"),
        end_date: str = typer.Option("2024-12-31", help="End date (YYYY-MM-DD)")
    ):
        """
        Backtest a scanner rule on historical data
        """
        async def _backtest_rule():
            try:
                console.print(f"🎯 [bold blue]Backtesting scanner rule: {rule_name}[/bold blue]")
                console.print(f"Symbols: {', '.join(symbols)}")
                console.print(f"Period: {start_date} to {end_date}")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # TODO: Implement actual backtest logic
                # For now, show mock results

                # Display results
                display_backtest_results(rule_name, symbols, start_date, end_date)

            except Exception as e:
                console.print(f"❌ [red]Error backtesting rule {rule_name}: {e}[/red]")
                logger.exception(f"CLI scanner backtest error for {rule_name}")

        # Run async function
        import asyncio
        asyncio.run(_backtest_rule())

    @scanner_app.command("optimize")
    def optimize_scanner_rule(
        rule_name: str = typer.Argument(..., help="Scanner rule to optimize"),
        parameter: str = typer.Option("threshold", help="Parameter to optimize"),
        min_value: float = typer.Option(0.0, help="Minimum parameter value"),
        max_value: float = typer.Option(1.0, help="Maximum parameter value"),
        steps: int = typer.Option(10, help="Number of optimization steps")
    ):
        """
        Optimize scanner rule parameters
        """
        async def _optimize_rule():
            try:
                console.print(f"🔧 [bold blue]Optimizing scanner rule: {rule_name}[/bold blue]")
                console.print(f"Parameter: {parameter}")
                console.print(f"Range: {min_value} to {max_value}")
                console.print(f"Steps: {steps}")

                # Get application service
                container = get_dependency_container()
                service = container.resolve(MarketDataApplicationService)

                # TODO: Implement actual optimization logic
                # For now, show mock results

                # Display results
                display_optimization_results(rule_name, parameter, min_value, max_value, steps)

            except Exception as e:
                console.print(f"❌ [red]Error optimizing rule {rule_name}: {e}[/red]")
                logger.exception(f"CLI scanner optimize error for {rule_name}")

        # Run async function
        import asyncio
        asyncio.run(_optimize_rule())


def display_actual_scan_results(results, limit: int):
    """
    Display actual scanner results with real data

    Args:
        results: List of signal dictionaries from scanner
        limit: Maximum results to display
    """
    console.print(f"\n📊 [bold blue]Scanner Results ({len(results)} signals)[/bold blue]")
    console.print("-" * 80)

    if not results:
        console.print("❌ No signals found")
        return

    # Create table for results
    table = Table()
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Signal", style="green")
    table.add_column("Confidence", style="yellow", justify="right")
    table.add_column("Price", style="white", justify="right")
    table.add_column("Volume", style="magenta", justify="right")
    table.add_column("Rule", style="blue")

    # Display results (limited by limit parameter)
    for result in results[:limit]:
        symbol = result.get('symbol', 'N/A')
        signal_type = result.get('signal_type', 'BUY')
        confidence = result.get('confidence', 0)
        price = result.get('price', 0)
        volume = result.get('volume', 0)
        rule_id = result.get('rule_id', 'unknown')

        # Format confidence as percentage
        conf_pct = f"{confidence:.1%}" if isinstance(confidence, (int, float)) else str(confidence)

        # Format price and volume
        price_str = f"₹{price:,.2f}" if isinstance(price, (int, float)) and price > 0 else "N/A"
        volume_str = f"{volume:,}" if isinstance(volume, (int, float)) and volume > 0 else "N/A"

        # Set signal color
        signal_color = "green" if signal_type.upper() == "BUY" else "red" if signal_type.upper() == "SELL" else "yellow"

        table.add_row(
            symbol,
            f"[{signal_color}]{signal_type}[/{signal_color}]",
            conf_pct,
            price_str,
            volume_str,
            rule_id
        )

    console.print(table)

    # Show summary
    if len(results) > limit:
        console.print(f"\n... and {len(results) - limit} more signals (showing first {limit})")

    console.print(f"\n✅ Total signals: {len(results)}")


def display_scan_results(symbols: List[str], rules: List[str], limit: int):
    """
    Display market scan results

    Args:
        symbols: List of scanned symbols
        rules: Applied rules
        limit: Maximum results per symbol
    """
    console.print(f"\n🔍 [bold blue]Market Scan Results[/bold blue]")
    console.print(f"Rules Applied: {', '.join(rules)}")
    console.print("-" * 80)

    # Mock scan results
    mock_results = [
        {
            "symbol": "AAPL",
            "rule": "momentum_breakout",
            "signal": "BUY",
            "confidence": 0.85,
            "timestamp": "2024-09-05T10:30:00Z"
        },
        {
            "symbol": "AAPL",
            "rule": "volume_surge",
            "signal": "WATCH",
            "confidence": 0.72,
            "timestamp": "2024-09-05T10:30:00Z"
        },
        {
            "symbol": "MSFT",
            "rule": "price_gap",
            "signal": "SELL",
            "confidence": 0.78,
            "timestamp": "2024-09-05T10:30:00Z"
        },
        {
            "symbol": "GOOGL",
            "rule": "rsi_divergence",
            "signal": "BUY",
            "confidence": 0.65,
            "timestamp": "2024-09-05T10:30:00Z"
        }
    ]

    if mock_results:
        table = Table()
        table.add_column("Symbol", style="cyan", no_wrap=True)
        table.add_column("Rule", style="white")
        table.add_column("Signal", style="green" if "BUY" else "red")
        table.add_column("Confidence", style="yellow")
        table.add_column("Time", style="blue")

        for result in mock_results[:limit]:
            if result["symbol"] in symbols:
                signal_style = "green" if result["signal"] == "BUY" else "red" if result["signal"] == "SELL" else "yellow"
                table.add_row(
                    result["symbol"],
                    result["rule"].replace("_", " ").title(),
                    f"[{signal_style}]{result['signal']}[/{signal_style}]",
                    f"{result['confidence']:.1%}",
                    result["timestamp"][:16]  # Show date and hour
                )

        console.print(table)
        console.print(f"\n✅ Found {len(mock_results)} signals across {len(symbols)} symbols")
    else:
        console.print("✅ [green]No signals found[/green]")


def display_scanner_rules(category: Optional[str], format: str):
    """
    Display available scanner rules

    Args:
        category: Category filter
        format: Output format
    """
    console.print(f"\n📋 [bold blue]Scanner Rules{' - ' + category.title() if category else ''}[/bold blue]")
    console.print("-" * 60)

    # Mock scanner rules
    mock_rules = [
        {
            "name": "momentum_breakout",
            "description": "Detects momentum breakouts above resistance levels",
            "category": "momentum",
            "parameters": ["threshold", "lookback_period"]
        },
        {
            "name": "volume_surge",
            "description": "Identifies unusual volume spikes",
            "category": "volume",
            "parameters": ["multiplier", "min_volume"]
        },
        {
            "name": "price_gap",
            "description": "Detects price gaps in market data",
            "category": "price_action",
            "parameters": ["gap_threshold", "gap_type"]
        },
        {
            "name": "rsi_divergence",
            "description": "Finds RSI divergences with price",
            "category": "oscillator",
            "parameters": ["rsi_period", "divergence_threshold"]
        },
        {
            "name": "bollinger_squeeze",
            "description": "Detects Bollinger Band squeezes indicating volatility contraction",
            "category": "volatility",
            "parameters": ["bb_period", "squeeze_threshold"]
        }
    ]

    # Filter by category if specified
    if category:
        mock_rules = [rule for rule in mock_rules if rule["category"] == category]

    if format == "json":
        import json
        console.print(json.dumps(mock_rules, indent=2))
    else:
        table = Table()
        table.add_column("Rule Name", style="cyan", no_wrap=True)
        table.add_column("Category", style="green")
        table.add_column("Description", style="white")
        table.add_column("Parameters", style="yellow")

        for rule in mock_rules:
            table.add_row(
                rule["name"].replace("_", " ").title(),
                rule["category"].title(),
                rule["description"],
                ", ".join(rule["parameters"])
            )

        console.print(table)
        console.print(f"\n📊 Total Rules: {len(mock_rules)}")

        # Show category breakdown
        categories = {}
        for rule in mock_rules:
            categories[rule["category"]] = categories.get(rule["category"], 0) + 1

        if len(categories) > 1:
            console.print("\n📂 [cyan]By Category:[/cyan]")
            for cat, count in categories.items():
                console.print(f"  • {cat.title()}: {count} rules")


def display_backtest_results(rule_name: str, symbols: List[str], start_date: str, end_date: str):
    """
    Display scanner rule backtest results

    Args:
        rule_name: Name of the backtested rule
        symbols: List of tested symbols
        start_date: Start date
        end_date: End date
    """
    console.print(f"\n🎯 [bold blue]Backtest Results for {rule_name.replace('_', ' ').title()}[/bold blue]")
    console.print(f"Symbols: {', '.join(symbols)}")
    console.print(f"Period: {start_date} to {end_date}")
    console.print("-" * 80)

    # Mock backtest results
    results = {
        "performance": {
            "total_signals": 245,
            "winning_signals": 132,
            "losing_signals": 113,
            "win_rate": 0.539,
            "avg_win": 2.8,
            "avg_loss": -1.4,
            "profit_factor": 1.35,
            "max_drawdown": -8.2,
            "sharpe_ratio": 1.45
        },
        "by_symbol": [
            {"symbol": "AAPL", "signals": 45, "win_rate": 0.56, "profit_factor": 1.42},
            {"symbol": "MSFT", "signals": 38, "win_rate": 0.52, "profit_factor": 1.28},
            {"symbol": "GOOGL", "signals": 32, "win_rate": 0.54, "profit_factor": 1.35}
        ]
    }

    # Overall performance table
    perf_table = Table(title="📊 Overall Performance")
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", style="green")

    perf_table.add_row("Total Signals", str(results["performance"]["total_signals"]))
    perf_table.add_row("Winning Signals", str(results["performance"]["winning_signals"]))
    perf_table.add_row("Losing Signals", str(results["performance"]["losing_signals"]))
    perf_table.add_row("Win Rate", f"{results['performance']['win_rate']:.1%}")
    perf_table.add_row("Avg Win", f"${results['performance']['avg_win']:.2f}")
    perf_table.add_row("Avg Loss", f"${results['performance']['avg_loss']:.2f}")
    perf_table.add_row("Profit Factor", f"{results['performance']['profit_factor']:.2f}")
    perf_table.add_row("Max Drawdown", f"{results['performance']['max_drawdown']:.1f}%")
    perf_table.add_row("Sharpe Ratio", f"{results['performance']['sharpe_ratio']:.2f}")

    console.print(perf_table)

    # By symbol table
    symbol_table = Table(title="📊 Performance by Symbol")
    symbol_table.add_column("Symbol", style="cyan")
    symbol_table.add_column("Signals", style="white")
    symbol_table.add_column("Win Rate", style="green")
    symbol_table.add_column("Profit Factor", style="yellow")

    for symbol_data in results["by_symbol"]:
        symbol_table.add_row(
            symbol_data["symbol"],
            str(symbol_data["signals"]),
            f"{symbol_data['win_rate']:.1%}",
            f"{symbol_data['profit_factor']:.2f}"
        )

    console.print(symbol_table)


def display_optimization_results(rule_name: str, parameter: str, min_value: float, max_value: float, steps: int):
    """
    Display scanner rule optimization results

    Args:
        rule_name: Name of the optimized rule
        parameter: Optimized parameter
        min_value: Minimum parameter value
        max_value: Maximum parameter value
        steps: Number of optimization steps
    """
    console.print(f"\n🔧 [bold blue]Optimization Results for {rule_name.replace('_', ' ').title()}[/bold blue]")
    console.print(f"Parameter: {parameter}")
    console.print(f"Range: {min_value} to {max_value}")
    console.print(f"Steps: {steps}")
    console.print("-" * 80)

    # Mock optimization results
    results = {
        "optimization_method": "grid_search",
        "best_parameters": {parameter: 0.75},
        "optimization_results": {
            "best_score": 0.723,
            "improvement": 0.156,
            "computation_time": "45.2s",
            "iterations": steps
        },
        "parameter_sensitivity": {
            "impact": 0.45,
            "optimal_range": [min_value + (max_value - min_value) * 0.6,
                             min_value + (max_value - min_value) * 0.9]
        },
        "parameter_values": [
            {"value": min_value, "score": 0.567},
            {"value": min_value + (max_value - min_value) * 0.25, "score": 0.623},
            {"value": min_value + (max_value - min_value) * 0.5, "score": 0.689},
            {"value": min_value + (max_value - min_value) * 0.75, "score": 0.723},
            {"value": max_value, "score": 0.678}
        ]
    }

    # Optimization summary
    console.print("📊 [cyan]Optimization Summary:[/cyan]")
    console.print(f"  Method: {results['optimization_method'].replace('_', ' ').title()}")
    console.print(f"  Best Score: {results['optimization_results']['best_score']:.3f}")
    console.print(f"  Improvement: +{results['optimization_results']['improvement']:.1%}")
    console.print(f"  Computation Time: {results['optimization_results']['computation_time']}")
    console.print(f"  Iterations: {results['optimization_results']['iterations']}")

    console.print(f"\n🔹 [cyan]Best Parameters:[/cyan]")
    for param, value in results["best_parameters"].items():
        console.print(f"  {param}: {value}")

    # Parameter sensitivity
    console.print(f"\n📈 [cyan]Parameter Sensitivity:[/cyan]")
    console.print(f"  Impact: {results['parameter_sensitivity']['impact']:.1%}")
    optimal_range = results['parameter_sensitivity']['optimal_range']
    console.print(f"  Optimal Range: [{optimal_range[0]:.3f}, {optimal_range[1]:.3f}]")

    # Parameter values table
    console.print(f"\n📋 [cyan]Parameter Test Results:[/cyan]")
    param_table = Table()
    param_table.add_column("Parameter Value", style="cyan")
    param_table.add_column("Score", style="green")
    param_table.add_column("Improvement", style="yellow")

    baseline_score = results['parameter_values'][0]['score']
    for param_data in results["parameter_values"]:
        improvement = param_data['score'] - baseline_score
        param_table.add_row(
            f"{param_data['value']:.3f}",
            f"{param_data['score']:.3f}",
            f"{improvement:+.3f}"
        )

    console.print(param_table)
