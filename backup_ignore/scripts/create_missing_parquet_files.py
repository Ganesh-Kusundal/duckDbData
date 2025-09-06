#!/usr/bin/env python3
"""
Create Missing Parquet Files for August-September 2025

This script fetches data from Dhan API and saves it directly as parquet files
in the same format and structure as existing files in /data/2025/.

Author: AI Assistant
Date: 2025-09-03
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import logging
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

from core.duckdb_infra.database import DuckDBManager
from broker import get_broker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ParquetFileCreator:
    """Creates per-day parquet files for requested date range"""
    
    def __init__(self, data_root: str = "/Users/apple/Downloads/duckDbData/data", start_date: Optional[date] = None, end_date: Optional[date] = None):
        """Initialize the parquet file creator
        
        Args:
            data_root: Root folder containing year/month/day structure
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        """
        # Load environment variables
        load_dotenv('config/.env')
        
        # Initialize database to get symbol list
        self.db_manager = DuckDBManager()
        
        # Initialize broker
        self.broker = get_broker()
        if not self.broker:
            raise ValueError("Failed to initialize broker")
        logger.info("✅ Initialized broker connection")

        # Set up paths
        self.data_root = Path(data_root)

        # Date window
        self.start_date = start_date or date(2025, 8, 1)
        self.end_date = end_date or date(2025, 9, 4)

        # Create month paths
        self.aug_path = self.data_root / "2025" / "08"
        self.sep_path = self.data_root / "2025" / "09"
        
        # Statistics
        self.stats = {
            'symbols_processed': 0,
            'symbols_success': 0,
            'symbols_failed': 0,
            'files_created': 0,
            'total_records': 0,
            'errors': []
        }
    
    def get_symbols_from_database(self) -> List[str]:
        """Get list of symbols from database"""
        logger.info("🔍 Getting symbols from database...")
        
        query = "SELECT DISTINCT symbol FROM market_data ORDER BY symbol"
        result = self.db_manager.execute_custom_query(query)
        symbols = result['symbol'].tolist()
        
        logger.info(f"📊 Found {len(symbols)} symbols in database")
        return symbols
    
    def fetch_symbol_data(self, symbol: str, start_date: date, end_date: date) -> Optional[pd.DataFrame]:
        """Fetch data for a symbol from Dhan API"""
        try:
            logger.info(f"📊 Fetching {symbol} data from {start_date} to {end_date}")
            
            # Get data using broker approach
            data = self.broker.get_historical_data(
                symbol, 'NSE', 'day',
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if data is None or len(data) == 0:
                logger.warning(f"⚠️ No data returned for {symbol}")
                return None
            
            # Convert to DataFrame if needed
            df = pd.DataFrame(data) if not isinstance(data, pd.DataFrame) else data
            
            # Ensure timestamp column exists and is properly formatted
            if 'timestamp' not in df.columns:
                logger.error(f"❌ No timestamp column in data for {symbol}")
                return None
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter data to the requested date range
            df = df[
                (df['timestamp'].dt.date >= start_date) & 
                (df['timestamp'].dt.date <= end_date)
            ]
            
            if len(df) == 0:
                logger.warning(f"⚠️ No data in requested date range for {symbol}")
                return None
            
            logger.info(f"✅ Got {len(df)} records for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            self.stats['errors'].append(f"{symbol}: {str(e)}")
            return None
    
    def create_parquet_files_for_symbol(self, symbol: str, df: pd.DataFrame) -> int:
        """Create parquet files for a symbol, organized by date"""
        files_created = 0
        
        try:
            # Group data by date
            df['date'] = df['timestamp'].dt.date
            grouped = df.groupby('date')
            
            for date_val, day_data in grouped:
                # Create YYYY/MM/DD directory
                year_path = self.data_root / f"{date_val.year}"
                month_path = year_path / f"{date_val.month:02d}"
                day_path = month_path / f"{date_val.day:02d}"
                day_path.mkdir(parents=True, exist_ok=True)
                
                # Prepare data in the same format as existing files
                # Remove timezone info and keep only OHLCV columns
                day_data_clean = day_data.copy()
                day_data_clean['timestamp'] = day_data_clean['timestamp'].dt.tz_localize(None)
                
                # Select only the required columns in the correct order
                columns_to_save = ['open', 'high', 'low', 'close', 'volume']
                day_data_final = day_data_clean[columns_to_save].copy()
                
                # Create filename in the same format as existing files
                filename = f"{symbol}_minute_{date_val}.parquet"
                file_path = day_path / filename
                
                # Save as parquet file
                day_data_final.to_parquet(file_path, index=False)
                
                logger.info(f"✅ Created {file_path} ({len(day_data_final)} records)")
                files_created += 1
                self.stats['total_records'] += len(day_data_final)
            
            return files_created
            
        except Exception as e:
            logger.error(f"❌ Error creating parquet files for {symbol}: {e}")
            self.stats['errors'].append(f"{symbol} parquet creation: {str(e)}")
            return 0
    
    def process_symbol(self, symbol: str) -> bool:
        """Process a single symbol - fetch data and create parquet files"""
        try:
            # Define requested date range
            start_date = self.start_date
            end_date = self.end_date
            
            # Fetch data from API
            df = self.fetch_symbol_data(symbol, start_date, end_date)
            
            if df is None or len(df) == 0:
                logger.warning(f"⚠️ No data available for {symbol}")
                return False
            
            # Create parquet files
            files_created = self.create_parquet_files_for_symbol(symbol, df)
            
            if files_created > 0:
                logger.info(f"✅ Created {files_created} parquet files for {symbol}")
                self.stats['files_created'] += files_created
                self.stats['symbols_success'] += 1
                return True
            else:
                logger.warning(f"⚠️ No files created for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error processing {symbol}: {e}")
            self.stats['errors'].append(f"{symbol}: {str(e)}")
            self.stats['symbols_failed'] += 1
            return False
    
    def create_all_missing_files(self, max_symbols: Optional[int] = None) -> Dict:
        """Create parquet files for all symbols"""
        logger.info("🚀 Starting parquet file creation process...")
        
        # Create month directories
        self.aug_path.mkdir(parents=True, exist_ok=True)
        self.sep_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created directories: {self.aug_path} and {self.sep_path}")
        
        # Get symbols from database
        symbols = self.get_symbols_from_database()
        
        # Limit symbols if specified
        if max_symbols:
            symbols = symbols[:max_symbols]
            logger.info(f"🔢 Limited to first {max_symbols} symbols")
        
        total_symbols = len(symbols)
        logger.info(f"📊 Processing {total_symbols} symbols...")
        
        # Process each symbol
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"🔄 [{i}/{total_symbols}] Processing {symbol}")
            
            success = self.process_symbol(symbol)
            self.stats['symbols_processed'] += 1
            
            # Progress update every 10 symbols
            if i % 10 == 0:
                logger.info(f"📊 Progress: {i}/{total_symbols} symbols processed")
        
        # Final statistics
        logger.info("📊 PARQUET FILE CREATION COMPLETED!")
        logger.info(f"   ✅ Symbols processed: {self.stats['symbols_processed']}")
        logger.info(f"   ✅ Symbols successful: {self.stats['symbols_success']}")
        logger.info(f"   ❌ Symbols failed: {self.stats['symbols_failed']}")
        logger.info(f"   📁 Files created: {self.stats['files_created']}")
        logger.info(f"   📊 Total records: {self.stats['total_records']:,}")
        
        if self.stats['errors']:
            logger.info(f"   ⚠️ Errors encountered: {len(self.stats['errors'])}")
        
        return self.stats

def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.strptime(s, '%Y-%m-%d').date()

def main():
    """Main function to run the parquet file creation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create parquet files for a date or date range from Dhan API')
    parser.add_argument('--date', type=str, help='Specific date (YYYY-MM-DD) to generate')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD) inclusive')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD) inclusive')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols')
    parser.add_argument('--max-symbols', type=int, help='Maximum number of symbols to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without actually creating files')
    
    args = parser.parse_args()
    
    try:
        # Determine date window
        if args.date:
            sd = ed = _parse_date(args.date)
        else:
            sd = _parse_date(args.start_date) or date(2025, 8, 1)
            ed = _parse_date(args.end_date) or date(2025, 9, 4)

        creator = ParquetFileCreator(start_date=sd, end_date=ed)
        
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No files will be created")
            symbols = creator.get_symbols_from_database()
            if args.symbols:
                symbols = [s.strip().upper() for s in args.symbols.split(',')]
            
            if args.max_symbols:
                symbols = symbols[:args.max_symbols]
            
            logger.info(f"📊 Would create parquet files for {len(symbols)} symbols:")
            logger.info(f"📁 Target directories:")
            logger.info(f"   📅 August: {creator.aug_path}")
            logger.info(f"   📅 September: {creator.sep_path}")
            
            for i, symbol in enumerate(symbols[:20], 1):  # Show first 20
                logger.info(f"   {i:3d}. {symbol}")
            
            if len(symbols) > 20:
                logger.info(f"   ... and {len(symbols) - 20} more symbols")
        else:
            # If symbols specified, limit to those
            if args.symbols:
                syms = [s.strip().upper() for s in args.symbols.split(',')]
                # Monkey-patch method to return provided symbols
                def get_fixed_symbols():
                    return syms
                creator.get_symbols_from_database = get_fixed_symbols

            # Run actual file creation
            stats = creator.create_all_missing_files(args.max_symbols)
            
            logger.info("🎉 Parquet file creation completed!")
            logger.info(f"📊 Final Statistics: {stats}")
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

