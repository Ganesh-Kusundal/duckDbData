#!/usr/bin/env python3
"""
Scanner Performance Backtesting System

This system backtests our momentum scanner to verify if it's effectively
picking up the top gainers of the day by analyzing only data until 09:50 AM.

Key Metrics:
1. How many scanner picks end up as top gainers for the day
2. Average performance of scanner picks vs market
3. Hit rate and accuracy of momentum predictions
4. Comparison with actual top performers

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
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import argparse

from core.duckdb_infra.database import DuckDBManager
from optimized_momentum_scanner import OptimizedMomentumScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScannerPerformanceBacktest:
    """Backtesting system to validate scanner performance"""
    
    def __init__(self):
        """Initialize the backtesting system"""
        self.db_manager = DuckDBManager()
        self.scanner = OptimizedMomentumScanner()
        
        # Performance tracking
        self.results = []
    
    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Get list of trading days with sufficient data"""
        logger.info(f"📅 Finding trading days between {start_date} and {end_date}")
        
        query = '''
        SELECT DISTINCT DATE(timestamp) as trade_date
        FROM market_data 
        WHERE DATE(timestamp) >= ? 
            AND DATE(timestamp) <= ?
            AND strftime('%H:%M', timestamp) <= '15:29'
            AND strftime('%H:%M', timestamp) >= '09:15'
        GROUP BY DATE(timestamp)
        HAVING COUNT(DISTINCT symbol) >= 30  -- At least 30 active symbols
            AND COUNT(*) >= 1000  -- Sufficient data points
        ORDER BY trade_date
        '''
        
        result = self.db_manager.execute_custom_query(query, [start_date, end_date])
        trading_days = [pd.to_datetime(row['trade_date']).date() for _, row in result.iterrows()]
        
        logger.info(f"📊 Found {len(trading_days)} trading days")
        return trading_days
    
    def get_actual_top_gainers(self, scan_date: date, top_n: int = 10) -> pd.DataFrame:
        """Get actual top gainers for the entire trading day"""
        
        query = '''
        SELECT 
            symbol,
            
            -- Opening price (09:15)
            (SELECT open FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:15'
             LIMIT 1) as opening_price,
             
            -- Closing price (15:29)
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '15:29'
             LIMIT 1) as closing_price,
             
            -- Day high and low
            MAX(high) as day_high,
            MIN(low) as day_low,
            
            -- Total day volume
            SUM(volume) as total_day_volume,
            COUNT(*) as minutes_active
            
        FROM market_data m1
        WHERE DATE(timestamp) = ?
            AND strftime('%H:%M', timestamp) >= '09:15'
            AND strftime('%H:%M', timestamp) <= '15:29'
        GROUP BY symbol
        HAVING opening_price IS NOT NULL 
            AND closing_price IS NOT NULL
            AND COUNT(*) >= 100  -- At least 100 minutes of data
        '''
        
        day_performance = self.db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
        
        if day_performance.empty:
            return pd.DataFrame()
        
        # Calculate performance metrics
        day_performance['day_return_pct'] = (
            (day_performance['closing_price'] - day_performance['opening_price']) / 
            day_performance['opening_price'] * 100
        )
        
        day_performance['max_gain_pct'] = (
            (day_performance['day_high'] - day_performance['opening_price']) / 
            day_performance['opening_price'] * 100
        )
        
        day_performance['max_loss_pct'] = (
            (day_performance['day_low'] - day_performance['opening_price']) / 
            day_performance['opening_price'] * 100
        )
        
        # Sort by day return to get top gainers
        top_gainers = day_performance.sort_values('day_return_pct', ascending=False).head(top_n)
        
        return top_gainers
    
    def get_scanner_picks_performance(self, scan_date: date, scanner_picks: List[str]) -> pd.DataFrame:
        """Get end-of-day performance for scanner picks"""
        if not scanner_picks:
            return pd.DataFrame()
        
        symbol_list = "', '".join(scanner_picks)
        
        query = f'''
        SELECT 
            symbol,
            
            -- Opening price (09:15)
            (SELECT open FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:15'
             LIMIT 1) as opening_price,
             
            -- 09:50 price
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:50'
             LIMIT 1) as price_0950,
             
            -- Closing price (15:29)
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '15:29'
             LIMIT 1) as closing_price,
             
            -- Day high and low
            MAX(high) as day_high,
            MIN(low) as day_low,
            
            -- Total day volume
            SUM(volume) as total_day_volume
            
        FROM market_data m1
        WHERE DATE(timestamp) = ?
            AND symbol IN ('{symbol_list}')
            AND strftime('%H:%M', timestamp) >= '09:15'
            AND strftime('%H:%M', timestamp) <= '15:29'
        GROUP BY symbol
        '''
        
        picks_performance = self.db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date, scan_date])
        
        if not picks_performance.empty:
            # Calculate performance metrics
            picks_performance['early_signal_pct'] = (
                (picks_performance['price_0950'] - picks_performance['opening_price']) / 
                picks_performance['opening_price'] * 100
            )
            
            picks_performance['day_return_pct'] = (
                (picks_performance['closing_price'] - picks_performance['opening_price']) / 
                picks_performance['opening_price'] * 100
            )
            
            picks_performance['post_0950_return_pct'] = (
                (picks_performance['closing_price'] - picks_performance['price_0950']) / 
                picks_performance['price_0950'] * 100
            )
            
            picks_performance['max_gain_pct'] = (
                (picks_performance['day_high'] - picks_performance['opening_price']) / 
                picks_performance['opening_price'] * 100
            )
        
        return picks_performance
    
    def backtest_single_day(self, scan_date: date) -> Dict:
        """Backtest scanner performance for a single day"""
        logger.info(f"📊 Backtesting {scan_date}")
        
        try:
            # Get scanner picks (using 09:50 data only)
            scanner_results = self.scanner.get_momentum_candidates(scan_date)
            
            if scanner_results.empty:
                logger.warning(f"⚠️ No scanner picks for {scan_date}")
                return {
                    'date': scan_date,
                    'scanner_picks_count': 0,
                    'top_gainers_captured': 0,
                    'hit_rate': 0,
                    'avg_scanner_return': 0,
                    'avg_market_return': 0,
                    'outperformance': 0,
                    'best_pick_return': 0,
                    'worst_pick_return': 0
                }
            
            # Calculate scores and get top picks
            scanner_results = self.scanner.calculate_momentum_scores(scanner_results)
            top_scanner_picks = scanner_results.head(5)['symbol'].tolist()
            
            # Get actual top gainers for the day
            actual_top_gainers = self.get_actual_top_gainers(scan_date, 10)
            
            if actual_top_gainers.empty:
                logger.warning(f"⚠️ No market data for {scan_date}")
                return {
                    'date': scan_date,
                    'scanner_picks_count': len(top_scanner_picks),
                    'top_gainers_captured': 0,
                    'hit_rate': 0,
                    'avg_scanner_return': 0,
                    'avg_market_return': 0,
                    'outperformance': 0,
                    'best_pick_return': 0,
                    'worst_pick_return': 0
                }
            
            # Get performance of scanner picks
            scanner_performance = self.get_scanner_picks_performance(scan_date, top_scanner_picks)
            
            # Calculate metrics
            top_gainer_symbols = set(actual_top_gainers.head(5)['symbol'].tolist())
            scanner_pick_symbols = set(top_scanner_picks)
            
            # How many scanner picks ended up as top gainers
            captured_top_gainers = len(scanner_pick_symbols.intersection(top_gainer_symbols))
            hit_rate = (captured_top_gainers / len(top_scanner_picks)) * 100 if top_scanner_picks else 0
            
            # Performance comparison
            avg_scanner_return = scanner_performance['day_return_pct'].mean() if not scanner_performance.empty else 0
            avg_market_return = actual_top_gainers['day_return_pct'].mean()
            
            # Best and worst picks
            best_pick_return = scanner_performance['day_return_pct'].max() if not scanner_performance.empty else 0
            worst_pick_return = scanner_performance['day_return_pct'].min() if not scanner_performance.empty else 0
            
            return {
                'date': scan_date,
                'scanner_picks_count': len(top_scanner_picks),
                'top_gainers_captured': captured_top_gainers,
                'hit_rate': hit_rate,
                'avg_scanner_return': avg_scanner_return,
                'avg_market_return': avg_market_return,
                'outperformance': avg_scanner_return - avg_market_return,
                'best_pick_return': best_pick_return,
                'worst_pick_return': worst_pick_return,
                'top_gainer_symbols': list(top_gainer_symbols),
                'scanner_pick_symbols': top_scanner_picks
            }
            
        except Exception as e:
            logger.error(f"❌ Error backtesting {scan_date}: {e}")
            return {
                'date': scan_date,
                'scanner_picks_count': 0,
                'top_gainers_captured': 0,
                'hit_rate': 0,
                'avg_scanner_return': 0,
                'avg_market_return': 0,
                'outperformance': 0,
                'best_pick_return': 0,
                'worst_pick_return': 0
            }
    
    def run_performance_backtest(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Run comprehensive performance backtest"""
        logger.info(f"🚀 Starting scanner performance backtest from {start_date} to {end_date}")
        
        # Get trading days
        trading_days = self.get_trading_days(start_date, end_date)
        
        if len(trading_days) < 3:
            logger.error("❌ Insufficient trading days for backtesting")
            return pd.DataFrame()
        
        logger.info(f"📊 Testing scanner performance across {len(trading_days)} trading days")
        
        results = []
        
        for day_idx, trading_day in enumerate(trading_days):
            logger.info(f"📅 Processing day {day_idx + 1}/{len(trading_days)}: {trading_day}")
            
            day_result = self.backtest_single_day(trading_day)
            results.append(day_result)
        
        results_df = pd.DataFrame(results)
        return results_df
    
    def analyze_results(self, results: pd.DataFrame) -> Dict:
        """Analyze backtest results and generate insights"""
        if results.empty:
            return {}
        
        # Filter out days with no picks
        valid_days = results[results['scanner_picks_count'] > 0]
        
        if valid_days.empty:
            return {'error': 'No valid trading days with scanner picks'}
        
        analysis = {
            'total_days': len(results),
            'active_days': len(valid_days),
            'avg_picks_per_day': valid_days['scanner_picks_count'].mean(),
            
            # Hit rate analysis
            'avg_hit_rate': valid_days['hit_rate'].mean(),
            'best_hit_rate': valid_days['hit_rate'].max(),
            'days_with_hits': (valid_days['hit_rate'] > 0).sum(),
            'hit_success_rate': (valid_days['hit_rate'] > 0).mean() * 100,
            
            # Performance analysis
            'avg_scanner_return': valid_days['avg_scanner_return'].mean(),
            'avg_market_return': valid_days['avg_market_return'].mean(),
            'avg_outperformance': valid_days['outperformance'].mean(),
            'positive_days': (valid_days['avg_scanner_return'] > 0).sum(),
            'negative_days': (valid_days['avg_scanner_return'] < 0).sum(),
            
            # Best/worst performance
            'best_day_return': valid_days['avg_scanner_return'].max(),
            'worst_day_return': valid_days['avg_scanner_return'].min(),
            'best_single_pick': valid_days['best_pick_return'].max(),
            'worst_single_pick': valid_days['worst_pick_return'].min(),
            
            # Consistency metrics
            'return_volatility': valid_days['avg_scanner_return'].std(),
            'sharpe_ratio': valid_days['avg_scanner_return'].mean() / valid_days['avg_scanner_return'].std() if valid_days['avg_scanner_return'].std() > 0 else 0,
            'win_rate': (valid_days['avg_scanner_return'] > 0).mean() * 100
        }
        
        return analysis
    
    def display_results(self, results: pd.DataFrame, analysis: Dict):
        """Display comprehensive backtest results"""
        if results.empty or not analysis:
            print("❌ No backtest results available")
            return
        
        print(f"\n🎯 SCANNER PERFORMANCE BACKTEST RESULTS")
        print("=" * 80)
        
        print(f"\n📊 OVERVIEW:")
        print(f"   📅 Total Days Analyzed: {analysis['total_days']}")
        print(f"   🎯 Active Trading Days: {analysis['active_days']}")
        print(f"   📈 Average Picks per Day: {analysis['avg_picks_per_day']:.1f}")
        
        print(f"\n🎯 HIT RATE ANALYSIS:")
        print(f"   🏆 Average Hit Rate: {analysis['avg_hit_rate']:.1f}%")
        print(f"   🥇 Best Hit Rate: {analysis['best_hit_rate']:.1f}%")
        print(f"   📊 Days with Successful Hits: {analysis['days_with_hits']}/{analysis['active_days']}")
        print(f"   ✅ Hit Success Rate: {analysis['hit_success_rate']:.1f}%")
        
        print(f"\n📈 PERFORMANCE ANALYSIS:")
        print(f"   🚀 Average Scanner Return: {analysis['avg_scanner_return']:.2f}%")
        print(f"   📊 Average Market Return: {analysis['avg_market_return']:.2f}%")
        print(f"   🎯 Average Outperformance: {analysis['avg_outperformance']:+.2f}%")
        print(f"   📈 Positive Days: {analysis['positive_days']}/{analysis['active_days']}")
        print(f"   📉 Negative Days: {analysis['negative_days']}/{analysis['active_days']}")
        print(f"   🏆 Win Rate: {analysis['win_rate']:.1f}%")
        
        print(f"\n🎲 RISK METRICS:")
        print(f"   📊 Return Volatility: {analysis['return_volatility']:.2f}%")
        print(f"   📈 Sharpe Ratio: {analysis['sharpe_ratio']:.2f}")
        print(f"   🥇 Best Day Return: {analysis['best_day_return']:.2f}%")
        print(f"   📉 Worst Day Return: {analysis['worst_day_return']:.2f}%")
        print(f"   🚀 Best Single Pick: {analysis['best_single_pick']:.2f}%")
        print(f"   💥 Worst Single Pick: {analysis['worst_single_pick']:.2f}%")
        
        # Show detailed day-by-day results
        print(f"\n📅 DETAILED DAILY RESULTS:")
        print("-" * 80)
        
        valid_results = results[results['scanner_picks_count'] > 0].sort_values('date')
        
        for _, row in valid_results.iterrows():
            hit_emoji = "🎯" if row['hit_rate'] > 0 else "❌"
            return_emoji = "📈" if row['avg_scanner_return'] > 0 else "📉"
            
            print(f"{hit_emoji} {row['date']}: "
                  f"Hit Rate {row['hit_rate']:.0f}% | "
                  f"Return {row['avg_scanner_return']:+.2f}% {return_emoji} | "
                  f"Picks: {row['scanner_picks_count']} | "
                  f"Captured: {row['top_gainers_captured']}")
        
        # Summary verdict
        print(f"\n🏆 SCANNER EFFECTIVENESS VERDICT:")
        if analysis['avg_hit_rate'] > 20:
            print(f"   ✅ EXCELLENT: Scanner shows strong predictive power!")
        elif analysis['avg_hit_rate'] > 10:
            print(f"   ✅ GOOD: Scanner captures meaningful momentum!")
        elif analysis['avg_hit_rate'] > 5:
            print(f"   ⚠️ MODERATE: Scanner shows some predictive ability")
        else:
            print(f"   ❌ POOR: Scanner needs optimization")
        
        if analysis['avg_outperformance'] > 0:
            print(f"   📈 Scanner picks outperform market by {analysis['avg_outperformance']:.2f}%")
        else:
            print(f"   📉 Scanner picks underperform market by {abs(analysis['avg_outperformance']):.2f}%")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Scanner Performance Backtesting System')
    parser.add_argument('--start-date', type=str, required=True,
                       help='Start date for backtesting (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True,
                       help='End date for backtesting (YYYY-MM-DD)')
    parser.add_argument('--export', type=str,
                       help='Export results to CSV file')
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        
        if start_date >= end_date:
            logger.error("❌ Start date must be before end date")
            return 1
        
        backtester = ScannerPerformanceBacktest()
        results = backtester.run_performance_backtest(start_date=start_date, end_date=end_date)
        
        if not results.empty:
            analysis = backtester.analyze_results(results)
            backtester.display_results(results, analysis)
            
            if args.export:
                results.to_csv(args.export, index=False)
                logger.info(f"📁 Results exported to {args.export}")
            
            print(f"\n✅ Scanner performance backtest completed!")
        else:
            print(f"\n⚠️ No results generated from backtesting")
            
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up
        try:
            backtester.db_manager.close()
        except:
            pass
    
    return 0

if __name__ == "__main__":
    exit(main())
