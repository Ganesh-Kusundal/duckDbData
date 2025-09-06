"""
Technical Indicators Storage Manager

Handles storage and retrieval of pre-calculated technical indicators in parquet format.
Provides efficient read/write operations with proper partitioning and indexing.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, date, timedelta
from pathlib import Path
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .schema import TechnicalIndicatorsSchema, TimeFrame

logger = logging.getLogger(__name__)


class TechnicalIndicatorsStorage:
    """
    Storage manager for technical indicators data.
    
    Handles:
    - Efficient parquet file storage with partitioning
    - Batch read/write operations
    - Data validation and schema enforcement
    - Concurrent operations for performance
    """
    
    def __init__(self, base_path: Union[str, Path] = "/Users/apple/Downloads/duckDbData/data/technical_indicators"):
        """
        Initialize storage manager.
        
        Args:
            base_path: Base directory for storing technical indicators data
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.schema = TechnicalIndicatorsSchema()
        self._lock = threading.Lock()
        
        logger.info(f"Initialized TechnicalIndicatorsStorage at {self.base_path}")
    
    def store_indicators(self, 
                        df: pd.DataFrame, 
                        symbol: str, 
                        timeframe: str, 
                        date_partition: date,
                        overwrite: bool = True) -> bool:
        """
        Store technical indicators data for a symbol/timeframe/date.
        
        Args:
            df: DataFrame with calculated indicators
            symbol: Trading symbol
            timeframe: Timeframe string
            date_partition: Date for partitioning
            overwrite: Whether to overwrite existing data
            
        Returns:
            bool: True if successful
        """
        try:
            # Validate DataFrame
            if not self.schema.validate_dataframe(df):
                logger.error(f"DataFrame validation failed for {symbol} {timeframe} {date_partition}")
                return False
            
            # Get file path
            file_path = self.schema.get_file_path(symbol, timeframe, date_partition, self.base_path)
            
            # Check if file exists and overwrite flag
            if file_path.exists() and not overwrite:
                logger.info(f"File exists and overwrite=False: {file_path}")
                return True
            
            # Ensure directory exists
            self.schema.ensure_directory_exists(file_path)
            
            # Convert DataFrame to match schema
            df_to_store = self._prepare_dataframe_for_storage(df)
            
            # Write to parquet with compression
            with self._lock:
                table = pa.Table.from_pandas(df_to_store, schema=self.schema.get_parquet_schema())
                pq.write_table(
                    table, 
                    file_path,
                    compression='snappy',
                    use_dictionary=True,
                    row_group_size=10000
                )
            
            logger.info(f"Stored {len(df)} indicators for {symbol} {timeframe} {date_partition}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing indicators for {symbol} {timeframe} {date_partition}: {e}")
            return False
    
    def load_indicators(self, 
                       symbol: str, 
                       timeframe: str, 
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None,
                       columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load technical indicators data for a symbol and timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            columns: Specific columns to load (None for all)
            
        Returns:
            pd.DataFrame: Loaded indicators data
        """
        try:
            # Determine date range
            if start_date is None:
                start_date = date.today() - timedelta(days=30)
            if end_date is None:
                end_date = date.today()
            
            # Collect all relevant files
            file_paths = self._get_file_paths_for_date_range(symbol, timeframe, start_date, end_date)
            
            if not file_paths:
                logger.warning(f"No indicator files found for {symbol} {timeframe} {start_date} to {end_date}")
                return self.schema.create_empty_dataframe()
            
            # Load and combine data
            dataframes = []
            for file_path in file_paths:
                if file_path.exists():
                    try:
                        df = pd.read_parquet(file_path, columns=columns)
                        if not df.empty:
                            dataframes.append(df)
                    except Exception as e:
                        logger.warning(f"Error reading {file_path}: {e}")
            
            if not dataframes:
                return self.schema.create_empty_dataframe()
            
            # Combine and sort
            combined_df = pd.concat(dataframes, ignore_index=True)
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            
            # Filter by date range if needed
            if 'timestamp' in combined_df.columns and not combined_df.empty:
                combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
                
                # For date filtering, check if we need to filter by date
                if 'date_partition' in combined_df.columns:
                    # Use date_partition for filtering if available
                    combined_df['date_partition'] = pd.to_datetime(combined_df['date_partition']).dt.date
                    mask = (combined_df['date_partition'] >= start_date) & (combined_df['date_partition'] <= end_date)
                    combined_df = combined_df[mask]
                else:
                    # Fallback to timestamp filtering
                    start_datetime = pd.to_datetime(start_date)
                    end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                    
                    mask = (combined_df['timestamp'] >= start_datetime) & (combined_df['timestamp'] <= end_datetime)
                    combined_df = combined_df[mask]
            
            logger.info(f"Loaded {len(combined_df)} indicator records for {symbol} {timeframe}")
            return combined_df
            
        except Exception as e:
            logger.error(f"Error loading indicators for {symbol} {timeframe}: {e}")
            return self.schema.create_empty_dataframe()
    
    def load_multiple_symbols(self, 
                             symbols: List[str], 
                             timeframe: str,
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None,
                             columns: Optional[List[str]] = None,
                             max_workers: int = 4) -> Dict[str, pd.DataFrame]:
        """
        Load indicators for multiple symbols concurrently.
        
        Args:
            symbols: List of trading symbols
            timeframe: Timeframe string
            start_date: Start date
            end_date: End date
            columns: Specific columns to load
            max_workers: Maximum number of concurrent workers
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping symbols to their data
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.load_indicators, symbol, timeframe, start_date, end_date, columns): symbol
                for symbol in symbols
            }
            
            # Collect results
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    df = future.result()
                    results[symbol] = df
                except Exception as e:
                    logger.error(f"Error loading indicators for {symbol}: {e}")
                    results[symbol] = self.schema.create_empty_dataframe()
        
        logger.info(f"Loaded indicators for {len(results)} symbols")
        return results
    
    def store_multiple_symbols(self, 
                              data_dict: Dict[str, pd.DataFrame], 
                              timeframe: str,
                              date_partition: date,
                              overwrite: bool = True,
                              max_workers: int = 4) -> Dict[str, bool]:
        """
        Store indicators for multiple symbols concurrently.
        
        Args:
            data_dict: Dictionary mapping symbols to their indicator DataFrames
            timeframe: Timeframe string
            date_partition: Date for partitioning
            overwrite: Whether to overwrite existing data
            max_workers: Maximum number of concurrent workers
            
        Returns:
            Dict[str, bool]: Dictionary mapping symbols to success status
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.store_indicators, df, symbol, timeframe, date_partition, overwrite): symbol
                for symbol, df in data_dict.items()
            }
            
            # Collect results
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    success = future.result()
                    results[symbol] = success
                except Exception as e:
                    logger.error(f"Error storing indicators for {symbol}: {e}")
                    results[symbol] = False
        
        successful_count = sum(results.values())
        logger.info(f"Stored indicators for {successful_count}/{len(results)} symbols")
        return results
    
    def get_available_symbols(self, timeframe: str) -> List[str]:
        """
        Get list of symbols that have indicator data for the given timeframe.
        
        Args:
            timeframe: Timeframe string
            
        Returns:
            List[str]: List of available symbols
        """
        symbols = set()
        
        try:
            timeframe_path = self.base_path
            
            # Walk through directory structure
            for year_dir in timeframe_path.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir():
                        continue
                    
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir():
                            continue
                        
                        tf_dir = day_dir / timeframe
                        if tf_dir.exists() and tf_dir.is_dir():
                            for file_path in tf_dir.glob("*.parquet"):
                                # Extract symbol from filename
                                # Format: {symbol}_indicators_{timeframe}_{date}.parquet
                                filename = file_path.stem
                                
                                # Find 'indicators' keyword and extract symbol
                                if '_indicators_' in filename:
                                    # Split on '_indicators_' to separate symbol from the rest
                                    symbol_part, rest = filename.split('_indicators_', 1)
                                    symbol = symbol_part
                                    symbols.add(symbol)
                                    logger.debug(f"Found symbol {symbol} in {file_path}")
                                else:
                                    logger.debug(f"Skipping file with unexpected format: {filename}")
        
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
        
        return sorted(list(symbols))
    
    def get_available_dates(self, symbol: str, timeframe: str) -> List[date]:
        """
        Get list of dates that have indicator data for the given symbol and timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            
        Returns:
            List[date]: List of available dates
        """
        dates = []
        
        try:
            # Walk through directory structure
            for year_dir in self.base_path.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                
                year = int(year_dir.name)
                
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir() or not month_dir.name.isdigit():
                        continue
                    
                    month = int(month_dir.name)
                    
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir() or not day_dir.name.isdigit():
                            continue
                        
                        day = int(day_dir.name)
                        
                        # Check if file exists for this symbol/timeframe/date
                        file_path = self.schema.get_file_path(symbol, timeframe, date(year, month, day), self.base_path)
                        if file_path.exists():
                            dates.append(date(year, month, day))
        
        except Exception as e:
            logger.error(f"Error getting available dates for {symbol} {timeframe}: {e}")
        
        return sorted(dates)
    
    def delete_indicators(self, 
                         symbol: str, 
                         timeframe: str, 
                         date_partition: date) -> bool:
        """
        Delete indicator data for a specific symbol/timeframe/date.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            date_partition: Date partition
            
        Returns:
            bool: True if successful
        """
        try:
            file_path = self.schema.get_file_path(symbol, timeframe, date_partition, self.base_path)
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted indicators for {symbol} {timeframe} {date_partition}")
                return True
            else:
                logger.warning(f"File not found: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting indicators for {symbol} {timeframe} {date_partition}: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Union[int, float, str]]:
        """
        Get storage statistics.
        
        Returns:
            Dict: Storage statistics
        """
        stats = {
            'total_files': 0,
            'total_size_mb': 0.0,
            'symbols_count': 0,
            'timeframes': [],
            'date_range': {'start': None, 'end': None}
        }
        
        try:
            symbols = set()
            timeframes = set()
            dates = []
            total_size = 0
            
            # Walk through all files
            for file_path in self.base_path.rglob("*.parquet"):
                stats['total_files'] += 1
                total_size += file_path.stat().st_size
                
                # Extract info from path
                parts = file_path.parts
                if len(parts) >= 5:  # .../year/month/day/timeframe/file.parquet
                    timeframe = parts[-2]
                    timeframes.add(timeframe)
                    
                    # Extract symbol from filename using same logic as get_available_symbols
                    filename = file_path.stem
                    if '_indicators_' in filename:
                        # Split on '_indicators_' to separate symbol from the rest
                        symbol_part, rest = filename.split('_indicators_', 1)
                        symbol = symbol_part
                        symbols.add(symbol)
                        
                        # Extract date from the rest part
                        try:
                            # rest should be like "1T_2025-01-01"
                            rest_parts = rest.split('_')
                            if len(rest_parts) >= 2:
                                date_str = rest_parts[-1]  # YYYY-MM-DD
                                file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                                dates.append(file_date)
                        except:
                            pass
            
            stats['total_size_mb'] = total_size / (1024 * 1024)
            stats['symbols_count'] = len(symbols)
            stats['timeframes'] = sorted(list(timeframes))
            
            if dates:
                stats['date_range']['start'] = min(dates).isoformat()
                stats['date_range']['end'] = max(dates).isoformat()
        
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
        
        return stats
    
    def _prepare_dataframe_for_storage(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare DataFrame for storage by ensuring proper types and schema compliance.
        
        Args:
            df: Input DataFrame
            
        Returns:
            pd.DataFrame: Prepared DataFrame
        """
        df_copy = df.copy()
        
        # Ensure timestamp is datetime
        if 'timestamp' in df_copy.columns:
            df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
        
        # Ensure date_partition is date
        if 'date_partition' in df_copy.columns:
            if df_copy['date_partition'].dtype == 'object':
                # If it's already date objects, keep as is
                pass
            else:
                df_copy['date_partition'] = pd.to_datetime(df_copy['date_partition']).dt.date
        
        # Ensure calculation_timestamp is datetime
        if 'calculation_timestamp' in df_copy.columns:
            df_copy['calculation_timestamp'] = pd.to_datetime(df_copy['calculation_timestamp'])
        
        # Fill missing columns with None
        schema_columns = self.schema.get_column_names()
        for col in schema_columns:
            if col not in df_copy.columns:
                df_copy[col] = None
        
        # Reorder columns to match schema
        df_copy = df_copy[schema_columns]
        
        return df_copy
    
    def _get_file_paths_for_date_range(self, 
                                      symbol: str, 
                                      timeframe: str, 
                                      start_date: date, 
                                      end_date: date) -> List[Path]:
        """
        Get list of file paths for a date range.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            start_date: Start date
            end_date: End date
            
        Returns:
            List[Path]: List of file paths
        """
        file_paths = []
        current_date = start_date
        
        while current_date <= end_date:
            file_path = self.schema.get_file_path(symbol, timeframe, current_date, self.base_path)
            file_paths.append(file_path)
            current_date += timedelta(days=1)
        
        return file_paths
