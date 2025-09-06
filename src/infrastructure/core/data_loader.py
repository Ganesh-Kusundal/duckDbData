"""
Data Loader for DuckDB Financial Infrastructure
Handles bulk loading and data management operations.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .database import DuckDBManager

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Handles bulk data loading operations for the DuckDB financial database.
    
    Features:
    - Parallel loading of multiple symbols
    - Incremental data updates
    - Data validation and error handling
    - Progress tracking and logging
    """
    
    def __init__(self, db_manager: DuckDBManager, max_workers: int = 4):
        """
        Initialize data loader.
        
        Args:
            db_manager: DuckDB manager instance
            max_workers: Maximum number of parallel workers
        """
        self.db_manager = db_manager
        self.max_workers = max_workers
        self._lock = threading.Lock()
        
    def load_all_symbols(self, 
                        start_date: Optional[date] = None, 
                        end_date: Optional[date] = None,
                        symbols: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Load data for all available symbols in parallel.
        
        Args:
            start_date: Start date for loading (optional)
            end_date: End date for loading (optional)
            symbols: Specific symbols to load (optional, loads all if None)
            
        Returns:
            Dictionary mapping symbol to number of records loaded
        """
        # Get symbols to load
        if symbols is None:
            symbols = self.db_manager.get_available_symbols()
        
        logger.info(f"Starting parallel load for {len(symbols)} symbols")
        
        results = {}
        
        # Use ThreadPoolExecutor for parallel loading
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all loading tasks
            future_to_symbol = {
                executor.submit(self.db_manager.load_symbol_data, symbol, start_date, end_date): symbol
                for symbol in symbols
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    records_loaded = future.result()
                    results[symbol] = records_loaded
                    logger.info(f"Completed loading {symbol}: {records_loaded} records")
                except Exception as e:
                    logger.error(f"Failed to load {symbol}: {e}")
                    results[symbol] = 0
        
        total_records = sum(results.values())
        logger.info(f"Parallel loading completed. Total records loaded: {total_records}")
        
        return results
    
    def load_recent_data(self, days: int = 7) -> Dict[str, int]:
        """
        Load recent data for all symbols.
        
        Args:
            days: Number of recent days to load
            
        Returns:
            Dictionary mapping symbol to number of records loaded
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Loading recent data from {start_date} to {end_date}")
        return self.load_all_symbols(start_date, end_date)
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """
        Validate data integrity across the database.
        
        Returns:
            Dictionary with validation results
        """
        conn = self.db_manager.connect()
        
        validation_results = {}
        
        # Check for duplicate records
        duplicates = conn.execute("""
            SELECT symbol, COUNT(*) as duplicate_count
            FROM (
                SELECT symbol, timestamp, COUNT(*) as cnt
                FROM market_data
                GROUP BY symbol, timestamp
                HAVING COUNT(*) > 1
            ) duplicates
            GROUP BY symbol
        """).df()
        
        validation_results['duplicates'] = duplicates.to_dict('records') if not duplicates.empty else []
        
        # Check for missing data gaps
        gaps = conn.execute("""
            WITH date_series AS (
                SELECT DISTINCT date_partition as trading_date
                FROM market_data
                ORDER BY date_partition
            ),
            symbol_dates AS (
                SELECT symbol, date_partition
                FROM market_data
                GROUP BY symbol, date_partition
            ),
            expected_combinations AS (
                SELECT s.symbol, d.trading_date
                FROM (SELECT DISTINCT symbol FROM market_data) s
                CROSS JOIN date_series d
            ),
            missing_data AS (
                SELECT ec.symbol, ec.trading_date
                FROM expected_combinations ec
                LEFT JOIN symbol_dates sd ON ec.symbol = sd.symbol AND ec.trading_date = sd.date_partition
                WHERE sd.symbol IS NULL
            )
            SELECT symbol, COUNT(*) as missing_days
            FROM missing_data
            GROUP BY symbol
            HAVING COUNT(*) > 0
            ORDER BY missing_days DESC
        """).df()
        
        validation_results['missing_data'] = gaps.to_dict('records') if not gaps.empty else []
        
        # Check data quality metrics
        quality_metrics = conn.execute("""
            SELECT 
                symbol,
                COUNT(*) as total_records,
                COUNT(CASE WHEN open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 THEN 1 END) as invalid_prices,
                COUNT(CASE WHEN volume < 0 THEN 1 END) as invalid_volumes,
                COUNT(CASE WHEN high < low THEN 1 END) as invalid_high_low,
                COUNT(CASE WHEN open < low OR open > high OR close < low OR close > high THEN 1 END) as invalid_ohlc
            FROM market_data
            GROUP BY symbol
            HAVING invalid_prices > 0 OR invalid_volumes > 0 OR invalid_high_low > 0 OR invalid_ohlc > 0
        """).df()
        
        validation_results['quality_issues'] = quality_metrics.to_dict('records') if not quality_metrics.empty else []
        
        # Summary statistics
        summary = conn.execute("""
            SELECT 
                COUNT(DISTINCT symbol) as total_symbols,
                COUNT(*) as total_records,
                MIN(date_partition) as earliest_date,
                MAX(date_partition) as latest_date,
                COUNT(DISTINCT date_partition) as trading_days
            FROM market_data
        """).fetchone()
        
        validation_results['summary'] = {
            'total_symbols': summary[0],
            'total_records': summary[1],
            'earliest_date': summary[2],
            'latest_date': summary[3],
            'trading_days': summary[4]
        }
        
        return validation_results
    
    def cleanup_duplicates(self) -> int:
        """
        Remove duplicate records from the database.
        
        Returns:
            Number of duplicate records removed
        """
        conn = self.db_manager.connect()
        
        # Count duplicates before cleanup
        before_count = conn.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
        
        # Remove duplicates keeping the first occurrence
        conn.execute("""
            DELETE FROM market_data
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM market_data
                GROUP BY symbol, timestamp
            )
        """)
        
        # Count after cleanup
        after_count = conn.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
        
        removed_count = before_count - after_count
        logger.info(f"Removed {removed_count} duplicate records")
        
        return removed_count
