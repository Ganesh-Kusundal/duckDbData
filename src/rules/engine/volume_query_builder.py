"""
Volume Query Builder

Specialized query builder for volume analysis rules.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import date, time
import logging

from .base_query_builder import BaseQueryBuilder

logger = logging.getLogger(__name__)


class VolumeQueryBuilder(BaseQueryBuilder):
    """Query builder specialized for volume analysis."""

    def build_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for volume analysis.

        Args:
            conditions: Volume analysis conditions
            scan_date: Date to scan
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter list

        Returns:
            Tuple of (SQL query string, parameters dict)
        """
        cache_key = self._create_cache_key("volume", conditions, scan_date, start_time, end_time, symbols)

        # Check cache first
        cached_result = self._get_cached_query(cache_key)
        if cached_result:
            return cached_result

        # Build query
        query_parts = []
        params = {}

        # Base volume analysis query
        volume_query = """
        SELECT
            symbol,
            timestamp,
            date_partition,
            open,
            high,
            low,
            close,
            volume,
            LAG(volume, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_volume,
            AVG(volume) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {lookback} PRECEDING) as avg_volume,
            MAX(volume) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {lookback} PRECEDING) as max_volume_period,
            MIN(volume) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {lookback} PRECEDING) as min_volume_period,
            STDDEV(volume) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {lookback} PRECEDING) as volume_stddev,
            SUM(volume) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as cumulative_volume,
            ROW_NUMBER() OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as period_row
        FROM market_data
        WHERE date_partition = '{scan_date}'
        """.format(
            scan_date=scan_date.isoformat(),
            lookback=conditions.get('lookback_period', 20)
        )

        query_parts.append(volume_query)

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

        # Apply volume-specific conditions
        volume_conditions = self._build_volume_conditions(conditions)
        if volume_conditions:
            query_parts.append("AND " + volume_conditions)

        # Final query assembly
        final_query = "\n".join(query_parts)

        # Wrap in subquery for volume signal detection
        volume_analysis_query = f"""
        SELECT *,
               CASE
                   WHEN volume > avg_volume * {conditions.get('volume_spike_threshold', 2.0)} THEN 'VOLUME_SPIKE'
                   WHEN volume < avg_volume * {conditions.get('volume_drop_threshold', 0.5)} THEN 'VOLUME_DROP'
                   WHEN volume > max_volume_period * 0.9 THEN 'HIGH_VOLUME_PERIOD'
                   WHEN volume < min_volume_period * 1.1 THEN 'LOW_VOLUME_PERIOD'
                   ELSE 'NORMAL_VOLUME'
               END as volume_signal,
               CASE
                   WHEN volume_stddev > 0 AND ABS(volume - avg_volume) / volume_stddev > {conditions.get('volatility_threshold', 2.0)} THEN 'HIGH_VOLATILITY'
                   ELSE 'NORMAL_VOLATILITY'
               END as volume_volatility,
               volume / NULLIF(LAG(volume, 1) OVER (PARTITION BY symbol ORDER BY timestamp), 0) as volume_ratio
        FROM ({final_query}) sub
        ORDER BY symbol, timestamp DESC
        """

        result = (volume_analysis_query, params)

        # Cache the result
        self._cache_query(cache_key, result)

        return result

    def _build_volume_conditions(self, conditions: Dict[str, Any]) -> str:
        """Build volume-specific WHERE conditions."""
        volume_conds = []

        # Volume threshold conditions
        if 'min_volume' in conditions:
            min_vol = conditions['min_volume']
            volume_conds.append(f"volume >= {min_vol}")

        if 'max_volume' in conditions:
            max_vol = conditions['max_volume']
            volume_conds.append(f"volume <= {max_vol}")

        # Volume change conditions
        if 'volume_change_pct' in conditions:
            change_pct = conditions['volume_change_pct']
            if change_pct > 0:
                volume_conds.append(f"volume > prev_volume * {1 + change_pct}")
            else:
                volume_conds.append(f"volume < prev_volume * {1 + abs(change_pct)}")

        # Average volume conditions
        if 'above_avg_volume' in conditions:
            multiplier = conditions['above_avg_volume']
            volume_conds.append(f"volume > avg_volume * {multiplier}")

        if 'below_avg_volume' in conditions:
            multiplier = conditions['below_avg_volume']
            volume_conds.append(f"volume < avg_volume * {multiplier}")

        # Volume patterns
        if 'volume_pattern' in conditions:
            pattern = conditions['volume_pattern']
            if pattern == 'increasing':
                # Check if volume is increasing over last few periods
                volume_conds.append("""
                volume > LAG(volume, 1) OVER (PARTITION BY symbol ORDER BY timestamp) AND
                LAG(volume, 1) OVER (PARTITION BY symbol ORDER BY timestamp) > LAG(volume, 2) OVER (PARTITION BY symbol ORDER BY timestamp)
                """)
            elif pattern == 'decreasing':
                volume_conds.append("""
                volume < LAG(volume, 1) OVER (PARTITION BY symbol ORDER BY timestamp) AND
                LAG(volume, 1) OVER (PARTITION BY symbol ORDER BY timestamp) < LAG(volume, 2) OVER (PARTITION BY symbol ORDER BY timestamp)
                """)

        # Volume-price relationship
        if 'volume_price_confirmation' in conditions:
            confirmation = conditions['volume_price_confirmation']
            if confirmation == 'bullish':
                volume_conds.append("close > open AND volume > avg_volume")
            elif confirmation == 'bearish':
                volume_conds.append("close < open AND volume > avg_volume")

        return " AND ".join(volume_conds) if volume_conds else ""
