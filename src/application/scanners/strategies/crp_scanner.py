"""
Enhanced CRP (Close, Range, Pattern) Stock Scanner for intraday trading opportunities.
CRP scanner identifies stocks with specific close-range-pattern characteristics:
- Close near high/low (Close component)
- Small/narrow trading range (Range component)
- Pattern-based analysis with momentum indicators (Pattern component)

Supports date range analysis with comprehensive price tracking from CRP detection to end-of-day.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np
import csv
import os

from ..base_scanner import BaseScanner


class CRPScanner(BaseScanner):
    """
    Enhanced CRP scanner that supports:
    - Date range analysis (multiple trading days)
    - CRP detection at configurable cutoff time (default: 09:50 AM)
    - End-of-day price tracking at configurable time (default: 15:15 PM)
    - Price change calculations from CRP detection to end-of-day
    - Success rate analysis and performance ranking
    - Professional table display with comprehensive CRP metrics
    - CSV export functionality
    """

    @property
    def scanner_name(self) -> str:
        return "enhanced_crp"

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'consolidation_period': 5,        # Days for consolidation check
            'close_threshold_pct': 2.0,       # Max % difference for close near high/low
            'range_threshold_pct': 3.0,       # Max % for narrow range
            'min_volume': 50000,              # Minimum volume for consideration
            'max_volume': 5000000,            # Maximum volume for consideration
            'min_price': 50,                  # Minimum stock price
            'max_price': 2000,                # Maximum stock price
            'max_results_per_day': 3,         # Top 3 stocks per day with highest probability
            'crp_cutoff_time': time(9, 50),   # Default CRP detection time
            'end_of_day_time': time(15, 15)   # Default end-of-day time
        }

    def scan_date_range(self,
                       start_date: date,
                       end_date: date,
                       cutoff_time: Optional[time] = None,
                       end_of_day_time: Optional[time] = None) -> List[Dict[str, Any]]:
        """
        Scan for CRP patterns over a date range and analyze performance throughout the day.

        Args:
            start_date: Start date for scanning
            end_date: End date for scanning
            cutoff_time: Time for CRP detection (default: 09:50)
            end_of_day_time: Time for end-of-day analysis (default: 15:15)

        Returns:
            List of dictionaries with comprehensive CRP analysis
        """
        cutoff_time = cutoff_time or self.config['crp_cutoff_time']
        end_of_day_time = end_of_day_time or self.config['end_of_day_time']

        print(f"🎯 Enhanced CRP Scanner - Date Range: {start_date} to {end_date}")
        print(f"⏰ CRP Detection: {cutoff_time}, End of Day: {end_of_day_time}")
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
                crp_results = self._scan_single_day_crp(scan_date, cutoff_time)

                if crp_results:
                    # Get end-of-day prices for CRP stocks
                    symbols = [result['symbol'] for result in crp_results]
                    eod_prices = self._get_end_of_day_prices(symbols, scan_date, end_of_day_time)

                    # Merge CRP and end-of-day data
                    daily_results = self._merge_crp_and_eod_data(crp_results, eod_prices, scan_date)

                    if daily_results:
                        all_results.extend(daily_results)
                        print(f"   ✅ Found {len(daily_results)} CRP candidates")

            except Exception as e:
                print(f"   ❌ Error scanning {scan_date}: {e}")

        if not all_results:
            print("❌ No CRP patterns found across the date range")
            return []

        # Add performance metrics
        all_results = self._add_performance_metrics(all_results)

        print(f"\n✅ Enhanced CRP Analysis Complete!")
        print(f"📊 Total CRP opportunities: {len(all_results)}")
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
            DataFrame with CRP analysis (limited functionality)
        """
        print(f"⚠️  Single-day scan mode (use scan_date_range() for full functionality)")

        # Get available symbols
        all_symbols = self.get_available_symbols()
        print(f"📊 Analyzing {len(all_symbols)} symbols for CRP patterns...")

        # Enhanced CRP query with probability scoring for backward compatibility
        crp_query = """
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
                AND volume BETWEEN ? AND ?
        ),

        latest_prices AS (
            SELECT * FROM current_data WHERE rn = 1
        ),

        recent_ranges AS (
            SELECT
                symbol,
                AVG(high - low) / NULLIF(AVG((high + low)/2), 0) * 100 as avg_range_pct,
                AVG(volume) as avg_volume
            FROM market_data
            WHERE date_partition < ?
                AND date_partition >= ?
            GROUP BY symbol
        ),

        crp_candidates AS (
            SELECT
                lp.symbol,
                lp.current_price,
                lp.current_high,
                lp.current_low,
                lp.current_volume,
                rr.avg_range_pct,
                rr.avg_volume,
                -- CRP Score Components
                -- 1. Close near high/low (40% weight)
                CASE
                    WHEN ABS(lp.current_price - lp.current_high) / NULLIF(lp.current_high, 0) * 100 <= ?
                        THEN 0.4
                    WHEN ABS(lp.current_price - lp.current_low) / NULLIF(lp.current_low, 0) * 100 <= ?
                        THEN 0.4
                    ELSE 0.1
                END as close_score,
                -- 2. Range tightness (30% weight)
                CASE
                    WHEN (lp.current_high - lp.current_low) / NULLIF(lp.current_price, 0) * 100 <= ?
                        THEN 0.3
                    WHEN (lp.current_high - lp.current_low) / NULLIF(lp.current_price, 0) * 100 <= ? * 1.5
                        THEN 0.2
                    ELSE 0.05
                END as range_score,
                -- 3. Volume pattern (20% weight)
                CASE
                    WHEN lp.current_volume > rr.avg_volume * 1.2 THEN 0.2
                    WHEN lp.current_volume > rr.avg_volume * 0.8 THEN 0.15
                    ELSE 0.05
                END as volume_score,
                -- 4. Price momentum (10% weight)
                CASE
                    WHEN (lp.current_price - lp.open_price) / NULLIF(lp.open_price, 0) > 0.005 THEN 0.1
                    WHEN (lp.current_price - lp.open_price) / NULLIF(lp.open_price, 0) > 0 THEN 0.05
                    ELSE 0.02
                END as momentum_score
            FROM latest_prices lp
            LEFT JOIN recent_ranges rr ON lp.symbol = rr.symbol
            WHERE rr.avg_range_pct IS NOT NULL
                AND rr.avg_volume IS NOT NULL
        ),

        final_crp AS (
            SELECT *,
                (close_score + range_score + volume_score + momentum_score) * 100 as crp_probability_score,
                (current_high - current_low) / NULLIF(current_price, 0) * 100 as current_range_pct,
                CASE
                    WHEN ABS(current_price - current_high) / NULLIF(current_high, 0) * 100 <= ? THEN 'Near High'
                    WHEN ABS(current_price - current_low) / NULLIF(current_low, 0) * 100 <= ? THEN 'Near Low'
                    ELSE 'Mid Range'
                END as close_position
            FROM crp_candidates
            WHERE (close_score + range_score + volume_score + momentum_score) > 0.5
        )

        SELECT *
        FROM final_crp
        WHERE crp_probability_score > 30  -- Minimum CRP probability threshold
        ORDER BY crp_probability_score DESC
        LIMIT ?
        """

        analysis_start = scan_date - timedelta(days=self.config['consolidation_period'])

        params = [
            scan_date,
            cutoff_time,
            self.config['min_price'], self.config['max_price'],
            self.config['min_volume'], self.config['max_volume'],
            scan_date,
            analysis_start,
            self.config['close_threshold_pct'],  # Close threshold
            self.config['close_threshold_pct'],  # Close threshold
            self.config['range_threshold_pct'],  # Range threshold
            self.config['range_threshold_pct'],  # Range threshold
            self.config['close_threshold_pct'],  # Close threshold for position
            self.config['close_threshold_pct'],  # Close threshold for position
            self.config['max_results_per_day']
        ]

        try:
            result = self._execute_query(crp_query, params)

            if result.empty:
                print("⚠️  No stocks showing clear CRP patterns")
                return pd.DataFrame()

            print(f"✅ Found {len(result)} stocks with CRP patterns")
            return result

        except Exception as e:
            print(f"❌ Error in CRP scanning: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _scan_single_day_crp(self, scan_date: date, cutoff_time: time) -> List[Dict[str, Any]]:
        """Scan for CRP patterns on a single day."""
        try:
            # Ensure database connection is established
            connection = self.db_manager.connect()
            cursor = connection.cursor()

            # Enhanced CRP query with probability scoring for top 3 stocks
            query = """
            WITH crp_candidates AS (
                SELECT
                    symbol,
                    close as crp_price,
                    open as open_price,
                    high as current_high,
                    low as current_low,
                    volume as current_volume,
                    (high - low) / NULLIF(close, 0) * 100 as current_range_pct,
                    -- CRP Components Scoring
                    -- Close Position (40% weight)
                    CASE
                        WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= ? THEN 0.4
                        WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= ? THEN 0.4
                        ELSE 0.1
                    END as close_score,
                    -- Range Tightness (30% weight)
                    CASE
                        WHEN (high - low) / NULLIF(close, 0) * 100 <= ? THEN 0.3
                        WHEN (high - low) / NULLIF(close, 0) * 100 <= ? * 1.5 THEN 0.2
                        ELSE 0.05
                    END as range_score,
                    -- Volume Pattern (20% weight)
                    CASE
                        WHEN volume > 75000 THEN 0.2
                        WHEN volume > 50000 THEN 0.15
                        WHEN volume > 25000 THEN 0.1
                        ELSE 0.05
                    END as volume_score,
                    -- Momentum (10% weight)
                    CASE
                        WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.1
                        WHEN (close - open) / NULLIF(open, 0) > 0 THEN 0.05
                        ELSE 0.02
                    END as momentum_score,
                    -- Overall CRP Probability
                    (
                        CASE
                            WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= ? THEN 0.4
                            WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= ? THEN 0.4
                            ELSE 0.1
                        END +
                        CASE
                            WHEN (high - low) / NULLIF(close, 0) * 100 <= ? THEN 0.3
                            WHEN (high - low) / NULLIF(close, 0) * 100 <= ? * 1.5 THEN 0.2
                            ELSE 0.05
                        END +
                        CASE
                            WHEN volume > 75000 THEN 0.2
                            WHEN volume > 50000 THEN 0.15
                            WHEN volume > 25000 THEN 0.1
                            ELSE 0.05
                        END +
                        CASE
                            WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.1
                            WHEN (close - open) / NULLIF(open, 0) > 0 THEN 0.05
                            ELSE 0.02
                        END
                    ) * 100 as crp_probability_score,
                    -- Close Position Classification
                    CASE
                        WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= ? THEN 'Near High'
                        WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= ? THEN 'Near Low'
                        ELSE 'Mid Range'
                    END as close_position
                FROM market_data
                WHERE date_partition = ?
                    AND CAST(timestamp AS TIME) <= ?
                    AND close BETWEEN ? AND ?
                    AND volume BETWEEN ? AND ?
                    AND (high - low) / NULLIF(close, 0) * 100 <= ?  -- Range filter
            )
            SELECT *
            FROM crp_candidates
            WHERE crp_probability_score > 30  -- Minimum CRP probability threshold
            ORDER BY crp_probability_score DESC
            LIMIT ?
            """

            params = [
                self.config['close_threshold_pct'],  # Close threshold
                self.config['close_threshold_pct'],  # Close threshold
                self.config['range_threshold_pct'],  # Range threshold
                self.config['range_threshold_pct'],  # Range threshold
                self.config['close_threshold_pct'],  # Close threshold for probability
                self.config['close_threshold_pct'],  # Close threshold for probability
                self.config['range_threshold_pct'],  # Range threshold for probability
                self.config['range_threshold_pct'],  # Range threshold for probability
                self.config['close_threshold_pct'],  # Close threshold for position
                self.config['close_threshold_pct'],  # Close threshold for position
                scan_date.isoformat(),
                cutoff_time.isoformat(),
                self.config['min_price'],
                self.config['max_price'],
                self.config['min_volume'],
                self.config['max_volume'],
                self.config['range_threshold_pct'] * 2,  # Relaxed range filter
                self.config['max_results_per_day']
            ]

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = {
                    'symbol': row[0],
                    'crp_price': float(row[1]) if row[1] else 0,
                    'open_price': float(row[2]) if row[2] else 0,
                    'current_high': float(row[3]) if row[3] else 0,
                    'current_low': float(row[4]) if row[4] else 0,
                    'current_volume': int(row[5]) if row[5] else 0,
                    'current_range_pct': float(row[6]) if row[6] else 0,
                    'close_score': float(row[7]) if row[7] else 0,
                    'range_score': float(row[8]) if row[8] else 0,
                    'volume_score': float(row[9]) if row[9] else 0,
                    'momentum_score': float(row[10]) if row[10] else 0,
                    'crp_probability_score': float(row[11]) if row[11] else 0,
                    'close_position': row[12] if row[12] else 'Unknown',
                    'scan_date': scan_date,
                    'crp_time': cutoff_time
                }
                results.append(result)

            cursor.close()
            return results

        except Exception as e:
            print(f"❌ Error in single day CRP scan: {e}")
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

    def _merge_crp_and_eod_data(self, crp_data: List[Dict[str, Any]], eod_data: Dict[str, Dict[str, Any]], scan_date: date) -> List[Dict[str, Any]]:
        """Merge CRP and end-of-day data."""
        merged_results = []

        for crp in crp_data:
            symbol = crp['symbol']
            eod_info = eod_data.get(symbol, {})

            merged = crp.copy()

            # Add end-of-day data
            merged.update({
                'eod_price': eod_info.get('eod_price', 0),
                'eod_high': eod_info.get('eod_high', 0),
                'eod_low': eod_info.get('eod_low', 0),
                'eod_volume': eod_info.get('eod_volume', 0),
            })

            # Calculate price changes and performance metrics
            crp_price = merged['crp_price']
            eod_price = merged['eod_price']

            if crp_price > 0 and eod_price > 0:
                price_change_pct = ((eod_price - crp_price) / crp_price) * 100
                merged['price_change_pct'] = round(price_change_pct, 2)
                merged['crp_successful'] = price_change_pct > 0
            else:
                merged['price_change_pct'] = 0
                merged['crp_successful'] = False

            # Calculate day range
            day_high = max(merged['current_high'], merged['eod_high'])
            day_low = min(merged['current_low'], merged['eod_low'])

            if crp_price > 0:
                day_range_pct = ((day_high - day_low) / crp_price) * 100
                merged['day_range_pct'] = round(day_range_pct, 2)
            else:
                merged['day_range_pct'] = 0

            # Calculate enhanced performance rank incorporating CRP probability score
            probability_weight = merged.get('crp_probability_score', 0) / 100.0  # Convert to 0-1 scale
            crp_score = merged['close_score'] + merged['range_score'] + merged['volume_score'] + merged['momentum_score']
            performance_score = merged['price_change_pct'] if merged['crp_successful'] else 0
            merged['performance_rank'] = round(probability_weight * 0.5 + crp_score * 0.3 + performance_score * 0.2, 2)

            merged_results.append(merged)

        return merged_results

    def _add_performance_metrics(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add performance metrics to the results."""
        if not results:
            return results

        # Calculate overall success rate
        successful_crps = sum(1 for r in results if r.get('crp_successful', False))
        total_crps = len(results)
        success_rate = (successful_crps / total_crps * 100) if total_crps > 0 else 0

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

    def display_results_table(self, results: List[Dict[str, Any]], title: str = "Enhanced CRP Scanner Results"):
        """Display results in a comprehensive table format."""
        if not results:
            print("⚠️  No results to display")
            return

        print(f"\n🎯 {title}")
        print("=" * 100)

        # Print table with better formatting (updated for top 3 stocks)
        print("┌" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 10 + "┬" + "─" * 12 + "┬" + "─" * 10 + "┬" + "─" * 10 + "┬" + "─" * 8 + "┬" + "─" * 6 + "┬" + "─" * 12 + "┐")
        print("│ {:<8} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<8} │ {:<8} │ {:<6} │ {:<4} │ {:<10} │".format(
            "Symbol", "Date", "CRP", "EOD", "Price", "Close", "Current", "Prob", "Rank", "Perform"))
        print("│ {:<8} │ {:<8} │ {:<10} │ {:<8} │ {:<10} │ {:<8} │ {:<8} │ {:<6} │ {:<4} │ {:<10} │".format(
            "", "", "Price", "Price", "Change", "Pos", "Range%", "Score", "", "Rank"))
        print("├" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 12 + "┼" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 8 + "┼" + "─" * 6 + "┼" + "─" * 12 + "┤")

        # Print data rows (show top 15, but typically only top 3 per day)
        for result in results[:15]:
            symbol = result.get('symbol', 'N/A')[:8]  # Truncate long symbols
            date_str = result.get('scan_date', '').strftime('%Y-%m-%d') if result.get('scan_date') else 'N/A'
            crp_price = result.get('crp_price', 0)
            eod_price = result.get('eod_price', 0)
            price_change = result.get('price_change_pct', 0)
            close_position = result.get('close_position', 'N/A')[:8]  # Truncate position
            current_range_pct = result.get('current_range_pct', 0)
            crp_probability_score = result.get('crp_probability_score', 0)
            performance_rank = result.get('performance_rank', 0)

            print("│ {:<8} │ {:<8} │ ₹{:>8.2f} │ ₹{:>6.2f} │ {:>+8.2f}% │ {:<8} │ {:>6.2f}% │ {:>5.1f}% │ {:>4.2f} │ {:>8.2f} │".format(
                symbol, date_str, crp_price, eod_price, price_change,
                close_position, current_range_pct, crp_probability_score, performance_rank, performance_rank))

        print("└" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 10 + "┴" + "─" * 12 + "┴" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 8 + "┴" + "─" * 6 + "┴" + "─" * 12 + "┘")

        print()

        # Display summary statistics
        if results:
            successful_count = sum(1 for r in results if r.get('crp_successful', False))
            total_count = len(results)
            success_rate = (successful_count / total_count * 100) if total_count > 0 else 0
            avg_change = sum(r.get('price_change_pct', 0) for r in results) / len(results) if results else 0

            print("📈 Summary Statistics (Top 3 Stocks Per Day):")
            print(f"   Total CRP Patterns: {total_count}")
            print(f"   Successful CRP Patterns: {successful_count}")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Average Price Change: {avg_change:.2f}%")
            print(f"   Average CRP Probability Score: {sum(r.get('crp_probability_score', 0) for r in results) / len(results) if results else 0:.1f}%")

    def export_results(self, results: List[Dict[str, Any]], filename: str = "enhanced_crp_results.csv"):
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
