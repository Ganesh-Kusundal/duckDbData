"""
Examples and Usage Patterns for DuckDB Financial Framework
========================================================

This file contains comprehensive examples showing how to use the
robust DuckDB framework for complex queries, analytics, scanning, and real-time trading.
"""

import asyncio
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Any

from .query_builder import AdvancedQueryBuilder
from .analytics import FinancialAnalytics, TechnicalIndicators
from .scanner import ScannerFramework, TechnicalScanner
from .realtime import RealtimeManager, OrderManager, RiskManager


class FrameworkExamples:
    """
    Comprehensive examples for the DuckDB Financial Framework.
    """

    def __init__(self, connection):
        self.connection = connection
        self.analytics = FinancialAnalytics(connection)
        self.indicators = TechnicalIndicators(connection)
        self.scanner = ScannerFramework(connection)

    # Query Framework Examples
    def complex_query_example(self):
        """Example of complex query building."""
        print("🔍 Complex Query Example")

        # Build a complex query with multiple conditions
        query_builder = AdvancedQueryBuilder()

        # Add filters and conditions
        query = (query_builder
                .select("symbol", "timestamp", "close", "volume")
                .time_series_filter("2024-01-01", "2024-12-31")
                .symbol_filter(["AAPL", "GOOGL", "MSFT"])
                .price_filter(min_price=100, max_price=500)
                .volume_filter(min_volume=1000000)
                .join("company_info", "market_data.symbol = company_info.symbol")
                .where("sector", "=", "Technology")
                .group_by("symbol")
                .order_by("volume", "DESC")
                .limit(100))

        sql, params = query.build()
        print(f"Generated SQL: {sql}")
        print(f"Parameters: {params}")

        # Execute query
        result = self.connection.execute(sql, list(params.values())).fetchdf()
        print(f"Query returned {len(result)} rows")
        return result

    def analytical_query_example(self):
        """Example of analytical query with window functions."""
        print("\n📊 Analytical Query Example")

        query = """
        WITH technical_analysis AS (
            SELECT
                symbol,
                timestamp,
                close,
                volume,
                -- Moving averages
                AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 19 PRECEDING) as sma_20,
                AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 49 PRECEDING) as sma_50,

                -- RSI calculation
                100 - (100 / (1 + (
                    AVG(CASE WHEN daily_change > 0 THEN daily_change ELSE 0 END) OVER (
                        PARTITION BY symbol ORDER BY timestamp ROWS 13 PRECEDING
                    ) /
                    NULLIF(AVG(CASE WHEN daily_change < 0 THEN ABS(daily_change) ELSE 0 END) OVER (
                        PARTITION BY symbol ORDER BY timestamp ROWS 13 PRECEDING
                    ), 0)
                ))) as rsi_14,

                -- Volatility
                STDDEV(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 29 PRECEDING) as volatility_30d,

                -- Volume analysis
                AVG(volume) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 4 PRECEDING) as avg_volume_5d,
                volume / NULLIF(AVG(volume) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 4 PRECEDING), 0) as volume_ratio

            FROM (
                SELECT
                    symbol,
                    timestamp,
                    close,
                    volume,
                    close - LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp) as daily_change
                FROM market_data
                WHERE timestamp >= '2024-01-01'
                  AND volume > 100000
            ) base_data
        )
        SELECT
            symbol,
            timestamp,
            close,
            sma_20,
            sma_50,
            rsi_14,
            volatility_30d,
            volume_ratio,
            -- Generate signals based on conditions
            CASE
                WHEN rsi_14 < 30 AND close > sma_20 THEN 'BUY_SIGNAL'
                WHEN rsi_14 > 70 AND close < sma_20 THEN 'SELL_SIGNAL'
                WHEN sma_20 > sma_50 AND volume_ratio > 1.5 THEN 'VOLUME_BREAKOUT'
                ELSE 'HOLD'
            END as signal
        FROM technical_analysis
        WHERE signal != 'HOLD'
        ORDER BY timestamp DESC
        LIMIT 50
        """

        result = self.connection.execute(query).fetchdf()
        print(f"Found {len(result)} trading signals")
        return result

    # Analytics Framework Examples
    def technical_analysis_example(self, symbols: List[str]):
        """Example of comprehensive technical analysis."""
        print("
📈 Technical Analysis Example"        print(f"Analyzing {len(symbols)} symbols: {symbols}")

        results = {}
        for symbol in symbols:
            print(f"\nAnalyzing {symbol}...")

            # Calculate multiple indicators
            try:
                sma = self.indicators.calculate_sma(symbol, period=20)
                rsi = self.indicators.calculate_rsi(symbol, period=14)
                bollinger = self.indicators.calculate_bollinger_bands(symbol, period=20)
                macd = self.indicators.calculate_macd(symbol)

                results[symbol] = {
                    'sma': sma,
                    'rsi': rsi,
                    'bollinger_bands': bollinger,
                    'macd': macd
                }

                print(f"✅ {symbol}: Calculated {len(sma.data)} data points")

                # Generate trading signals
                latest_rsi = rsi.data['rsi_14'].iloc[-1] if not rsi.data.empty else None
                latest_close = bollinger.data['close'].iloc[-1] if not bollinger.data.empty else None
                bb_lower = bollinger.data['bb_lower'].iloc[-1] if not bollinger.data.empty else None

                signals = []
                if latest_rsi and latest_rsi < 30:
                    signals.append("OVERSOLD")
                if latest_rsi and latest_rsi > 70:
                    signals.append("OVERBOUGHT")
                if latest_close and bb_lower and latest_close < bb_lower:
                    signals.append("BELOW_LOWER_BB")

                if signals:
                    print(f"🎯 Signals for {symbol}: {', '.join(signals)}")

            except Exception as e:
                print(f"❌ Error analyzing {symbol}: {e}")

        return results

    def portfolio_analysis_example(self, symbols: List[str],
                                  start_date: str, end_date: str):
        """Example of portfolio analysis."""
        print("
📊 Portfolio Analysis Example"        print(f"Analyzing portfolio: {symbols}")

        # Analyze individual stock returns
        individual_analysis = self.analytics.analyze_portfolio_returns(
            symbols, start_date, end_date
        )

        # Calculate correlation matrix
        correlation_matrix = self.analytics.correlation_matrix(
            symbols, start_date, end_date
        )

        # Risk metrics for each symbol
        risk_metrics = {}
        for symbol in symbols:
            metrics = self.analytics.risk_metrics(symbol)
            risk_metrics[symbol] = metrics

        # Summary statistics
        print("
📈 Portfolio Summary:"        total_return = sum(analysis.cumulative_returns.iloc[-1]
                             for analysis in individual_analysis.values()
                             if not analysis.cumulative_returns.empty)

        avg_volatility = sum(analysis.volatility for analysis in individual_analysis.values()) / len(symbols)
        avg_sharpe = sum(analysis.sharpe_ratio for analysis in individual_analysis.values()) / len(symbols)

        print(f"Total Portfolio Return: {total_return:.2%}")
        print(f"Average Volatility: {avg_volatility:.2%}")
        print(f"Average Sharpe Ratio: {avg_sharpe:.2f}")

        print("
🎯 Risk Metrics Summary:"        for symbol, metrics in risk_metrics.items():
            if metrics:
                print(f"{symbol}: VaR(95%)={metrics.get('var_95', 0):.2%}, "
                      f"Max Loss={metrics.get('max_loss', 0):.2%}")

        return {
            'individual_analysis': individual_analysis,
            'correlation_matrix': correlation_matrix,
            'risk_metrics': risk_metrics
        }

    # Scanner Framework Examples
    def scanner_example(self, symbols: List[str], start_date: str, end_date: str):
        """Example of comprehensive scanning."""
        print("
🔍 Scanner Framework Example"        print(f"Scanning {len(symbols)} symbols for trading signals")

        # Run multiple scanners
        scanner_result = self.scanner.run_scan(
            scanner_types=['technical', 'pattern'],
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )

        print("
📊 Scanner Results:"        print(f"Total Signals Found: {len(scanner_result.signals)}")
        print(f"Execution Time: {scanner_result.execution_time:.2f}s")
        print(f"Symbols Scanned: {scanner_result.symbols_scanned}")
        print(f"Patterns Found: {scanner_result.patterns_found}")

        # Group signals by type
        buy_signals = [s for s in scanner_result.signals if s.signal_type.name == 'BUY']
        sell_signals = [s for s in scanner_result.signals if s.signal_type.name == 'SELL']

        print(f"Buy Signals: {len(buy_signals)}")
        print(f"Sell Signals: {len(sell_signals)}")

        # Show top signals by confidence
        top_signals = sorted(scanner_result.signals, key=lambda x: x.confidence, reverse=True)[:5]

        print("
🎯 Top 5 Signals by Confidence:"        for i, signal in enumerate(top_signals, 1):
            print(f"{i}. {signal.symbol}: {signal.signal_type.name} "
                  f"(Confidence: {signal.confidence:.2f}, Price: ${signal.price:.2f})")

        return scanner_result

    # Real-time Framework Examples
    async def realtime_example(self):
        """Example of real-time data streaming."""
        print("
📡 Real-time Trading Example"        # Initialize components
        realtime_manager = RealtimeManager(self.connection)
        order_manager = OrderManager(self.connection, realtime_manager)
        risk_manager = RiskManager(order_manager)

        # Subscribe to symbols
        symbols = ['AAPL', 'GOOGL', 'MSFT']

        def price_callback(data):
            print(f"📈 {data.symbol}: ${data.price:.2f} "
                  f"(Volume: {data.volume:,})")

        for symbol in symbols:
            realtime_manager.subscribe(symbol, price_callback)

        # Create sample orders
        print("
📝 Creating Sample Orders..."        orders = []
        for symbol in symbols:
            # Get current price
            current_price = realtime_manager.get_real_time_price(symbol)
            if current_price:
                # Create limit order
                order = order_manager.create_order(
                    symbol=symbol,
                    side='BUY',
                    order_type='LIMIT',
                    quantity=100,
                    price=current_price * 0.98  # 2% below current price
                )
                orders.append(order)
                print(f"✅ Created order for {symbol}: {order.order_id}")

        # Check risk limits
        for order in orders:
            is_valid, reason = risk_manager.validate_order(order)
            print(f"🔍 Risk Check for {order.symbol}: {'✅' if is_valid else '❌'} {reason}")

        # Portfolio management
        portfolio_value = order_manager.get_portfolio_value()
        positions = order_manager.get_positions()

        print("
💼 Portfolio Status:"        print(f"Total Value: ${portfolio_value:.2f}")
        print(f"Active Positions: {len(positions)}")

        return {
            'realtime_manager': realtime_manager,
            'order_manager': order_manager,
            'risk_manager': risk_manager,
            'orders': orders
        }

    def backtesting_example(self, signals: List, start_date: str, end_date: str):
        """Example of signal backtesting."""
        print("
📈 Backtesting Example"        # Use the scanner's signal engine for backtesting
        backtest_results = self.scanner.signal_engine.backtest_signals(
            signals, start_date, end_date
        )

        print("
📊 Backtest Results:"        print(f"Total Signals: {backtest_results['total_signals']}")
        print(f"Winning Trades: {backtest_results['winning_trades']}")
        print(f"Losing Trades: {backtest_results['losing_trades']}")
        print(f"Win Rate: {backtest_results['win_rate']:.2%}")
        print(f"Total Return: {backtest_results['total_return']:.2%}")
        print(f"Sharpe Ratio: {backtest_results['sharpe_ratio']:.2f}")

        return backtest_results

    # Comprehensive Workflow Example
    def comprehensive_workflow_example(self, symbols: List[str],
                                      start_date: str, end_date: str):
        """Complete workflow combining all framework components."""
        print("🚀 Comprehensive Financial Analysis Workflow")
        print("=" * 50)

        results = {}

        # 1. Complex Query Analysis
        print("\n1️⃣ Complex Query Analysis")
        query_results = self.complex_query_example()
        results['query_results'] = query_results

        # 2. Technical Analysis
        print("\n2️⃣ Technical Analysis")
        tech_results = self.technical_analysis_example(symbols[:3])  # Limit to 3 symbols
        results['technical_analysis'] = tech_results

        # 3. Portfolio Analysis
        print("\n3️⃣ Portfolio Analysis")
        portfolio_results = self.portfolio_analysis_example(symbols[:5], start_date, end_date)
        results['portfolio_analysis'] = portfolio_results

        # 4. Scanner Analysis
        print("\n4️⃣ Scanner Analysis")
        scanner_results = self.scanner_example(symbols[:3], start_date, end_date)
        results['scanner_results'] = scanner_results

        # 5. Backtesting
        print("\n5️⃣ Backtesting")
        if scanner_results.signals:
            backtest_results = self.backtesting_example(
                scanner_results.signals[:10], start_date, end_date
            )
            results['backtest_results'] = backtest_results

        print("\n🎉 Workflow Complete!")
        print(f"Generated insights for {len(symbols)} symbols")
        print(f"Total signals found: {len(results.get('scanner_results', {}).signals) if 'scanner_results' in results else 0}")

        return results


# Convenience functions for quick usage
def run_complex_query(connection, symbols: List[str], start_date: str, end_date: str):
    """Quick function to run complex query analysis."""
    examples = FrameworkExamples(connection)
    return examples.complex_query_example()


def run_technical_analysis(connection, symbols: List[str]):
    """Quick function to run technical analysis."""
    examples = FrameworkExamples(connection)
    return examples.technical_analysis_example(symbols)


def run_portfolio_analysis(connection, symbols: List[str], start_date: str, end_date: str):
    """Quick function to run portfolio analysis."""
    examples = FrameworkExamples(connection)
    return examples.portfolio_analysis_example(symbols, start_date, end_date)


def run_scanner(connection, symbols: List[str], start_date: str, end_date: str):
    """Quick function to run scanner analysis."""
    examples = FrameworkExamples(connection)
    return examples.scanner_example(symbols, start_date, end_date)


def run_comprehensive_workflow(connection, symbols: List[str], start_date: str, end_date: str):
    """Run the complete financial analysis workflow."""
    examples = FrameworkExamples(connection)
    return examples.comprehensive_workflow_example(symbols, start_date, end_date)
