"""
Simple Breakout Stock Scanner for intraday trading.
Uses basic technical analysis to identify breakout patterns.
"""

from typing import Dict, Any, List
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np

from ..base_scanner import BaseScanner


class SimpleBreakoutScanner(BaseScanner):
    """
    Simple breakout scanner that identifies stocks with:
    - Recent price consolidation
    - Breakout above recent highs
    - Volume confirmation
    - Momentum indicators
    """

    @property
    def scanner_name(self) -> str:
        return "simple_breakout"

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'lookback_period': 5,             # Days to analyze for consolidation
            'breakout_threshold': 1.5,        # Break above recent high by %
            'volume_multiplier': 1.5,         # Volume must be X times average
            'min_price': 50,                  # Minimum stock price
            'max_price': 2000,                # Maximum stock price
            'max_results': 20                 # Maximum results to return
        }

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Scan for stocks showing simple breakout patterns.

        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning

        Returns:
            DataFrame with breakout analysis
        """
        print(f"🚀 Scanning for simple breakout patterns by {cutoff_time}")

        # Get available symbols
        all_symbols = self.get_available_symbols()
        print(f"📊 Analyzing {len(all_symbols)} symbols for simple breakouts...")

        # Simple breakout query
        breakout_query = """
        WITH current_data AS (
            -- Get latest data for each symbol up to cutoff time
            SELECT
                symbol,
                close as current_price,
                high as current_high,
                low as current_low,
                volume as current_volume,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) as rn
            FROM market_data_unified
            WHERE date_partition = ?
                AND timestamp <= ?
                AND close BETWEEN ? AND ?
        ),

        latest_prices AS (
            SELECT * FROM current_data WHERE rn = 1
        ),

        historical_data AS (
            -- Get historical data for analysis
            SELECT
                symbol,
                date_partition,
                high,
                low,
                close,
                volume
            FROM market_data_unified
            WHERE date_partition BETWEEN ? AND ?
                AND symbol IN (SELECT symbol FROM latest_prices)
        ),

        recent_highs AS (
            -- Calculate recent price highs
            SELECT
                symbol,
                MAX(high) as recent_high,
                MIN(low) as recent_low,
                AVG(volume) as avg_volume
            FROM historical_data
            WHERE date_partition >= ?
            GROUP BY symbol
        ),

        price_range AS (
            -- Calculate price consolidation range
            SELECT
                symbol,
                (MAX(high) - MIN(low)) / AVG(close) * 100 as price_range_pct
            FROM historical_data
            WHERE date_partition >= ?
            GROUP BY symbol
        )

        SELECT
            lp.symbol,
            lp.current_price,
            lp.current_high,
            lp.current_low,
            lp.current_volume,

            -- Recent levels
            rh.recent_high,
            rh.recent_low,
            rh.avg_volume,

            -- Price range (consolidation)
            pr.price_range_pct,

            -- Breakout calculations
            ROUND(((lp.current_high - rh.recent_high) / NULLIF(rh.recent_high, 0)) * 100, 2) as breakout_pct,
            ROUND(lp.current_volume / NULLIF(rh.avg_volume, 0), 2) as volume_ratio,

            -- Simple breakout score
            CASE
                WHEN lp.current_high > rh.recent_high * (1 + ?/100)  -- Breakout above threshold
                     AND lp.current_volume > rh.avg_volume * ?        -- Volume confirmation
                     AND pr.price_range_pct <= 5.0                    -- Consolidation (tight range)
                THEN
                    ROUND(
                        (((lp.current_high - rh.recent_high) / NULLIF(rh.recent_high, 0)) * 100 * 0.4) +
                        (lp.current_volume / NULLIF(rh.avg_volume, 0) * 0.3) +
                        ((5.0 - pr.price_range_pct) / 5.0 * 0.3)
                    , 2)
                ELSE 0
            END as breakout_score

        FROM latest_prices lp
        LEFT JOIN recent_highs rh ON lp.symbol = rh.symbol
        LEFT JOIN price_range pr ON lp.symbol = pr.symbol

        WHERE breakout_score > 0
        ORDER BY breakout_score DESC
        LIMIT ?
        """

        # Calculate date ranges
        end_date = scan_date - timedelta(days=1)
        start_date = end_date - timedelta(days=self.config['lookback_period'] + 5)
        analysis_start = scan_date - timedelta(days=self.config['lookback_period'])

        # Create proper timestamp for cutoff
        cutoff_timestamp = datetime.combine(scan_date, cutoff_time)

        params = [
            scan_date, cutoff_timestamp,  # current_data
            self.config['min_price'], self.config['max_price'],  # price filters
            start_date, end_date,  # historical_data
            analysis_start,  # recent_highs
            analysis_start,  # price_range
            self.config['breakout_threshold'],  # breakout conditions
            self.config['volume_multiplier'],
            self.config['max_results']  # limit
        ]

        try:
            result = self._execute_query(breakout_query, params)

            if result.empty:
                print("⚠️  No stocks showing simple breakout patterns")
                return pd.DataFrame()

            # Add analysis
            result['breakout_signal'] = result.apply(
                lambda row: self._classify_signal(row), axis=1
            )

            result['risk_level'] = result.apply(
                lambda row: self._assess_risk(row), axis=1
            )

            print(f"✅ Found {len(result)} stocks with simple breakout patterns")
            return result

        except Exception as e:
            print(f"❌ Error in simple breakout scanning: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _classify_signal(self, row) -> str:
        """Classify the breakout signal strength."""
        score = row.get('breakout_score', 0)
        breakout_pct = row.get('breakout_pct', 0)
        volume_ratio = row.get('volume_ratio', 1)

        if score >= 2.0 and breakout_pct >= 2.0 and volume_ratio >= 2.0:
            return "STRONG_BREAKOUT"
        elif score >= 1.5 and (breakout_pct >= 1.5 or volume_ratio >= 1.8):
            return "MODERATE_BREAKOUT"
        elif score >= 1.0:
            return "WEAK_BREAKOUT"
        else:
            return "NO_SIGNAL"

    def _assess_risk(self, row) -> str:
        """Assess the risk level."""
        breakout_pct = abs(row.get('breakout_pct', 0))
        volume_ratio = row.get('volume_ratio', 1)

        if breakout_pct > 3.0 or volume_ratio > 3.0:
            return "HIGH_RISK"
        elif breakout_pct > 1.5 or volume_ratio > 2.0:
            return "MEDIUM_RISK"
        else:
            return "LOW_RISK"
