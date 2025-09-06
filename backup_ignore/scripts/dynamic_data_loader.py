#!/usr/bin/env python3
"""
Dynamic Data Loader
===================

Automatically discovers and loads all available symbols and dates from parquet files.
Adapts to whatever data structure exists in the filesystem.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import argparse
from typing import List, Optional, Dict, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.duckdb_infra import DuckDBManager

class DynamicDataLoader:
    """Dynamic loader that discovers and loads all available parquet data."""
    
    def __init__(self, data_root: str = "/Users/apple/Downloads/duckDbData/data"):
        self.data_root = Path(data_root)
        self.db_manager = None
        self._lock = threading.Lock()
        self.stats = {
            'symbols_discovered': 0,
            'dates_discovered': 0,
            'files_processed': 0,
            'records_loaded': 0,
            'errors': [],
            'skipped_duplicates': 0
        }
    
    def discover_all_data(self) -> Dict[str, List[date]]:
        """
        Dynamically discover all available symbols and their date ranges.
        
        Returns:
            Dictionary mapping symbol -> list of available dates
        """
        print("🔍 DYNAMICALLY DISCOVERING ALL AVAILABLE DATA...")
        print("="*60)
        
        symbol_dates = {}
        total_files = 0
        
        # Scan all year directories
        for year_dir in sorted(self.data_root.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
                
            year = int(year_dir.name)
            print(f"📅 Scanning year {year}...")
            
            # Scan all month directories
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue
                    
                month = int(month_dir.name)
                
                # Scan all day directories
                for day_dir in sorted(month_dir.iterdir()):
                    if not day_dir.is_dir() or not day_dir.name.isdigit():
                        continue
                        
                    day = int(day_dir.name)
                    
                    try:
                        target_date = date(year, month, day)
                    except ValueError:
                        continue  # Invalid date
                    
                    # Scan parquet files in this date directory
                    parquet_files = list(day_dir.glob("*_minute_*.parquet"))
                    
                    for file_path in parquet_files:
                        # Extract symbol from filename
                        filename = file_path.stem
                        parts = filename.split('_minute_')
                        
                        if len(parts) == 2:
                            symbol = parts[0]
                            
                            if symbol not in symbol_dates:
                                symbol_dates[symbol] = []
                            
                            symbol_dates[symbol].append(target_date)
                            total_files += 1
        
        # Sort dates for each symbol
        for symbol in symbol_dates:
            symbol_dates[symbol] = sorted(list(set(symbol_dates[symbol])))
        
        self.stats['symbols_discovered'] = len(symbol_dates)
        self.stats['dates_discovered'] = len(set(date for dates in symbol_dates.values() for date in dates))
        
        print(f"✅ Discovery complete!")
        print(f"   📈 Symbols found: {len(symbol_dates)}")
        print(f"   📅 Unique dates: {self.stats['dates_discovered']}")
        print(f"   📁 Total files: {total_files}")
        
        if symbol_dates:
            all_dates = [date for dates in symbol_dates.values() for date in dates]
            print(f"   📊 Date range: {min(all_dates)} to {max(all_dates)}")
        
        return symbol_dates
    
    def get_existing_data(self) -> Dict[str, Set[date]]:
        """Get symbols and dates already in the database."""
        if not self.db_manager:
            return {}
        
        try:
            query = """
            SELECT DISTINCT symbol, DATE(timestamp) as date
            FROM market_data
            """
            result = self.db_manager.execute_custom_query(query)
            
            existing = {}
            for _, row in result.iterrows():
                symbol = row['symbol']
                date_val = pd.to_datetime(row['date']).date()
                
                if symbol not in existing:
                    existing[symbol] = set()
                existing[symbol].add(date_val)
            
            return existing
            
        except Exception as e:
            print(f"⚠️  Could not check existing data: {e}")
            return {}
    
    def load_symbol_date_file(self, symbol: str, target_date: date) -> int:
        """Load a single symbol-date combination."""
        year = target_date.year
        month = target_date.month
        day = target_date.day
        
        file_path = self.data_root / str(year) / f"{month:02d}" / f"{day:02d}" / f"{symbol}_minute_{target_date}.parquet"
        
        if not file_path.exists():
            return 0
        
        try:
            # Read parquet file
            df = pd.read_parquet(file_path)
            
            if df.empty:
                return 0
            
            # Add metadata columns
            df['symbol'] = symbol
            df['date_partition'] = target_date
            
            # Create timestamp from index
            df = df.reset_index(drop=True)
            market_open = pd.to_datetime(f"{target_date} 09:15:00")
            df['timestamp'] = market_open + pd.to_timedelta(df.index, unit='m')
            
            # Reorder columns
            df = df[['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'date_partition']]
            
            # Insert into database with duplicate checking
            with self._lock:
                conn = self.db_manager.connect()
                
                # Check for existing data
                check_query = """
                SELECT COUNT(*) as count 
                FROM market_data 
                WHERE symbol = ? AND DATE(timestamp) = ?
                """
                existing = conn.execute(check_query, [symbol, str(target_date)]).fetchone()[0]
                
                if existing > 0:
                    self.stats['skipped_duplicates'] += 1
                    return 0
                
                # Insert new data
                conn.register('temp_data', df)
                conn.execute("INSERT INTO market_data SELECT * FROM temp_data")
                conn.unregister('temp_data')
                
                return len(df)
                
        except Exception as e:
            error_msg = f"Error loading {file_path}: {e}"
            with self._lock:
                self.stats['errors'].append(error_msg)
            return 0
    
    def load_data_parallel(self, 
                          symbol_dates: Dict[str, List[date]], 
                          max_workers: int = 4,
                          batch_size: int = 100) -> bool:
        """Load data in parallel with progress tracking."""
        
        # Prepare work items
        work_items = []
        for symbol, dates in symbol_dates.items():
            for target_date in dates:
                work_items.append((symbol, target_date))
        
        total_items = len(work_items)
        print(f"🚀 Starting parallel loading of {total_items} items with {max_workers} workers...")
        
        completed = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit work in batches
            for i in range(0, total_items, batch_size):
                batch = work_items[i:i+batch_size]
                
                # Submit batch
                future_to_item = {
                    executor.submit(self.load_symbol_date_file, symbol, target_date): (symbol, target_date)
                    for symbol, target_date in batch
                }
                
                # Process results
                for future in as_completed(future_to_item):
                    symbol, target_date = future_to_item[future]
                    
                    try:
                        records = future.result()
                        if records > 0:
                            with self._lock:
                                self.stats['records_loaded'] += records
                                self.stats['files_processed'] += 1
                        
                    except Exception as e:
                        error_msg = f"Failed {symbol} {target_date}: {e}"
                        with self._lock:
                            self.stats['errors'].append(error_msg)
                    
                    completed += 1
                    
                    # Progress update
                    if completed % 100 == 0 or completed == total_items:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (total_items - completed) / rate if rate > 0 else 0
                        
                        print(f"📊 Progress: {completed}/{total_items} ({completed/total_items*100:.1f}%) "
                              f"| Rate: {rate:.1f}/sec | ETA: {eta/60:.1f}min | "
                              f"Records: {self.stats['records_loaded']:,}")
        
        return len(self.stats['errors']) == 0
    
    def smart_load(self, 
                   start_date: Optional[date] = None,
                   end_date: Optional[date] = None,
                   symbols: Optional[List[str]] = None,
                   max_workers: int = 4,
                   skip_existing: bool = True) -> bool:
        """
        Smart loading that discovers data and loads efficiently.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter  
            symbols: Optional symbol filter
            max_workers: Number of parallel workers
            skip_existing: Skip data already in database
            
        Returns:
            True if successful
        """
        print("🤖 SMART DYNAMIC DATA LOADING")
        print("="*50)
        print(f"🕐 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Initialize database
        self.db_manager = DuckDBManager()
        self.db_manager.create_schema()
        
        # Discover all available data
        all_symbol_dates = self.discover_all_data()
        
        if not all_symbol_dates:
            print("❌ No data discovered!")
            return False
        
        # Apply filters
        filtered_symbol_dates = {}
        
        for symbol, dates in all_symbol_dates.items():
            # Filter by symbols
            if symbols and symbol not in symbols:
                continue
            
            # Filter by date range
            filtered_dates = dates
            if start_date:
                filtered_dates = [d for d in filtered_dates if d >= start_date]
            if end_date:
                filtered_dates = [d for d in filtered_dates if d <= end_date]
            
            if filtered_dates:
                filtered_symbol_dates[symbol] = filtered_dates
        
        print(f"\n📊 AFTER FILTERING:")
        print(f"   📈 Symbols: {len(filtered_symbol_dates)}")
        total_files = sum(len(dates) for dates in filtered_symbol_dates.values())
        print(f"   📁 Files to process: {total_files}")
        
        if filtered_symbol_dates:
            all_dates = [date for dates in filtered_symbol_dates.values() for date in dates]
            print(f"   📅 Date range: {min(all_dates)} to {max(all_dates)}")
        
        # Check existing data if requested
        if skip_existing:
            print(f"\n🔍 Checking existing data in database...")
            existing_data = self.get_existing_data()
            
            # Remove already loaded data
            for symbol in list(filtered_symbol_dates.keys()):
                if symbol in existing_data:
                    original_count = len(filtered_symbol_dates[symbol])
                    filtered_symbol_dates[symbol] = [
                        d for d in filtered_symbol_dates[symbol] 
                        if d not in existing_data[symbol]
                    ]
                    removed = original_count - len(filtered_symbol_dates[symbol])
                    if removed > 0:
                        print(f"   ⏭️  {symbol}: skipping {removed} existing dates")
                    
                    # Remove symbol if no dates left
                    if not filtered_symbol_dates[symbol]:
                        del filtered_symbol_dates[symbol]
            
            remaining_files = sum(len(dates) for dates in filtered_symbol_dates.values())
            print(f"   📁 Files remaining after dedup: {remaining_files}")
        
        if not filtered_symbol_dates:
            print("✅ All data already loaded!")
            return True
        
        # Confirm loading
        print(f"\n❓ Proceed with loading {len(filtered_symbol_dates)} symbols? (y/N): ", end="")
        confirm = input().strip().lower()
        if confirm != 'y':
            print("⚠️  Operation cancelled")
            return False
        
        # Start loading
        success = self.load_data_parallel(filtered_symbol_dates, max_workers)
        
        # Print final summary
        print(f"\n{'='*60}")
        print(f"📊 LOADING SUMMARY")
        print(f"{'='*60}")
        print(f"🕐 Duration: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 Symbols processed: {len(filtered_symbol_dates)}")
        print(f"📁 Files processed: {self.stats['files_processed']}")
        print(f"📊 Records loaded: {self.stats['records_loaded']:,}")
        print(f"⏭️  Duplicates skipped: {self.stats['skipped_duplicates']}")
        
        if self.stats['errors']:
            print(f"❌ Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"   {error}")
            if len(self.stats['errors']) > 5:
                print(f"   ... and {len(self.stats['errors']) - 5} more errors")
        
        print(f"{'='*60}")
        
        return success

def main():
    """Main function with command line arguments."""
    parser = argparse.ArgumentParser(description='Dynamic data loader - discovers and loads all available data')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to load')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--max-workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--include-existing', action='store_true', help='Include data already in database')
    parser.add_argument('--data-root', default='/Users/apple/Downloads/duckDbData', help='Root directory')
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = None
    end_date = None
    
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"❌ Invalid start date: {args.start_date}")
            sys.exit(1)
    
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"❌ Invalid end date: {args.end_date}")
            sys.exit(1)
    
    try:
        loader = DynamicDataLoader(args.data_root)
        
        success = loader.smart_load(
            start_date=start_date,
            end_date=end_date,
            symbols=args.symbols,
            max_workers=args.max_workers,
            skip_existing=not args.include_existing
        )
        
        if success:
            print("\n🎉 Dynamic loading completed successfully!")
        else:
            print("\n⚠️  Loading completed with errors")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
