"""
Enhanced Breakout Stock Scanner for intraday trading opportunities.
Supports date range analysis with comprehensive price tracking from breakout detection to end-of-day.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np
import csv
import os

from ..base_scanner import BaseScanner
from ...interfaces.base_scanner_interface import IBaseScanner
from ...ports.scanner_read_port import ScannerReadPort


class BreakoutScanner(BaseScanner):
    """
    Enhanced breakout scanner that supports:
    - Date range analysis (multiple trading days)
    - Breakout detection at configurable cutoff time (default: 09:50 AM)
    - End-of-day price tracking at configurable time (default: 15:15 PM)
    - Price change calculations from breakout to end-of-day
    - Success rate analysis and performance ranking
    - Professional table display with comprehensive metrics
    - CSV export functionality
    """

    def __init__(self, *args, scanner_read_port: ScannerReadPort = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Require explicit injection to avoid infra dependency in strategies
        self.scanner_read = scanner_read_port

    @property
    def scanner_name(self) -> str:
        return "enhanced_breakout"

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'consolidation_period': 5,        # Days for consolidation check
            'breakout_volume_ratio': 1.5,     # Volume ratio for breakout confirmation
            'resistance_break_pct': 0.5,      # Break above resistance by %
            'min_price': 50,                  # Minimum stock price
            'max_price': 2000,                # Maximum stock price
            'max_results_per_day': 3,         # Top 3 stocks per day with highest probability
            'breakout_cutoff_time': time(9, 50),  # Default breakout detection time
            'end_of_day_time': time(15, 15)       # Default end-of-day time
        }

    def scan_date_range(self,
                       start_date: date,
                       end_date: date,
                       cutoff_time: Optional[time] = None,
                       end_of_day_time: Optional[time] = None) -> List[Dict[str, Any]]:
        """
        Scan for breakout patterns over a date range and analyze performance throughout the day.

        Args:
            start_date: Start date for scanning
            end_date: End date for scanning
            cutoff_time: Time for breakout detection (default: 09:50)
            end_of_day_time: Time for end-of-day analysis (default: 15:15)

        Returns:
            List of dictionaries with comprehensive breakout analysis
        """
        cutoff_time = cutoff_time or self.config['breakout_cutoff_time']
        end_of_day_time = end_of_day_time or self.config['end_of_day_time']

        print(f"🚀 Enhanced Breakout Scanner - Date Range: {start_date} to {end_date}")
        print(f"⏰ Breakout Detection: {cutoff_time}, End of Day: {end_of_day_time}")
        print(f"🎯 Selecting Top {self.config['max_results_per_day']} Stocks Per Day with Highest Probability")

        # Generate list of trading days in range
        trading_days = self._get_trading_days(start_date, end_date)

        if not trading_days:
            print("⚠️  No trading days found in the specified date range")
            return []

        print(f"📅 Found {len(trading_days)} trading days to analyze")

        all_results = []

        for scan_date in trading_days:
            try:
                print(f"📊 Scanning {scan_date}...")
                breakout_results = self._scan_single_day_breakouts(scan_date, cutoff_time)

                if breakout_results:
                    # Get end-of-day prices for breakout stocks
                    symbols = [result['symbol'] for result in breakout_results]
                    eod_prices = self._get_end_of_day_prices(symbols, scan_date, end_of_day_time)

                    # Merge breakout and end-of-day data
                    daily_results = self._merge_breakout_and_eod_data(breakout_results, eod_prices, scan_date)

                    if daily_results:
                        all_results.extend(daily_results)
                        print(f"   ✅ Found {len(daily_results)} breakout candidates")

            except Exception as e:
                print(f"   ❌ Error scanning {scan_date}: {e}")

        if not all_results:
            print("❌ No breakout patterns found across the date range")
            return []

        # Add performance metrics
        all_results = self._add_performance_metrics(all_results)

        print(f"\n✅ Enhanced Breakout Analysis Complete!")
        print(f"📊 Total breakout opportunities: {len(all_results)}")
        print(f"📅 Trading days analyzed: {len(trading_days)}")

        return all_results

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Backward compatibility: single-day scan returning a DataFrame.
        Uses ScannerReadPort-backed single-day scan under the hood.
        """
        print("⚠️  Single-day scan mode (use scan_date_range() for full functionality)")
        try:
            records = self._scan_single_day_breakouts(scan_date, cutoff_time)
            if not records:
                print("⚠️  No stocks showing clear breakout patterns")
                return pd.DataFrame()
            return pd.DataFrame.from_records(records)
        except Exception as e:
            print(f"❌ Error in breakout scanning: {e}")
            return pd.DataFrame()

    def _scan_single_day_breakouts(self, scan_date: date, cutoff_time: time) -> List[Dict[str, Any]]:
        """Scan for breakout patterns on a single day."""
        try:
            if not getattr(self, 'scanner_read', None):
                raise RuntimeError("ScannerRead port is not available")
            results = self.scanner_read.get_breakout_candidates(
                scan_date=scan_date,
                cutoff_time=cutoff_time,
                config=self.config,
                max_results=self.config.get('max_results_per_day', 3),
            )
            for r in results:
                r['scan_date'] = scan_date
                r['breakout_time'] = cutoff_time
            return results
        except Exception as e:
            print(f"❌ Error in single day scan: {e}")
            return []

    def _get_end_of_day_prices(self, symbols: List[str], scan_date: date, end_time: time) -> Dict[str, Dict[str, Any]]:
        """Get end-of-day prices for the given symbols using optimized batch query."""
        if not symbols:
            return {}

        try:
            if not getattr(self, 'scanner_read', None):
                raise RuntimeError("ScannerRead port is not available")
            return self.scanner_read.get_end_of_day_prices(symbols, scan_date, end_time)
        except Exception as e:
            print(f"❌ Error getting end-of-day prices: {e}")
            return {}

    def _merge_breakout_and_eod_data(self, breakout_data: List[Dict[str, Any]], eod_data: Dict[str, Dict[str, Any]], scan_date: date) -> List[Dict[str, Any]]:
        """Merge breakout and end-of-day data."""
        merged_results = []

        for breakout in breakout_data:
            symbol = breakout['symbol']
            eod_info = eod_data.get(symbol, {})

            merged = breakout.copy()

            # Add end-of-day data
            merged.update({
                'eod_price': eod_info.get('eod_price', 0),
                'eod_high': eod_info.get('eod_high', 0),
                'eod_low': eod_info.get('eod_low', 0),
                'eod_volume': eod_info.get('eod_volume', 0),
            })

            # Calculate price changes and performance metrics
            breakout_price = merged['breakout_price']
            eod_price = merged['eod_price']

            if breakout_price > 0 and eod_price > 0:
                price_change_pct = ((eod_price - breakout_price) / breakout_price) * 100
                merged['price_change_pct'] = round(price_change_pct, 2)
                merged['breakout_successful'] = price_change_pct > 0
            else:
                merged['price_change_pct'] = 0
                merged['breakout_successful'] = False

            # Calculate day range
            day_high = max(merged['current_high'], merged['eod_high'])
            day_low = min(merged['current_low'], merged['eod_low'])

            if breakout_price > 0:
                day_range_pct = ((day_high - day_low) / breakout_price) * 100
                merged['day_range_pct'] = round(day_range_pct, 2)
            else:
                merged['day_range_pct'] = 0

            # Calculate enhanced performance rank incorporating probability score
            probability_weight = merged.get('probability_score', 0) / 100.0  # Convert to 0-1 scale
            breakout_score = merged['breakout_pct'] * 0.3 + merged['volume_ratio'] * 0.2
            performance_score = merged['price_change_pct'] if merged['breakout_successful'] else 0
            merged['performance_rank'] = round(probability_weight * 0.5 + breakout_score * 0.3 + performance_score * 0.2, 2)

            merged_results.append(merged)

        return merged_results

    def _add_performance_metrics(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add performance metrics to the results."""
        if not results:
            return results

        # Calculate overall success rate
        successful_breakouts = sum(1 for r in results if r.get('breakout_successful', False))
        total_breakouts = len(results)
        success_rate = (successful_breakouts / total_breakouts * 100) if total_breakouts > 0 else 0

        # Add success rate to each result
        for result in results:
            result['overall_success_rate'] = round(success_rate, 2)

        # Sort by performance rank
        results.sort(key=lambda x: x.get('performance_rank', 0), reverse=True)

        return results

    def _get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Get list of trading days in the date range."""
        trading_days = []
        current_date = start_date

        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday=0, Tuesday=1, ..., Friday=4
                trading_days.append(current_date)
            current_date += timedelta(days=1)

        return trading_days

    def display_results_table(self, results: List[Dict[str, Any]], title: str = "Enhanced Breakout Scanner Results"):
        """Display results in a comprehensive table format."""
        if not results:
            print("⚠️  No results to display")
            return

        print(f"\n📊 {title}")
        print("=" * 80)

        # Print table with better formatting (updated for top 3 stocks)
        print("┌" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 8 + "┬" + "─" * 6 + "┬" + "─" * 10 + "┬" + "─" * 6 + "┬" + "─" * 12 + "┐")
        print("│ {:<8} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<6} │ {:<4} │ {:<8} │ {:<4} │ {:<10} │".format(
            "Symbol", "Date", "Breakout", "EOD", "Price", "Breakout", "Volume", "Prob", "Rank", "Day", "Succ", "Perform"))
        print("│ {:<8} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<6} │ {:<4} │ {:<8} │ {:<4} │ {:<10} │".format(
            "", "", "Price", "Price", "Change", "%", "Ratio", "Score", "", "Range%", "", "Rank"))
        print("├" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 8 + "┼" + "─" * 6 + "┼" + "─" * 10 + "┼" + "─" * 6 + "┼" + "─" * 12 + "┤")

        # Print data rows (show top 15, but typically only top 3 per day)
        for result in results[:15]:
            symbol = result.get('symbol', 'N/A')[:8]  # Truncate long symbols
            date_str = result.get('scan_date', '').strftime('%Y-%m-%d') if result.get('scan_date') else 'N/A'
            breakout_price = result.get('breakout_price', 0)
            eod_price = result.get('eod_price', 0)
            price_change = result.get('price_change_pct', 0)
            breakout_pct = result.get('breakout_pct', 0)
            volume_ratio = result.get('volume_ratio', 0)
            probability_score = result.get('probability_score', 0)
            performance_rank = result.get('performance_rank', 0)
            day_range_pct = result.get('day_range_pct', 0)
            success = "✅" if result.get('breakout_successful', False) else "❌"

            print("│ {:<8} │ {:<8} │ ₹{:>8.2f} │ ₹{:>6.2f} │ {:>+8.2f}% │ {:>6.2f}% │ {:>8.1f}x │ {:>5.1f}% │ {:>4.2f} │ {:>6.2f}% │ {:<4} │ {:>8.2f} │".format(
                symbol, date_str, breakout_price, eod_price, price_change,
                breakout_pct, volume_ratio, probability_score, performance_rank, day_range_pct, success, performance_rank))

        print("└" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 8 + "┴" + "─" * 6 + "┴" + "─" * 10 + "┴" + "─" * 6 + "┴" + "─" * 12 + "┘")

        print()

        # Display summary statistics
        if results:
            successful_count = sum(1 for r in results if r.get('breakout_successful', False))
            total_count = len(results)
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
            avg_change = sum(r.get('price_change_pct', 0) for r in results) / len(results) if results else 0

            print("📈 Summary Statistics (Top 3 Stocks Per Day):")
            print(f"   Total Breakouts: {total_count}")
            print(f"   Successful Breakouts: {successful_count}")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Average Price Change: {avg_change:.2f}%")
            print(f"   Average Probability Score: {sum(r.get('probability_score', 0) for r in results) / len(results) if results else 0:.1f}%")

    def export_results(self, results: List[Dict[str, Any]], filename: str = "enhanced_breakout_results.csv"):
        """Export results to CSV file."""
        if not results:
            print("⚠️  No results to export")
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if results:
                    fieldnames = results[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(results)

            print(f"💾 Results exported to {filename}")
            print(f"📊 Exported {len(results)} records")

        except Exception as e:
            print(f"❌ Failed to export results: {e}")
