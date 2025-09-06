#!/usr/bin/env python3
"""
Simple Fast 3-Stock Backtest

Simplified version that focuses on speed and reliability.
Tests both scanners with top 3 picks per day.

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
from typing import List, Dict, Optional
import argparse
import time

from core.duckdb_infra.database import DuckDBManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleFastBacktest:
    """Simple and fast backtesting system"""
    
    def __init__(self):
        self.db_manager = DuckDBManager()
        self.TOP_N = 3
    
    def get_trading_days(self, start_year: int, end_year: int, sample_size: Optional[int] = None) -> List[date]:
        """Get list of trading days"""
        query = '''
        SELECT DISTINCT DATE(timestamp) as trade_date
        FROM market_data 
        WHERE EXTRACT(YEAR FROM timestamp) >= ?
            AND EXTRACT(YEAR FROM timestamp) <= ?
        ORDER BY trade_date
        '''
        
        result = self.db_manager.execute_custom_query(query, [start_year, end_year])
        dates = [pd.to_datetime(row['trade_date']).date() for _, row in result.iterrows()]
        
        if sample_size and len(dates) > sample_size:
            # Sample evenly
            step = len(dates) // sample_size
            dates = dates[::step][:sample_size]
        
        return dates
    
    def get_day_candidates(self, scan_date: date) -> pd.DataFrame:
        """Get momentum candidates for a single day"""
        query = '''
        WITH day_data AS (
            SELECT 
                symbol,
                COUNT(*) as minutes_active,
                SUM(volume) as total_volume,
                
                MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) as open_price,
                MAX(CASE WHEN strftime('%H:%M', timestamp) = '09:50' THEN close END) as price_0950,
                MAX(high) as high_0950,
                MIN(low) as low_0950,
                AVG(close) as avg_price
                
            FROM market_data 
            WHERE DATE(timestamp) = ?
                AND strftime('%H:%M', timestamp) <= '09:50'
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
            HAVING COUNT(*) >= 25
                AND open_price IS NOT NULL 
                AND price_0950 IS NOT NULL
        )
        
        SELECT 
            symbol,
            total_volume,
            open_price,
            price_0950,
            high_0950,
            low_0950,
            avg_price,
            (price_0950 - open_price) / open_price * 100 as price_change_pct,
            (high_0950 - low_0950) / avg_price * 100 as volatility_pct,
            ABS((price_0950 - open_price) / open_price * 100) as abs_momentum
            
        FROM day_data
        WHERE avg_price >= 10 
            AND avg_price <= 2000
            AND total_volume >= 50000
            AND ABS((price_0950 - open_price) / open_price * 100) >= 0.5
        ORDER BY ABS((price_0950 - open_price) / open_price * 100) DESC
        '''
        
        return self.db_manager.execute_custom_query(query, [scan_date])
    
    def get_day_performance(self, scan_date: date) -> pd.DataFrame:
        """Get end-of-day performance for all stocks"""
        query = '''
        SELECT 
            symbol,
            (SELECT open FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:15'
             LIMIT 1) as open_price,
             
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '15:29'
             LIMIT 1) as close_price
             
        FROM market_data m1
        WHERE DATE(timestamp) = ?
        GROUP BY symbol
        HAVING open_price IS NOT NULL AND close_price IS NOT NULL
        '''
        
        result = self.db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
        
        if not result.empty:
            result['day_return_pct'] = (result['close_price'] - result['open_price']) / result['open_price'] * 100
        
        return result
    
    def apply_original_scanner(self, candidates: pd.DataFrame) -> List[str]:
        """Apply original scanner logic"""
        if candidates.empty:
            return []
        
        # Original scanner filters
        filtered = candidates[
            (candidates['total_volume'] >= 100000) &
            (candidates['abs_momentum'] >= 1.0) &
            (candidates['volatility_pct'] >= 1.5)
        ].copy()
        
        if filtered.empty:
            return []
        
        # Simple scoring
        filtered['score'] = (
            filtered['abs_momentum'] * 0.4 +
            (filtered['total_volume'] / 100000) * 0.3 +
            filtered['volatility_pct'] * 0.3
        )
        
        return filtered.nlargest(self.TOP_N, 'score')['symbol'].tolist()
    
    def apply_enhanced_scanner(self, candidates: pd.DataFrame) -> List[str]:
        """Apply enhanced scanner logic"""
        if candidates.empty:
            return []
        
        # Enhanced scanner filters
        filtered = candidates[
            (candidates['total_volume'] >= 150000) &
            (candidates['abs_momentum'] >= 0.8) &
            (candidates['volatility_pct'] >= 1.2) &
            (candidates['avg_price'] >= 15) &
            (candidates['avg_price'] <= 1500)
        ].copy()
        
        if filtered.empty:
            return []
        
        # Enhanced scoring with bonuses
        filtered['base_score'] = (
            filtered['abs_momentum'] * 0.35 +
            (filtered['total_volume'] / 150000) * 0.35 +
            filtered['volatility_pct'] * 0.3
        )
        
        # Bonuses for optimal ranges
        filtered['momentum_bonus'] = np.where(filtered['abs_momentum'] >= 2.0, 10, 0)
        filtered['volume_bonus'] = np.where(filtered['total_volume'] >= 300000, 5, 0)
        filtered['price_bonus'] = np.where(
            (filtered['avg_price'] >= 50) & (filtered['avg_price'] <= 500), 5, 0
        )
        
        filtered['final_score'] = (
            filtered['base_score'] + 
            filtered['momentum_bonus'] + 
            filtered['volume_bonus'] + 
            filtered['price_bonus']
        )
        
        return filtered.nlargest(self.TOP_N, 'final_score')['symbol'].tolist()
    
    def backtest_single_day(self, scan_date: date) -> Dict:
        """Backtest a single day"""
        try:
            # Get candidates and performance
            candidates = self.get_day_candidates(scan_date)
            performance = self.get_day_performance(scan_date)
            
            if candidates.empty or performance.empty:
                return {
                    'date': scan_date,
                    'original_picks': 0,
                    'enhanced_picks': 0,
                    'original_hits_top3': 0,
                    'enhanced_hits_top3': 0,
                    'original_hits_top5': 0,
                    'enhanced_hits_top5': 0,
                    'status': 'NO_DATA'
                }
            
            # Apply scanners
            original_picks = self.apply_original_scanner(candidates)
            enhanced_picks = self.apply_enhanced_scanner(candidates)
            
            # Get top gainers
            top_gainers = performance.nlargest(10, 'day_return_pct')
            top_3_gainers = set(top_gainers.head(3)['symbol'])
            top_5_gainers = set(top_gainers.head(5)['symbol'])
            
            # Calculate hits
            orig_hits_3 = len(set(original_picks).intersection(top_3_gainers))
            enh_hits_3 = len(set(enhanced_picks).intersection(top_3_gainers))
            orig_hits_5 = len(set(original_picks).intersection(top_5_gainers))
            enh_hits_5 = len(set(enhanced_picks).intersection(top_5_gainers))
            
            # Calculate returns
            orig_performance = performance[performance['symbol'].isin(original_picks)]
            enh_performance = performance[performance['symbol'].isin(enhanced_picks)]
            
            orig_return = orig_performance['day_return_pct'].mean() if not orig_performance.empty else 0
            enh_return = enh_performance['day_return_pct'].mean() if not enh_performance.empty else 0
            
            return {
                'date': scan_date,
                'year': scan_date.year,
                'original_picks': len(original_picks),
                'enhanced_picks': len(enhanced_picks),
                'original_hits_top3': orig_hits_3,
                'enhanced_hits_top3': enh_hits_3,
                'original_hits_top5': orig_hits_5,
                'enhanced_hits_top5': enh_hits_5,
                'original_return': orig_return,
                'enhanced_return': enh_return,
                'market_return': top_gainers.head(10)['day_return_pct'].mean(),
                'original_picks_list': original_picks,
                'enhanced_picks_list': enhanced_picks,
                'top_3_gainers': list(top_3_gainers),
                'status': 'SUCCESS'
            }
            
        except Exception as e:
            logger.warning(f"Error processing {scan_date}: {e}")
            return {
                'date': scan_date,
                'original_picks': 0,
                'enhanced_picks': 0,
                'original_hits_top3': 0,
                'enhanced_hits_top3': 0,
                'original_hits_top5': 0,
                'enhanced_hits_top5': 0,
                'status': 'ERROR'
            }
    
    def run_backtest(self, start_year: int, end_year: int, sample_size: Optional[int] = None) -> pd.DataFrame:
        """Run the complete backtest"""
        start_time = time.time()
        
        logger.info(f"🚀 Starting Simple Fast Backtest ({start_year}-{end_year})")
        
        # Get trading days
        trading_days = self.get_trading_days(start_year, end_year, sample_size)
        logger.info(f"📅 Processing {len(trading_days)} trading days")
        
        results = []
        
        for i, scan_date in enumerate(trading_days):
            if (i + 1) % 20 == 0:
                elapsed = time.time() - start_time
                eta = (elapsed / (i + 1)) * (len(trading_days) - i - 1)
                logger.info(f"📊 Progress: {i+1}/{len(trading_days)} - ETA: {eta/60:.1f} min")
            
            result = self.backtest_single_day(scan_date)
            results.append(result)
        
        total_time = time.time() - start_time
        logger.info(f"✅ Backtest completed in {total_time:.1f} seconds")
        
        return pd.DataFrame(results)
    
    def analyze_results(self, results: pd.DataFrame):
        """Analyze and display results"""
        if results.empty:
            print("❌ No results to analyze")
            return
        
        # Filter successful days
        success_results = results[results['status'] == 'SUCCESS']
        
        print(f"\n🎯 SIMPLE FAST BACKTEST RESULTS")
        print("=" * 50)
        
        print(f"\n📊 OVERVIEW:")
        print(f"   📅 Total Days: {len(results)}")
        print(f"   ✅ Successful Days: {len(success_results)}")
        print(f"   📈 Date Range: {results['date'].min()} to {results['date'].max()}")
        
        if success_results.empty:
            print("❌ No successful trading days found")
            return
        
        # Original scanner analysis
        orig_days = success_results[success_results['original_picks'] > 0]
        if not orig_days.empty:
            orig_total_picks = orig_days['original_picks'].sum()
            orig_hits_3 = orig_days['original_hits_top3'].sum()
            orig_hits_5 = orig_days['original_hits_top5'].sum()
            
            print(f"\n🔍 ORIGINAL SCANNER:")
            print(f"   📊 Total Picks: {orig_total_picks}")
            print(f"   🥇 Top 3 Hit Rate: {orig_hits_3/orig_total_picks*100:.1f}% ({orig_hits_3}/{orig_total_picks})")
            print(f"   🥈 Top 5 Hit Rate: {orig_hits_5/orig_total_picks*100:.1f}% ({orig_hits_5}/{orig_total_picks})")
            print(f"   💰 Avg Return: {orig_days['original_return'].mean():.2f}%")
        
        # Enhanced scanner analysis
        enh_days = success_results[success_results['enhanced_picks'] > 0]
        if not enh_days.empty:
            enh_total_picks = enh_days['enhanced_picks'].sum()
            enh_hits_3 = enh_days['enhanced_hits_top3'].sum()
            enh_hits_5 = enh_days['enhanced_hits_top5'].sum()
            
            print(f"\n💎 ENHANCED SCANNER:")
            print(f"   📊 Total Picks: {enh_total_picks}")
            print(f"   🥇 Top 3 Hit Rate: {enh_hits_3/enh_total_picks*100:.1f}% ({enh_hits_3}/{enh_total_picks})")
            print(f"   🥈 Top 5 Hit Rate: {enh_hits_5/enh_total_picks*100:.1f}% ({enh_hits_5}/{enh_total_picks})")
            print(f"   💰 Avg Return: {enh_days['enhanced_return'].mean():.2f}%")
        
        # Comparison
        if not orig_days.empty and not enh_days.empty:
            orig_hit_rate_3 = orig_hits_3/orig_total_picks*100
            enh_hit_rate_3 = enh_hits_3/enh_total_picks*100
            improvement = enh_hit_rate_3 - orig_hit_rate_3
            
            print(f"\n📈 COMPARISON:")
            print(f"   🎯 Top 3 Hit Rate Improvement: {improvement:+.1f}%")
            
            if improvement > 2:
                print(f"   🚀 ENHANCED SCANNER SIGNIFICANTLY BETTER!")
            elif improvement > 0:
                print(f"   ✅ ENHANCED SCANNER BETTER")
            else:
                print(f"   ⚠️ ORIGINAL SCANNER BETTER")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Simple Fast 3-Stock Backtest')
    parser.add_argument('--start-year', type=int, default=2024)
    parser.add_argument('--end-year', type=int, default=2025)
    parser.add_argument('--sample-size', type=int, help='Sample size')
    parser.add_argument('--export', type=str, help='Export to CSV')
    
    args = parser.parse_args()
    
    try:
        backtester = SimpleFastBacktest()
        results = backtester.run_backtest(args.start_year, args.end_year, args.sample_size)
        
        backtester.analyze_results(results)
        
        if args.export:
            results.to_csv(args.export, index=False)
            logger.info(f"📁 Results exported to {args.export}")
        
        print(f"\n✅ Simple fast backtest completed!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1
    finally:
        try:
            backtester.db_manager.close()
        except:
            pass
    
    return 0

if __name__ == "__main__":
    exit(main())

