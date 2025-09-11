"""
Technical Indicators Query Builder

Specialized query builder for technical indicator calculation rules.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import date, time
import logging

from .base_query_builder import BaseQueryBuilder

logger = logging.getLogger(__name__)


class TechnicalQueryBuilder(BaseQueryBuilder):
    """Query builder specialized for technical indicator calculations."""

    def build_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for technical indicator calculations.

        Args:
            conditions: Technical indicator conditions
            scan_date: Date to scan
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter list

        Returns:
            Tuple of (SQL query string, parameters dict)
        """
        cache_key = self._create_cache_key("technical", conditions, scan_date, start_time, end_time, symbols)

        # Check cache first
        cached_result = self._get_cached_query(cache_key)
        if cached_result:
            return cached_result

        # Build query based on indicator type
        indicator_type = conditions.get('indicator_type', 'SMA')

        if indicator_type == 'RSI':
            query, params = self._build_rsi_query(conditions, scan_date, start_time, end_time, symbols)
        elif indicator_type == 'MACD':
            query, params = self._build_macd_query(conditions, scan_date, start_time, end_time, symbols)
        elif indicator_type == 'SMA':
            query, params = self._build_sma_query(conditions, scan_date, start_time, end_time, symbols)
        elif indicator_type == 'EMA':
            query, params = self._build_ema_query(conditions, scan_date, start_time, end_time, symbols)
        elif indicator_type == 'BBANDS':
            query, params = self._build_bbands_query(conditions, scan_date, start_time, end_time, symbols)
        else:
            query, params = self._build_generic_indicator_query(conditions, scan_date, start_time, end_time, symbols)

        result = (query, params)

        # Cache the result
        self._cache_query(cache_key, result)

        return result

    def _build_rsi_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build RSI (Relative Strength Index) query."""
        period = conditions.get('period', 14)

        query = """
        WITH price_changes AS (
            SELECT
                symbol,
                timestamp,
                close,
                date_partition,
                close - LAG(close, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) as price_change
            FROM market_data
            WHERE date_partition = '{scan_date}'
        ),
        gains_losses AS (
            SELECT
                symbol,
                timestamp,
                date_partition,
                CASE WHEN price_change > 0 THEN price_change ELSE 0 END as gain,
                CASE WHEN price_change < 0 THEN ABS(price_change) ELSE 0 END as loss
            FROM price_changes
        ),
        avg_gains_losses AS (
            SELECT
                symbol,
                timestamp,
                date_partition,
                AVG(gain) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {period} PRECEDING) as avg_gain,
                AVG(loss) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {period} PRECEDING) as avg_loss
            FROM gains_losses
        )
        SELECT
            symbol,
            timestamp,
            date_partition,
            CASE
                WHEN avg_loss = 0 THEN 100
                ELSE 100 - (100 / (1 + (avg_gain / avg_loss)))
            END as rsi_value,
            CASE
                WHEN rsi_value > {overbought} THEN 'OVERBOUGHT'
                WHEN rsi_value < {oversold} THEN 'OVERSOLD'
                ELSE 'NEUTRAL'
            END as rsi_signal
        FROM avg_gains_losses
        """.format(
            scan_date=scan_date.isoformat(),
            period=period - 1,  # Window frame
            overbought=conditions.get('overbought_level', 70),
            oversold=conditions.get('oversold_level', 30)
        )

        params = {}

        # Apply filters
        query = self._apply_standard_filters(query, scan_date, start_time, end_time, symbols, params)

        return query, params

    def _build_macd_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build MACD (Moving Average Convergence Divergence) query."""
        fast_period = conditions.get('fast_period', 12)
        slow_period = conditions.get('slow_period', 26)
        signal_period = conditions.get('signal_period', 9)

        query = """
        WITH ema_fast AS (
            SELECT
                symbol,
                timestamp,
                date_partition,
                close,
                AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {fast_period} PRECEDING) as ema_fast
            FROM market_data
            WHERE date_partition = '{scan_date}'
        ),
        ema_slow AS (
            SELECT
                symbol,
                timestamp,
                date_partition,
                ema_fast,
                AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {slow_period} PRECEDING) as ema_slow
            FROM ema_fast
        ),
        macd_calc AS (
            SELECT
                symbol,
                timestamp,
                date_partition,
                ema_fast - ema_slow as macd_line,
                AVG(ema_fast - ema_slow) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {signal_period} PRECEDING) as signal_line
            FROM ema_slow
        )
        SELECT
            symbol,
            timestamp,
            date_partition,
            macd_line,
            signal_line,
            macd_line - signal_line as histogram,
            CASE
                WHEN macd_line > signal_line THEN 'BULLISH'
                WHEN macd_line < signal_line THEN 'BEARISH'
                ELSE 'NEUTRAL'
            END as macd_signal
        FROM macd_calc
        """.format(
            scan_date=scan_date.isoformat(),
            fast_period=fast_period - 1,
            slow_period=slow_period - 1,
            signal_period=signal_period - 1
        )

        params = {}

        # Apply filters
        query = self._apply_standard_filters(query, scan_date, start_time, end_time, symbols, params)

        return query, params

    def _build_sma_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build SMA (Simple Moving Average) query."""
        period = conditions.get('period', 20)

        query = """
        SELECT
            symbol,
            timestamp,
            date_partition,
            close,
            AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {period} PRECEDING) as sma_value,
            CASE
                WHEN close > AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {period} PRECEDING) THEN 'ABOVE_SMA'
                WHEN close < AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {period} PRECEDING) THEN 'BELOW_SMA'
                ELSE 'AT_SMA'
            END as sma_signal
        FROM market_data
        WHERE date_partition = '{scan_date}'
        """.format(
            scan_date=scan_date.isoformat(),
            period=period - 1
        )

        params = {}

        # Apply filters
        query = self._apply_standard_filters(query, scan_date, start_time, end_time, symbols, params)

        return query, params

    def _build_ema_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build EMA (Exponential Moving Average) query."""
        period = conditions.get('period', 20)
        multiplier = 2 / (period + 1)

        query = """
        WITH ema_calc AS (
            SELECT
                symbol,
                timestamp,
                date_partition,
                close,
                close * {multiplier} + LAG(close * {multiplier}, 1) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp) * (1 - {multiplier}) as ema_value
            FROM market_data
            WHERE date_partition = '{scan_date}'
        )
        SELECT
            symbol,
            timestamp,
            date_partition,
            close,
            ema_value,
            CASE
                WHEN close > ema_value THEN 'ABOVE_EMA'
                WHEN close < ema_value THEN 'BELOW_EMA'
                ELSE 'AT_EMA'
            END as ema_signal
        FROM ema_calc
        """.format(
            scan_date=scan_date.isoformat(),
            multiplier=multiplier
        )

        params = {}

        # Apply filters
        query = self._apply_standard_filters(query, scan_date, start_time, end_time, symbols, params)

        return query, params

    def _build_bbands_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build Bollinger Bands query."""
        period = conditions.get('period', 20)
        std_dev = conditions.get('std_dev', 2)

        query = """
        WITH bb_calc AS (
            SELECT
                symbol,
                timestamp,
                date_partition,
                close,
                AVG(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {period} PRECEDING) as sma,
                STDDEV(close) OVER (PARTITION BY symbol, date_partition ORDER BY timestamp ROWS {period} PRECEDING) as stddev
            FROM market_data
            WHERE date_partition = '{scan_date}'
        )
        SELECT
            symbol,
            timestamp,
            date_partition,
            close,
            sma as middle_band,
            sma + (stddev * {std_dev}) as upper_band,
            sma - (stddev * {std_dev}) as lower_band,
            CASE
                WHEN close > sma + (stddev * {std_dev}) THEN 'UPPER_BREAKOUT'
                WHEN close < sma - (stddev * {std_dev}) THEN 'LOWER_BREAKOUT'
                WHEN close BETWEEN sma - (stddev * {std_dev}) AND sma + (stddev * {std_dev}) THEN 'WITHIN_BANDS'
                ELSE 'NEUTRAL'
            END as bb_signal
        FROM bb_calc
        """.format(
            scan_date=scan_date.isoformat(),
            period=period - 1,
            std_dev=std_dev
        )

        params = {}

        # Apply filters
        query = self._apply_standard_filters(query, scan_date, start_time, end_time, symbols, params)

        return query, params

    def _build_generic_indicator_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build generic technical indicator query."""
        indicator_type = conditions.get('indicator_type', 'UNKNOWN')

        query = """
        SELECT
            symbol,
            timestamp,
            date_partition,
            open,
            high,
            low,
            close,
            volume,
            '{indicator_type}' as indicator_type,
            NULL as indicator_value,
            'UNKNOWN' as signal
        FROM market_data
        WHERE date_partition = '{scan_date}'
        """.format(
            scan_date=scan_date.isoformat(),
            indicator_type=indicator_type
        )

        params = {}

        # Apply filters
        query = self._apply_standard_filters(query, scan_date, start_time, end_time, symbols, params)

        return query, params

    def _apply_standard_filters(
        self,
        query: str,
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]],
        params: Dict[str, Any]
    ) -> str:
        """Apply standard filters to query."""
        conditions = []

        # Symbol filter
        if symbols:
            symbol_list = "', '".join(symbols)
            conditions.append(f"symbol IN ('{symbol_list}')")

        # Time filters
        if start_time:
            datetime_start = f"{scan_date.isoformat()} {start_time.strftime('%H:%M:%S')}"
            conditions.append(f"timestamp >= '{datetime_start}'")
        if end_time:
            datetime_end = f"{scan_date.isoformat()} {end_time.strftime('%H:%M:%S')}"
            conditions.append(f"timestamp <= '{datetime_end}'")

        if conditions:
            query += "\nWHERE " + " AND ".join(conditions)

        return query
