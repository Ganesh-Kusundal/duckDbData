"""
CRP (Central Pivot Range) Query Builder

Specialized query builder for CRP pattern analysis rules.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import date, time
import logging

from .base_query_builder import BaseQueryBuilder

logger = logging.getLogger(__name__)


class CRPQueryBuilder(BaseQueryBuilder):
    """Query builder specialized for CRP pattern analysis."""

    def build_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for CRP pattern analysis.

        Args:
            conditions: CRP rule conditions
            scan_date: Date to scan
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter list

        Returns:
            Tuple of (SQL query string, parameters dict)
        """
        cache_key = self._create_cache_key("crp", conditions, scan_date, start_time, end_time, symbols)

        # Check cache first
        cached_result = self._get_cached_query(cache_key)
        if cached_result:
            return cached_result

        # Build query
        query_parts = []
        params = {}

        # Calculate pivot levels
        pivot_calculation = """
        SELECT
            symbol,
            date_partition,
            (MAX(high) + MIN(low) + LAST(close)) / 3 as pivot_point,
            MAX(high) as resistance_1,
            MIN(low) as support_1,
            ((MAX(high) + MIN(low) + LAST(close)) / 3) + (MAX(high) - MIN(low)) as resistance_2,
            ((MAX(high) + MIN(low) + LAST(close)) / 3) - (MAX(high) - MIN(low)) as support_2,
            LAST(close) as prev_close
        FROM market_data
        WHERE date_partition = '{prev_date}'
        GROUP BY symbol, date_partition
        """.format(prev_date=(scan_date.replace(day=scan_date.day-1)).isoformat())

        # Main CRP query
        crp_query = """
        WITH pivot_levels AS ({pivot_calc}),
        current_data AS (
            SELECT
                md.symbol,
                md.timestamp,
                md.open,
                md.high,
                md.low,
                md.close,
                md.volume,
                md.date_partition,
                pl.pivot_point,
                pl.resistance_1,
                pl.support_1,
                pl.resistance_2,
                pl.support_2,
                CASE
                    WHEN md.close BETWEEN pl.support_1 AND pl.resistance_1 THEN 'WITHIN_RANGE'
                    WHEN md.close > pl.resistance_1 THEN 'ABOVE_RANGE'
                    WHEN md.close < pl.support_1 THEN 'BELOW_RANGE'
                    ELSE 'OUTSIDE_RANGE'
                END as range_position,
                ABS(md.close - pl.pivot_point) / pl.pivot_point as distance_from_pivot
            FROM market_data md
            LEFT JOIN pivot_levels pl ON md.symbol = pl.symbol
            WHERE md.date_partition = '{scan_date}'
        )
        SELECT *
        FROM current_data
        """.format(
            pivot_calc=pivot_calculation,
            scan_date=scan_date.isoformat()
        )

        query_parts.append(crp_query)

        # Apply symbol filter
        if symbols:
            symbol_list = "', '".join(symbols)
            query_parts.append(f"WHERE symbol IN ('{symbol_list}')")

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
                connector = "AND" if symbols else "WHERE"
                query_parts.append(f"{connector} (" + " AND ".join(time_conditions) + ")")

        # Apply CRP-specific conditions
        crp_conditions = self._build_crp_conditions(conditions)
        if crp_conditions:
            connector = "AND" if (symbols or start_time or end_time) else "WHERE"
            query_parts.append(f"{connector} {crp_conditions}")

        # Final query assembly
        final_query = "\n".join(query_parts)

        # Add ordering
        final_query += "\nORDER BY symbol, timestamp DESC"

        result = (final_query, params)

        # Cache the result
        self._cache_query(cache_key, result)

        return result

    def _build_crp_conditions(self, conditions: Dict[str, Any]) -> str:
        """Build CRP-specific WHERE conditions."""
        crp_conds = []

        # Range position conditions
        if 'range_position' in conditions:
            position = conditions['range_position']
            if isinstance(position, list):
                positions = "', '".join(position)
                crp_conds.append(f"range_position IN ('{positions}')")
            else:
                crp_conds.append(f"range_position = '{position}'")

        # Distance from pivot conditions
        if 'max_distance_from_pivot' in conditions:
            max_distance = conditions['max_distance_from_pivot']
            crp_conds.append(f"distance_from_pivot <= {max_distance}")

        if 'min_distance_from_pivot' in conditions:
            min_distance = conditions['min_distance_from_pivot']
            crp_conds.append(f"distance_from_pivot >= {min_distance}")

        # Volume conditions for CRP
        if 'min_volume' in conditions:
            min_vol = conditions['min_volume']
            crp_conds.append(f"volume >= {min_vol}")

        # Price action conditions
        if 'price_action' in conditions:
            action = conditions['price_action']
            if action == 'bullish':
                crp_conds.append("close > open")
            elif action == 'bearish':
                crp_conds.append("close < open")
            elif action == 'doji':
                crp_conds.append("ABS(close - open) / open <= 0.001")  # Very small body

        # Pivot level reactions
        if 'pivot_reaction' in conditions:
            reaction = conditions['pivot_reaction']
            if reaction == 'rejection':
                crp_conds.append("range_position IN ('ABOVE_RANGE', 'BELOW_RANGE')")
            elif reaction == 'acceptance':
                crp_conds.append("range_position = 'WITHIN_RANGE'")

        return " AND ".join(crp_conds) if crp_conds else ""
