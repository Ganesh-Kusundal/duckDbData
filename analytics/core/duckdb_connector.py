"""
DuckDB Connector for Analytics Dashboard
========================================

Connects to unified DuckDB infrastructure and provides analytics queries.
Refactored to use the unified DuckDB manager for consistent connection handling.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

from src.infrastructure.database import UnifiedDuckDBManager, DuckDBConfig
from src.infrastructure.config.config_manager import ConfigManager
from src.domain.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


class DuckDBAnalytics:
    """DuckDB connector for analytics dashboard using unified infrastructure."""

    def __init__(self, config_manager: Optional[ConfigManager] = None, db_path: Optional[str] = None):
        """
        Initialize DuckDB analytics connector with unified infrastructure.

        Args:
            config_manager: ConfigManager instance for centralized configuration (optional for backward compatibility)
            db_path: Path to existing DuckDB database file (fallback)
        """
        self.config_manager = config_manager

        # Build unified configuration
        config = self._build_config(db_path)

        # Initialize unified manager
        self.db_manager = UnifiedDuckDBManager(config)

        # Load data paths from config or use defaults
        self.data_paths = self._load_data_paths()

        logger.info("DuckDBAnalytics initialized with unified infrastructure")

    def _build_config(self, db_path: Optional[str] = None) -> DuckDBConfig:
        """Build unified DuckDB configuration."""
        # Default configuration
        config_dict = {
            'database_path': db_path or "data/financial_data.duckdb",
            'max_connections': 10,
            'connection_timeout': 30.0,
            'memory_limit': "2GB",
            'threads': 4,
            'enable_object_cache': True,
            'enable_profiling': False,
            'read_only': False,
            'enable_httpfs': True,
            'use_parquet_in_unified_view': True
        }

        # Load from ConfigManager if available
        if self.config_manager:
            try:
                database_config = self.config_manager.get_config('database')
                if database_config:
                    config_dict.update({
                        'database_path': str(database_config.get('path', config_dict['database_path'])),
                        'memory_limit': database_config.get('memory_limit', config_dict['memory_limit']),
                        'threads': database_config.get('threads', config_dict['threads']),
                        'read_only': database_config.get('read_only', config_dict['read_only']),
                    })

                analytics_config = self.config_manager.get_config('analytics')
                if analytics_config:
                    config_dict.update({
                        'parquet_root': analytics_config.get('data_paths', {}).get('parquet_base', './data/'),
                        'parquet_glob': analytics_config.get('data_paths', {}).get('parquet_glob'),
                    })

            except Exception as e:
                logger.warning(f"Could not load configuration from ConfigManager: {e}")

        # Fallback to global settings if no path provided
        if not db_path and config_dict['database_path'] == "data/financial_data.duckdb":
            try:
                from src.infrastructure.config.settings import get_settings
                config_dict['database_path'] = get_settings().database.path
            except Exception:
                pass

        return DuckDBConfig(**config_dict)

    def _load_data_paths(self) -> Dict[str, str]:
        """Load data paths from configuration."""
        defaults = {
            'parquet_base': './data/',
            'indicators': './data/technical_indicators/',
            'processed': './data/processed/'
        }

        if self.config_manager:
            try:
                analytics_config = self.config_manager.get_config('analytics')
                data_paths = analytics_config.get('data_paths', {})
                return {
                    'parquet_base': data_paths.get('parquet_base', defaults['parquet_base']),
                    'indicators': data_paths.get('indicators', defaults['indicators']),
                    'processed': data_paths.get('processed', defaults['processed'])
                }
            except Exception:
                pass

        return defaults

    def get_market_data_schema(self) -> pd.DataFrame:
        """Get schema information for market data tables."""
        query = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_name LIKE '%market_data%'
        ORDER BY table_name, ordinal_position
        """

        try:
            return self.db_manager.persistence_query(query)
        except Exception as e:
            logger.warning(f"Could not get schema info: {e}")
            return pd.DataFrame()

    def scan_parquet_files(self, pattern: str = "**/*.parquet") -> List[str]:
        """Scan for available parquet files."""
        base_path = Path(self.data_paths['parquet_base'])
        parquet_files = []

        for parquet_file in base_path.rglob(pattern):
            if parquet_file.is_file():
                parquet_files.append(str(parquet_file))

        logger.info(f"Found {len(parquet_files)} parquet files")
        return sorted(parquet_files)

    def execute_analytics_query(self, query: str, **params) -> pd.DataFrame:
        """Execute analytics query with parameters using unified infrastructure."""
        try:
            return self.db_manager.analytics_query(query, **params)
        except Exception as e:
            error_msg = f"Analytics query execution failed: {str(e)}"
            context = {
                'query': query[:200] + '...' if len(query) > 200 else query,
                'params_count': len(params),
            }
            exc = DatabaseConnectionError(error_msg, 'execute_analytics_query', context=context)
            logger.error("Analytics query execution failed", extra=exc.to_dict())
            raise exc

    def get_available_symbols(self) -> List[str]:
        """Get list of available stock symbols."""
        query = """
        SELECT DISTINCT regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1) as symbol
        FROM parquet_scan('./data/**/*.parquet')
        ORDER BY symbol
        """

        try:
            result = self.execute_analytics_query(query)
            return result['symbol'].tolist()
        except Exception as e:
            logger.warning(f"Could not get symbols: {e}")
            return []

    def get_date_range(self) -> Tuple[str, str]:
        """Get available date range in the data."""
        query = """
        SELECT
            MIN(regexp_extract(filename, '_minute_([0-9-]+)\\.parquet', 1)) as start_date,
            MAX(regexp_extract(filename, '_minute_([0-9-]+)\\.parquet', 1)) as end_date
        FROM parquet_scan('./data/**/*.parquet')
        """

        try:
            result = self.execute_analytics_query(query)
            start_date = result['start_date'].iloc[0]
            end_date = result['end_date'].iloc[0]
            return start_date, end_date
        except Exception as e:
            logger.warning(f"Could not get date range: {e}")
            return "2015-01-01", "2025-12-31"

    def get_volume_spike_patterns(self,
                                min_volume_multiplier: Optional[float] = None,
                                time_window_minutes: Optional[int] = None,
                                min_price_move: Optional[float] = None) -> pd.DataFrame:
        """Find volume spike patterns that lead to breakouts."""

        # Use defaults if not provided
        if min_volume_multiplier is None:
            min_volume_multiplier = 1.5
        if time_window_minutes is None:
            time_window_minutes = 10
        if min_price_move is None:
            min_price_move = 0.03

        """Find volume spike patterns that lead to breakouts."""

        query = f"""
        WITH volume_analysis AS (
            SELECT
                regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1) as symbol,
                regexp_extract(filename, '_minute_([0-9-]+)\\.parquet', 1) as date,
                __index_level_0__ as ts,
                volume,
                close,
                high,
                -- Rolling volume over {time_window_minutes} minutes (simplified - using row numbers)
                AVG(volume) OVER (
                    PARTITION BY regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1)
                    ORDER BY __index_level_0__
                    ROWS BETWEEN {time_window_minutes - 1} PRECEDING AND CURRENT ROW
                ) as avg_volume_{time_window_minutes}min,

                -- Max high in next 60 minutes (simplified)
                MAX(high) OVER (
                    PARTITION BY regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1)
                    ORDER BY __index_level_0__
                    ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
                ) as max_high_next_60min
            FROM parquet_scan('./data/**/*.parquet')
            WHERE volume > 0 AND close > 0
        )
        SELECT
            symbol,
            date,
            ts as spike_time,
            volume,
            close as entry_price,
            max_high_next_60min,
            (max_high_next_60min - close) / close as price_move_pct,
            volume / avg_volume_{time_window_minutes}min as volume_multiplier
        FROM volume_analysis
        WHERE
            volume / avg_volume_{time_window_minutes}min >= {min_volume_multiplier}
            AND (max_high_next_60min - close) / close >= {min_price_move}
        ORDER BY volume_multiplier DESC, price_move_pct DESC
        LIMIT 1000
        """

        return self.execute_analytics_query(query)

    def get_time_window_analysis(self,
                               start_time: Optional[str] = None,
                               end_time: Optional[str] = None) -> pd.DataFrame:
        """Analyze breakout patterns within specific time windows."""

        # Use defaults if not provided
        if start_time is None:
            start_time = "09:35"
        if end_time is None:
            end_time = "09:50"

        """Analyze breakout patterns within specific time windows."""

        query = f"""
        WITH time_window_data AS (
            SELECT
                regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1) as symbol,
                regexp_extract(filename, '_minute_([0-9-]+)\\.parquet', 1) as date,
                __index_level_0__ as ts,
                open,
                high,
                low,
                close,
                volume,
                -- Pre-window average volume (first 30 minutes - simplified)
                AVG(volume) OVER (
                    PARTITION BY regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1)
                    ORDER BY __index_level_0__
                    ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
                ) as pre_window_avg_volume,

                -- Post-window max high (next 60 minutes - simplified)
                MAX(high) OVER (
                    PARTITION BY regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1)
                    ORDER BY __index_level_0__
                    ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
                ) as post_window_max_high
            FROM parquet_scan('./data/**/*.parquet')
            WHERE __index_level_0__ >= 0  -- Simplified time filtering
        )
        SELECT
            symbol,
            date,
            ts as trade_time,
            volume,
            close as entry_price,
            post_window_max_high,
            (post_window_max_high - close) / close as breakout_move_pct,
            volume / pre_window_avg_volume as volume_ratio
        FROM time_window_data
        WHERE
            volume / pre_window_avg_volume >= 1.2  -- 20% volume increase
            AND (post_window_max_high - close) / close >= 0.02  -- 2% breakout
        ORDER BY breakout_move_pct DESC, volume_ratio DESC
        LIMIT 1000
        """

        return self.execute_analytics_query(query)

    def close(self):
        """Close unified DuckDB manager and cleanup resources."""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()
            logger.info("Unified DuckDB manager closed")

    def get_connection_stats(self) -> Dict[str, int]:
        """Get connection pool statistics from unified manager."""
        if hasattr(self, 'db_manager'):
            return self.db_manager.get_connection_stats()
        return {'active_connections': 0, 'available_connections': 0, 'max_connections': 0}

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # OPTIMIZED PERFORMANCE METHODS

    def get_available_symbols_fast(self) -> List[str]:
        """Get list of available stock symbols using a faster approach."""
        # Use a single day's data to get sample symbols, then extrapolate
        query = """
        SELECT DISTINCT regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1) as symbol
        FROM parquet_scan('./data/2024/01/02/*.parquet')
        WHERE regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1) != ''
        ORDER BY symbol
        """
        try:
            result = self.execute_analytics_query(query)
            return result['symbol'].tolist()
        except Exception as e:
            logger.warning(f"Could not get symbols: {e}")
            return []

    def get_date_range_fast(self) -> Tuple[str, str]:
        """Get available date range using a faster approach."""
        # Sample from a specific date directory
        query = """
        SELECT
            MIN(regexp_extract(filename, '_minute_([0-9-]+)\\.parquet', 1)) as start_date,
            MAX(regexp_extract(filename, '_minute_([0-9-]+)\\.parquet', 1)) as end_date
        FROM parquet_scan('./data/2024/01/02/*.parquet')
        """
        try:
            result = self.execute_analytics_query(query)
            start_date = result['start_date'].iloc[0]
            end_date = result['end_date'].iloc[0]
            return start_date, end_date
        except Exception as e:
            logger.warning(f"Could not get date range: {e}")
            return "2024-01-01", "2025-01-02"

    def get_volume_spike_patterns_fast(self,
                                     symbol_limit: int = 5,
                                     min_volume_multiplier: Optional[float] = None,
                                     min_price_move: Optional[float] = None) -> pd.DataFrame:
        """Find volume spike patterns using a faster approach with limited symbols."""

        # Get a sample of symbols to analyze
        symbols = self.get_available_symbols_fast()[:symbol_limit]
        if not symbols:
            return pd.DataFrame()

        # Build query for specific symbols only (much faster)
        symbol_conditions = " OR ".join([f"filename LIKE '%{symbol}%'" for symbol in symbols])

        if min_volume_multiplier is None:
            min_volume_multiplier = 1.5
        if min_price_move is None:
            min_price_move = 0.03

        query = f"""
        WITH volume_analysis AS (
            SELECT
                regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1) as symbol,
                __index_level_0__ as ts,
                volume,
                close,
                high,
                -- Simple volume comparison using LAG (much faster than complex window functions)
                LAG(volume, 10) OVER (
                    PARTITION BY regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1)
                    ORDER BY __index_level_0__
                ) as prev_volume_10min,
                -- Simple max high comparison with shorter window
                MAX(high) OVER (
                    PARTITION BY regexp_extract(filename, '.*/([A-Za-z0-9._-]+)_minute_.*', 1)
                    ORDER BY __index_level_0__
                    ROWS BETWEEN CURRENT ROW AND 30 FOLLOWING
                ) as max_high_next_30min
            FROM parquet_scan('./data/2024/01/02/*.parquet')
            WHERE ({symbol_conditions})
              AND volume > 0 AND close > 0
        )
        SELECT
            symbol,
            ts as spike_time,
            volume,
            close as entry_price,
            max_high_next_30min,
            (max_high_next_30min - close) / close as price_move_pct,
            CASE
                WHEN prev_volume_10min > 0 THEN volume / prev_volume_10min
                ELSE volume / 1000.0  -- fallback
            END as volume_multiplier
        FROM volume_analysis
        WHERE prev_volume_10min > 0
          AND CASE
                WHEN prev_volume_10min > 0 THEN volume / prev_volume_10min
                ELSE 0
              END >= {min_volume_multiplier}
          AND (max_high_next_30min - close) / close >= {min_price_move}
        ORDER BY volume_multiplier DESC, price_move_pct DESC
        LIMIT 100
        """

        return self.execute_analytics_query(query)