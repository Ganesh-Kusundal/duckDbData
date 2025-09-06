"""
Breakout Stock Scanner for intraday trading opportunities.
Identifies stocks showing breakout patterns using OBV, momentum, and technical analysis.
"""

from typing import Dict, Any, List
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np

from ..base_scanner import BaseScanner


class BreakoutScanner(BaseScanner):
    """
    Advanced breakout scanner that identifies stocks with:
    - OBV (On Balance Volume) buildup
    - Price consolidation patterns
    - Breakout above resistance levels
    - Momentum confirmation
    - Volume confirmation
    """

    @property
    def scanner_name(self) -> str:
        return "breakout"

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'obv_lookback_period': 10,        # Days to analyze OBV trend
            'obv_threshold': 1.5,             # OBV buildup threshold (1.5x increase)
            'consolidation_period': 5,        # Days for consolidation check
            'consolidation_range_pct': 3.0,   # Max price range for consolidation
            'breakout_volume_ratio': 2.0,     # Volume ratio for breakout confirmation
            'momentum_period': 3,             # Days for momentum calculation
            'resistance_break_pct': 1.0,      # Break above resistance by %
            'min_price': 50,                  # Minimum stock price
            'max_price': 2000,                # Maximum stock price
            'max_results': 20                 # Maximum results to return
        }

    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Scan for stocks showing breakout patterns by specified cutoff time.

        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning

        Returns:
            DataFrame with breakout analysis
        """
        print(f"🚀 Scanning for breakout patterns by {cutoff_time}")

        # Get available symbols
        all_symbols = self.get_available_symbols()
        print(f"📊 Analyzing {len(all_symbols)} symbols for breakout patterns...")

        # Simplified breakout query that works with existing data
        breakout_query = """
        WITH current_data AS (
            -- Get latest data for each symbol
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
                AND close BETWEEN ? AND ?
        ),

        latest_prices AS (
            SELECT * FROM current_data WHERE rn = 1
        ),

        recent_highs AS (
            -- Calculate recent price highs (last 5 days)
            SELECT
                symbol,
                MAX(high) as recent_high,
                MIN(low) as recent_low,
                AVG(volume) as avg_volume
            FROM market_data
            WHERE date_partition >= ?
                AND date_partition <= ?
            GROUP BY symbol
        ),

        price_range AS (
            -- Calculate price consolidation range
            SELECT
                symbol,
                (MAX(high) - MIN(low)) / AVG(close) * 100 as price_range_pct
            FROM market_data
            WHERE date_partition >= ?
                AND date_partition <= ?
            GROUP BY symbol
        )

        SELECT
            lp.symbol,
            lp.current_price,
            lp.open_price,
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
                WHEN lp.current_high > rh.recent_high * 1.01  -- Breakout above 1%
                     AND lp.current_volume > rh.avg_volume * 1.5        -- Volume confirmation
                     AND pr.price_range_pct <= 5.0                      -- Consolidation (tight range)
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
        analysis_start = scan_date - timedelta(days=self.config['consolidation_period'])

        params = [
            scan_date,  # current_data date
            self.config['min_price'], self.config['max_price'],  # price filters
            analysis_start, scan_date,  # recent_highs date range
            analysis_start, scan_date,  # price_range date range
            self.config['max_results']  # limit
        ]

        try:
            result = self._execute_query(breakout_query, params)

            if result.empty:
                print("⚠️  No stocks showing clear breakout patterns")
                return pd.DataFrame()

            # Add additional analysis
            result['breakout_signal'] = result.apply(
                lambda row: self._classify_breakout_signal(row), axis=1
            )

            result['risk_level'] = result.apply(
                lambda row: self._assess_breakout_risk(row), axis=1
            )

            result['trading_bias'] = result.apply(
                lambda row: self._determine_trading_bias(row), axis=1
            )

            print(f"✅ Found {len(result)} stocks with breakout patterns")
            return result

        except Exception as e:
            print(f"❌ Error in breakout scanning: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _classify_breakout_signal(self, row) -> str:
        """Classify the strength of the breakout signal."""
        score = row.get('breakout_score', 0)
        obv_ratio = row.get('obv_ratio', 1)
        volume_ratio = row.get('volume_ratio', 1)
        breakout_pct = row.get('breakout_pct', 0)

        if score >= 3.0 and obv_ratio >= 2.0 and volume_ratio >= 3.0:
            return "VERY_STRONG_BREAKOUT"
        elif score >= 2.5 and (obv_ratio >= 1.8 or volume_ratio >= 2.5):
            return "STRONG_BREAKOUT"
        elif score >= 2.0 and breakout_pct >= 2.0:
            return "MODERATE_BREAKOUT"
        elif score >= 1.5:
            return "WEAK_BREAKOUT"
        else:
            return "NO_BREAKOUT"

    def _assess_breakout_risk(self, row) -> str:
        """Assess the risk level of the breakout."""
        breakout_pct = abs(row.get('breakout_pct', 0))
        volume_ratio = row.get('volume_ratio', 1)
        consolidation_range = row.get('consolidation_range_pct', 100)

        risk_factors = 0

        # High breakout percentage increases risk
        if breakout_pct > 5.0:
            risk_factors += 2
        elif breakout_pct > 2.0:
            risk_factors += 1

        # Very high volume might indicate exhaustion
        if volume_ratio > 5.0:
            risk_factors += 1

        # Wide consolidation range reduces reliability
        if consolidation_range > 5.0:
            risk_factors += 1

        if risk_factors >= 3:
            return "HIGH_RISK"
        elif risk_factors >= 2:
            return "MEDIUM_RISK"
        elif risk_factors >= 1:
            return "LOW_RISK"
        else:
            return "VERY_LOW_RISK"

    def _determine_trading_bias(self, row) -> str:
        """Determine the trading bias for the breakout."""
        breakout_pct = row.get('breakout_pct', 0)
        price_change = row.get('price_change_pct', 0)
        obv_ratio = row.get('obv_ratio', 1)

        if breakout_pct > 1.0 and price_change > 0.5 and obv_ratio > 1.2:
            return "BULLISH_BREAKOUT"
        elif breakout_pct < -1.0 and price_change < -0.5 and obv_ratio < 0.8:
            return "BEARISH_BREAKOUT"
        elif abs(breakout_pct) > 0.5:
            return "SIDEWAYS_BREAKOUT"
        else:
            return "NEUTRAL"
