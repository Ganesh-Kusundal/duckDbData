"""
DuckDB Analytics Adapter
======================

Implements AnalyticsPort using DuckDB for technical analysis
and scoring computations.
"""

import duckdb
from typing import Dict, List, Optional
from datetime import date, time
from decimal import Decimal
import os

from ..domain.models import Score, LeaderScore
from ..ports.analytics import AnalyticsPort


class DuckDBAnalytics(AnalyticsPort):
    """DuckDB-based analytics implementation"""

    def __init__(self, db_path: str, config: Dict):
        self.db_path = db_path
        self.config = config
        self._conn = None
        self._ensure_connection()

    def _ensure_connection(self):
        """Ensure database connection exists"""
        if self._conn is None:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database not found: {self.db_path}")
            self._conn = duckdb.connect(self.db_path, read_only=True)
            self._conn.execute("SET memory_limit='2GB'")
            self._conn.execute("SET threads=2")

    def compute_warmup_features(self, trading_date: date, symbols: List[str],
                               start_time: time, end_time: time) -> Dict[str, Score]:
        """
        Compute 09:15-09:50 warmup features and scores

        This implements the scoring logic from your specification
        """
        self._ensure_connection()

        # If no symbols provided, get from available universe
        if not symbols:
            symbols = self._get_available_symbols()

        scores = {}

        for symbol in symbols:
            try:
                score = self._compute_symbol_score(symbol, trading_date, start_time, end_time)
                if score:
                    scores[symbol] = score
            except Exception as e:
                print(f"Error computing score for {symbol}: {e}")

        return scores

    def _compute_symbol_score(self, symbol: str, trading_date: date,
                            start_time: time, end_time: time) -> Optional[Score]:
        """Compute comprehensive score for a symbol"""
        # Simplified scoring - in production you'd implement the full SQL logic
        query = """
        SELECT
            AVG(close) as avg_price,
            COUNT(*) as bar_count,
            STDDEV(close) as volatility,
            SUM(volume) as total_volume
        FROM market_data_unified
        WHERE symbol = ?
          AND date_partition = ?
          AND CAST(timestamp AS TIME) BETWEEN ? AND ?
        """

        params = [symbol, trading_date.isoformat(), start_time.isoformat(), end_time.isoformat()]

        try:
            result = self._conn.execute(query, params).fetchone()

            if not result or result[1] == 0:  # No bars
                return None

            avg_price = result[0]
            bar_count = result[1]
            volatility = result[2] or 0
            total_volume = result[3] or 0

            # Simplified scoring logic (you'd implement the full formula)
            ret_score = min(volatility / avg_price * 100, 5.0) if avg_price > 0 else 0
            vol_score = min(total_volume / 1000000, 5.0)  # Volume score

            total_score = (ret_score * self.config['selection']['score_weights']['ret_0915_0950'] +
                          vol_score * self.config['selection']['score_weights']['vspike_10m'])

            return Score(
                symbol=symbol,
                date=trading_date,
                ret_0915_0950=ret_score,
                vspike_10m=vol_score,
                obv_delta_35m=0.0,  # Placeholder
                sector_strength=0.0,  # Placeholder
                range_compression=0.0,  # Placeholder
                spread_penalty=0.0,    # Placeholder
                illiq_penalty=0.0,     # Placeholder
                total_score=total_score
            )

        except Exception as e:
            print(f"Error in score computation for {symbol}: {e}")
            return None

    def compute_leader_scores(self, symbols: List[str], trading_date: date,
                             current_time: time, entry_timestamps: Dict[str, time]) -> Dict[str, LeaderScore]:
        """Compute real-time leader scores"""
        scores = {}

        for symbol in symbols:
            # Simplified leader scoring
            entry_time = entry_timestamps.get(symbol)
            if not entry_time:
                continue

            # Calculate returns since entry
            ret_since_entry = self._calculate_return_since_entry(symbol, trading_date, entry_time, current_time)

            scores[symbol] = LeaderScore(
                symbol=symbol,
                timestamp=current_time,  # Should be datetime
                ret_since_entry=ret_since_entry,
                vspike_5m=0.0,  # Placeholder
                obv_delta_10m=0.0,  # Placeholder
                total_score=ret_since_entry * 0.5  # Simplified
            )

        return scores

    def _calculate_return_since_entry(self, symbol: str, trading_date: date,
                                    entry_time: time, current_time: time) -> float:
        """Calculate return since entry time"""
        query = """
        SELECT
            (LAST(close) - FIRST(close)) / FIRST(close) * 100 as return_pct
        FROM market_data_unified
        WHERE symbol = ?
          AND date_partition = ?
          AND CAST(timestamp AS TIME) BETWEEN ? AND ?
        """

        params = [symbol, trading_date.isoformat(), entry_time.isoformat(), current_time.isoformat()]

        try:
            result = self._conn.execute(query, params).fetchone()
            return float(result[0]) if result and result[0] else 0.0
        except:
            return 0.0

    def calculate_atr(self, symbol: str, trading_date: date,
                     window: int = 14, timeframe: str = "5m") -> Optional[Decimal]:
        """Calculate Average True Range"""
        query = f"""
        SELECT AVG(
            GREATEST(
                high - low,
                ABS(high - LAG(close) OVER (ORDER BY timestamp)),
                ABS(low - LAG(close) OVER (ORDER BY timestamp))
            )
        ) as atr
        FROM market_data_unified
        WHERE symbol = ?
          AND date_partition = ?
        ORDER BY timestamp DESC
        LIMIT {window}
        """

        params = [symbol, trading_date.isoformat()]

        try:
            result = self._conn.execute(query, params).fetchone()
            return Decimal(str(result[0])) if result and result[0] else None
        except:
            return None

    def calculate_ema(self, symbol: str, period: int, trading_date: date,
                     timeframe: str = "1m") -> Optional[Decimal]:
        """Calculate Exponential Moving Average"""
        # Simplified EMA calculation
        query = f"""
        SELECT AVG(close) as ema
        FROM (
            SELECT close
            FROM market_data_unified
            WHERE symbol = ?
              AND date_partition = ?
            ORDER BY timestamp DESC
            LIMIT {period}
        )
        """

        params = [symbol, trading_date.isoformat()]

        try:
            result = self._conn.execute(query, params).fetchone()
            return Decimal(str(result[0])) if result and result[0] else None
        except:
            return None

    def calculate_obv(self, symbol: str, trading_date: date,
                     window: int = 10, timeframe: str = "1m") -> Optional[Decimal]:
        """Calculate On Balance Volume delta"""
        query = f"""
        SELECT
            (LAST(obv) - FIRST(obv)) / FIRST(obv) * 100 as obv_delta
        FROM (
            SELECT
                SUM(CASE WHEN close > LAG(close) OVER (ORDER BY timestamp) THEN volume
                         WHEN close < LAG(close) OVER (ORDER BY timestamp) THEN -volume
                         ELSE 0 END) OVER (ORDER BY timestamp) as obv
            FROM market_data
            WHERE symbol = ?
              AND date_partition = ?
            ORDER BY timestamp DESC
            LIMIT {window}
        )
        """

        params = [symbol, trading_date.isoformat()]

        try:
            result = self._conn.execute(query, params).fetchone()
            return Decimal(str(result[0])) if result and result[0] else None
        except:
            return None

    def check_entry_triggers(self, symbol: str, current_bar, ema_9: Optional[Decimal],
                           ema_30: Optional[Decimal]) -> Dict[str, bool]:
        """Check entry trigger conditions"""
        # This would be implemented with the actual trigger logic
        return {
            'ema_9_30': ema_9 and ema_30 and ema_9 > ema_30,
            'range_break': True,  # Placeholder
            'tape_confirm': False  # Placeholder
        }

    def _get_available_symbols(self) -> List[str]:
        """Get available symbols from database"""
        try:
            result = self._conn.execute("SELECT DISTINCT symbol FROM market_data_unified").fetchall()
            return [row[0] for row in result]
        except:
            return []

    def __del__(self):
        """Cleanup connection"""
        if self._conn:
            self._conn.close()
