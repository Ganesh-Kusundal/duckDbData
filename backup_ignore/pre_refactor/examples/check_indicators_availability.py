#!/usr/bin/env python3
"""
Check Technical Indicators Availability

This script checks the availability of precalculated technical indicators
by querying the storage system and displaying statistics.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from datetime import date, timedelta
import argparse
import logging

from core.technical_indicators.storage import TechnicalIndicatorsStorage
from core.technical_indicators.schema import TimeFrame
from core.duckdb_infra.database import DuckDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_indicators_availability():
    """Check availability of precalculated technical indicators"""
    # Initialize storage and database manager
    storage = TechnicalIndicatorsStorage()
    db_manager = DuckDBManager()
    
    # Get all available symbols from database
    db_symbols = db_manager.get_available_symbols()
    logger.info(f"Database has {len(db_symbols)} symbols available")
    
    # Get available timeframes
    timeframes = [tf.value for tf in TimeFrame]
    logger.info(f"Supported timeframes: {timeframes}")
    
    # Check indicators availability for each timeframe
    print("\nTechnical Indicators Availability:")
    print("-" * 60)
    print(f"{'Timeframe':<10} {'Symbols':<10} {'Date Range':<30} {'Status':<10}")
    print("-" * 60)
    
    for timeframe in timeframes:
        # Get symbols with indicators for this timeframe
        indicator_symbols = storage.get_available_symbols(timeframe)
        
        if not indicator_symbols:
            print(f"{timeframe:<10} {'0':<10} {'N/A':<30} {'❌ Missing':<10}")
            continue
        
        # Get date range for first symbol
        if indicator_symbols:
            first_symbol = indicator_symbols[0]
            dates = storage.get_available_dates(first_symbol, timeframe)
            if dates:
                date_range = f"{min(dates)} to {max(dates)}"
            else:
                date_range = "N/A"
        else:
            date_range = "N/A"
        
        # Calculate coverage percentage
        coverage = len(indicator_symbols) / len(db_symbols) * 100 if db_symbols else 0
        status = "✅ Complete" if coverage >= 95 else "⚠️ Partial" if coverage > 0 else "❌ Missing"
        
        print(f"{timeframe:<10} {len(indicator_symbols):<10} {date_range:<30} {status:<10}")
    
    # Check specific symbols
    print("\nChecking specific symbols...")
    sample_symbols = db_symbols[:5] if len(db_symbols) >= 5 else db_symbols
    
    for symbol in sample_symbols:
        print(f"\nSymbol: {symbol}")
        print("-" * 40)
        
        for timeframe in timeframes:
            dates = storage.get_available_dates(symbol, timeframe)
            if dates:
                print(f"{timeframe:<10} ✅ Available ({len(dates)} days, {min(dates)} to {max(dates)})")
            else:
                print(f"{timeframe:<10} ❌ Not available")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Check Technical Indicators Availability')
    args = parser.parse_args()
    
    check_indicators_availability()


if __name__ == "__main__":
    main()