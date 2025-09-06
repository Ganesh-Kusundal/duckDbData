#!/usr/bin/env python3
"""
Technical Indicators Update Script

This script updates pre-calculated technical indicators for all symbols across multiple timeframes.
It can be run manually or scheduled to automatically update indicators when market data changes.

Features:
- Updates all technical indicators (OBV, ADX, ATR, RSI, etc.)
- Calculates support/resistance and supply/demand zones
- Processes multiple timeframes (1T, 5T, 15T, 1H, 1D)
- Supports incremental updates for efficiency
- Concurrent processing for performance

Author: AI Assistant
Date: 2025-09-03
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import logging
import argparse
from datetime import datetime, date, timedelta
from typing import List, Optional

from core.duckdb_infra.database import DuckDBManager
from core.technical_indicators.updater import TechnicalIndicatorsUpdater
from core.technical_indicators.storage import TechnicalIndicatorsStorage
from core.technical_indicators.calculator import TechnicalIndicatorsCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run the technical indicators update process."""
    parser = argparse.ArgumentParser(
        description='Update pre-calculated technical indicators for all symbols'
    )
    
    # Basic options
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to update (default: all)')
    parser.add_argument('--timeframes', nargs='+', 
                       choices=['1T', '5T', '15T', '1H', '1D'],
                       help='Timeframes to update (default: all)')
    parser.add_argument('--max-symbols', type=int, help='Maximum number of symbols to process')
    parser.add_argument('--max-workers', type=int, default=4, help='Maximum concurrent workers')
    
    # Date range options
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--days-back', type=int, default=7, 
                       help='Number of days back to update (default: 7)')
    
    # Update options
    parser.add_argument('--force-recalculate', action='store_true',
                       help='Force recalculation even if indicators exist')
    parser.add_argument('--stale-only', action='store_true',
                       help='Only update stale indicators (older than 24 hours)')
    parser.add_argument('--max-age-hours', type=int, default=24,
                       help='Maximum age in hours before considering stale')
    
    # Utility options
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be updated without actually updating')
    parser.add_argument('--stats', action='store_true',
                       help='Show storage statistics and exit')
    parser.add_argument('--list-symbols', action='store_true',
                       help='List available symbols and exit')
    
    args = parser.parse_args()
    
    try:
        # Initialize components
        logger.info("🚀 Initializing Technical Indicators Updater...")
        
        db_manager = DuckDBManager()
        storage = TechnicalIndicatorsStorage()
        calculator = TechnicalIndicatorsCalculator()
        updater = TechnicalIndicatorsUpdater(db_manager, storage, calculator)
        
        # Handle utility commands
        if args.stats:
            show_storage_stats(storage)
            return 0
        
        if args.list_symbols:
            list_available_symbols(db_manager, storage)
            return 0
        
        # Parse date arguments
        start_date, end_date = parse_date_arguments(args)
        
        # Determine symbols to process
        if args.symbols:
            symbols = args.symbols
            logger.info(f"📊 Processing specified symbols: {symbols}")
        else:
            symbols = db_manager.get_available_symbols()
            if args.max_symbols:
                symbols = symbols[:args.max_symbols]
                logger.info(f"🔢 Limited to first {args.max_symbols} symbols")
            logger.info(f"📊 Processing all {len(symbols)} symbols")
        
        if not symbols:
            logger.error("❌ No symbols found to process")
            return 1
        
        # Handle stale-only updates
        if args.stale_only:
            logger.info(f"🔍 Detecting stale indicators (older than {args.max_age_hours} hours)...")
            results = updater.update_stale_indicators(args.max_age_hours, args.max_workers)
        else:
            # Handle dry run
            if args.dry_run:
                show_dry_run_info(updater, symbols, args.timeframes, start_date, end_date)
                return 0
            
            # Run actual update
            logger.info("🔄 Starting technical indicators update...")
            results = updater.update_multiple_symbols(
                symbols=symbols,
                timeframes=args.timeframes,
                start_date=start_date,
                end_date=end_date,
                force_recalculate=args.force_recalculate,
                max_workers=args.max_workers
            )
        
        # Show results
        show_update_results(updater, results)
        
        logger.info("🎉 Technical indicators update completed!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️ Update cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def parse_date_arguments(args) -> tuple:
    """Parse and validate date arguments."""
    end_date = date.today()
    
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
    
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=args.days_back)
    
    logger.info(f"📅 Date range: {start_date} to {end_date}")
    return start_date, end_date


def show_storage_stats(storage: TechnicalIndicatorsStorage):
    """Show storage statistics."""
    logger.info("📊 Technical Indicators Storage Statistics:")
    
    stats = storage.get_storage_stats()
    
    print(f"\n📈 STORAGE STATISTICS")
    print(f"{'='*50}")
    print(f"Total Files: {stats['total_files']:,}")
    print(f"Total Size: {stats['total_size_mb']:.2f} MB")
    print(f"Symbols Count: {stats['symbols_count']:,}")
    print(f"Timeframes: {', '.join(stats['timeframes'])}")
    
    if stats['date_range']['start'] and stats['date_range']['end']:
        print(f"Date Range: {stats['date_range']['start']} to {stats['date_range']['end']}")
    
    # Show symbols by timeframe
    print(f"\n📊 SYMBOLS BY TIMEFRAME")
    print(f"{'='*50}")
    for timeframe in stats['timeframes']:
        symbols = storage.get_available_symbols(timeframe)
        print(f"{timeframe:>4s}: {len(symbols):,} symbols")


def list_available_symbols(db_manager: DuckDBManager, storage: TechnicalIndicatorsStorage):
    """List available symbols."""
    logger.info("📋 Available Symbols:")
    
    # Get symbols from market data
    market_symbols = db_manager.get_available_symbols()
    
    # Get symbols with indicators
    indicator_symbols = {}
    for timeframe in ['1T', '5T', '15T', '1H', '1D']:
        indicator_symbols[timeframe] = set(storage.get_available_symbols(timeframe))
    
    print(f"\n📊 SYMBOL AVAILABILITY")
    print(f"{'='*70}")
    print(f"{'Symbol':<15} {'Market Data':<12} {'1T':<5} {'5T':<5} {'15T':<5} {'1H':<5} {'1D':<5}")
    print(f"{'-'*70}")
    
    for symbol in sorted(market_symbols[:50]):  # Show first 50
        market_check = "✅"
        tf_checks = []
        
        for tf in ['1T', '5T', '15T', '1H', '1D']:
            if symbol in indicator_symbols[tf]:
                tf_checks.append("✅")
            else:
                tf_checks.append("❌")
        
        print(f"{symbol:<15} {market_check:<12} {tf_checks[0]:<5} {tf_checks[1]:<5} {tf_checks[2]:<5} {tf_checks[3]:<5} {tf_checks[4]:<5}")
    
    if len(market_symbols) > 50:
        print(f"... and {len(market_symbols) - 50} more symbols")


def show_dry_run_info(updater: TechnicalIndicatorsUpdater, 
                     symbols: List[str], 
                     timeframes: Optional[List[str]], 
                     start_date: date, 
                     end_date: date):
    """Show dry run information."""
    logger.info("🔍 DRY RUN MODE - No indicators will be updated")
    
    if timeframes is None:
        timeframes = ['1T', '5T', '15T', '1H', '1D']
    
    print(f"\n📊 UPDATE PLAN")
    print(f"{'='*50}")
    print(f"Symbols: {len(symbols)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Total Operations: {len(symbols) * len(timeframes)}")
    
    # Show sample of symbols
    print(f"\n📋 SYMBOLS TO UPDATE (first 20):")
    for i, symbol in enumerate(symbols[:20], 1):
        print(f"  {i:3d}. {symbol}")
    
    if len(symbols) > 20:
        print(f"  ... and {len(symbols) - 20} more symbols")
    
    # Detect stale indicators
    stale_indicators = updater.detect_stale_indicators(24)
    if stale_indicators:
        print(f"\n⚠️  STALE INDICATORS DETECTED:")
        print(f"Symbols with stale data: {len(stale_indicators)}")
        for symbol, stale_list in list(stale_indicators.items())[:10]:
            timeframes_str = ', '.join([item[0] for item in stale_list])
            print(f"  {symbol}: {timeframes_str}")


def show_update_results(updater: TechnicalIndicatorsUpdater, results: dict):
    """Show update results and statistics."""
    stats = updater.get_update_statistics()
    
    successful_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 UPDATE RESULTS")
    print(f"{'='*50}")
    print(f"✅ Symbols Updated: {successful_count}/{total_count}")
    print(f"📊 Records Updated: {stats['total_records_updated']:,}")
    
    if stats.get('duration_seconds'):
        duration = stats['duration_seconds']
        print(f"⏱️  Duration: {duration:.2f} seconds")
        
        if stats['total_records_updated'] > 0:
            rate = stats['total_records_updated'] / duration
            print(f"🚀 Processing Rate: {rate:.0f} records/second")
    
    # Show failed symbols
    failed_symbols = [symbol for symbol, success in results.items() if not success]
    if failed_symbols:
        print(f"\n❌ FAILED SYMBOLS ({len(failed_symbols)}):")
        for symbol in failed_symbols[:10]:
            print(f"  • {symbol}")
        if len(failed_symbols) > 10:
            print(f"  ... and {len(failed_symbols) - 10} more")
    
    # Show errors
    if stats['errors']:
        print(f"\n⚠️  ERRORS ({len(stats['errors'])}):")
        for error in stats['errors'][:5]:
            print(f"  • {error}")
        if len(stats['errors']) > 5:
            print(f"  ... and {len(stats['errors']) - 5} more errors")


if __name__ == "__main__":
    exit(main())

