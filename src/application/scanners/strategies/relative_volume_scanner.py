"""
Relative Volume Scanner for intraday stock selection.
Identifies stocks with unusual volume levels by 09:50 AM.
"""

from typing import Dict, Any, List
from datetime import datetime, date, time, timedelta
import pandas as pd

from ..base_scanner import BaseScanner


class RelativeVolumeScanner(BaseScanner):
    """Scanner that identifies stocks with high relative volume by 9:50 AM."""

    @property
    def scanner_name(self) -> str:
        return "relative_volume"

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'min_relative_volume': 5.0,  # Minimum 5x relative volume
            'min_avg_volume': 100000,    # Minimum average daily volume
            'lookback_days': 14,         # Days to look back for averages
            'min_sample_days': 5,        # Minimum days of historical data
            'price_change_min': -2.0,    # Minimum price change
            'price_change_max': 2.0,     # Maximum price change
            'max_results': 50            # Maximum results to return
        }

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Scan for stocks with high relative volume by specified cutoff time.

        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for volume calculation

        Returns:
            DataFrame with stocks meeting criteria
        """
        print(f"🔍 Scanning for relative volume >= {self.config['min_relative_volume']}x by {cutoff_time}")

        # Calculate date range for historical average
        end_date = scan_date - timedelta(days=1)  # Previous day
        start_date = end_date - timedelta(days=self.config['lookback_days'] + 5)  # Buffer

        # Build SQL query for relative volume analysis
        relative_volume_query = f"""
        WITH historical_volume AS (
            -- Calculate average volume by time for historical period
            SELECT
                symbol,
                strftime('%H:%M', timestamp) as time_slot,
                AVG(volume) as avg_volume_at_time,
                COUNT(*) as sample_days
            FROM market_data
            WHERE date_partition BETWEEN ? AND ?
                AND strftime('%H:%M', timestamp) <= ?
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol, time_slot
            HAVING COUNT(*) >= ?
        ),

        historical_daily_avg AS (
            -- Calculate average daily volume for filtering
            SELECT
                symbol,
                AVG(daily_volume) as avg_daily_volume
            FROM (
                SELECT
                    symbol,
                    date_partition,
                    SUM(volume) as daily_volume
                FROM market_data
                WHERE date_partition BETWEEN ? AND ?
                GROUP BY symbol, date_partition
            ) daily_totals
            GROUP BY symbol
            HAVING AVG(daily_volume) >= ?  -- Minimum average volume filter
        ),

        current_day_volume AS (
            -- Calculate cumulative volume for scan date up to cutoff time
            SELECT
                symbol,
                SUM(volume) as current_volume,
                COUNT(*) as current_ticks,
                MIN(timestamp) as first_tick,
                MAX(timestamp) as last_tick,
                AVG(close) as avg_price,
                MAX(high) as day_high,
                MIN(low) as day_low,
                (SELECT close FROM market_data m2
                 WHERE m2.symbol = m1.symbol
                   AND m2.date_partition = ?
                   AND m2.timestamp = MIN(m1.timestamp)) as open_price,
                (SELECT close FROM market_data m2
                 WHERE m2.symbol = m1.symbol
                   AND m2.date_partition = ?
                   AND m2.timestamp = MAX(m1.timestamp)) as current_price
            FROM market_data m1
            WHERE date_partition = ?
                AND strftime('%H:%M', timestamp) <= ?
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
        ),

        expected_volume AS (
            -- Calculate expected volume based on historical average
            SELECT
                h.symbol,
                SUM(h.avg_volume_at_time) as expected_volume_by_cutoff,
                COUNT(*) as time_slots_covered
            FROM historical_volume h
            WHERE h.time_slot <= ?
            GROUP BY h.symbol
        )

        SELECT
            c.symbol,
            c.current_volume,
            e.expected_volume_by_cutoff,
            ROUND(c.current_volume / NULLIF(e.expected_volume_by_cutoff, 0), 2) as relative_volume,
            h.avg_daily_volume,
            c.current_ticks,
            c.open_price,
            c.current_price,
            c.day_high,
            c.day_low,
            ROUND(((c.current_price - c.open_price) / c.open_price) * 100, 2) as price_change_pct,
            ROUND(((c.day_high - c.day_low) / c.open_price) * 100, 2) as intraday_range_pct,
            c.first_tick,
            c.last_tick,
            e.time_slots_covered
        FROM current_day_volume c
        JOIN expected_volume e ON c.symbol = e.symbol
        JOIN historical_daily_avg h ON c.symbol = h.symbol
        WHERE c.current_volume / NULLIF(e.expected_volume_by_cutoff, 0) >= ?
            AND e.expected_volume_by_cutoff > 0
            AND c.current_ticks >= 10  -- Minimum ticks for reliability
            AND ABS((c.current_price - c.open_price) / c.open_price * 100) BETWEEN ? AND ?
        ORDER BY relative_volume DESC
        LIMIT ?
        """

        # Parameters for the query
        min_sample_days = max(5, self.config['lookback_days'] // 3)

        params = [
            start_date, end_date, cutoff_time.strftime('%H:%M'), min_sample_days,  # historical_volume
            start_date, end_date, self.config['min_avg_volume'],  # historical_daily_avg
            scan_date, scan_date, scan_date, cutoff_time.strftime('%H:%M'),  # current_day_volume
            cutoff_time.strftime('%H:%M'),  # expected_volume
            self.config['min_relative_volume'],  # relative volume filter
            self.config['price_change_min'], self.config['price_change_max'],  # price change filter
            self.config['max_results']  # limit
        ]

        try:
            result = self._execute_query(relative_volume_query, params)

            if result.empty:
                print(f"⚠️  No stocks found with relative volume >= {self.config['min_relative_volume']}x")
                return pd.DataFrame()

            # Add additional calculated fields
            result['volume_ratio_text'] = result['relative_volume'].apply(
                lambda x: f"{x:.1f}x" if pd.notna(x) else "N/A"
            )

            result['momentum_signal'] = result.apply(
                lambda row: self._classify_momentum(
                    row['price_change_pct'],
                    row.get('intraday_range_pct', 0)
                ), axis=1
            )

            print(f"✅ Found {len(result)} stocks meeting criteria")
            return result

        except Exception as e:
            print(f"❌ Error in relative volume scanning: {e}")
            return pd.DataFrame()

    def _classify_momentum(self, price_change: float, intraday_range: float) -> str:
        """Classify momentum based on price change and range."""
        if pd.isna(price_change) or pd.isna(intraday_range):
            return "NEUTRAL"

        if abs(price_change) >= 1.5 and intraday_range >= 2.0:
            return "HIGH_MOMENTUM"
        elif abs(price_change) >= 1.0 and intraday_range >= 1.5:
            return "MODERATE_MOMENTUM"
        elif abs(price_change) >= 0.5:
            return "LOW_MOMENTUM"
        else:
            return "NEUTRAL"
