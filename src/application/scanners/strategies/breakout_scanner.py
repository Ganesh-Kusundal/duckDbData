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
        Backward compatibility method - scans single day and returns DataFrame.
        For enhanced functionality, use scan_date_range() instead.

        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning

        Returns:
            DataFrame with breakout analysis (limited functionality)
        """
        print(f"⚠️  Single-day scan mode (use scan_date_range() for full functionality)")

        # Get available symbols
        all_symbols = self.get_available_symbols()
        print(f"📊 Analyzing {len(all_symbols)} symbols for breakout patterns...")

        # Enhanced breakout query with probability scoring for backward compatibility
        breakout_query = """
        WITH current_data AS (
            SELECT
                symbol,
                close as current_price,
                open as open_price,
                high as current_high,
                low as current_low,
                volume as current_volume,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) as rn
            FROM market_data
            WHERE date_partition = ?
                AND CAST(timestamp AS TIME) <= ?
                AND close BETWEEN ? AND ?
        ),

        latest_prices AS (
            SELECT * FROM current_data WHERE rn = 1
        ),

        recent_highs AS (
            SELECT
                symbol,
                MAX(high) as recent_high,
                AVG(volume) as avg_volume
            FROM market_data
            WHERE date_partition < ?
                AND date_partition >= ?
            GROUP BY symbol
        ),

        breakout_candidates AS (
            SELECT
                lp.symbol,
                lp.current_price,
                lp.current_high,
                lp.current_low,
                lp.current_volume,
                rh.recent_high,
                rh.avg_volume,
                ROUND(((lp.current_high - rh.recent_high) / NULLIF(rh.recent_high, 0)) * 100, 2) as breakout_pct,
                ROUND(lp.current_volume / NULLIF(rh.avg_volume, 0), 2) as volume_ratio,
                -- Calculate probability score (same logic as enhanced scanner)
                (
                    -- Breakout strength (50% weight)
                    CASE WHEN ((lp.current_high - rh.recent_high) / NULLIF(rh.recent_high, 0) * 100) > 2.0 THEN 0.5
                         WHEN ((lp.current_high - rh.recent_high) / NULLIF(rh.recent_high, 0) * 100) > 1.0 THEN 0.3
                         WHEN ((lp.current_high - rh.recent_high) / NULLIF(rh.recent_high, 0) * 100) > 0.5 THEN 0.2
                         ELSE 0.1 END +
                    -- Volume confirmation (30% weight)
                    CASE WHEN lp.current_volume > 50000 THEN 0.3
                         WHEN lp.current_volume > 20000 THEN 0.2
                         WHEN lp.current_volume > 10000 THEN 0.1
                         ELSE 0.05 END +
                    -- Price momentum (20% weight)
                    CASE WHEN (lp.current_price - lp.open_price) / NULLIF(lp.open_price, 0) > 0.01 THEN 0.2 ELSE 0 END
                ) * 100 as probability_score
            FROM latest_prices lp
            LEFT JOIN recent_highs rh ON lp.symbol = rh.symbol
            WHERE lp.current_high > rh.recent_high * (1.0 + ?/100.0)
                AND lp.current_volume > rh.avg_volume * ?
                AND rh.recent_high IS NOT NULL
                AND rh.avg_volume IS NOT NULL
        )

        SELECT *
        FROM breakout_candidates
        WHERE probability_score > 10  -- Minimum probability threshold
        ORDER BY probability_score DESC
        LIMIT ?
        """

        analysis_start = scan_date - timedelta(days=self.config['consolidation_period'])

        params = [
            scan_date,
            cutoff_time,
            self.config['min_price'], self.config['max_price'],
            scan_date,
            analysis_start,
            self.config['resistance_break_pct'],
            self.config['breakout_volume_ratio'],
            self.config['max_results_per_day']
        ]

        try:
            result = self._execute_query(breakout_query, params)

            if result.empty:
                print("⚠️  No stocks showing clear breakout patterns")
                return pd.DataFrame()

            print(f"✅ Found {len(result)} stocks with breakout patterns")
            return result

        except Exception as e:
            print(f"❌ Error in breakout scanning: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _scan_single_day_breakouts(self, scan_date: date, cutoff_time: time) -> List[Dict[str, Any]]:
        """Scan for breakout patterns on a single day."""
        try:
            # Ensure database connection is established
            connection = self.db_manager.connect()
            cursor = connection.cursor()

            # Enhanced breakout query with probability scoring for top 3 stocks
            query = """
            WITH breakout_candidates AS (
                SELECT
                    symbol,
                    close as breakout_price,
                    open as open_price,
                    high as current_high,
                    low as current_low,
                    volume as current_volume,
                    high - close as breakout_above_resistance,
                    (high - close) / NULLIF(close, 0) * 100 as breakout_pct,
                    volume / NULLIF(AVG(volume) OVER (PARTITION BY symbol ORDER BY date_partition ROWS 4 PRECEDING), 0) as volume_ratio,
                    -- Calculate probability score (weighted combination of breakout strength and volume confirmation)
                    (
                        -- Breakout strength (50% weight) - normalized breakout percentage
                        CASE WHEN ((high - close) / NULLIF(close, 0) * 100) > 2.0 THEN 0.5
                             WHEN ((high - close) / NULLIF(close, 0) * 100) > 1.0 THEN 0.3
                             WHEN ((high - close) / NULLIF(close, 0) * 100) > 0.5 THEN 0.2
                             ELSE 0.1 END +
                        -- Volume confirmation (30% weight) - simple volume multiplier
                        CASE WHEN volume > 50000 THEN 0.3
                             WHEN volume > 20000 THEN 0.2
                             WHEN volume > 10000 THEN 0.1
                             ELSE 0.05 END +
                        -- Price momentum (20% weight)
                        CASE WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.2 ELSE 0 END
                    ) * 100 as probability_score
                FROM market_data
                WHERE date_partition = ?
                    AND CAST(timestamp AS TIME) <= ?
                    AND close BETWEEN ? AND ?
                    AND high > close * 1.005  -- At least 0.5% breakout
                    AND volume > 10000  -- Minimum volume
            )
            SELECT *
            FROM breakout_candidates
            WHERE probability_score > 10  -- Minimum probability threshold
            ORDER BY probability_score DESC
            LIMIT ?
            """

            params = [
                scan_date.isoformat(),
                cutoff_time.isoformat(),
                self.config['min_price'],
                self.config['max_price'],
                self.config['max_results_per_day']
            ]

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = {
                    'symbol': row[0],
                    'breakout_price': float(row[1]) if row[1] else 0,
                    'open_price': float(row[2]) if row[2] else 0,
                    'current_high': float(row[3]) if row[3] else 0,
                    'current_low': float(row[4]) if row[4] else 0,
                    'current_volume': int(row[5]) if row[5] else 0,
                    'breakout_above_resistance': float(row[6]) if row[6] else 0,
                    'breakout_pct': float(row[7]) if row[7] else 0,
                    'volume_ratio': float(row[8]) if row[8] else 0,
                    'probability_score': float(row[9]) if row[9] else 0,
                    'scan_date': scan_date,
                    'breakout_time': cutoff_time
                }
                results.append(result)

            cursor.close()
            return results

        except Exception as e:
            print(f"❌ Error in single day scan: {e}")
            return []

    def _get_end_of_day_prices(self, symbols: List[str], scan_date: date, end_time: time) -> Dict[str, Dict[str, Any]]:
        """Get end-of-day prices for the given symbols."""
        if not symbols:
            return {}

        try:
            # Ensure database connection is established
            connection = self.db_manager.connect()
            cursor = connection.cursor()

            # Create placeholders for IN clause
            placeholders = ','.join(['?' for _ in symbols])

            query = f"""
            SELECT
                symbol,
                close as eod_price,
                high as eod_high,
                low as eod_low,
                volume as eod_volume
            FROM market_data
            WHERE date_partition = ?
                AND symbol IN ({placeholders})
                AND CAST(timestamp AS TIME) <= ?
            ORDER BY symbol, timestamp DESC
            """

            params = [scan_date.isoformat()] + symbols + [end_time.isoformat()]

            cursor.execute(query, params)
            rows = cursor.fetchall()

            eod_data = {}
            for row in rows:
                symbol = row[0]
                if symbol not in eod_data:  # Take the most recent entry for each symbol
                    eod_data[symbol] = {
                        'eod_price': float(row[1]) if row[1] else 0,
                        'eod_high': float(row[2]) if row[2] else 0,
                        'eod_low': float(row[3]) if row[3] else 0,
                        'eod_volume': int(row[4]) if row[4] else 0
                    }

            cursor.close()
            return eod_data

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
