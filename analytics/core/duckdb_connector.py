"""
DuckDB Connector for Analytics Dashboard
========================================

Connects to existing DuckDB infrastructure and provides analytics queries.
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from src.infrastructure.config.config_manager import ConfigManager
from src.domain.exceptions import DatabaseConnectionError
from src.infrastructure.utils.retry import retry_db_operation

logger = logging.getLogger(__name__)


class DuckDBAnalytics:
    """DuckDB connector for analytics dashboard."""

    def __init__(self, config_manager: Optional[ConfigManager] = None, db_path: Optional[str] = None):
        """
        Initialize DuckDB analytics connector with centralized configuration.

        Args:
            config_manager: ConfigManager instance for centralized configuration (optional for backward compatibility)
            db_path: Path to existing DuckDB database file (fallback)
        """
        self.config_manager = config_manager
        self.connection = None
        
        # Backward compatible database path loading
        if self.config_manager:
            try:
                database_config = self.config_manager.get_config('database')
                print(f"DEBUG DB PATH: config={database_config}")
                self.db_path = str(database_config.get('path', 'financial_data.duckdb'))
            except Exception:
                self.db_path = db_path or "financial_data.duckdb"
        else:
            self.db_path = db_path or "../data/financial_data.duckdb"
        
        # Load data paths from config or use defaults
        if self.config_manager:
            try:
                analytics_config = self.config_manager.get_config('analytics')
                self.data_paths = {
                    'parquet_base': analytics_config.get('data_paths', {}).get('parquet_base', './data/'),
                    'indicators': analytics_config.get('data_paths', {}).get('indicators', './data/technical_indicators/'),
                    'processed': analytics_config.get('data_paths', {}).get('processed', './data/processed/')
                }
            except Exception:
                self.data_paths = {
                    'parquet_base': './data/',
                    'indicators': './data/technical_indicators/',
                    'processed': './data/processed/'
                }
        else:
            self.data_paths = {
                'parquet_base': './data/',
                'indicators': './data/technical_indicators/',
                'processed': './data/processed/'
            }

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Connect to DuckDB database."""
        try:
            self.connection = duckdb.connect(self.db_path)
            logger.info(f"Connected to DuckDB: {self.db_path}")

            # Enable HTTPFS for S3 access if needed
            self.connection.execute("INSTALL httpfs;")
            self.connection.execute("LOAD httpfs;")

            return self.connection
        except Exception as e:
            error_msg = f"Failed to connect to DuckDB database: {str(e)}"
            context = {
                'database_path': self.db_path,
                'config_manager': bool(self.config_manager)
            }
            exc = DatabaseConnectionError(error_msg, 'connect', context=context)
            logger.error("DuckDB connection failed", extra=exc.to_dict())
            raise exc

    def get_market_data_schema(self) -> pd.DataFrame:
        """Get schema information for market data tables."""
        if not self.connection:
            self.connect()

        query = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_name LIKE '%market_data%'
        ORDER BY table_name, ordinal_position
        """

        try:
            return self.connection.execute(query).fetchdf()
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
        """Execute analytics query with parameters."""
        if not self.connection:
            self.connect()
        
        try:
            # Replace placeholders with actual values
            formatted_query = query
            for key, value in params.items():
                if isinstance(value, str):
                    formatted_query = formatted_query.replace(f"{{{key}}}", f"'{value}'")
                else:
                    formatted_query = formatted_query.replace(f"{{{key}}}", str(value))
            
            logger.debug(f"Executing query: {formatted_query[:100]}...")
            result = self.connection.execute(formatted_query).fetchdf()
            logger.info(f"Query returned {len(result)} rows")
            return result
            
        except Exception as e:
            error_msg = f"Analytics query execution failed: {str(e)}"
            context = {
                'query': query[:200] + '...' if len(query) > 200 else query,
                'params_count': len(params),
                'database_path': self.db_path,
                'formatted_query_length': len(formatted_query)
            }
            exc = DatabaseConnectionError(error_msg, 'execute_analytics_query', context=context)
            logger.error("Analytics query execution failed", extra=exc.to_dict())
            logger.error(f"Query: {query}")
            raise exc

    def get_available_symbols(self) -> List[str]:
        """Get list of available stock symbols."""
        query = """
        SELECT DISTINCT symbol
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
            MIN(date) as start_date,
            MAX(date) as end_date
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
        """Find volume spike patterns that lead to breakouts using ConfigManager parameters."""
        # Load parameters from ConfigManager or use defaults
        if self.config_manager:
            try:
                analytics_config = self.config_manager.get_config('analytics')
                query_config = analytics_config.get('queries', {}).get('volume_spike', {})
                min_volume_multiplier = min_volume_multiplier or query_config.get('min_volume_multiplier', 1.5)
                time_window_minutes = time_window_minutes or query_config.get('time_window_minutes', 10)
                min_price_move = min_price_move or query_config.get('min_price_move', 0.03)
            except Exception:
                # Fallback to provided parameters or defaults
                min_volume_multiplier = min_volume_multiplier or 1.5
                time_window_minutes = time_window_minutes or 10
                min_price_move = min_price_move or 0.03
        else:
            min_volume_multiplier = min_volume_multiplier or 1.5
            time_window_minutes = time_window_minutes or 10
            min_price_move = min_price_move or 0.03

        """Find volume spike patterns that lead to breakouts."""

        query = f"""
        WITH volume_analysis AS (
            SELECT
                symbol,
                date,
                ts,
                volume,
                close,
                high,
                -- Rolling volume over {time_window_minutes} minutes
                AVG(volume) OVER (
                    PARTITION BY symbol, date
                    ORDER BY ts
                    ROWS BETWEEN {time_window_minutes - 1} PRECEDING AND CURRENT ROW
                ) as avg_volume_{time_window_minutes}min,

                -- Max high in next 60 minutes
                MAX(high) OVER (
                    PARTITION BY symbol, date
                    ORDER BY ts
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
        """Analyze breakout patterns within specific time windows using ConfigManager."""
        # Load time window parameters from ConfigManager or use defaults
        if self.config_manager:
            try:
                analytics_config = self.config_manager.get_config('analytics')
                dashboard_config = analytics_config.get('dashboard', {})
                start_time = start_time or dashboard_config.get('analysis_start_time', "09:35")
                end_time = end_time or dashboard_config.get('analysis_end_time', "09:50")
            except Exception:
                start_time = start_time or "09:35"
                end_time = end_time or "09:50"
        else:
            start_time = start_time or "09:35"
            end_time = end_time or "09:50"

        """Analyze breakout patterns within specific time windows."""

        query = f"""
        WITH time_window_data AS (
            SELECT
                symbol,
                date,
                ts,
                time(ts) as trade_time,
                open,
                high,
                low,
                close,
                volume,
                -- Pre-window average volume (first 30 minutes)
                AVG(volume) OVER (
                    PARTITION BY symbol, date
                    ORDER BY ts
                    ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
                ) as pre_window_avg_volume,

                -- Post-window max high (next 60 minutes)
                MAX(high) OVER (
                    PARTITION BY symbol, date
                    ORDER BY ts
                    ROWS BETWEEN CURRENT ROW AND 59 FOLLOWING
                ) as post_window_max_high
            FROM parquet_scan('./data/**/*.parquet')
            WHERE time(ts) BETWEEN '{start_time}' AND '{end_time}'
        )
        SELECT
            symbol,
            date,
            trade_time,
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
        """Close DuckDB connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("DuckDB connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
