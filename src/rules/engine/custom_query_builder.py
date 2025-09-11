"""
Custom Query Builder

Specialized query builder for custom rule conditions and complex queries.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import date, time
import logging

from .base_query_builder import BaseQueryBuilder

logger = logging.getLogger(__name__)


class CustomQueryBuilder(BaseQueryBuilder):
    """Query builder specialized for custom rule conditions."""

    def build_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for custom rule conditions.

        Args:
            conditions: Custom rule conditions
            scan_date: Date to scan
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter list

        Returns:
            Tuple of (SQL query string, parameters dict)
        """
        cache_key = self._create_cache_key("custom", conditions, scan_date, start_time, end_time, symbols)

        # Check cache first
        cached_result = self._get_cached_query(cache_key)
        if cached_result:
            return cached_result

        # Build custom query based on conditions
        query_parts = []
        params = {}

        # Start with base market data query
        base_query = """
        SELECT
            symbol,
            timestamp,
            date_partition,
            open,
            high,
            low,
            close,
            volume,
            ROW_NUMBER() OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as row_num,
            LAG(close, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_close,
            LAG(high, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_high,
            LAG(low, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_low,
            LAG(volume, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as prev_volume
        FROM market_data
        WHERE date_partition = '{scan_date}'
        """.format(scan_date=scan_date.isoformat())

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

        # Apply custom conditions
        custom_conditions = self._build_custom_conditions(conditions)
        if custom_conditions:
            query_parts.append("AND " + custom_conditions)

        # Final query assembly
        final_query = "\n".join(query_parts)

        result = (final_query, params)

        # Cache the result
        self._cache_query(cache_key, result)

        return result

    def _build_custom_conditions(self, conditions: Dict[str, Any]) -> str:
        """Build custom WHERE conditions from rule conditions."""
        custom_conds = []

        # Handle various custom condition types
        for condition_key, condition_value in conditions.items():
            if condition_key == 'custom_sql':
                # Direct SQL condition
                if isinstance(condition_value, str):
                    custom_conds.append(f"({condition_value})")

            elif condition_key == 'price_range':
                # Price within range
                if isinstance(condition_value, dict):
                    min_price = condition_value.get('min')
                    max_price = condition_value.get('max')
                    if min_price is not None:
                        custom_conds.append(f"close >= {min_price}")
                    if max_price is not None:
                        custom_conds.append(f"close <= {max_price}")

            elif condition_key == 'volume_range':
                # Volume within range
                if isinstance(condition_value, dict):
                    min_vol = condition_value.get('min')
                    max_vol = condition_value.get('max')
                    if min_vol is not None:
                        custom_conds.append(f"volume >= {min_vol}")
                    if max_vol is not None:
                        custom_conds.append(f"volume <= {max_vol}")

            elif condition_key == 'price_change':
                # Price change percentage
                if isinstance(condition_value, dict):
                    min_change = condition_value.get('min')
                    max_change = condition_value.get('max')
                    if min_change is not None:
                        custom_conds.append(f"ABS((close - prev_close) / prev_close) >= {min_change}")
                    if max_change is not None:
                        custom_conds.append(f"ABS((close - prev_close) / prev_close) <= {max_change}")

            elif condition_key == 'moving_average':
                # Moving average conditions
                if isinstance(condition_value, dict):
                    period = condition_value.get('period', 20)
                    position = condition_value.get('position')
                    ma_query = f"AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {period-1} PRECEDING)"

                    if position == 'above':
                        custom_conds.append(f"close > {ma_query}")
                    elif position == 'below':
                        custom_conds.append(f"close < {ma_query}")
                    elif position == 'crossing_above':
                        custom_conds.append(f"close > {ma_query} AND prev_close <= {ma_query.replace('timestamp', 'timestamp - INTERVAL 1 MINUTE')}")
                    elif position == 'crossing_below':
                        custom_conds.append(f"close < {ma_query} AND prev_close >= {ma_query.replace('timestamp', 'timestamp - INTERVAL 1 MINUTE')}")

            elif condition_key == 'volatility':
                # Volatility conditions
                if isinstance(condition_value, dict):
                    threshold = condition_value.get('threshold', 0.02)
                    lookback = condition_value.get('lookback', 20)
                    vol_query = f"STDDEV(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {lookback-1} PRECEDING) / AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {lookback-1} PRECEDING)"
                    custom_conds.append(f"{vol_query} >= {threshold}")

            elif condition_key == 'pattern_recognition':
                # Pattern recognition conditions
                if isinstance(condition_value, str):
                    if condition_value == 'hammer':
                        custom_conds.append("""
                        (high - low) > 2 * ABS(open - close) AND
                        (close - low) / (high - low) > 0.6 AND
                        (open - low) / (high - low) > 0.6
                        """)
                    elif condition_value == 'shooting_star':
                        custom_conds.append("""
                        (high - low) > 2 * ABS(open - close) AND
                        (high - close) / (high - low) > 0.6 AND
                        (high - open) / (high - low) > 0.6
                        """)

        return " AND ".join(custom_conds) if custom_conds else ""
