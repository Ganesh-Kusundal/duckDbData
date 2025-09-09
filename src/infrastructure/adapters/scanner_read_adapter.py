"""
Unified DuckDB implementation of ScannerReadPort.

Provides read-model queries for scanners (CRP, EOD prices) using the unified DuckDB layer
for consistent performance, resource management, and error handling.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Union
from datetime import date, time
from functools import lru_cache
import time as time_module

import duckdb

from src.application.ports.scanner_read_port import ScannerReadPort
from src.infrastructure.database.unified_duckdb import UnifiedDuckDBManager, DuckDBConfig
from src.infrastructure.config.settings import get_settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class DuckDBScannerReadAdapter(ScannerReadPort):
    """
    Unified DuckDB scanner read adapter.

    This adapter provides optimized scanner queries through the unified DuckDB manager,
    leveraging connection pooling, query caching, and consistent error handling.

    Supports both legacy mode (direct connection) and unified mode (connection pooling).
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        unified_manager: Optional[UnifiedDuckDBManager] = None,
        enable_cache: bool = True,
        cache_ttl: int = 300,
        legacy_mode: bool = False
    ):
        """
        Initialize the scanner read adapter.

        Args:
            db_path: Database path (for legacy mode)
            unified_manager: Unified DuckDB manager instance
            enable_cache: Whether to enable result caching for performance
            cache_ttl: Time-to-live for cached results in seconds
            legacy_mode: Whether to use legacy direct connection mode
        """
        self.legacy_mode = legacy_mode
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self._cache = {} if enable_cache else None
        self._logger = get_logger(__name__)

        if unified_manager:
            # Use provided unified manager
            self.unified_manager = unified_manager
            self.legacy_mode = False
        elif not legacy_mode:
            # Auto-create unified manager
            settings = get_settings()
            config = DuckDBConfig(
                database_path=db_path or settings.database.path,
                max_connections=getattr(settings.database, 'max_connections', 10),
                memory_limit=getattr(settings.database, 'memory_limit', '2GB'),
                threads=getattr(settings.database, 'threads', 4),
                enable_object_cache=getattr(settings.database, 'enable_object_cache', True),
                read_only=True,  # Scanner operations are typically read-only
                enable_httpfs=getattr(settings.database, 'enable_httpfs', True),
                parquet_root=getattr(settings.database, 'parquet_root', None),
                use_parquet_in_unified_view=getattr(settings.database, 'use_parquet_in_unified_view', True)
            )
            self.unified_manager = UnifiedDuckDBManager(config)
        else:
            # Legacy mode - direct connection
            self.unified_manager = None
            settings = get_settings()
            self._db_path = db_path or settings.database.path
            self._conn: Optional[duckdb.DuckDBPyConnection] = None
            self._memory_limit = getattr(settings.database, "memory_limit", None)
            self._threads = getattr(settings.database, "threads", None)

    def _truncate_query(self, query: str, max_length: int = 200) -> str:
        """Truncate query for logging purposes."""
        if len(query) <= max_length:
            return query
        return query[:max_length] + "..."

    def _log_db_error(self, operation: str, query: str, params: List[Any], error: Exception):
        """Log database error with context information."""
        truncated_query = self._truncate_query(query)
        mode = "legacy" if self.legacy_mode else "unified"
        self._logger.error(
            f"DuckDB error in {operation}: {str(error)} | "
            f"Mode: {mode} | Query: {truncated_query} | "
            f"Params count: {len(params) if params else 0}"
        )

    def _conn_or_open(self) -> duckdb.DuckDBPyConnection:
        """Legacy mode: Get or create direct connection."""
        if self._conn is None:
            try:
                config = {
                    "access_mode": "READ_ONLY" if getattr(get_settings().database, "read_only", False) else "READ_WRITE",
                }
                self._conn = duckdb.connect(self._db_path, config=config)
                if self._memory_limit:
                    self._conn.execute(f"SET memory_limit='{self._memory_limit}'")
                if self._threads:
                    self._conn.execute(f"SET threads={int(self._threads)}")
                if getattr(get_settings().database, 'enable_object_cache', True):
                    try:
                        self._conn.execute("SET enable_object_cache=true")
                    except Exception:
                        pass
            except Exception as e:
                self._logger.error(
                    f"DuckDB connection error in _conn_or_open: {str(e)} | "
                    f"DB: {self._db_path} | Memory: {self._memory_limit} | Threads: {self._threads}"
                )
                raise
        return self._conn

    def _resolve_market_data_relation(self, conn: duckdb.DuckDBPyConnection) -> str:
        """Return unified relation if available, else base table."""
        try:
            check = conn.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'market_data_unified'
                """
            ).fetchone()
            if check:
                return "market_data_unified"
        except Exception:
            pass
        return "market_data"

    def _log_scanner_operation(self, operation: str, start_time: float, result_count: int = None):
        """Log scanner operation with performance metrics."""
        duration = time_module.time() - start_time
        mode = "legacy" if self.legacy_mode else "unified"
        self._logger.info(
            f"Scanner operation completed",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            result_count=result_count,
            cache_enabled=self.enable_cache,
            mode=mode
        )

    def _get_cache_key(self, operation: str, *args) -> str:
        """Generate cache key for operation."""
        if not self.enable_cache:
            return ""
        key_parts = [operation] + [str(arg) for arg in args]
        return "|".join(key_parts)

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if available and not expired."""
        if not self.enable_cache or not self._cache:
            return None

        cached_item = self._cache.get(cache_key)
        if cached_item:
            timestamp, result = cached_item
            current_time = time_module.time()
            time_diff = current_time - timestamp
            if time_diff < self.cache_ttl:
                self._logger.debug(f"Cache hit for key: {cache_key}")
                return result
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
                self._logger.debug(f"Cache expired for key: {cache_key}, age: {time_diff}s")

        return None

    def _set_cached_result(self, cache_key: str, result: Any):
        """Store result in cache."""
        if self.enable_cache and self._cache is not None:
            self._cache[cache_key] = (time_module.time(), result)
            self._logger.debug(f"Cached result for key: {cache_key}")

    def get_crp_candidates(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Get Close to Resistance/Price candidates using unified layer.

        Args:
            scan_date: Date to scan for CRP candidates
            cutoff_time: Time cutoff for the scan
            config: Scanner configuration parameters
            max_results: Maximum number of results to return

        Returns:
            List of CRP candidate dictionaries
        """
        start_time = time_module.time()
        cache_key = self._get_cache_key("crp_candidates", scan_date, cutoff_time, str(config), max_results)

        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            self._log_scanner_operation("crp_candidates_cache_hit", start_time, len(cached_result))
            return cached_result

        if self.legacy_mode:
            # Legacy mode implementation
            return self._get_crp_candidates_legacy(scan_date, cutoff_time, config, max_results, start_time, cache_key)
        else:
            # Unified mode implementation
            return self._get_crp_candidates_unified(scan_date, cutoff_time, config, max_results, start_time, cache_key)

    def _get_crp_candidates_legacy(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
        start_time: float,
        cache_key: str
    ) -> List[Dict[str, Any]]:
        """Legacy mode CRP candidates implementation."""
        try:
            conn = self._conn_or_open()

            rel = self._resolve_market_data_relation(conn)
            query = f"""
                WITH crp_candidates AS (
                    SELECT
                        symbol,
                        close as crp_price,
                        open as open_price,
                        high as current_high,
                        low as current_low,
                        volume as current_volume,
                        (high - low) / NULLIF(close, 0) * 100 as current_range_pct,
                        -- Close Position (40% weight)
                        CASE
                            WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= ? THEN 0.4
                            WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= ? THEN 0.4
                            ELSE 0.1
                        END as close_score,
                        -- Range Tightness (30% weight)
                        CASE
                            WHEN (high - low) / NULLIF(close, 0) * 100 <= ? THEN 0.3
                            WHEN (high - low) / NULLIF(close, 0) * 100 <= ? * 1.5 THEN 0.2
                            ELSE 0.05
                        END as range_score,
                        -- Volume Pattern (20% weight)
                        CASE
                            WHEN volume > 75000 THEN 0.2
                            WHEN volume > 50000 THEN 0.15
                            WHEN volume > 25000 THEN 0.1
                            ELSE 0.05
                        END as volume_score,
                        -- Momentum (10% weight)
                        CASE
                            WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.1
                            WHEN (close - open) / NULLIF(open, 0) > 0 THEN 0.05
                            ELSE 0.02
                        END as momentum_score,
                        (
                            CASE
                                WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= ? THEN 0.4
                                WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= ? THEN 0.4
                                ELSE 0.1
                            END +
                            CASE
                                WHEN (high - low) / NULLIF(close, 0) * 100 <= ? THEN 0.3
                                WHEN (high - low) / NULLIF(close, 0) * 100 <= ? * 1.5 THEN 0.2
                                ELSE 0.05
                            END +
                            CASE
                                WHEN volume > 75000 THEN 0.2
                                WHEN volume > 50000 THEN 0.15
                                WHEN volume > 25000 THEN 0.1
                                ELSE 0.05
                            END +
                            CASE
                                WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.1
                                WHEN (close - open) / NULLIF(open, 0) > 0 THEN 0.05
                                ELSE 0.02
                            END
                        ) * 100 as crp_probability_score,
                        CASE
                            WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= ? THEN 'Near High'
                            WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= ? THEN 'Near Low'
                            ELSE 'Mid Range'
                        END as close_position
                    FROM {rel}
                    WHERE date_partition = ?
                      AND CAST(timestamp AS TIME) <= ?
                      AND close BETWEEN ? AND ?
                      AND volume BETWEEN ? AND ?
                )
                SELECT * FROM crp_candidates
                WHERE (close_score + range_score + volume_score + momentum_score) > 0.5
                  AND crp_probability_score > 30
                ORDER BY crp_probability_score DESC
                LIMIT ?
            """

            params = [
                config['close_threshold_pct'],
                config['close_threshold_pct'],
                config['range_threshold_pct'],
                config['range_threshold_pct'],
                config['close_threshold_pct'],
                config['close_threshold_pct'],
                config['range_threshold_pct'],
                config['range_threshold_pct'],
                config['close_threshold_pct'],
                config['close_threshold_pct'],
                scan_date.isoformat(),
                cutoff_time.isoformat(),
                config['min_price'],
                config['max_price'],
                config['min_volume'],
                config['max_volume'],
                max_results,
            ]

            rows = conn.execute(query, params).fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                # Order aligns with SELECT in query above
                result = {
                    'symbol': row[0],
                    'crp_price': float(row[1]) if row[1] else 0,
                    'open_price': float(row[2]) if row[2] else 0,
                    'current_high': float(row[3]) if row[3] else 0,
                    'current_low': float(row[4]) if row[4] else 0,
                    'current_volume': int(row[5]) if row[5] else 0,
                    'current_range_pct': float(row[6]) if row[6] else 0,
                    'close_score': float(row[7]) if row[7] else 0,
                    'range_score': float(row[8]) if row[8] else 0,
                    'volume_score': float(row[9]) if row[9] else 0,
                    'momentum_score': float(row[10]) if row[10] else 0,
                    'crp_probability_score': float(row[11]) if row[11] else 0,
                    'close_position': row[12] if row[12] else 'Unknown',
                }
                results.append(result)

            # Cache the results
            if cache_key:
                self._set_cached_result(cache_key, results)

            self._log_scanner_operation("get_crp_candidates", start_time, len(results))
            return results

        except Exception as e:
            self._log_db_error("get_crp_candidates", query, params, e)
            raise

    def _get_crp_candidates_unified(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
        start_time: float,
        cache_key: str
    ) -> List[Dict[str, Any]]:
        """Unified mode CRP candidates implementation."""
        try:
            # Build optimized CRP query using unified layer
            query = """
                WITH crp_candidates AS (
                    SELECT
                        symbol,
                        close as crp_price,
                        open as open_price,
                        high as current_high,
                        low as current_low,
                        volume as current_volume,
                        (high - low) / NULLIF(close, 0) * 100 as current_range_pct,
                        -- Close Position scoring (40% weight)
                        CASE
                            WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= {close_threshold_pct} THEN 0.4
                            WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= {close_threshold_pct} THEN 0.4
                            ELSE 0.1
                        END as close_score,
                        -- Range Tightness scoring (30% weight)
                        CASE
                            WHEN (high - low) / NULLIF(close, 0) * 100 <= {range_threshold_pct} THEN 0.3
                            WHEN (high - low) / NULLIF(close, 0) * 100 <= {range_threshold_pct} * 1.5 THEN 0.2
                            ELSE 0.05
                        END as range_score,
                        -- Volume Pattern scoring (20% weight)
                        CASE
                            WHEN volume > 75000 THEN 0.2
                            WHEN volume > 50000 THEN 0.15
                            WHEN volume > 25000 THEN 0.1
                            ELSE 0.05
                        END as volume_score,
                        -- Momentum scoring (10% weight)
                        CASE
                            WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.1
                            WHEN (close - open) / NULLIF(open, 0) > 0 THEN 0.05
                            ELSE 0.02
                        END as momentum_score,
                        (
                            CASE
                                WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= {close_threshold_pct} THEN 0.4
                                WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= {close_threshold_pct} THEN 0.4
                                ELSE 0.1
                            END +
                            CASE
                                WHEN (high - low) / NULLIF(close, 0) * 100 <= {range_threshold_pct} THEN 0.3
                                WHEN (high - low) / NULLIF(close, 0) * 100 <= {range_threshold_pct} * 1.5 THEN 0.2
                                ELSE 0.05
                            END +
                            CASE
                                WHEN volume > 75000 THEN 0.2
                                WHEN volume > 50000 THEN 0.15
                                WHEN volume > 25000 THEN 0.1
                                ELSE 0.05
                            END +
                            CASE
                                WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.1
                                WHEN (close - open) / NULLIF(open, 0) > 0 THEN 0.05
                                ELSE 0.02
                            END
                        ) * 100 as crp_probability_score,
                        CASE
                            WHEN ABS(close - high) / NULLIF(high, 0) * 100 <= {close_threshold_pct} THEN 'Near High'
                            WHEN ABS(close - low) / NULLIF(low, 0) * 100 <= {close_threshold_pct} THEN 'Near Low'
                            ELSE 'Mid Range'
                        END as close_position
                    FROM market_data
                    WHERE date_partition = '{scan_date}'
                      AND CAST(timestamp AS TIME) <= '{cutoff_time}'
                      AND close BETWEEN {min_price} AND {max_price}
                      AND volume BETWEEN {min_volume} AND {max_volume}
                )
                SELECT * FROM crp_candidates
                WHERE (close_score + range_score + volume_score + momentum_score) > 0.5
                  AND crp_probability_score > 30
                ORDER BY crp_probability_score DESC
                LIMIT {max_results}
            """

            # Execute query through unified manager
            df_results = self.unified_manager.analytics_query(
                query,
                scan_date=scan_date.strftime('%Y-%m-%d'),
                cutoff_time=cutoff_time.strftime('%H:%M:%S'),
                close_threshold_pct=config.get('close_threshold_pct', 2.0),
                range_threshold_pct=config.get('range_threshold_pct', 3.0),
                min_price=config.get('min_price', 50),
                max_price=config.get('max_price', 2000),
                min_volume=config.get('min_volume', 50000),
                max_volume=config.get('max_volume', 5000000),
                max_results=max_results
            )

            # Convert DataFrame to list of dictionaries
            results = []
            if not df_results.empty:
                for _, row in df_results.iterrows():
                    result = {
                        'symbol': str(row.get('symbol', '')),
                        'crp_price': float(row.get('crp_price', 0)),
                        'open_price': float(row.get('open_price', 0)),
                        'current_high': float(row.get('current_high', 0)),
                        'current_low': float(row.get('current_low', 0)),
                        'current_volume': int(row.get('current_volume', 0)),
                        'current_range_pct': float(row.get('current_range_pct', 0)),
                        'close_score': float(row.get('close_score', 0)),
                        'range_score': float(row.get('range_score', 0)),
                        'volume_score': float(row.get('volume_score', 0)),
                        'momentum_score': float(row.get('momentum_score', 0)),
                        'crp_probability_score': float(row.get('crp_probability_score', 0)),
                        'close_position': str(row.get('close_position', 'Unknown')),
                    }
                    results.append(result)

            # Cache the results
            if cache_key:
                self._set_cached_result(cache_key, results)

            self._log_scanner_operation("get_crp_candidates", start_time, len(results))
            return results

        except Exception as e:
            self._logger.error(
                "CRP candidates query failed",
                error=str(e),
                scan_date=scan_date.isoformat(),
                cutoff_time=cutoff_time.isoformat(),
                config_keys=list(config.keys())
            )
            raise

    def get_end_of_day_prices(
        self,
        symbols: List[str],
        scan_date: date,
        end_time: time,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get end-of-day prices for symbols using unified layer.

        Args:
            symbols: List of symbols to get EOD prices for
            scan_date: Date to get EOD prices for
            end_time: End time for the trading day

        Returns:
            Dictionary mapping symbols to their EOD price data
        """
        start_time = time_module.time()

        if not symbols:
            self._log_scanner_operation("get_end_of_day_prices", start_time, 0)
            return {}

        cache_key = self._get_cache_key("eod_prices", str(symbols), scan_date, end_time)

        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            self._log_scanner_operation("eod_prices_cache_hit", start_time, len(cached_result))
            return cached_result

        if self.legacy_mode:
            # Legacy mode implementation
            return self._get_end_of_day_prices_legacy(symbols, scan_date, end_time, start_time, cache_key)
        else:
            # Unified mode implementation
            return self._get_end_of_day_prices_unified(symbols, scan_date, end_time, start_time, cache_key)

    def _get_end_of_day_prices_legacy(
        self,
        symbols: List[str],
        scan_date: date,
        end_time: time,
        start_time: float,
        cache_key: str
    ) -> Dict[str, Dict[str, Any]]:
        """Legacy mode end-of-day prices implementation."""
        try:
            conn = self._conn_or_open()

            placeholders = ','.join(['?' for _ in symbols])
            query = f"""
                SELECT
                    symbol,
                    close as eod_price,
                    high as eod_high,
                    low as eod_low,
                    volume as eod_volume
                FROM market_data
                WHERE date_partition = ?
                  AND symbol IN ({placeholders})
                  AND CAST(timestamp AS TIME) <= ?
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) = 1
            """
            params = [scan_date.isoformat()] + symbols + [end_time.isoformat()]
            rows = conn.execute(query, params).fetchall()
            results: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                results[row[0]] = {
                    'eod_price': float(row[1]) if row[1] else 0,
                    'eod_high': float(row[2]) if row[2] else 0,
                    'eod_low': float(row[3]) if row[3] else 0,
                    'eod_volume': int(row[4]) if row[4] else 0,
                }

            # Cache the results
            if cache_key:
                self._set_cached_result(cache_key, results)

            self._log_scanner_operation("get_end_of_day_prices", start_time, len(results))
            return results

        except Exception as e:
            self._log_db_error("get_end_of_day_prices", query, params, e)
            raise

    def _get_end_of_day_prices_unified(
        self,
        symbols: List[str],
        scan_date: date,
        end_time: time,
        start_time: float,
        cache_key: str
    ) -> Dict[str, Dict[str, Any]]:
        """Unified mode end-of-day prices implementation."""
        try:
            # Build placeholders for SQL query
            placeholders = ','.join(['?' for _ in symbols])

            query = f"""
                SELECT
                    symbol,
                    close as eod_price,
                    high as eod_high,
                    low as eod_low,
                    volume as eod_volume
                FROM market_data
                WHERE date_partition = ?
                  AND symbol IN ({placeholders})
                  AND CAST(timestamp AS TIME) <= ?
                QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) = 1
            """

            # Execute query through unified manager
            params = [scan_date.isoformat()] + symbols + [end_time.isoformat()]
            df_results = self.unified_manager.persistence_query(query, params)

            # Convert to dictionary format
            results = {}
            if not df_results.empty:
                for _, row in df_results.iterrows():
                    symbol = str(row.get('symbol', ''))
                    if symbol:
                        results[symbol] = {
                            'eod_price': float(row.get('eod_price', 0)),
                            'eod_high': float(row.get('eod_high', 0)),
                            'eod_low': float(row.get('eod_low', 0)),
                            'eod_volume': int(row.get('eod_volume', 0)),
                        }

            # Cache the results
            if cache_key:
                self._set_cached_result(cache_key, results)

            self._log_scanner_operation("get_end_of_day_prices", start_time, len(results))
            return results

        except Exception as e:
            self._logger.error(
                "End-of-day prices query failed",
                error=str(e),
                symbol_count=len(symbols),
                scan_date=scan_date.isoformat(),
                end_time=end_time.isoformat()
            )
            raise

    def get_breakout_candidates(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Get breakout candidates using unified layer.

        Args:
            scan_date: Date to scan for breakout candidates
            cutoff_time: Time cutoff for the scan
            config: Scanner configuration parameters
            max_results: Maximum number of results to return

        Returns:
            List of breakout candidate dictionaries
        """
        start_time = time_module.time()
        cache_key = self._get_cache_key("breakout_candidates", scan_date, cutoff_time, str(config), max_results)

        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            self._log_scanner_operation("breakout_candidates_cache_hit", start_time, len(cached_result))
            return cached_result

        if self.legacy_mode:
            # Legacy mode implementation
            return self._get_breakout_candidates_legacy(scan_date, cutoff_time, config, max_results, start_time, cache_key)
        else:
            # Unified mode implementation
            return self._get_breakout_candidates_unified(scan_date, cutoff_time, config, max_results, start_time, cache_key)

    def _get_breakout_candidates_legacy(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
        start_time: float,
        cache_key: str
    ) -> List[Dict[str, Any]]:
        """Legacy mode breakout candidates implementation."""
        try:
            conn = self._conn_or_open()
            query = """
                WITH breakout_candidates AS (
                    SELECT
                        symbol,
                        close as breakout_price,
                        open as open_price,
                        high as current_high,
                        low as current_low,
                        volume as current_volume,
                        high - close as breakout_above_resistance,
                        (high - close) / NULLIF(close, 0) * 100 as breakout_pct,
                        volume / NULLIF(AVG(volume) OVER (PARTITION BY symbol ORDER BY date_partition ROWS 4 PRECEDING), 0) as volume_ratio,
                        (
                            CASE WHEN ((high - close) / NULLIF(close, 0) * 100) > 2.0 THEN 0.5
                                 WHEN ((high - close) / NULLIF(close, 0) * 100) > 1.0 THEN 0.3
                                 WHEN ((high - close) / NULLIF(close, 0) * 100) > 0.5 THEN 0.2
                                 ELSE 0.1 END +
                            CASE WHEN volume > 50000 THEN 0.3
                                 WHEN volume > 20000 THEN 0.2
                                 WHEN volume > 10000 THEN 0.1
                                 ELSE 0.05 END +
                            CASE WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.2 ELSE 0 END
                        ) * 100 as probability_score
                    FROM market_data
                    WHERE date_partition = ?
                      AND CAST(timestamp AS TIME) <= ?
                      AND close BETWEEN ? AND ?
                      AND high > close * 1.005
                      AND volume > 10000
                )
                SELECT *
                FROM breakout_candidates
                WHERE probability_score > 10
                ORDER BY probability_score DESC
                LIMIT ?
            """
            params = [
                scan_date.isoformat(),
                cutoff_time.isoformat(),
                config.get('min_price', 50),
                config.get('max_price', 2000),
                max_results,
            ]
            rows = conn.execute(query, params).fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                results.append({
                    'symbol': row[0],
                    'breakout_price': float(row[1]) if row[1] else 0,
                    'open_price': float(row[2]) if row[2] else 0,
                    'current_high': float(row[3]) if row[3] else 0,
                    'current_low': float(row[4]) if row[4] else 0,
                    'current_volume': int(row[5]) if row[5] else 0,
                    'breakout_above_resistance': float(row[6]) if row[6] else 0,
                    'breakout_pct': float(row[7]) if row[7] else 0,
                    'volume_ratio': float(row[8]) if row[8] else 0,
                    'probability_score': float(row[9]) if row[9] else 0,
                })

            # Cache the results
            if cache_key:
                self._set_cached_result(cache_key, results)

            self._log_scanner_operation("get_breakout_candidates", start_time, len(results))
            return results

        except Exception as e:
            self._log_db_error("get_breakout_candidates", query, params, e)
            raise

    def _get_breakout_candidates_unified(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
        start_time: float,
        cache_key: str
    ) -> List[Dict[str, Any]]:
        """Unified mode breakout candidates implementation."""
        try:
            # Build optimized breakout query using unified layer
            # Build query with proper parameter placeholders
            query = """
                WITH breakout_candidates AS (
                    SELECT
                        symbol,
                        close as breakout_price,
                        open as open_price,
                        high as current_high,
                        low as current_low,
                        volume as current_volume,
                        high - close as breakout_above_resistance,
                        (high - close) / NULLIF(close, 0) * 100 as breakout_pct,
                        volume / NULLIF(AVG(volume) OVER (PARTITION BY symbol ORDER BY date_partition ROWS 4 PRECEDING), 0) as volume_ratio,
                        (
                            CASE WHEN ((high - close) / NULLIF(close, 0) * 100) > 2.0 THEN 0.5
                                 WHEN ((high - close) / NULLIF(close, 0) * 100) > 1.0 THEN 0.3
                                 WHEN ((high - close) / NULLIF(close, 0) * 100) > 0.5 THEN 0.2
                                 ELSE 0.1 END +
                            CASE WHEN volume > 50000 THEN 0.3
                                 WHEN volume > 20000 THEN 0.2
                                 WHEN volume > 10000 THEN 0.1
                                 ELSE 0.05 END +
                            CASE WHEN (close - open) / NULLIF(open, 0) > 0.01 THEN 0.2 ELSE 0 END
                        ) * 100 as probability_score
                    FROM market_data
                    WHERE date_partition = ?
                      AND CAST(timestamp AS TIME) <= ?
                      AND close BETWEEN ? AND ?
                      AND high > close * 1.005
                      AND volume > 10000
                )
                SELECT *
                FROM breakout_candidates
                WHERE probability_score > 10
                ORDER BY probability_score DESC
                LIMIT ?
            """

            # Execute query through unified manager with proper parameters
            params = [
                scan_date.isoformat(),
                cutoff_time.isoformat(),
                config.get('min_price', 50),
                config.get('max_price', 2000),
                max_results
            ]

            df_results = self.unified_manager.persistence_query(query, params)

            # Convert DataFrame to list of dictionaries
            results = []
            if not df_results.empty:
                for _, row in df_results.iterrows():
                    result = {
                        'symbol': str(row.get('symbol', '')),
                        'breakout_price': float(row.get('breakout_price', 0)),
                        'open_price': float(row.get('open_price', 0)),
                        'current_high': float(row.get('current_high', 0)),
                        'current_low': float(row.get('current_low', 0)),
                        'current_volume': int(row.get('current_volume', 0)),
                        'breakout_above_resistance': float(row.get('breakout_above_resistance', 0)),
                        'breakout_pct': float(row.get('breakout_pct', 0)),
                        'volume_ratio': float(row.get('volume_ratio', 1.0)),
                        'probability_score': float(row.get('probability_score', 0)),
                    }
                    results.append(result)

            # Cache the results
            if cache_key:
                self._set_cached_result(cache_key, results)

            self._log_scanner_operation("get_breakout_candidates", start_time, len(results))
            return results

        except Exception as e:
            self._logger.error(
                "Breakout candidates query failed",
                error=str(e),
                scan_date=scan_date.isoformat(),
                cutoff_time=cutoff_time.isoformat(),
                config_keys=list(config.keys())
            )
            raise

    def clear_cache(self):
        """Clear all cached results."""
        if self._cache:
            self._cache.clear()
            self._logger.info("Scanner result cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enable_cache or self._cache is None:
            return {"enabled": False}

        total_entries = len(self._cache)
        current_time = time_module.time()
        expired_entries = sum(1 for _, (timestamp, _) in self._cache.items()
                             if current_time - timestamp > self.cache_ttl)

        return {
            "enabled": self.enable_cache,
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "ttl_seconds": self.cache_ttl
        }
