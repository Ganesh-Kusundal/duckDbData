#!/usr/bin/env python3
"""
Breakout Scanner Backtesting Script
===================================
Backtests the breakout scanner over the last 3 months, tracking growth from 09:50 to 15:15.
Generates a CSV report in reports/backtesting/scanner/breakout.csv.
"""

import os
import sys
import pandas as pd
from datetime import date, time, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
from src.infrastructure.core.database import DuckDBManager
from src.infrastructure.logging import setup_logging

# Setup logging
setup_logging()

def get_trading_days(start_date: date, end_date: date) -> List[date]:
    """
    Get trading days between start and end date (simplified - assumes all days are trading days).
    In production, use a calendar to get actual trading days.
    """
    days = []
    current = start_date
    while current <= end_date:
        # Skip weekends for simplicity
        if current.weekday() < 5:  # Monday=0 to Friday=4
            days.append(current)
        current += timedelta(days=1)
    return days

def calculate_growth(entry_price: float, exit_price: float) -> float:
    """Calculate percentage growth from entry to exit."""
    if entry_price == 0:
        return 0.0
    return ((exit_price - entry_price) / entry_price) * 100

def backtest_breakout_scanner(start_date: date = None, end_date: date = None, max_results: int = 5) -> pd.DataFrame:
    """
    Backtest the breakout scanner over the specified period.
    
    Args:
        start_date: Start date for backtesting (default: 3 months ago)
        end_date: End date for backtesting (default: today)
        max_results: Max results per day to track (to limit computation)
    
    Returns:
        DataFrame with backtest results
    """
    # Default to last 3 months
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)
    
    print(f"🚀 Starting backtest from {start_date} to {end_date}")
    
    # Initialize scanner
    db_manager = DuckDBManager()
    scanner = BreakoutScanner(db_manager)
    
    # Get trading days
    trading_days = get_trading_days(start_date, end_date)
    print(f"📅 Backtesting over {len(trading_days)} trading days")
    
    # Results storage
    results = []
    
    for day in trading_days:
        try:
            print(f"📊 Scanning day: {day}")
            
            # Run scanner for the day at 09:50
            scan_results = scanner.scan(day, time(9, 50))
            
            if scan_results.empty:
                print(f"⚠️  No breakout stocks found for {day}")
                continue
            
            # Limit to max_results for efficiency
            scan_results = scan_results.head(max_results)
            
            print(f"📈 Found {len(scan_results)} breakout stocks for {day}")
            
            # For each stock, get intraday data from 09:50 to 15:15
            for _, stock in scan_results.iterrows():
                symbol = stock['symbol']
                print(f"   📊 Tracking {symbol}")
                
                # Get intraday data for the day
                intraday_data = get_intraday_data_for_symbol(db_manager, symbol, day)
                if intraday_data is None or intraday_data.empty:
                    print(f"   ⚠️  No intraday data for {symbol} on {day}")
                    continue
                
                # Get price at 09:50
                entry_time = time(9, 50)
                entry_data = intraday_data[intraday_data['timestamp'].dt.time >= entry_time]
                if entry_data.empty:
                    print(f"   ⚠️  No data after 09:50 for {symbol}")
                    continue
                entry_price = entry_data.iloc[0]['close']  # Use first available after 09:50
                
                # Get price at 15:15
                exit_time = time(15, 15)
                exit_data = intraday_data[intraday_data['timestamp'].dt.time >= exit_time]
                if exit_data.empty:
                    # Use last available close of the day
                    exit_price = intraday_data.iloc[-1]['close']
                else:
                    exit_price = exit_data.iloc[0]['close']
                
                growth_pct = calculate_growth(entry_price, exit_price)
                
                # Store result
                results.append({
                    'date': day,
                    'symbol': symbol,
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(exit_price, 2),
                    'growth_pct': round(growth_pct, 2),
                    'breakout_score': stock.get('breakout_score', 0),
                    'volume_ratio': stock.get('volume_ratio', 1.0),
                    'breakout_pct': stock.get('breakout_pct', 0)
                })
                
                print(f"   📊 {symbol}: Entry ₹{entry_price:.2f} -> Exit ₹{exit_price:.2f} = {growth_pct:.2f}%")
            
        except Exception as e:
            print(f"❌ Error backtesting day {day}: {e}")
            continue
    
    # Create results DataFrame
    if results:
        results_df = pd.DataFrame(results)
        print(f"📊 Backtest complete. Average growth: {results_df['growth_pct'].mean():.2f}%")
        print(f"📈 Best performing stock: {results_df.loc[results_df['growth_pct'].idxmax(), 'symbol']} with {results_df['growth_pct'].max():.2f}% growth")
        return results_df
    else:
        print("⚠️  No backtest results generated")
        return pd.DataFrame()

def get_intraday_data_for_symbol(db_manager: DuckDBManager, symbol: str, scan_date: date, timeframe: str = '1m') -> pd.DataFrame:
    """
    Get intraday data for a symbol on a specific date.
    
    Args:
        db_manager: DuckDB manager
        symbol: Trading symbol
        scan_date: Date for intraday data
        timeframe: Intraday timeframe
    
    Returns:
        DataFrame with intraday data or None if failed
    """
    try:
        from src.infrastructure.core.query_api import QueryAPI
        query_api = QueryAPI(db_manager)
        
        # Get intraday data for the day
        data = query_api.get_market_data(
            symbols=[symbol],
            start_date=scan_date,
            end_date=scan_date,
            timeframe=timeframe
        )
        
        if data is not None and not data.empty:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            return data
        else:
            return pd.DataFrame()
    
    except Exception as e:
        print(f"Error getting intraday data for {symbol} on {scan_date}: {e}")
        return pd.DataFrame()

def save_backtest_report(results_df: pd.DataFrame, report_path: str = "reports/backtesting/scanner/breakout.csv"):
    """
    Save backtest results to CSV.
    
    Args:
        results_df: DataFrame with backtest results
        report_path: Path to save the report
    """
    try:
        # Create directory if it doesn't exist
        report_dir = Path(report_path).parent
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to CSV
        results_df.to_csv(report_path, index=False)
        print(f"📁 Backtest report saved to: {report_path}")
        
    except Exception as e:
        print(f"Error saving backtest report: {e}")

if __name__ == "__main__":
    # Run backtest for last 3 months
    results = backtest_breakout_scanner()
    
    if not results.empty:
        # Save report
        report_path = "reports/backtesting/scanner/breakout.csv"
        save_backtest_report(results, report_path)
        
        # Print summary
        print("\n" + "="*60)
        print("BACKTEST SUMMARY")
        print("="*60)
        print(f"Period: {results['date'].min()} to {results['date'].max()}")
        print(f"Total trades: {len(results)}")
        print(f"Average growth: {results['growth_pct'].mean():.2f}%")
        print(f"Win rate: {len(results[results['growth_pct'] > 0]) / len(results) * 100:.1f}%")
        print(f"Total growth: {results['growth_pct'].sum():.2f}%")
        print(f"Best day: {results.loc[results['growth_pct'].idxmax(), 'date']} with {results['growth_pct'].max():.2f}%")
        print("="*60)
    else:
        print("No results to save. Backtest completed with no breakout opportunities found.")