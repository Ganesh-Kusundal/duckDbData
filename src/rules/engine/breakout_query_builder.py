"""
Breakout Query Builder

Specialized query builder for breakout pattern detection rules.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import date, time
import logging

from .base_query_builder import BaseQueryBuilder

logger = logging.getLogger(__name__)


class BreakoutQueryBuilder(BaseQueryBuilder):
    """Query builder specialized for breakout pattern detection."""

    def build_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for breakout pattern detection.

        Args:
            conditions: Breakout rule conditions
            scan_date: Date to scan
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter list

        Returns:
            Tuple of (SQL query string, parameters dict)
        """
        cache_key = self._create_cache_key("breakout", conditions, scan_date, start_time, end_time, symbols)

        # Check cache first
        cached_result = self._get_cached_query(cache_key)
        if cached_result:
            return cached_result

        # Build query
        query_parts = []
        params = {}

        # Base query structure
        base_query = """
        SELECT
            symbol,
            timestamp,
            open,
            high,
            low,
            close,
            volume,
            date_partition,
            LAG(close, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_close,
            LAG(high, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_high,
            LAG(low, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_low,
            LAG(volume, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_volume,
            AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {lookback} PRECEDING) as avg_price,
            AVG(volume) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {lookback} PRECEDING) as avg_volume
        FROM market_data
        WHERE date_partition = '{scan_date}'
        """.format(
            scan_date=scan_date.isoformat(),
            lookback=conditions.get('lookback_period', 20)
        )

        query_parts.append(base_query)

        # Apply symbol filter
        if symbols:
            symbol_list = "', '".join(symbols)
            query_parts.append(f"AND symbol IN ('{symbol_list}')")

        # Apply time filters
        if start_time or end_time:
            time_conditions = []
            if start_time:
                datetime_start = f"{scan_date.isoformat()} {start_time.strftime('%H:%M:%S')}"
                time_conditions.append(f"timestamp >= '{datetime_start}'")
            if end_time:
                datetime_end = f"{scan_date.isoformat()} {end_time.strftime('%H:%M:%S')}"
                time_conditions.append(f"timestamp <= '{datetime_end}'")

            if time_conditions:
                query_parts.append("AND (" + " AND ".join(time_conditions) + ")")

        # Apply breakout conditions
        breakout_conditions = self._build_breakout_conditions(conditions)
        if breakout_conditions:
            query_parts.append("AND " + breakout_conditions)

        # Final query assembly
        final_query = "\n".join(query_parts)

        # Wrap in subquery for breakout detection
        breakout_query = f"""
        SELECT *,
               CASE
                   WHEN close > prev_high * (1 + {conditions.get('breakout_threshold', 0.02)}) THEN 'UPWARD_BREAKOUT'
                   WHEN close < prev_low * (1 - {conditions.get('breakout_threshold', 0.02)}) THEN 'DOWNWARD_BREAKOUT'
                   ELSE 'NO_BREAKOUT'
               END as breakout_signal,
               CASE
                   WHEN volume > avg_volume * {conditions.get('volume_multiplier', 1.5)} THEN 'HIGH_VOLUME'
                   ELSE 'NORMAL_VOLUME'
               END as volume_signal
        FROM ({final_query}) sub
        WHERE breakout_signal != 'NO_BREAKOUT'
        ORDER BY timestamp DESC
        """

        result = (breakout_query, params)

        # Cache the result
        self._cache_query(cache_key, result)

        return result

    def _build_breakout_conditions(self, conditions: Dict[str, Any]) -> str:
        """Build breakout-specific WHERE conditions."""
        breakout_conds = []

        # Price movement conditions
        if 'min_price_change' in conditions:
            min_change = conditions['min_price_change']
            breakout_conds.append(f"ABS((close - prev_close) / prev_close) >= {min_change}")

        # Volume conditions
        if 'min_volume' in conditions:
            min_vol = conditions['min_volume']
            breakout_conds.append(f"volume >= {min_vol}")

        if 'volume_spike' in conditions:
            spike_ratio = conditions['volume_spike']
            breakout_conds.append(f"volume > prev_volume * {spike_ratio}")

        # Price range conditions
        if 'min_range' in conditions:
            min_range_pct = conditions['min_range']
            breakout_conds.append(f"((high - low) / low) >= {min_range_pct}")

        # Consolidation period
        if 'consolidation_period' in conditions:
            consolidation_days = conditions['consolidation_period']
            # This would require additional logic to check previous days' ranges
            pass

        return " AND ".join(breakout_conds) if breakout_conds else ""
