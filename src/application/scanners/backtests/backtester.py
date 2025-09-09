"""
Backtester for evaluating scanner performance on historical data.
"""

import sys
import os
from datetime import datetime, date, time, timedelta
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.infrastructure.core.singleton_database import DuckDBConnectionManager, create_db_manager
from src.infrastructure.core.query_api import QueryAPI
from ..strategies.relative_volume_scanner import RelativeVolumeScanner
from ..strategies.technical_scanner import TechnicalScanner


class Backtester:
    """
    Comprehensive backtesting framework for scanner strategies.
    Evaluates scanner performance over historical data periods.
    """

    def __init__(self, db_manager: DuckDBConnectionManager = None):
        """Initialize backtester with database manager."""
        self.db_manager = db_manager or create_db_manager()
        self.query_api = QueryAPI(self.db_manager)

        # Initialize scanner strategies
        self.scanners = {
            'relative_volume': RelativeVolumeScanner,
            'technical': TechnicalScanner
        }

        self.results_dir = Path("scanners/results/backtests")
        self.results_dir.mkdir(exist_ok=True, parents=True)

        print("🔬 Backtester initialized")

    def backtest_scanner(
                        self, 
                        scanner_name: str,
                        start_date: date,
                        end_date: date,
                        cutoff_time: time = time(9, 50),
                        config_override: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Backtest a specific scanner over a date range.

        Args:
            scanner_name: Name of scanner to backtest
            start_date: Start date for backtesting
            end_date: End date for backtesting
            cutoff_time: Time cutoff for scanning
            config_override: Configuration overrides

        Returns:
            Backtest results dictionary
        """
        if scanner_name not in self.scanners:
            raise ValueError(f"Scanner '{scanner_name}' not found")

        print(f"🔬 Backtesting {scanner_name} scanner from {start_date} to {end_date}")

        results = []
        current_date = start_date

        # Create scanner instance
        scanner_class = self.scanners[scanner_name]
        scanner = scanner_class(self.db_manager)

        # Apply configuration overrides
        if config_override:
            scanner.config.update(config_override)

        # Loop through each trading day
        while current_date <= end_date:
            # Skip weekends and holidays (simplified logic)
            if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                current_date += timedelta(days=1)
                continue

            try:
                # Run scanner for this date
                scan_result = scanner.scan(current_date, cutoff_time)

                if not scan_result.empty:
                    # Add metadata
                    scan_result['scan_date'] = current_date
                    scan_result['scanner_type'] = scanner_name

                    # Calculate winning probabilities for this date
                    date_performance = self._evaluate_date_performance(
                        current_date, scan_result['symbol'].tolist()
                    )

                    results.append({
                        'date': current_date,
                        'stock_count': len(scan_result),
                        'stocks': scan_result['symbol'].tolist(),
                        'performance': date_performance,
                        'scan_details': scan_result
                    })

                    print(f"✅ {current_date}: {len(scan_result)} stocks found")

            except Exception as e:
                print(f"❌ Error scanning {current_date}: {e}")
                continue

            current_date += timedelta(days=1)

        # Aggregate results
        summary = self._aggregate_backtest_results(results, scanner_name, start_date, end_date)

        # Save detailed results
        self._save_backtest_results(summary, scanner_name, start_date, end_date)

        return summary

    def _evaluate_date_performance(self, scan_date: date, symbols: List[str]) -> Dict[str, Any]:
        """
        Evaluate how the scanned stocks performed from 09:50 to market close.

        This correctly evaluates the scanner's effectiveness by:
        1. Using historical data to build reference (done in scanner.scan())
        2. Using scan_date data up to 09:50 to select stocks (done in scanner.scan())
        3. Measuring performance from 09:50 to 15:30 analysis window

        Args:
            scan_date: Date of scan (09:50 cutoff)
            symbols: List of symbols selected by scanner

        Returns:
            Performance metrics for the date
        """
        if not symbols:
            return {'stocks_analyzed': 0, 'winners': 0, 'avg_return': 0}

        print(f"🔍 Evaluating {len(symbols)} stocks for {scan_date} performance (09:50 → 15:30)")

        # Query performance from 09:50 cutoff time to market close
        performance_query = f"""
        WITH scan_stocks AS (
            SELECT unnest(ARRAY{symbols}) as symbol
        ),

        performance_window AS (
            -- Get price at 09:50 (scanner cutoff time)
            SELECT
                m1.symbol,
                m1.close as scan_price_0950,
                m1.timestamp as scan_timestamp_0950
            FROM market_data_unified m1
            WHERE m1.date_partition = ?
                AND m1.timestamp <= '09:50:00'
                AND m1.symbol IN ({','.join(['?' for _ in symbols])})
                AND m1.timestamp = (
                    -- Get the last data point before or exactly at 09:50
                    SELECT MAX(timestamp)
                    FROM market_data_unified m2
                    WHERE m2.symbol = m1.symbol
                      AND m2.date_partition = m1.date_partition
                      AND m2.timestamp <= '09:50:00'
                )
        ),

        market_close_prices AS (
            -- Get market close price (final price of day)
            SELECT
                m3.symbol,
                m3.close as close_price_1530,
                m3.timestamp as close_timestamp_1530
            FROM market_data_unified m3
            WHERE m3.date_partition = ?
                AND m3.symbol IN ({','.join(['?' for _ in symbols])})
                AND m3.timestamp = (
                    -- Get the final price of the trading day
                    SELECT MAX(timestamp)
                    FROM market_data_unified m4
                    WHERE m4.symbol = m3.symbol
                      AND m4.date_partition = m3.date_partition
                      AND m4.timestamp >= '09:15:00'  -- Valid trading hours
                      AND m4.timestamp <= '16:00:00'  -- Conservative market close
                )
        )

        SELECT
            s.symbol,
            pw.scan_price_0950,
            cp.close_price_1530,
            ROUND(((cp.close_price_1530 - pw.scan_price_0950) / pw.scan_price_0950) * 100, 4) as performance_pct,
            CASE
                WHEN cp.close_price_1530 > pw.scan_price_0950 THEN 'WINNER'
                WHEN cp.close_price_1530 < pw.scan_price_0950 THEN 'LOSER'
                ELSE 'FLAT'
            END as result_type,
            pw.scan_timestamp_0950,
            cp.close_timestamp_1530
        FROM scan_stocks s
        LEFT JOIN performance_window pw ON s.symbol = pw.symbol
        LEFT JOIN market_close_prices cp ON s.symbol = cp.symbol
        WHERE pw.scan_price_0950 IS NOT NULL
          AND cp.close_price_1530 IS NOT NULL
        """

        try:
            params = [scan_date] + symbols + [scan_date] + symbols
            performance_df = self.db_manager.execute_custom_query(performance_query, params)

            if performance_df.empty:
                print(f"⚠️  No performance data found for any scanned stocks on {scan_date}")
                return {'stocks_analyzed': 0, 'winners': 0, 'avg_return': 0}

            print(f"✅ Analyzed {len(performance_df)}/{len(symbols)} stocks with sufficient data")

            # Calculate performance metrics
            winners = sum(performance_df['performance_pct'] > 0)
            losers = sum(performance_df['performance_pct'] < 0)
            flat = sum(performance_df['performance_pct'] == 0)

            avg_return = performance_df['performance_pct'].mean()
            positive_returns = (performance_df['performance_pct'] > 0).sum()
            profitable_stocks = (performance_df['performance_pct'] > 0.5).sum()  # Profitable > 0.5%
            total_return = performance_df['performance_pct'].sum()

            win_rate = positive_returns / len(performance_df) * 100 if len(performance_df) > 0 else 0

            print(".1f")
            print(".3f")
            return {
                'stocks_analyzed': len(performance_df),
                'stocks_requested': len(symbols),
                'winners': int(winners),
                'losers': int(losers),
                'flat': int(flat),
                'win_rate': win_rate,
                'avg_return': float(avg_return),
                'profitable_stocks_0.5pct': int(profitable_stocks),
                'total_return': float(total_return),
                'performance_range': [
                    performance_df['performance_pct'].min(),
                    performance_df['performance_pct'].max()
                ],
                'median_performance': performance_df['performance_pct'].median(),
                'best_performer': performance_df.loc[performance_df['performance_pct'].idxmax()]['symbol']
                    if not performance_df.empty else None,
                'worst_performer': performance_df.loc[performance_df['performance_pct'].idxmin()]['symbol']
                    if not performance_df.empty else None
            }

        except Exception as e:
            print(f"❌ Error evaluating date performance: {e}")
            import traceback
            traceback.print_exc()
            return {'stocks_analyzed': 0, 'winners': 0, 'avg_return': 0}

    def _aggregate_backtest_results(self, results: List[Dict[str, Any]],
                                  scanner_name: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Aggregate backtest results across all dates.

        Args:
            results: List of daily results
            scanner_name: Name of scanner
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            Aggregated backtest metrics
        """
        if not results:
            return {'summary': {'total_days': 0, 'win_rate': 0, 'total_return': 0}}

        total_days = len(results)
        successful_days = sum(1 for r in results if r['stock_count'] > 0)
        total_stocks_scanned = sum(r['stock_count'] for r in results)
        total_winners = sum(r['performance']['winners'] for r in results)
        total_stocks_analyzed = sum(r['performance']['stocks_analyzed'] for r in results)

        total_return = sum(r['performance']['total_return'] for r in results
                          if 'total_return' in r['performance'])

        win_rate = total_winners / total_stocks_analyzed * 100 if total_stocks_analyzed > 0 else 0
        avg_return_per_day = total_return / total_days if total_days > 0 else 0
        avg_stocks_per_day = total_stocks_scanned / total_days if total_days > 0 else 0

        summary = {
            'scanner_name': scanner_name,
            'backtest_period': {
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days,
                'trading_days': successful_days,
                'duration_days': (end_date - start_date).days + 1
            },
            'performance_metrics': {
                'total_stocks_scanned': total_stocks_scanned,
                'avg_stocks_per_day': avg_stocks_per_day,
                'total_winners': total_winners,
                'total_losers': total_stocks_analyzed - total_winners,
                'win_rate': win_rate,
                'total_return_pct': total_return,
                'avg_return_per_day_pct': avg_return_per_day,
                'sharpe_ratio': total_return / np.std([r['performance']['total_return']
                                                    for r in results if r['performance'].get('total_return')])
            },
            'scan_consistency': {
                'successful_scan_rate': successful_days / total_days * 100 if total_days > 0 else 0,
                'avg_win_rate_per_day': win_rate / total_days if total_days > 0 else 0,
                'volatility_risk': 'HIGH' if total_stocks_scanned / total_days < 5 else 'MEDIUM'
                                   if total_stocks_scanned / total_days < 10 else 'LOW'
            },
            'detailed_results': results
        }

        return summary

    def _save_backtest_results(self, summary: Dict[str, Any], scanner_name: str,
                             start_date: date, end_date: date):
        """Save backtest results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{scanner_name}_backtest_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{timestamp}.json"

        filepath = self.results_dir / filename

        # Convert to serializable format
        serializable_summary = self._make_json_serializable(summary)

        import json
        with open(filepath, 'w') as f:
            json.dump(serializable_summary, f, indent=2, default=str)

        print(f"📁 Backtest results saved: {filepath}")

    def _make_json_serializable(self, obj):
        """Convert object to JSON serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    def compare_scanners(self, scanners: List[str], start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Compare performance of multiple scanners over the same period.

        Args:
            scanners: List of scanner names to compare
            start_date: Start date for comparison
            end_date: End date for comparison

        Returns:
            Comparison analysis
        """
        print(f"🔬 Comparing {len(scanners)} scanners from {start_date} to {end_date}")

        results = {}
        for scanner in scanners:
            try:
                results[scanner] = self.backtest_scanner(scanner, start_date, end_date)
            except Exception as e:
                print(f"❌ Failed to backtest {scanner}: {e}")
                continue

        # Generate comparison report
        comparison = self._generate_scanner_comparison(results, start_date, end_date)
        return comparison

    def _generate_scanner_comparison(self, results: Dict[str, Any],
                                   start_date: date, end_date: date) -> Dict[str, Any]:
        """Generate detailed comparison between scanners."""
        if not results:
            return {'error': 'No successful backtests'}

        comparison = {
            'comparison_period': {
                'start_date': start_date,
                'end_date': end_date,
                'duration_days': (end_date - start_date).days + 1
            },
            'scanner_comparison': {},
            'best_performers': {}
        }

        # Extract key metrics for each scanner
        for scanner_name, result in results.items():
            metrics = result.get('performance_metrics', {})
            comparison['scanner_comparison'][scanner_name] = {
                'total_stocks_scanned': metrics.get('total_stocks_scanned', 0),
                'win_rate': metrics.get('win_rate', 0),
                'total_return': metrics.get('total_return_pct', 0),
                'avg_stocks_per_day': metrics.get('avg_stocks_per_day', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0)
            }

        # Identify best performers
        if comparison['scanner_comparison']:
            sorted_by_return = sorted(comparison['scanner_comparison'].items(),
                                    key=lambda x: x[1]['total_return'], reverse=True)
            sorted_by_winrate = sorted(comparison['scanner_comparison'].items(),
                                     key=lambda x: x[1]['win_rate'], reverse=True)

            comparison['best_performers'] = {
                'highest_return_scanner': sorted_by_return[0][0] if sorted_by_return else None,
                'highest_winrate_scanner': sorted_by_winrate[0][0] if sorted_by_winrate else None,
                'most_consistent_scanner': max(comparison['scanner_comparison'].items(),
                                             key=lambda x: x[1]['sharpe_ratio'])[0]
                                             if all(x[1]['sharpe_ratio'] for x in comparison['scanner_comparison'].items()) else None
            }

        # Save comparison results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scanner_comparison_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{timestamp}.json"
        filepath = self.results_dir / filename

        import json
        with open(filepath, 'w') as f:
            json.dump(comparison, f, indent=2, default=str)

        print(f"📁 Scanner comparison saved: {filepath}")

        return comparison


def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Scanner Backtester")
    parser.add_argument("--scanner", type=str, required=True,
                       help="Scanner to backtest")
    parser.add_argument("--start-date", type=str, required=True,
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, required=True,
                       help="End date (YYYY-MM-DD)")
    parser.add_argument("--compare", nargs='+', help="Compare multiple scanners")

    args = parser.parse_args()

    # Parse dates
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    backtester = Backtester()

    if args.compare:
        print(f"🔬 Comparing scanners: {args.compare}")
        results = backtester.compare_scanners(args.compare, start_date, end_date)

        print("\n📊 COMPARISON RESULTS:")
        print("="*50)

        for scanner_name, metrics in results.get('scanner_comparison', {}).items():
            print(f"\n{scanner_name.upper()}:")
            print(f"Total Stocks:   {metrics.get('total_stocks_scanned', 0):.0f}")
            print(f"Win Rate:       {metrics.get('win_rate', 0):.1f}%")
            print(f"Total Return:   {metrics.get('total_return', 0):.2f}%")

    else:
        print(f"🔬 Backtesting {args.scanner} from {start_date} to {end_date}")
        results = backtester.backtest_scanner(args.scanner, start_date, end_date)

        # Display key metrics
        perf = results.get('performance_metrics', {})
        print(f"\n📊 BACKTEST RESULTS FOR {args.scanner.upper()}:")
        print("="*50)
        print(f"Total Stocks:   {perf.get('total_stocks_scanned', 0):.0f}")
        print(f"Avg Stocks/Day: {perf.get('avg_stocks_per_day', 0):.1f}")
        print(f"Win Rate:       {perf.get('win_rate', 0):.1f}%")
        print(f"Avg Daily Return: {perf.get('avg_return_per_day_pct', 0):.2f}%")
        print(f"Total Return:     {perf.get('total_return_pct', 0):.2f}%")


if __name__ == "__main__":
    main()
