#!/usr/bin/env python3
"""
Momentum Scanner Backtesting System

This system backtests different scanner parameters to find the optimal criteria
for selecting high momentum stocks by 09:50 AM that continue to perform well
throughout the day.

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
from itertools import product

from core.duckdb_infra.database import DuckDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MomentumScannerBacktest:
    """Backtesting system for momentum scanner optimization"""
    
    def __init__(self):
        """Initialize the backtesting system"""
        self.db_manager = DuckDBManager()
        
        # Parameter ranges to test
        self.param_ranges = {
            'min_volume_threshold': [50000, 100000, 200000, 500000],
            'min_price_change': [0.5, 1.0, 1.5, 2.0, 3.0],
            'min_relative_volume': [1.5, 2.0, 2.5, 3.0, 4.0],
            'min_volatility': [1.0, 1.5, 2.0, 2.5, 3.0],
            'max_price': [50, 100, 200, 500, 1000, 2000]
        }
        
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
            AND strftime('%H:%M', timestamp) <= '09:50'
        GROUP BY DATE(timestamp)
        HAVING COUNT(DISTINCT symbol) >= 50  -- At least 50 active symbols
        ORDER BY trade_date
        '''
        
        result = self.db_manager.execute_custom_query(query, [start_date, end_date])
        trading_days = [pd.to_datetime(row['trade_date']).date() for _, row in result.iterrows()]
        
        logger.info(f"📊 Found {len(trading_days)} trading days")
        return trading_days
    
    def get_0950_candidates(self, scan_date: date, params: Dict) -> pd.DataFrame:
        """Get momentum candidates by 09:50 AM for a specific date"""
        
        query = '''
        SELECT 
            symbol,
            
            -- Volume metrics
            SUM(volume) as volume_0950,
            COUNT(*) as minutes_traded,
            AVG(volume) as avg_minute_volume,
            
            -- Price metrics  
            (SELECT open FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:15'
             LIMIT 1) as opening_price,
             
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:50'
             LIMIT 1) as price_0950,
             
            MAX(high) as high_0950,
            MIN(low) as low_0950,
            AVG(close) as avg_price_0950
            
        FROM market_data m1
        WHERE DATE(timestamp) = ?
            AND strftime('%H:%M', timestamp) <= '09:50'
        GROUP BY symbol
        HAVING COUNT(*) >= 30  -- At least 30 minutes of data
        '''
        
        candidates = self.db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
        
        if candidates.empty:
            return pd.DataFrame()
        
        # Calculate derived metrics
        candidates['price_change_pct'] = (
            (candidates['price_0950'] - candidates['opening_price']) / candidates['opening_price'] * 100
        )
        candidates['volatility_0950'] = (
            (candidates['high_0950'] - candidates['low_0950']) / candidates['avg_price_0950'] * 100
        )
        
        # Get historical volume for relative volume calculation
        hist_query = '''
        SELECT 
            symbol,
            AVG(daily_volume) as avg_historical_volume
        FROM (
            SELECT 
                symbol,
                DATE(timestamp) as trade_date,
                SUM(volume) as daily_volume
            FROM market_data 
            WHERE DATE(timestamp) >= ? - INTERVAL '10 days'
                AND DATE(timestamp) < ?
                AND strftime('%H:%M', timestamp) <= '09:50'
            GROUP BY symbol, DATE(timestamp)
        ) hist
        GROUP BY symbol
        HAVING COUNT(*) >= 5
        '''
        
        hist_data = self.db_manager.execute_custom_query(hist_query, [scan_date, scan_date])
        
        # Merge with historical data
        candidates = candidates.merge(hist_data, on='symbol', how='left')
        candidates['avg_historical_volume'] = candidates['avg_historical_volume'].fillna(candidates['volume_0950'])
        candidates['relative_volume'] = candidates['volume_0950'] / candidates['avg_historical_volume']
        
        # Apply parameter filters
        filtered = candidates[
            (candidates['volume_0950'] >= params['min_volume_threshold']) &
            (abs(candidates['price_change_pct']) >= params['min_price_change']) &
            (candidates['relative_volume'] >= params['min_relative_volume']) &
            (candidates['volatility_0950'] >= params['min_volatility']) &
            (candidates['avg_price_0950'] <= params['max_price']) &
            (candidates['avg_price_0950'] >= 10)  # Minimum price filter
        ].copy()
        
        return filtered
    
    def get_eod_performance(self, symbols: List[str], scan_date: date) -> pd.DataFrame:
        """Get end-of-day performance for selected symbols"""
        if not symbols:
            return pd.DataFrame()
        
        symbol_list = "', '".join(symbols)
        
        query = f'''
        SELECT 
            symbol,
            
            -- 09:50 price
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:50'
             LIMIT 1) as price_0950,
             
            -- End of day price (15:29)
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '15:29'
             LIMIT 1) as price_eod,
             
            -- Day high and low
            MAX(high) as day_high,
            MIN(low) as day_low,
            
            -- Total day volume
            SUM(volume) as total_day_volume
            
        FROM market_data m1
        WHERE DATE(timestamp) = ?
            AND symbol IN ('{symbol_list}')
        GROUP BY symbol
        '''
        
        eod_data = self.db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
        
        if not eod_data.empty:
            # Calculate performance metrics
            eod_data['eod_return_pct'] = (
                (eod_data['price_eod'] - eod_data['price_0950']) / eod_data['price_0950'] * 100
            )
            eod_data['max_gain_pct'] = (
                (eod_data['day_high'] - eod_data['price_0950']) / eod_data['price_0950'] * 100
            )
            eod_data['max_loss_pct'] = (
                (eod_data['day_low'] - eod_data['price_0950']) / eod_data['price_0950'] * 100
            )
        
        return eod_data
    
    def backtest_single_day(self, scan_date: date, params: Dict) -> Dict:
        """Backtest scanner parameters for a single day"""
        
        # Get 09:50 candidates
        candidates = self.get_0950_candidates(scan_date, params)
        
        if candidates.empty:
            return {
                'date': scan_date,
                'candidates_count': 0,
                'avg_eod_return': 0,
                'win_rate': 0,
                'max_gain': 0,
                'max_loss': 0,
                'sharpe_ratio': 0
            }
        
        # Get EOD performance
        symbols = candidates['symbol'].tolist()
        eod_performance = self.get_eod_performance(symbols, scan_date)
        
        if eod_performance.empty:
            return {
                'date': scan_date,
                'candidates_count': len(candidates),
                'avg_eod_return': 0,
                'win_rate': 0,
                'max_gain': 0,
                'max_loss': 0,
                'sharpe_ratio': 0
            }
        
        # Calculate performance metrics
        returns = eod_performance['eod_return_pct'].dropna()
        
        if len(returns) == 0:
            return {
                'date': scan_date,
                'candidates_count': len(candidates),
                'avg_eod_return': 0,
                'win_rate': 0,
                'max_gain': 0,
                'max_loss': 0,
                'sharpe_ratio': 0
            }
        
        avg_return = returns.mean()
        win_rate = (returns > 0).mean() * 100
        max_gain = eod_performance['max_gain_pct'].max()
        max_loss = eod_performance['max_loss_pct'].min()
        
        # Calculate Sharpe ratio (assuming risk-free rate of 0)
        sharpe_ratio = avg_return / returns.std() if returns.std() > 0 else 0
        
        return {
            'date': scan_date,
            'candidates_count': len(candidates),
            'avg_eod_return': avg_return,
            'win_rate': win_rate,
            'max_gain': max_gain,
            'max_loss': max_loss,
            'sharpe_ratio': sharpe_ratio
        }
    
    def run_backtest(self, start_date: date, end_date: date, max_combinations: int = 50) -> pd.DataFrame:
        """Run comprehensive backtest across parameter combinations"""
        logger.info(f"🚀 Starting momentum scanner backtest from {start_date} to {end_date}")
        
        # Get trading days
        trading_days = self.get_trading_days(start_date, end_date)
        
        if len(trading_days) < 5:
            logger.error("❌ Insufficient trading days for backtesting")
            return pd.DataFrame()
        
        # Generate parameter combinations
        param_names = list(self.param_ranges.keys())
        param_values = list(self.param_ranges.values())
        
        all_combinations = list(product(*param_values))
        
        # Limit combinations for performance
        if len(all_combinations) > max_combinations:
            logger.info(f"📊 Limiting to {max_combinations} parameter combinations (out of {len(all_combinations)})")
            # Sample combinations to get good coverage
            step = len(all_combinations) // max_combinations
            all_combinations = all_combinations[::step][:max_combinations]
        
        logger.info(f"🧪 Testing {len(all_combinations)} parameter combinations across {len(trading_days)} days")
        
        results = []
        
        for combo_idx, param_combo in enumerate(all_combinations):
            params = dict(zip(param_names, param_combo))
            
            logger.info(f"📊 Testing combination {combo_idx + 1}/{len(all_combinations)}: {params}")
            
            daily_results = []
            
            for day_idx, trading_day in enumerate(trading_days):
                try:
                    day_result = self.backtest_single_day(trading_day, params)
                    daily_results.append(day_result)
                    
                    if (day_idx + 1) % 10 == 0:
                        logger.info(f"   📅 Processed {day_idx + 1}/{len(trading_days)} days")
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ Error processing {trading_day}: {e}")
                    continue
            
            if daily_results:
                # Aggregate results for this parameter combination
                df_daily = pd.DataFrame(daily_results)
                
                aggregate_result = {
                    'param_combo': str(params),
                    **params,
                    'total_days': len(df_daily),
                    'avg_candidates_per_day': df_daily['candidates_count'].mean(),
                    'total_avg_return': df_daily['avg_eod_return'].mean(),
                    'overall_win_rate': df_daily['win_rate'].mean(),
                    'avg_sharpe_ratio': df_daily['sharpe_ratio'].mean(),
                    'max_single_day_gain': df_daily['max_gain'].max(),
                    'max_single_day_loss': df_daily['max_loss'].min(),
                    'return_volatility': df_daily['avg_eod_return'].std(),
                    'positive_days': (df_daily['avg_eod_return'] > 0).sum(),
                    'negative_days': (df_daily['avg_eod_return'] < 0).sum(),
                    'consistency_score': (df_daily['avg_eod_return'] > 0).mean() * 100
                }
                
                results.append(aggregate_result)
        
        results_df = pd.DataFrame(results)
        
        if not results_df.empty:
            # Calculate composite score
            results_df['composite_score'] = (
                results_df['total_avg_return'] * 0.4 +
                results_df['overall_win_rate'] * 0.3 +
                results_df['avg_sharpe_ratio'] * 0.2 +
                results_df['consistency_score'] * 0.1
            )
            
            results_df = results_df.sort_values('composite_score', ascending=False)
        
        return results_df
    
    def display_backtest_results(self, results: pd.DataFrame, top_n: int = 10):
        """Display backtest results"""
        if results.empty:
            print("❌ No backtest results available")
            return
        
        print(f"\n🏆 TOP {min(top_n, len(results))} PARAMETER COMBINATIONS")
        print("=" * 100)
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            print(f"\n🥇 RANK {i}: Composite Score {row['composite_score']:.2f}")
            print(f"   📊 Parameters:")
            print(f"      Min Volume: {row['min_volume_threshold']:,}")
            print(f"      Min Price Change: {row['min_price_change']:.1f}%")
            print(f"      Min Relative Volume: {row['min_relative_volume']:.1f}x")
            print(f"      Min Volatility: {row['min_volatility']:.1f}%")
            print(f"      Max Price: ₹{row['max_price']:,}")
            
            print(f"   📈 Performance:")
            print(f"      Average Return: {row['total_avg_return']:.2f}%")
            print(f"      Win Rate: {row['overall_win_rate']:.1f}%")
            print(f"      Sharpe Ratio: {row['avg_sharpe_ratio']:.2f}")
            print(f"      Consistency: {row['consistency_score']:.1f}%")
            print(f"      Avg Candidates/Day: {row['avg_candidates_per_day']:.1f}")
        
        # Best parameter summary
        best_params = results.iloc[0]
        print(f"\n🎯 OPTIMAL SCANNER PARAMETERS:")
        print(f"   📊 Min Volume Threshold: {best_params['min_volume_threshold']:,} shares")
        print(f"   📈 Min Price Change: {best_params['min_price_change']:.1f}%")
        print(f"   📊 Min Relative Volume: {best_params['min_relative_volume']:.1f}x")
        print(f"   📈 Min Volatility: {best_params['min_volatility']:.1f}%")
        print(f"   💰 Max Price: ₹{best_params['max_price']:,}")
        
        print(f"\n📊 EXPECTED PERFORMANCE:")
        print(f"   📈 Average Daily Return: {best_params['total_avg_return']:.2f}%")
        print(f"   🎯 Win Rate: {best_params['overall_win_rate']:.1f}%")
        print(f"   📊 Daily Candidates: {best_params['avg_candidates_per_day']:.1f} stocks")
    
    def generate_optimized_scanner(self, results: pd.DataFrame) -> str:
        """Generate optimized scanner code based on best parameters"""
        if results.empty:
            return ""
        
        best_params = results.iloc[0]
        
        scanner_code = f'''
# OPTIMIZED MOMENTUM SCANNER PARAMETERS (Backtested)
# Expected Performance: {best_params['total_avg_return']:.2f}% avg return, {best_params['overall_win_rate']:.1f}% win rate

OPTIMAL_PARAMS = {{
    'min_volume_threshold': {int(best_params['min_volume_threshold'])},
    'min_price_change': {best_params['min_price_change']},
    'min_relative_volume': {best_params['min_relative_volume']},
    'min_volatility': {best_params['min_volatility']},
    'max_price': {int(best_params['max_price'])},
    'min_price': 10
}}

def scan_momentum_stocks_0950(scan_date):
    \"\"\"
    Optimized momentum scanner for 09:50 AM cutoff
    Backtested performance: {best_params['total_avg_return']:.2f}% avg return, {best_params['overall_win_rate']:.1f}% win rate
    \"\"\"
    # Implementation would use the OPTIMAL_PARAMS above
    pass
'''
        
        return scanner_code

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Momentum Scanner Backtesting System')
    parser.add_argument('--start-date', type=str, required=True,
                       help='Start date for backtesting (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True,
                       help='End date for backtesting (YYYY-MM-DD)')
    parser.add_argument('--max-combinations', type=int, default=30,
                       help='Maximum parameter combinations to test')
    parser.add_argument('--top-n', type=int, default=5,
                       help='Number of top results to display')
    parser.add_argument('--export', type=str,
                       help='Export results to CSV file')
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        
        if start_date >= end_date:
            logger.error("❌ Start date must be before end date")
            return 1
        
        backtester = MomentumScannerBacktest()
        results = backtester.run_backtest(
            start_date=start_date,
            end_date=end_date,
            max_combinations=args.max_combinations
        )
        
        if not results.empty:
            backtester.display_backtest_results(results, args.top_n)
            
            # Generate optimized scanner code
            scanner_code = backtester.generate_optimized_scanner(results)
            print(f"\n📝 OPTIMIZED SCANNER CODE:")
            print(scanner_code)
            
            if args.export:
                results.to_csv(args.export, index=False)
                logger.info(f"📁 Results exported to {args.export}")
            
            print(f"\n✅ Backtesting completed successfully!")
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
    
    return 0

if __name__ == "__main__":
    exit(main())

