"""
Advanced Query API for DuckDB Financial Infrastructure
Supports complex queries, resampling, and analytical operations.
"""

import pandas as pd
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime, timedelta
import logging
from enum import Enum

from .database import DuckDBManager

logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """Supported timeframes for resampling."""
    MINUTE_1 = "1T"
    MINUTE_5 = "5T"
    MINUTE_15 = "15T"
    MINUTE_30 = "30T"
    HOUR_1 = "1H"
    HOUR_4 = "4H"
    DAILY = "1D"
    WEEKLY = "1W"
    MONTHLY = "1M"


class QueryAPI:
    """
    Advanced query interface for financial data with resampling and analytical capabilities.
    
    Features:
    - Data resampling to higher timeframes
    - Technical indicators calculation
    - Complex analytical queries
    - Performance optimization
    """
    
    def __init__(self, db_manager: DuckDBManager):
        """
        Initialize query API.
        
        Args:
            db_manager: DuckDB manager instance
        """
        self.db_manager = db_manager
    
    def resample_data(self, 
                     symbol: str,
                     timeframe: Union[TimeFrame, str],
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None,
                     start_time: Optional[str] = None,
                     end_time: Optional[str] = None) -> pd.DataFrame:
        """
        Resample minute data to higher timeframes.
        
        Args:
            symbol: Symbol to query
            timeframe: Target timeframe (TimeFrame enum or string)
            start_date: Start date filter
            end_date: End date filter
            start_time: Start time filter (HH:MM format)
            end_time: End time filter (HH:MM format)
            
        Returns:
            DataFrame with resampled OHLCV data
        """
        conn = self.db_manager.connect()
        
        # Convert timeframe to string if enum
        if isinstance(timeframe, TimeFrame):
            tf_str = timeframe.value
        else:
            tf_str = timeframe
        
        # Build base query with filters
        where_clauses = ["symbol = ?"]
        params = [symbol]
        
        if start_date:
            where_clauses.append("date_partition >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("date_partition <= ?")
            params.append(end_date)
        
        if start_time:
            where_clauses.append("TIME(timestamp) >= ?")
            params.append(start_time)
        
        if end_time:
            where_clauses.append("TIME(timestamp) <= ?")
            params.append(end_time)
        
        where_clause = " AND ".join(where_clauses)
        
        # Use DuckDB's time_bucket function for efficient resampling
        if tf_str in ["5T", "15T", "30T"]:
            # For minute-based intervals
            minutes = int(tf_str.replace("T", ""))
            bucket_sql = f"time_bucket(INTERVAL '{minutes} minutes', timestamp)"
        elif tf_str in ["1H", "4H"]:
            # For hour-based intervals
            hours = int(tf_str.replace("H", ""))
            bucket_sql = f"time_bucket(INTERVAL '{hours} hours', timestamp)"
        elif tf_str == "1D":
            bucket_sql = "time_bucket(INTERVAL '1 day', timestamp)"
        elif tf_str == "1W":
            bucket_sql = "time_bucket(INTERVAL '1 week', timestamp)"
        elif tf_str == "1M":
            bucket_sql = "time_bucket(INTERVAL '1 month', timestamp)"
        else:
            raise ValueError(f"Unsupported timeframe: {tf_str}")
        
        query = f"""
            SELECT 
                symbol,
                {bucket_sql} as timestamp,
                FIRST(open ORDER BY timestamp) as open,
                MAX(high) as high,
                MIN(low) as low,
                LAST(close ORDER BY timestamp) as close,
                SUM(volume) as volume,
                COUNT(*) as tick_count
            FROM market_data_unified
            WHERE {where_clause}
            GROUP BY symbol, {bucket_sql}
            ORDER BY timestamp
        """
        
        df = conn.execute(query, params).df()
        
        if not df.empty:
            df['timeframe'] = tf_str
        
        logger.info(f"Resampled {symbol} to {tf_str}: {len(df)} periods")
        return df
    
    def get_multiple_timeframes(self,
                              symbol: str,
                              timeframes: List[Union[TimeFrame, str]],
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple timeframes simultaneously.
        
        Args:
            symbol: Symbol to query
            timeframes: List of timeframes to resample to
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Dictionary mapping timeframe to DataFrame
        """
        results = {}
        
        for tf in timeframes:
            tf_str = tf.value if isinstance(tf, TimeFrame) else tf
            try:
                results[tf_str] = self.resample_data(symbol, tf, start_date, end_date)
            except Exception as e:
                logger.error(f"Failed to resample {symbol} to {tf_str}: {e}")
                results[tf_str] = pd.DataFrame()
        
        return results
    
    def calculate_technical_indicators(self,
                                     symbol: str,
                                     timeframe: Union[TimeFrame, str] = TimeFrame.MINUTE_1,
                                     start_date: Optional[date] = None,
                                     end_date: Optional[date] = None,
                                     indicators: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Calculate technical indicators using SQL window functions.
        
        Args:
            symbol: Symbol to analyze
            timeframe: Timeframe for analysis
            start_date: Start date filter
            end_date: End date filter
            indicators: List of indicators to calculate (default: common ones)
            
        Returns:
            DataFrame with OHLCV data and technical indicators
        """
        conn = self.db_manager.connect()
        
        # Default indicators if none specified
        if indicators is None:
            indicators = ['sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi_14', 'bollinger_bands']
        
        # Get base resampled data if not minute timeframe
        if timeframe != TimeFrame.MINUTE_1 and timeframe != "1T":
            base_df = self.resample_data(symbol, timeframe, start_date, end_date)
            if base_df.empty:
                return base_df
            
            # Create temporary view for calculations
            conn.execute("DROP VIEW IF EXISTS temp_data")
            conn.execute("CREATE TEMPORARY VIEW temp_data AS SELECT * FROM base_df")
            data_source = "temp_data"
        else:
            # Use original data
            where_clauses = ["symbol = ?"]
            params = [symbol]
            
            if start_date:
                where_clauses.append("date_partition >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("date_partition <= ?")
                params.append(end_date)
            
            where_clause = " AND ".join(where_clauses)
            data_source = f"(SELECT * FROM market_data_unified WHERE {where_clause})"
        
        # Build indicator calculations
        indicator_calcs = []
        
        if 'sma_20' in indicators:
            indicator_calcs.append("AVG(close) OVER (ORDER BY timestamp ROWS 19 PRECEDING) as sma_20")
        
        if 'sma_50' in indicators:
            indicator_calcs.append("AVG(close) OVER (ORDER BY timestamp ROWS 49 PRECEDING) as sma_50")
        
        if 'ema_12' in indicators:
            # Exponential moving average approximation
            indicator_calcs.append("""
                EXP(AVG(LN(close)) OVER (ORDER BY timestamp ROWS 11 PRECEDING)) as ema_12_approx
            """)
        
        if 'rsi_14' in indicators:
            # Simplified RSI calculation (approximation)
            indicator_calcs.append("""
                CASE 
                    WHEN STDDEV(close) OVER (ORDER BY timestamp ROWS 13 PRECEDING) = 0 THEN 50
                    ELSE 50 + 50 * (
                        (close - AVG(close) OVER (ORDER BY timestamp ROWS 13 PRECEDING)) / 
                        STDDEV(close) OVER (ORDER BY timestamp ROWS 13 PRECEDING)
                    )
                END as rsi_14
            """)
        
        if 'bollinger_bands' in indicators:
            indicator_calcs.extend([
                "AVG(close) OVER (ORDER BY timestamp ROWS 19 PRECEDING) + 2 * STDDEV(close) OVER (ORDER BY timestamp ROWS 19 PRECEDING) as bb_upper",
                "AVG(close) OVER (ORDER BY timestamp ROWS 19 PRECEDING) as bb_middle",
                "AVG(close) OVER (ORDER BY timestamp ROWS 19 PRECEDING) - 2 * STDDEV(close) OVER (ORDER BY timestamp ROWS 19 PRECEDING) as bb_lower"
            ])
        
        # Add price change indicators
        indicator_calcs.extend([
            "close - LAG(close) OVER (ORDER BY timestamp) as price_change",
            "(close - LAG(close) OVER (ORDER BY timestamp)) / LAG(close) OVER (ORDER BY timestamp) * 100 as price_change_pct",
            "high - low as daily_range",
            "(high - low) / close * 100 as daily_range_pct"
        ])
        
        # Build final query
        base_columns = "symbol, timestamp, open, high, low, close, volume"
        if timeframe != TimeFrame.MINUTE_1:
            base_columns += ", tick_count"
        
        indicators_sql = ", ".join(indicator_calcs)
        
        query = f"""
            SELECT 
                {base_columns},
                {indicators_sql}
            FROM {data_source}
            ORDER BY timestamp
        """
        
        if timeframe == TimeFrame.MINUTE_1:
            df = conn.execute(query, params).df()
        else:
            df = conn.execute(query).df()
        
        logger.info(f"Calculated technical indicators for {symbol} ({timeframe}): {len(df)} periods")
        return df
    
    def get_market_summary(self,
                          symbols: Optional[List[str]] = None,
                          date_filter: Optional[date] = None) -> pd.DataFrame:
        """
        Get market summary statistics for symbols.
        
        Args:
            symbols: List of symbols (optional, uses all if None)
            date_filter: Specific date to analyze (optional, uses latest if None)
            
        Returns:
            DataFrame with market summary statistics
        """
        conn = self.db_manager.connect()
        
        where_clauses = []
        params = []
        
        if symbols:
            placeholders = ",".join(["?" for _ in symbols])
            where_clauses.append(f"symbol IN ({placeholders})")
            params.extend(symbols)
        
        if date_filter:
            where_clauses.append("date_partition = ?")
            params.append(date_filter)
        else:
            # Use latest available date
            where_clauses.append("date_partition = (SELECT MAX(date_partition) FROM market_data_unified)")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Add all parameters for the query
        all_params = params + params  # Duplicate params for the two subqueries
        
        query = f"""
            SELECT 
                symbol,
                date_partition as trading_date,
                FIRST(open ORDER BY timestamp) as day_open,
                MAX(high) as day_high,
                MIN(low) as day_low,
                LAST(close ORDER BY timestamp) as day_close,
                SUM(volume) as total_volume,
                COUNT(*) as total_ticks,
                LAST(close ORDER BY timestamp) - FIRST(open ORDER BY timestamp) as day_change,
                (LAST(close ORDER BY timestamp) - FIRST(open ORDER BY timestamp)) / FIRST(open ORDER BY timestamp) * 100 as day_change_pct,
                MAX(high) - MIN(low) as day_range,
                (MAX(high) - MIN(low)) / LAST(close ORDER BY timestamp) * 100 as day_range_pct,
                AVG(volume) as avg_volume_per_minute,
                STDDEV(close) as price_volatility
            FROM market_data_unified
            WHERE {where_clause}
            GROUP BY symbol, date_partition
            ORDER BY day_change_pct DESC
        """
        
        df = conn.execute(query, params).df()
        logger.info(f"Generated market summary for {len(df)} symbols")
        return df
    
    def get_correlation_matrix(self,
                             symbols: List[str],
                             timeframe: Union[TimeFrame, str] = TimeFrame.DAILY,
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None,
                             method: str = 'returns') -> pd.DataFrame:
        """
        Calculate correlation matrix between symbols.
        
        Args:
            symbols: List of symbols to analyze
            timeframe: Timeframe for correlation analysis
            start_date: Start date filter
            end_date: End date filter
            method: 'returns' or 'prices'
            
        Returns:
            Correlation matrix as DataFrame
        """
        # Get data for all symbols
        all_data = []
        
        for symbol in symbols:
            df = self.resample_data(symbol, timeframe, start_date, end_date)
            if not df.empty:
                if method == 'returns':
                    df['value'] = df['close'].pct_change()
                else:
                    df['value'] = df['close']
                
                df = df[['timestamp', 'value']].rename(columns={'value': symbol})
                all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        # Merge all data on timestamp
        merged_df = all_data[0]
        for df in all_data[1:]:
            merged_df = merged_df.merge(df, on='timestamp', how='outer')
        
        # Calculate correlation matrix
        correlation_matrix = merged_df.drop('timestamp', axis=1).corr()
        
        logger.info(f"Calculated correlation matrix for {len(symbols)} symbols")
        return correlation_matrix
    
    def execute_custom_analytical_query(self, query: str, params: Optional[List] = None) -> pd.DataFrame:
        """
        Execute custom analytical SQL queries with full DuckDB capabilities.
        
        Args:
            query: Custom SQL query
            params: Query parameters
            
        Returns:
            Query results as DataFrame
        """
        conn = self.db_manager.connect()
        
        try:
            result = conn.execute(query, params or []).df()
            logger.info(f"Executed custom query, returned {len(result)} rows")
            return result
        except Exception as e:
            logger.error(f"Custom query failed: {e}")
            raise
    
    def get_volume_profile(self,
                          symbol: str,
                          start_date: Optional[date] = None,
                          end_date: Optional[date] = None,
                          price_bins: int = 50) -> pd.DataFrame:
        """
        Calculate volume profile (volume at price levels).
        
        Args:
            symbol: Symbol to analyze
            start_date: Start date filter
            end_date: End date filter
            price_bins: Number of price bins
            
        Returns:
            DataFrame with volume profile data
        """
        conn = self.db_manager.connect()
        
        where_clauses = ["symbol = ?"]
        params = [symbol]
        
        if start_date:
            where_clauses.append("date_partition >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("date_partition <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
            WITH price_range AS (
                SELECT 
                    MIN(low) as min_price,
                    MAX(high) as max_price,
                    (MAX(high) - MIN(low)) / {price_bins} as bin_size
                FROM market_data
                WHERE {where_clause}
            ),
            binned_data AS (
                SELECT 
                    FLOOR((close - pr.min_price) / pr.bin_size) as price_bin,
                    pr.min_price + (FLOOR((close - pr.min_price) / pr.bin_size) * pr.bin_size) as price_level,
                    pr.min_price + ((FLOOR((close - pr.min_price) / pr.bin_size) + 1) * pr.bin_size) as price_level_upper,
                    volume,
                    close
                FROM market_data md
                CROSS JOIN price_range pr
                WHERE md.symbol = ? AND md.date_partition >= COALESCE(?, md.date_partition) AND md.date_partition <= COALESCE(?, md.date_partition)
            )
            SELECT 
                price_bin,
                price_level,
                price_level_upper,
                (price_level + price_level_upper) / 2 as price_midpoint,
                SUM(volume) as total_volume,
                COUNT(*) as tick_count,
                AVG(close) as avg_price,
                MIN(close) as min_price,
                MAX(close) as max_price
            FROM binned_data
            GROUP BY price_bin, price_level, price_level_upper
            ORDER BY price_level
        """
        
        # Prepare parameters for volume profile query
        volume_params = [symbol, start_date, end_date]
        df = conn.execute(query, volume_params).df()
        logger.info(f"Calculated volume profile for {symbol}: {len(df)} price levels")
        return df
