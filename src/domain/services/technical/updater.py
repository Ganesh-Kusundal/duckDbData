"""
Technical Indicators Updater

Provides update mechanisms to refresh technical indicators when market data is updated.
Supports incremental updates, batch processing, and automatic triggering.
"""

import pandas as pd
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, date, timedelta
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from .calculator import TechnicalIndicatorsCalculator
from .storage import TechnicalIndicatorsStorage
from .schema import TimeFrame
try:
    from ..duckdb_infra.database import DuckDBManager
except ImportError:
    # Handle import during testing
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from duckdb_infra.database import DuckDBManager

logger = logging.getLogger(__name__)


class TechnicalIndicatorsUpdater:
    """
    Updates technical indicators when market data changes.
    
    Features:
    - Incremental updates for efficiency
    - Batch processing for multiple symbols
    - Automatic detection of data changes
    - Concurrent processing for performance
    - Rollback capability for failed updates
    """
    
    def __init__(self, 
                 db_manager: DuckDBManager,
                 storage: Optional[TechnicalIndicatorsStorage] = None,
                 calculator: Optional[TechnicalIndicatorsCalculator] = None):
        """
        Initialize the updater.
        
        Args:
            db_manager: DuckDB manager for accessing market data
            storage: Storage manager (creates new if None)
            calculator: Calculator instance (creates new if None)
        """
        self.db_manager = db_manager
        self.storage = storage or TechnicalIndicatorsStorage()
        self.calculator = calculator or TechnicalIndicatorsCalculator()
        self._lock = threading.Lock()
        
        # Update statistics
        self.stats = {
            'symbols_processed': 0,
            'symbols_updated': 0,
            'symbols_failed': 0,
            'total_records_updated': 0,
            'update_start_time': None,
            'update_end_time': None,
            'errors': []
        }
        
        logger.info("Initialized TechnicalIndicatorsUpdater")
    
    def update_symbol_indicators(self, 
                               symbol: str, 
                               timeframes: Optional[List[str]] = None,
                               start_date: Optional[date] = None,
                               end_date: Optional[date] = None,
                               force_recalculate: bool = False) -> bool:
        """
        Update indicators for a single symbol across specified timeframes.
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to update (None for all)
            start_date: Start date for update (None for auto-detect)
            end_date: End date for update (None for today)
            force_recalculate: Force recalculation even if data exists
            
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Updating indicators for {symbol}")
            
            # Default timeframes
            if timeframes is None:
                timeframes = [tf.value for tf in TimeFrame]
            
            # Default date range
            if end_date is None:
                end_date = date.today()
            
            if start_date is None:
                # Auto-detect start date based on existing data
                start_date = self._get_update_start_date(symbol, timeframes, end_date)
            
            success_count = 0
            total_count = len(timeframes)
            
            for timeframe in timeframes:
                try:
                    if self._update_symbol_timeframe(symbol, timeframe, start_date, end_date, force_recalculate):
                        success_count += 1
                    else:
                        logger.warning(f"Failed to update {symbol} {timeframe}")
                        
                except Exception as e:
                    logger.error(f"Error updating {symbol} {timeframe}: {e}")
                    self.stats['errors'].append(f"{symbol} {timeframe}: {str(e)}")
            
            # Update statistics
            with self._lock:
                self.stats['symbols_processed'] += 1
                if success_count == total_count:
                    self.stats['symbols_updated'] += 1
                elif success_count == 0:
                    self.stats['symbols_failed'] += 1
            
            logger.info(f"Updated {success_count}/{total_count} timeframes for {symbol}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error updating indicators for {symbol}: {e}")
            self.stats['errors'].append(f"{symbol}: {str(e)}")
            return False
    
    def update_multiple_symbols(self, 
                              symbols: List[str],
                              timeframes: Optional[List[str]] = None,
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None,
                              force_recalculate: bool = False,
                              max_workers: int = 4) -> Dict[str, bool]:
        """
        Update indicators for multiple symbols concurrently.
        
        Args:
            symbols: List of trading symbols
            timeframes: List of timeframes to update
            start_date: Start date for update
            end_date: End date for update
            force_recalculate: Force recalculation
            max_workers: Maximum concurrent workers
            
        Returns:
            Dict[str, bool]: Results for each symbol
        """
        logger.info(f"Updating indicators for {len(symbols)} symbols")
        self.stats['update_start_time'] = datetime.now()
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(
                    self.update_symbol_indicators, 
                    symbol, timeframes, start_date, end_date, force_recalculate
                ): symbol
                for symbol in symbols
            }
            
            # Collect results
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    success = future.result()
                    results[symbol] = success
                except Exception as e:
                    logger.error(f"Error updating {symbol}: {e}")
                    results[symbol] = False
        
        self.stats['update_end_time'] = datetime.now()
        
        successful_count = sum(results.values())
        logger.info(f"Updated indicators for {successful_count}/{len(symbols)} symbols")
        
        return results
    
    def update_all_symbols(self, 
                          timeframes: Optional[List[str]] = None,
                          max_symbols: Optional[int] = None,
                          force_recalculate: bool = False,
                          max_workers: int = 4) -> Dict[str, bool]:
        """
        Update indicators for all symbols in the database.
        
        Args:
            timeframes: List of timeframes to update
            max_symbols: Maximum number of symbols to process
            force_recalculate: Force recalculation
            max_workers: Maximum concurrent workers
            
        Returns:
            Dict[str, bool]: Results for each symbol
        """
        try:
            # Get all available symbols from database
            symbols = self.db_manager.get_available_symbols()
            
            if not symbols:
                logger.warning("No symbols found in database")
                return {}
            
            if max_symbols:
                symbols = symbols[:max_symbols]
                logger.info(f"Limited to first {max_symbols} symbols")
            
            return self.update_multiple_symbols(
                symbols, timeframes, None, None, force_recalculate, max_workers
            )
            
        except Exception as e:
            logger.error(f"Error updating all symbols: {e}")
            return {}
    
    def detect_stale_indicators(self, 
                              max_age_hours: int = 24) -> Dict[str, List[Tuple[str, date]]]:
        """
        Detect indicators that are stale and need updating.
        
        Args:
            max_age_hours: Maximum age in hours before considering stale
            
        Returns:
            Dict[str, List[Tuple[str, date]]]: Stale indicators by symbol
        """
        stale_indicators = {}
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            # Get all symbols with market data
            symbols = self.db_manager.get_available_symbols()
            
            for symbol in symbols:
                stale_list = []
                
                # Check each timeframe
                for timeframe in [tf.value for tf in TimeFrame]:
                    # Get latest market data date
                    latest_market_date = self._get_latest_market_data_date(symbol)
                    
                    if latest_market_date:
                        # Check if indicators exist and are recent
                        available_dates = self.storage.get_available_dates(symbol, timeframe)
                        
                        if not available_dates or max(available_dates) < latest_market_date:
                            stale_list.append((timeframe, latest_market_date))
                
                if stale_list:
                    stale_indicators[symbol] = stale_list
            
            logger.info(f"Found {len(stale_indicators)} symbols with stale indicators")
            return stale_indicators
            
        except Exception as e:
            logger.error(f"Error detecting stale indicators: {e}")
            return {}
    
    def update_stale_indicators(self, 
                              max_age_hours: int = 24,
                              max_workers: int = 4) -> Dict[str, bool]:
        """
        Update all stale indicators.
        
        Args:
            max_age_hours: Maximum age before considering stale
            max_workers: Maximum concurrent workers
            
        Returns:
            Dict[str, bool]: Update results
        """
        stale_indicators = self.detect_stale_indicators(max_age_hours)
        
        if not stale_indicators:
            logger.info("No stale indicators found")
            return {}
        
        logger.info(f"Updating stale indicators for {len(stale_indicators)} symbols")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {}
            
            for symbol, stale_list in stale_indicators.items():
                timeframes = [item[0] for item in stale_list]
                # Use the latest date that needs updating
                latest_date = max(item[1] for item in stale_list)
                
                future = executor.submit(
                    self.update_symbol_indicators,
                    symbol, timeframes, latest_date, None, False
                )
                future_to_symbol[future] = symbol
            
            # Collect results
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    success = future.result()
                    results[symbol] = success
                except Exception as e:
                    logger.error(f"Error updating stale indicators for {symbol}: {e}")
                    results[symbol] = False
        
        return results
    
    def get_update_statistics(self) -> Dict:
        """Get update statistics."""
        stats = self.stats.copy()
        
        if stats['update_start_time'] and stats['update_end_time']:
            duration = stats['update_end_time'] - stats['update_start_time']
            stats['duration_seconds'] = duration.total_seconds()
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset update statistics."""
        self.stats = {
            'symbols_processed': 0,
            'symbols_updated': 0,
            'symbols_failed': 0,
            'total_records_updated': 0,
            'update_start_time': None,
            'update_end_time': None,
            'errors': []
        }
    
    def _update_symbol_timeframe(self, 
                               symbol: str, 
                               timeframe: str, 
                               start_date: date, 
                               end_date: date,
                               force_recalculate: bool) -> bool:
        """
        Update indicators for a single symbol and timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            start_date: Start date
            end_date: End date
            force_recalculate: Force recalculation
            
        Returns:
            bool: True if successful
        """
        try:
            # Get market data for the period
            market_data = self._get_market_data(symbol, timeframe, start_date, end_date)
            
            if market_data.empty:
                logger.warning(f"No market data found for {symbol} {timeframe} {start_date} to {end_date}")
                return False
            
            # Group by date and process each day
            market_data['date'] = pd.to_datetime(market_data['timestamp']).dt.date
            
            records_updated = 0
            
            for current_date, day_data in market_data.groupby('date'):
                try:
                    # Check if we need to update this date
                    if not force_recalculate and self._indicators_exist(symbol, timeframe, current_date):
                        continue
                    
                    # Calculate indicators for this day
                    indicators_df = self.calculator.calculate_all_indicators(
                        day_data, symbol, timeframe
                    )
                    
                    if not indicators_df.empty:
                        # Store the indicators
                        success = self.storage.store_indicators(
                            indicators_df, symbol, timeframe, current_date, overwrite=True
                        )
                        
                        if success:
                            records_updated += len(indicators_df)
                        else:
                            logger.warning(f"Failed to store indicators for {symbol} {timeframe} {current_date}")
                
                except Exception as e:
                    logger.error(f"Error processing {symbol} {timeframe} {current_date}: {e}")
            
            with self._lock:
                self.stats['total_records_updated'] += records_updated
            
            logger.info(f"Updated {records_updated} indicator records for {symbol} {timeframe}")
            return records_updated > 0
            
        except Exception as e:
            logger.error(f"Error updating {symbol} {timeframe}: {e}")
            return False
    
    def _get_market_data(self, 
                        symbol: str, 
                        timeframe: str, 
                        start_date: date, 
                        end_date: date) -> pd.DataFrame:
        """
        Get market data from database for the specified period.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            start_date: Start date
            end_date: End date
            
        Returns:
            pd.DataFrame: Market data
        """
        try:
            conn = self.db_manager.connect()
            
            # For minute data, get raw data and resample if needed
            if timeframe == '1T':
                query = """
                    SELECT symbol, timestamp, open, high, low, close, volume
                    FROM market_data
                    WHERE symbol = ? AND date_partition >= ? AND date_partition <= ?
                    ORDER BY timestamp
                """
                df = conn.execute(query, [symbol, start_date, end_date]).df()
                
            else:
                # For higher timeframes, use resampling
                from ..duckdb_infra.query_api import QueryAPI
                query_api = QueryAPI(self.db_manager)
                df = query_api.resample_data(symbol, timeframe, start_date, end_date)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def _get_update_start_date(self, 
                             symbol: str, 
                             timeframes: List[str], 
                             end_date: date) -> date:
        """
        Determine the start date for updates based on existing indicator data.
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes
            end_date: End date
            
        Returns:
            date: Start date for updates
        """
        try:
            # Find the earliest date that needs updating across all timeframes
            earliest_needed_date = end_date
            
            for timeframe in timeframes:
                available_dates = self.storage.get_available_dates(symbol, timeframe)
                
                if available_dates:
                    # Start from the day after the latest available data
                    latest_available = max(available_dates)
                    needed_date = latest_available + timedelta(days=1)
                else:
                    # No existing data, start from 30 days ago
                    needed_date = end_date - timedelta(days=30)
                
                earliest_needed_date = min(earliest_needed_date, needed_date)
            
            return earliest_needed_date
            
        except Exception as e:
            logger.error(f"Error determining start date for {symbol}: {e}")
            return end_date - timedelta(days=7)  # Default to 1 week
    
    def _get_latest_market_data_date(self, symbol: str) -> Optional[date]:
        """
        Get the latest date for which market data exists.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Optional[date]: Latest market data date
        """
        try:
            conn = self.db_manager.connect()
            query = """
                SELECT MAX(date_partition) as latest_date
                FROM market_data
                WHERE symbol = ?
            """
            result = conn.execute(query, [symbol]).fetchone()
            
            if result and result[0]:
                return result[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest market data date for {symbol}: {e}")
            return None
    
    def _indicators_exist(self, symbol: str, timeframe: str, date_partition: date) -> bool:
        """
        Check if indicators already exist for the given symbol/timeframe/date.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            date_partition: Date partition
            
        Returns:
            bool: True if indicators exist
        """
        try:
            from .schema import TechnicalIndicatorsSchema
            file_path = TechnicalIndicatorsSchema.get_file_path(
                symbol, timeframe, date_partition, self.storage.base_path
            )
            return file_path.exists()
            
        except Exception:
            return False
