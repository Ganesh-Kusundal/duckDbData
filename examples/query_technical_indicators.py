#!/usr/bin/env python3
"""
Example script to query precalculated technical indicators

This script demonstrates how to access and use the precalculated technical indicators
for various symbols and timeframes.
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def query_indicators(symbol, timeframe, start_date=None, end_date=None):
    """Query precalculated technical indicators for a symbol"""
    # Initialize storage
    storage = TechnicalIndicatorsStorage()
    
    # Set default dates if not provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    logger.info(f"Loading indicators for {symbol} ({timeframe}) from {start_date} to {end_date}")
    
    # Load indicators
    indicators = storage.load_indicators(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date
    )
    
    if indicators.empty:
        logger.warning(f"No indicators found for {symbol} ({timeframe})")
        return None
    
    logger.info(f"Loaded {len(indicators)} records with {len(indicators.columns)} indicators")
    
    # Display available indicators
    indicator_columns = [col for col in indicators.columns 
                        if col not in ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
    logger.info(f"Available indicators: {indicator_columns[:10]}...")
    
    # Display latest values for key indicators
    latest = indicators.iloc[-1]
    print(f"\nLatest Technical Indicators for {symbol} ({timeframe}) on {latest['timestamp'].date()}:")
    print(f"Price: {latest['close']:.2f}")
    
    # Display key indicators if available
    key_indicators = [
        ('RSI (14)', 'rsi_14'),
        ('ADX (14)', 'adx_14'),
        ('SMA (20)', 'sma_20'),
        ('EMA (20)', 'ema_20'),
        ('Bollinger Upper', 'bb_upper'),
        ('Bollinger Lower', 'bb_lower'),
        ('Support Level 1', 'support_level_1'),
        ('Resistance Level 1', 'resistance_level_1')
    ]
    
    for name, col in key_indicators:
        if col in indicators.columns:
            print(f"{name}: {latest[col]:.2f}")
    
    return indicators


def query_multiple_symbols(symbols, timeframe, start_date=None, end_date=None):
    """Query precalculated technical indicators for multiple symbols"""
    # Initialize storage
    storage = TechnicalIndicatorsStorage()
    
    # Set default dates if not provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    logger.info(f"Loading indicators for {len(symbols)} symbols ({timeframe}) from {start_date} to {end_date}")
    
    # Load indicators for multiple symbols concurrently
    data = storage.load_multiple_symbols(
        symbols=symbols,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        max_workers=4
    )
    
    # Display summary for each symbol
    print(f"\nSummary for {len(data)} symbols ({timeframe}):")
    for symbol, df in data.items():
        if df.empty:
            print(f"{symbol}: No data available")
            continue
            
        latest = df.iloc[-1]
        print(f"{symbol}: {len(df)} records, Latest Close: {latest['close']:.2f}, RSI: {latest.get('rsi_14', 'N/A')}")
    
    return data


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Query Technical Indicators Example')
    parser.add_argument('--symbol', type=str, help='Symbol to query')
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols to query')
    parser.add_argument('--timeframe', type=str, default='1D', help='Timeframe (1T, 5T, 15T, 1H, 1D)')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Parse dates if provided
    start_date = None
    end_date = None
    
    if args.start_date:
        start_date = date.fromisoformat(args.start_date)
    if args.end_date:
        end_date = date.fromisoformat(args.end_date)
    
    # Query single symbol or multiple symbols
    if args.symbol:
        indicators = query_indicators(args.symbol, args.timeframe, start_date, end_date)
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
        data = query_multiple_symbols(symbols, args.timeframe, start_date, end_date)
    else:
        # Default to querying a few common symbols
        symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
        data = query_multiple_symbols(symbols, args.timeframe, start_date, end_date)


if __name__ == "__main__":
    main()