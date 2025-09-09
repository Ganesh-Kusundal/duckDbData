"""
Query Builder

This module dynamically generates optimized SQL queries from rule conditions for:
- Breakout pattern detection
- CRP pattern analysis
- Technical indicator calculations
- Volume analysis
- Custom rule conditions
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import date, time
import logging

from ..schema.rule_types import RuleType

logger = logging.getLogger(__name__)


class QueryBuilder:
    """Dynamically builds SQL queries from rule conditions."""

    def __init__(self):
        self.query_cache = {}
        self.max_cache_size = 1000

    def build_query(
        self,
        rule_type: RuleType,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for rule execution.

        Args:
            rule_type: Type of rule (breakout, crp, technical, etc.)
            conditions: Rule conditions dictionary
            scan_date: Date to scan
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter list

        Returns:
            Tuple of (SQL query string, parameters dictionary)
        """
        # Create cache key
        cache_key = self._create_cache_key(rule_type, conditions, scan_date, start_time, end_time, symbols)

        # Check cache
        if cache_key in self.query_cache:
            logger.debug(f"Using cached query for {cache_key}")
            return self.query_cache[cache_key]

        # Build query based on rule type
        if rule_type == RuleType.BREAKOUT:
            query, params = self._build_breakout_query(conditions, scan_date, start_time, end_time, symbols)
        elif rule_type == RuleType.CRP:
            query, params = self._build_crp_query(conditions, scan_date, start_time, end_time, symbols)
        elif rule_type == RuleType.TECHNICAL:
            query, params = self._build_technical_query(conditions, scan_date, start_time, end_time, symbols)
        elif rule_type == RuleType.VOLUME:
            query, params = self._build_volume_query(conditions, scan_date, start_time, end_time, symbols)
        elif rule_type == RuleType.MOMENTUM:
            query, params = self._build_momentum_query(conditions, scan_date, start_time, end_time, symbols)
        else:
            query, params = self._build_custom_query(conditions, scan_date, start_time, end_time, symbols)

        # Cache the query
        self._cache_query(cache_key, (query, params))

        logger.debug(f"Built query for rule type {rule_type.value}: {len(query)} chars")
        return query, params

    def _build_breakout_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build breakout pattern detection query."""

        # Extract conditions
        time_window = conditions.get('time_window', {})
        breakout_conditions = conditions.get('breakout_conditions', {})
        market_conditions = conditions.get('market_conditions', {})

        # Build filters for price_data_full and price_data first
        price_data_filters = []
        params = [scan_date]

        # Build base query structure
        query = """
        WITH price_data_full AS (
            SELECT
                symbol,
                timestamp,
                close as price,
                volume
            FROM market_data
            WHERE date_partition = ?
        """

        query += """
        ),
        price_data AS (
            SELECT
                symbol,
                timestamp,
                price,
                volume,
                LAG(price, 1) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_price,
                LAG(volume, 1) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_volume,
                AVG(price) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 10 PRECEDING) as avg_price_10,
                AVG(volume) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 10 PRECEDING) as avg_volume_10
            FROM price_data_full
        """

        # Add time filter
        if start_time or end_time:
            time_conditions = []
            if start_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) >= ?")
                total_seconds = start_time.hour * 3600 + start_time.minute * 60
                params.append(total_seconds)
            if end_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) <= ?")
                total_seconds = end_time.hour * 3600 + end_time.minute * 60
                params.append(total_seconds)
            if time_conditions:
                price_data_filters.append(f"({' AND '.join(time_conditions)})")

        # Add symbol filter
        if symbols:
            placeholders = ','.join(['?' for _ in symbols])
            price_data_filters.append(f"symbol IN ({placeholders})")
            params.extend(symbols)

        # Apply filters to price_data_full if any
        if price_data_filters:
            query += "            WHERE " + " AND ".join(price_data_filters)


        # Market condition filters will be applied to breakout_signals, not price_data

        query += """
        ),
        breakout_signals AS (
            SELECT
                symbol,
                timestamp,
                price,
                volume,
                prev_price,
                prev_volume,
                avg_price_10,
                avg_volume_10,
                CASE
                    WHEN prev_price > 0 THEN ((price - prev_price) / prev_price) * 100
                    ELSE 0
                END as price_change_pct,
                CASE
                    WHEN avg_volume_10 > 0 THEN volume / avg_volume_10
                    ELSE 1
                END as volume_multiplier,
                CASE
                    WHEN avg_price_10 > 0 THEN ((price - avg_price_10) / avg_price_10) * 100
                    ELSE 0
                END as breakout_strength
            FROM price_data
            WHERE prev_price IS NOT NULL
        """

        # Add breakout condition filters
        where_conditions = []
        if breakout_conditions.get('min_price_move_pct'):
            where_conditions.append("price_change_pct >= ?")
            params.append(breakout_conditions['min_price_move_pct'])
        if breakout_conditions.get('max_price_move_pct'):
            where_conditions.append("price_change_pct <= ?")
            params.append(breakout_conditions['max_price_move_pct'])
        if breakout_conditions.get('min_volume_multiplier'):
            where_conditions.append("volume_multiplier >= ?")
            params.append(breakout_conditions['min_volume_multiplier'])

        # Add market condition filters to breakout_signals
        if market_conditions.get('min_price'):
            where_conditions.append("price >= ?")
            params.append(market_conditions['min_price'])
        if market_conditions.get('max_price'):
            where_conditions.append("price <= ?")
            params.append(market_conditions['max_price'])
        if market_conditions.get('min_volume'):
            where_conditions.append("volume >= ?")
            params.append(market_conditions['min_volume'])

        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)

        query += """
        ),
        daily_prices AS (
            SELECT
                symbol,
                FIRST(price) FILTER (WHERE (EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) >= 33300
                                      AND (EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) <= 35400) as price_at_0950,
                -- Get the last price available after 15:00 (afternoon session)
                LAST(price) FILTER (WHERE EXTRACT(hour FROM timestamp) >= 15) as price_at_1515
            FROM price_data_full
            GROUP BY symbol
        )
        SELECT
            bs.symbol,
            bs.timestamp,
            bs.price,
            bs.volume,
            bs.price_change_pct,
            bs.volume_multiplier,
            bs.breakout_strength,
            dp.price_at_0950,
            dp.price_at_1515,
            CASE
                WHEN dp.price_at_0950 > 0 AND dp.price_at_1515 IS NOT NULL
                THEN ((dp.price_at_1515 - dp.price_at_0950) / dp.price_at_0950) * 100
                ELSE NULL
            END as daily_performance_pct,
            'breakout' as pattern_type
        FROM breakout_signals bs
        LEFT JOIN daily_prices dp ON bs.symbol = dp.symbol
        ORDER BY bs.volume_multiplier DESC, bs.price_change_pct DESC
        """

        return query, params

    def _build_crp_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build CRP (Close-Range-Pattern) detection query."""

        # Extract conditions
        time_window = conditions.get('time_window', {})
        crp_conditions = conditions.get('crp_conditions', {})
        market_conditions = conditions.get('market_conditions', {})

        consolidation_period = crp_conditions.get('consolidation_period', 5)

        query = f"""
        WITH daily_ranges AS (
            SELECT
                symbol,
                date,
                MIN(low) as day_low,
                MAX(high) as day_high,
                (MAX(high) - MIN(low)) / NULLIF(MIN(low), 0) * 100 as daily_range_pct
            FROM market_data
            WHERE date >= date '{scan_date.isoformat()}', '-{consolidation_period + 1} days')
            AND date <= '{scan_date.isoformat()}'
            GROUP BY symbol, date
        ),
        consolidation_analysis AS (
            SELECT
                symbol,
                AVG(daily_range_pct) as avg_range_pct,
                STDDEV(daily_range_pct) as range_volatility,
                MIN(day_low) as consolidation_low,
                MAX(day_high) as consolidation_high
            FROM daily_ranges
            GROUP BY symbol
        ),
        close_analysis AS (
            SELECT
                m.symbol,
                m.timestamp,
                m.close,
                m.volume,
                ca.consolidation_low,
                ca.consolidation_high,
                ca.avg_range_pct,
                CASE
                    WHEN m.close >= ca.consolidation_high * (1 - ?) THEN 'near_high'
                    WHEN m.close <= ca.consolidation_low * (1 + ?) THEN 'near_low'
                    ELSE 'mid_range'
                END as close_position,
                ABS(m.close - ((ca.consolidation_high + ca.consolidation_low) / 2)) /
                NULLIF(((ca.consolidation_high - ca.consolidation_low) / 2), 0) as distance_from_mid
            FROM market_data m
            JOIN consolidation_analysis ca ON m.symbol = ca.symbol
            WHERE m.date_partition = ?
        """

        params = [
            crp_conditions.get('close_threshold_pct', 2.0) / 100,  # Convert to decimal
            crp_conditions.get('close_threshold_pct', 2.0) / 100,  # Convert to decimal
            scan_date.isoformat()
        ]

        # Add time filter
        if start_time or end_time:
            time_conditions = []
            if start_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) >= ?")
                # Convert time to seconds since midnight
                total_seconds = start_time.hour * 3600 + start_time.minute * 60
                params.append(total_seconds)
            if end_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) <= ?")
                # Convert time to seconds since midnight
                total_seconds = end_time.hour * 3600 + end_time.minute * 60
                params.append(total_seconds)
            if time_conditions:
                query += f" AND ({' AND '.join(time_conditions)})"

        # Add symbol filter
        if symbols:
            placeholders = ','.join(['?' for _ in symbols])
            query += f" AND m.symbol IN ({placeholders})"
            params.extend(symbols)

        # Add market condition filters
        if market_conditions.get('min_price'):
            query += " AND m.close >= ?"
            params.append(market_conditions['min_price'])
        if market_conditions.get('max_price'):
            query += " AND m.close <= ?"
            params.append(market_conditions['max_price'])
        if market_conditions.get('min_volume'):
            query += " AND m.volume >= ?"
            params.append(market_conditions['min_volume'])

        query += """
        )
        SELECT
            symbol,
            timestamp,
            close as price,
            volume,
            close_position,
            distance_from_mid,
            avg_range_pct as consolidation_range_pct,
            'crp' as pattern_type
        FROM close_analysis
        WHERE 1=1
        """

        # Add CRP condition filters
        where_conditions = []
        if crp_conditions.get('range_threshold_pct'):
            where_conditions.append("avg_range_pct <= ?")
            params.append(crp_conditions['range_threshold_pct'])

        close_position_preference = crp_conditions.get('close_position_preference')
        if close_position_preference and close_position_preference != 'any':
            where_conditions.append("close_position = ?")
            params.append(close_position_preference)

        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)

        query += """
        ORDER BY distance_from_mid ASC, avg_range_pct ASC
        """

        return query, params

    def _build_technical_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build technical indicator analysis query."""

        # Extract conditions
        time_window = conditions.get('time_window', {})
        technical_conditions = conditions.get('technical_conditions', {})
        market_conditions = conditions.get('market_conditions', {})

        query = """
        WITH technical_indicators AS (
            SELECT
                symbol,
                timestamp,
                close,
                volume,
                -- RSI calculation (simplified)
                AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 13 PRECEDING) as rsi_basis,
                -- MACD calculation
                close - AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 25 PRECEDING) as macd_line,
                AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 25 PRECEDING) -
                AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 34 PRECEDING) as macd_signal,
                -- Bollinger Bands
                AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 19 PRECEDING) as sma_20,
                STDDEV(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 19 PRECEDING) as stddev_20
            FROM market_data
            WHERE date_partition = ?
        """

        params = [scan_date]

        # Add time filter
        if start_time or end_time:
            time_conditions = []
            if start_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) >= ?")
                # Convert time to seconds since midnight
                total_seconds = start_time.hour * 3600 + start_time.minute * 60
                params.append(total_seconds)
            if end_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) <= ?")
                # Convert time to seconds since midnight
                total_seconds = end_time.hour * 3600 + end_time.minute * 60
                params.append(total_seconds)
            if time_conditions:
                query += f" AND ({' AND '.join(time_conditions)})"

        # Add symbol filter
        if symbols:
            placeholders = ','.join(['?' for _ in symbols])
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        query += """
        ),
        technical_signals AS (
            SELECT
                symbol,
                timestamp,
                close as price,
                volume,
                -- RSI calculation (simplified approximation)
                CASE
                    WHEN rsi_basis > close THEN 100 - (100 / (1 + (rsi_basis - close) / NULLIF(close, 0)))
                    ELSE 100 / (1 + (close - rsi_basis) / NULLIF(rsi_basis, 0))
                END as rsi,
                -- MACD histogram
                macd_line - macd_signal as macd_histogram,
                -- Bollinger Band position
                (close - sma_20) / NULLIF(stddev_20, 0) as bb_position
            FROM technical_indicators
        )
        SELECT
            symbol,
            timestamp,
            price,
            volume,
            rsi,
            macd_histogram,
            bb_position,
            'technical' as pattern_type
        FROM technical_signals
        WHERE 1=1
        """

        # Add technical condition filters
        where_conditions = []
        rsi_conditions = technical_conditions.get('rsi', {})
        if rsi_conditions.get('condition') == 'oversold':
            where_conditions.append("rsi <= ?")
            params.append(rsi_conditions.get('oversold', 30))
        elif rsi_conditions.get('condition') == 'overbought':
            where_conditions.append("rsi >= ?")
            params.append(rsi_conditions.get('overbought', 70))

        macd_conditions = technical_conditions.get('macd', {})
        if macd_conditions.get('condition') == 'bullish':
            where_conditions.append("macd_histogram > 0")
        elif macd_conditions.get('condition') == 'bearish':
            where_conditions.append("macd_histogram < 0")

        bb_conditions = technical_conditions.get('bollinger_bands', {})
        if bb_conditions.get('condition') == 'upper_breakout':
            where_conditions.append("bb_position >= ?")
            params.append(bb_conditions.get('deviations', 2.0))
        elif bb_conditions.get('condition') == 'lower_breakout':
            where_conditions.append("bb_position <= ?")
            params.append(-bb_conditions.get('deviations', 2.0))

        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)

        # Add market condition filters
        if market_conditions.get('min_price'):
            query += " AND price >= ?"
            params.append(market_conditions['min_price'])
        if market_conditions.get('max_price'):
            query += " AND price <= ?"
            params.append(market_conditions['max_price'])
        if market_conditions.get('min_volume'):
            query += " AND volume >= ?"
            params.append(market_conditions['min_volume'])

        query += """
        ORDER BY timestamp DESC
        """

        return query, params

    def _build_volume_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build volume analysis query."""

        # Extract conditions
        time_window = conditions.get('time_window', {})
        volume_conditions = conditions.get('volume_conditions', {})
        market_conditions = conditions.get('market_conditions', {})

        query = """
        WITH volume_analysis AS (
            SELECT
                symbol,
                timestamp,
                close as price,
                volume,
                AVG(volume) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 10 PRECEDING) as avg_volume_10,
                AVG(volume) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 20 PRECEDING) as avg_volume_20,
                STDDEV(volume) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 10 PRECEDING) as volume_stddev,
                LAG(volume, 1) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_volume
            FROM market_data
            WHERE date_partition = ?
        """

        params = [scan_date]

        # Add time filter
        if start_time or end_time:
            time_conditions = []
            if start_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) >= ?")
                # Convert time to seconds since midnight
                total_seconds = start_time.hour * 3600 + start_time.minute * 60
                params.append(total_seconds)
            if end_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) <= ?")
                # Convert time to seconds since midnight
                total_seconds = end_time.hour * 3600 + end_time.minute * 60
                params.append(total_seconds)
            if time_conditions:
                query += f" AND ({' AND '.join(time_conditions)})"

        # Add symbol filter
        if symbols:
            placeholders = ','.join(['?' for _ in symbols])
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        query += """
        ),
        volume_signals AS (
            SELECT
                symbol,
                timestamp,
                price,
                volume,
                avg_volume_10,
                avg_volume_20,
                CASE
                    WHEN avg_volume_10 > 0 THEN volume / avg_volume_10
                    ELSE 1
                END as volume_ratio_10,
                CASE
                    WHEN avg_volume_20 > 0 THEN volume / avg_volume_20
                    ELSE 1
                END as volume_ratio_20,
                CASE
                    WHEN prev_volume > 0 THEN (volume - prev_volume) / prev_volume * 100
                    ELSE 0
                END as volume_change_pct
            FROM volume_analysis
        )
        SELECT
            symbol,
            timestamp,
            price,
            volume,
            volume_ratio_10,
            volume_ratio_20,
            volume_change_pct,
            'volume' as pattern_type
        FROM volume_signals
        WHERE 1=1
        """

        # Add volume condition filters
        where_conditions = []
        if volume_conditions.get('min_volume'):
            where_conditions.append("volume >= ?")
            params.append(volume_conditions['min_volume'])
        if volume_conditions.get('max_volume'):
            where_conditions.append("volume <= ?")
            params.append(volume_conditions['max_volume'])
        if volume_conditions.get('relative_volume'):
            where_conditions.append("volume_ratio_10 >= ?")
            params.append(volume_conditions['relative_volume'])
        if volume_conditions.get('volume_trend') == 'increasing':
            where_conditions.append("volume_change_pct > 0")
        elif volume_conditions.get('volume_trend') == 'decreasing':
            where_conditions.append("volume_change_pct < 0")

        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)

        # Add market condition filters
        if market_conditions.get('min_price'):
            query += " AND price >= ?"
            params.append(market_conditions['min_price'])
        if market_conditions.get('max_price'):
            query += " AND price <= ?"
            params.append(market_conditions['max_price'])

        query += """
        ORDER BY volume_ratio_10 DESC, volume DESC
        """

        return query, params

    def _build_momentum_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build momentum analysis query."""
        # Simplified implementation - can be expanded based on specific momentum indicators
        return self._build_technical_query(conditions, scan_date, start_time, end_time, symbols)

    def _build_custom_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build custom rule query."""
        # For custom rules, provide a flexible base query
        query = """
        SELECT
            symbol,
            timestamp,
            close as price,
            volume,
            'custom' as pattern_type
        FROM market_data
        WHERE date_partition = ?
        """

        params = [scan_date]

        # Add time filter
        if start_time or end_time:
            time_conditions = []
            if start_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) >= ?")
                # Convert time to seconds since midnight
                total_seconds = start_time.hour * 3600 + start_time.minute * 60
                params.append(total_seconds)
            if end_time:
                time_conditions.append("(EXTRACT(hour FROM timestamp) * 3600 + EXTRACT(minute FROM timestamp) * 60) <= ?")
                # Convert time to seconds since midnight
                total_seconds = end_time.hour * 3600 + end_time.minute * 60
                params.append(total_seconds)
            if time_conditions:
                query += f" AND ({' AND '.join(time_conditions)})"

        # Add symbol filter
        if symbols:
            placeholders = ','.join(['?' for _ in symbols])
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)

        return query, params

    def _create_cache_key(
        self,
        rule_type: RuleType,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> str:
        """Create a cache key for query caching."""
        # Create a deterministic key from query parameters
        key_parts = [
            rule_type.value,
            str(conditions),  # This will be the same for identical conditions
            scan_date.isoformat(),
            start_time.strftime('%H:%M:%S') if start_time else 'none',
            end_time.strftime('%H:%M:%S') if end_time else 'none',
            ','.join(sorted(symbols)) if symbols else 'all'
        ]
        return '|'.join(key_parts)

    def _cache_query(self, key: str, query_data: Tuple[str, Dict[str, Any]]):
        """Cache a query with size management."""
        self.query_cache[key] = query_data

        # Manage cache size
        if len(self.query_cache) > self.max_cache_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]

    def clear_cache(self):
        """Clear the query cache."""
        self.query_cache.clear()
        logger.info("Query cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cache_size': len(self.query_cache),
            'max_cache_size': self.max_cache_size,
            'cache_hit_ratio': 0  # Would need hit/miss counters for this
        }
