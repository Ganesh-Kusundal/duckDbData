#!/usr/bin/env python3
"""
Ultra-Fast 3-Stock Backtest

Optimized for maximum speed by:
1. Batch processing all days at once
2. Single database connection with bulk queries
3. Vectorized operations instead of loops
4. Minimal scanner instantiation
5. Pre-computed data structures

This should be 10-50x faster than the threaded version.

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
import warnings
import time
warnings.filterwarnings('ignore')

from core.duckdb_infra.database import DuckDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UltraFastBacktest:
    """Ultra-fast backtesting using bulk operations"""
    
    def __init__(self):
        """Initialize the ultra-fast backtesting system"""
        self.db_manager = DuckDBManager()
        self.TOP_N_PICKS = 3
        
        # Scanner parameters (embedded for speed)
        self.original_params = {
            'min_volume_threshold': 100000,
            'min_relative_volume': 2.0,
            'min_price_change': 1.0,
            'min_volatility': 1.5,
            'max_price': 2000,
            'min_price': 10,
            'min_minutes': 30
        }
        
        self.enhanced_params = {
            'min_volume_threshold': 150000,
            'min_relative_volume': 2.5,
            'min_price_change': 0.8,
            'min_volatility': 1.2,
            'max_price': 1500,
            'min_price': 15,
            'min_minutes': 32
        }
    
    def get_all_data_bulk(self, start_year: int, end_year: int, sample_size: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Get all required data in bulk queries"""
        logger.info("📊 Loading all data in bulk for maximum speed...")
        
        # Get trading days
        trading_days_query = '''
        SELECT DISTINCT DATE(timestamp) as trade_date
        FROM market_data 
        WHERE EXTRACT(YEAR FROM timestamp) >= ?
            AND EXTRACT(YEAR FROM timestamp) <= ?
            AND strftime('%H:%M', timestamp) <= '15:29'
            AND strftime('%H:%M', timestamp) >= '09:15'
        ORDER BY trade_date
        '''
        
        trading_days = self.db_manager.execute_custom_query(trading_days_query, [start_year, end_year])
        
        if trading_days.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        # Sample if requested
        if sample_size and len(trading_days) > sample_size:
            trading_days = trading_days.sample(n=sample_size, random_state=42).sort_values('trade_date')
        
        logger.info(f"📅 Processing {len(trading_days)} trading days")
        
        # Convert to date list for SQL
        date_list = "', '".join([str(d) for d in trading_days['trade_date']])
        
        # Bulk query for 09:50 AM data (scanner input)
        logger.info("🔍 Loading 09:50 AM scanner data...")
        scanner_data_query = f'''
        WITH daily_0950_data AS (
            SELECT 
                DATE(timestamp) as trade_date,
                symbol,
                COUNT(*) as minutes_active,
                SUM(volume) as total_volume_0950,
                AVG(volume) as avg_minute_volume,
                
                MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) as opening_price,
                MAX(CASE WHEN strftime('%H:%M', timestamp) = '09:50' THEN close END) as price_0950,
                MAX(high) as high_0950,
                MIN(low) as low_0950,
                AVG(close) as avg_price
                
            FROM market_data 
            WHERE DATE(timestamp) IN ('{date_list}')
                AND strftime('%H:%M', timestamp) <= '09:50'
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY DATE(timestamp), symbol
            HAVING COUNT(*) >= 25
                AND opening_price IS NOT NULL 
                AND price_0950 IS NOT NULL
        ),
        
        historical_volume AS (
            SELECT 
                symbol,
                AVG(daily_vol) as avg_historical_volume
            FROM (
                SELECT 
                    symbol,
                    DATE(timestamp) as trade_date,
                    SUM(volume) as daily_vol
                FROM market_data 
                WHERE DATE(timestamp) >= (SELECT MIN(trade_date) FROM daily_0950_data) - INTERVAL '10 days'
                    AND DATE(timestamp) < (SELECT MIN(trade_date) FROM daily_0950_data)
                    AND strftime('%H:%M', timestamp) <= '09:50'
                    AND strftime('%H:%M', timestamp) >= '09:15'
                GROUP BY symbol, DATE(timestamp)
            ) hist
            GROUP BY symbol
            HAVING COUNT(*) >= 3
        )
        
        SELECT 
            d.*,
            COALESCE(h.avg_historical_volume, d.total_volume_0950 * 0.6) as historical_avg,
            d.total_volume_0950 / COALESCE(h.avg_historical_volume, d.total_volume_0950 * 0.6) as relative_volume,
            (d.price_0950 - d.opening_price) / d.opening_price * 100 as price_change_pct,
            (d.high_0950 - d.low_0950) / d.avg_price * 100 as volatility_pct,
            ABS((d.price_0950 - d.opening_price) / d.opening_price * 100) as abs_momentum
            
        FROM daily_0950_data d
        LEFT JOIN historical_volume h ON d.symbol = h.symbol
        WHERE d.avg_price >= 10 AND d.avg_price <= 2000
        ORDER BY d.trade_date, d.symbol
        '''
        
        scanner_data = self.db_manager.execute_custom_query(scanner_data_query)
        
        # Bulk query for EOD performance data
        logger.info("📈 Loading end-of-day performance data...")
        eod_data_query = f'''
        SELECT 
            DATE(timestamp) as trade_date,
            symbol,
            
            (SELECT open FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = DATE(m1.timestamp)
                AND strftime('%H:%M', m2.timestamp) = '09:15'
             LIMIT 1) as opening_price,
             
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = DATE(m1.timestamp)
                AND strftime('%H:%M', m2.timestamp) = '15:29'
             LIMIT 1) as closing_price
             
        FROM market_data m1
        WHERE DATE(timestamp) IN ('{date_list}')
            AND strftime('%H:%M', timestamp) >= '09:15'
            AND strftime('%H:%M', timestamp) <= '15:29'
        GROUP BY DATE(timestamp), symbol
        HAVING opening_price IS NOT NULL AND closing_price IS NOT NULL
        '''
        
        eod_data = self.db_manager.execute_custom_query(eod_data_query)
        
        if not eod_data.empty:
            eod_data['day_return_pct'] = (
                (eod_data['closing_price'] - eod_data['opening_price']) / 
                eod_data['opening_price'] * 100
            )
        
        logger.info(f"✅ Loaded {len(scanner_data):,} scanner records and {len(eod_data):,} EOD records")
        
        return trading_days, scanner_data, eod_data
    
    def apply_scanner_logic_vectorized(self, scanner_data: pd.DataFrame, scanner_type: str = 'original') -> pd.DataFrame:
        """Apply scanner logic using vectorized operations"""
        
        if scanner_data.empty:
            return pd.DataFrame()
        
        params = self.original_params if scanner_type == 'original' else self.enhanced_params
        
        # Apply filters vectorized
        filtered = scanner_data[
            (scanner_data['total_volume_0950'] >= params['min_volume_threshold']) &
            (scanner_data['abs_momentum'] >= params['min_price_change']) &
            (scanner_data['relative_volume'] >= params['min_relative_volume']) &
            (scanner_data['volatility_pct'] >= params['min_volatility']) &
            (scanner_data['avg_price'] >= params['min_price']) &
            (scanner_data['avg_price'] <= params['max_price']) &
            (scanner_data['minutes_active'] >= params['min_minutes'])
        ].copy()
        
        if filtered.empty:
            return pd.DataFrame()
        
        # Calculate scores vectorized
        if scanner_type == 'original':
            # Original scoring
            filtered['volume_score'] = np.clip((filtered['relative_volume'] - 1) * 25, 0, 100)
            filtered['momentum_score'] = np.clip(filtered['abs_momentum'] * 15, 0, 100)
            filtered['liquidity_score'] = filtered['total_volume_0950'].rank(pct=True) * 100
            filtered['volatility_score'] = np.clip(100 - abs(filtered['volatility_pct'] - 3) * 20, 0, 100)
            
            filtered['composite_score'] = (
                filtered['volume_score'] * 0.35 +
                filtered['momentum_score'] * 0.30 +
                filtered['liquidity_score'] * 0.20 +
                filtered['volatility_score'] * 0.15
            )
        else:
            # Enhanced scoring
            filtered['volume_base_score'] = np.clip((filtered['relative_volume'] - 1) * 20, 0, 100)
            filtered['volume_optimal_bonus'] = np.where(
                (filtered['relative_volume'] >= 3) & (filtered['relative_volume'] <= 5), 20, 0
            )
            filtered['volume_score'] = np.clip(
                filtered['volume_base_score'] + filtered['volume_optimal_bonus'], 0, 100
            )
            
            filtered['momentum_base_score'] = np.clip(filtered['abs_momentum'] * 12, 0, 100)
            filtered['strong_momentum_bonus'] = np.where(filtered['abs_momentum'] >= 2.0, 15, 0)
            filtered['breakout_bonus'] = np.where(filtered['abs_momentum'] >= 3.0, 25, 0)
            filtered['momentum_score'] = np.clip(
                filtered['momentum_base_score'] + filtered['strong_momentum_bonus'] + filtered['breakout_bonus'],
                0, 100
            )
            
            filtered['liquidity_score'] = filtered['total_volume_0950'].rank(pct=True) * 100
            
            filtered['volatility_base_score'] = np.clip(filtered['volatility_pct'] * 20, 0, 100)
            filtered['volatility_optimal_bonus'] = np.where(
                (filtered['volatility_pct'] >= 2.0) & (filtered['volatility_pct'] <= 4.0), 20, 0
            )
            filtered['volatility_score'] = np.clip(
                filtered['volatility_base_score'] + filtered['volatility_optimal_bonus'], 0, 100
            )
            
            # Price range multiplier
            price_range_multiplier = np.where(
                (filtered['avg_price'] >= 50) & (filtered['avg_price'] <= 500), 1.1, 1.0
            )
            
            filtered['composite_score'] = (
                filtered['volume_score'] * 0.35 +
                filtered['momentum_score'] * 0.30 +
                filtered['liquidity_score'] * 0.20 +
                filtered['volatility_score'] * 0.15
            ) * price_range_multiplier
        
        return filtered
    
    def get_top_picks_vectorized(self, scanner_results: pd.DataFrame) -> pd.DataFrame:
        """Get top 3 picks per day using vectorized operations"""
        if scanner_results.empty:
            return pd.DataFrame()
        
        # Get top 3 per day
        if 'trade_date' not in scanner_results.columns:
            return pd.DataFrame()
            
        top_picks = (scanner_results
                    .sort_values(['trade_date', 'composite_score'], ascending=[True, False])
                    .groupby('trade_date')
                    .head(self.TOP_N_PICKS)
                    .reset_index(drop=True))
        
        return top_picks
    
    def calculate_performance_vectorized(self, trading_days: pd.DataFrame, scanner_data: pd.DataFrame, eod_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate performance metrics using vectorized operations"""
        logger.info("🧮 Calculating performance metrics...")
        
        results = []
        
        # Process original scanner
        logger.info("🔍 Processing original scanner...")
        original_filtered = self.apply_scanner_logic_vectorized(scanner_data, 'original')
        logger.info(f"📊 Original filtered columns: {list(original_filtered.columns) if not original_filtered.empty else 'Empty'}")
        original_picks = self.get_top_picks_vectorized(original_filtered)
        
        # Process enhanced scanner  
        logger.info("💎 Processing enhanced scanner...")
        enhanced_filtered = self.apply_scanner_logic_vectorized(scanner_data, 'enhanced')
        enhanced_picks = self.get_top_picks_vectorized(enhanced_filtered)
        
        # Calculate performance for each day
        for _, day_row in trading_days.iterrows():
            trade_date = day_row['trade_date']
            
            # Get day's data
            day_eod = eod_data[eod_data['trade_date'] == trade_date].copy()
            
            if day_eod.empty:
                continue
            
            # Get top gainers for the day
            day_eod_sorted = day_eod.sort_values('day_return_pct', ascending=False)
            top_3_gainers = set(day_eod_sorted.head(3)['symbol'])
            top_5_gainers = set(day_eod_sorted.head(5)['symbol'])
            
            # Get scanner picks for the day
            orig_day_picks = original_picks[original_picks['trade_date'] == trade_date]['symbol'].tolist()
            enh_day_picks = enhanced_picks[enhanced_picks['trade_date'] == trade_date]['symbol'].tolist()
            
            # Calculate hits
            orig_hits_top3 = len(set(orig_day_picks).intersection(top_3_gainers))
            enh_hits_top3 = len(set(enh_day_picks).intersection(top_3_gainers))
            orig_hits_top5 = len(set(orig_day_picks).intersection(top_5_gainers))
            enh_hits_top5 = len(set(enh_day_picks).intersection(top_5_gainers))
            
            # Calculate returns
            orig_returns = day_eod[day_eod['symbol'].isin(orig_day_picks)]['day_return_pct']
            enh_returns = day_eod[day_eod['symbol'].isin(enh_day_picks)]['day_return_pct']
            
            orig_avg_return = orig_returns.mean() if not orig_returns.empty else 0
            enh_avg_return = enh_returns.mean() if not enh_returns.empty else 0
            
            # Calculate scores
            orig_scores = original_picks[original_picks['trade_date'] == trade_date]['composite_score']
            enh_scores = enhanced_picks[enhanced_picks['trade_date'] == trade_date]['composite_score']
            
            orig_avg_score = orig_scores.mean() if not orig_scores.empty else 0
            enh_avg_score = enh_scores.mean() if not enh_scores.empty else 0
            
            results.append({
                'date': trade_date,
                'year': pd.to_datetime(trade_date).year,
                'month': pd.to_datetime(trade_date).month,
                
                'original_picks': len(orig_day_picks),
                'enhanced_picks': len(enh_day_picks),
                
                'original_hits_top3': orig_hits_top3,
                'enhanced_hits_top3': enh_hits_top3,
                'original_hits_top5': orig_hits_top5,
                'enhanced_hits_top5': enh_hits_top5,
                
                'original_hit_rate_top3': (orig_hits_top3 / len(orig_day_picks) * 100) if orig_day_picks else 0,
                'enhanced_hit_rate_top3': (enh_hits_top3 / len(enh_day_picks) * 100) if enh_day_picks else 0,
                'original_hit_rate_top5': (orig_hits_top5 / len(orig_day_picks) * 100) if orig_day_picks else 0,
                'enhanced_hit_rate_top5': (enh_hits_top5 / len(enh_day_picks) * 100) if enh_day_picks else 0,
                
                'original_avg_return': orig_avg_return,
                'enhanced_avg_return': enh_avg_return,
                'market_avg_return': day_eod_sorted.head(10)['day_return_pct'].mean(),
                
                'original_avg_score': orig_avg_score,
                'enhanced_avg_score': enh_avg_score,
                
                'original_picks_list': orig_day_picks,
                'enhanced_picks_list': enh_day_picks,
                'top_3_gainers': list(top_3_gainers),
                'top_5_gainers': list(top_5_gainers)
            })
        
        return pd.DataFrame(results)
    
    def run_ultra_fast_backtest(self, start_year: int = 2024, end_year: int = 2025, 
                               sample_size: Optional[int] = None) -> pd.DataFrame:
        """Run ultra-fast backtest"""
        start_time = time.time()
        
        logger.info(f"🚀 Starting Ultra-Fast 3-Stock Backtest ({start_year}-{end_year})")
        logger.info(f"⚡ Optimized for maximum speed with bulk operations")
        
        try:
            # Load all data in bulk
            trading_days, scanner_data, eod_data = self.get_all_data_bulk(start_year, end_year, sample_size)
            
            if trading_days.empty:
                logger.error("❌ No trading days found")
                return pd.DataFrame()
            
            # Calculate performance using vectorized operations
            results = self.calculate_performance_vectorized(trading_days, scanner_data, eod_data)
            
            total_time = time.time() - start_time
            logger.info(f"✅ Ultra-fast backtest completed in {total_time:.1f} seconds!")
            logger.info(f"📊 Processed {len(results)} trading days")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in ultra-fast backtest: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        finally:
            self.db_manager.close()
    
    def analyze_and_display_results(self, results: pd.DataFrame):
        """Analyze and display results"""
        if results.empty:
            print("❌ No results to analyze")
            return
        
        print(f"\n⚡ ULTRA-FAST 3-STOCK BACKTEST RESULTS")
        print("=" * 60)
        
        # Filter valid days
        valid_results = results[(results['original_picks'] > 0) | (results['enhanced_picks'] > 0)]
        
        print(f"\n📊 OVERVIEW:")
        print(f"   📅 Total Days: {len(results)}")
        print(f"   📈 Valid Days: {len(valid_results)}")
        print(f"   🗓️ Date Range: {results['date'].min()} to {results['date'].max()}")
        
        # Original scanner stats
        orig_valid = results[results['original_picks'] > 0]
        if not orig_valid.empty:
            orig_total_picks = orig_valid['original_picks'].sum()
            orig_hits_top3 = orig_valid['original_hits_top3'].sum()
            orig_hits_top5 = orig_valid['original_hits_top5'].sum()
            
            print(f"\n🔍 ORIGINAL SCANNER:")
            print(f"   📊 Total Picks: {orig_total_picks} (avg {orig_total_picks/len(orig_valid):.1f}/day)")
            print(f"   🥇 Top 3 Hit Rate: {orig_hits_top3/orig_total_picks*100:.1f}% ({orig_hits_top3}/{orig_total_picks})")
            print(f"   🥈 Top 5 Hit Rate: {orig_hits_top5/orig_total_picks*100:.1f}% ({orig_hits_top5}/{orig_total_picks})")
            print(f"   💰 Avg Return: {orig_valid['original_avg_return'].mean():.2f}%")
            print(f"   📊 Avg Score: {orig_valid['original_avg_score'].mean():.1f}")
        
        # Enhanced scanner stats
        enh_valid = results[results['enhanced_picks'] > 0]
        if not enh_valid.empty:
            enh_total_picks = enh_valid['enhanced_picks'].sum()
            enh_hits_top3 = enh_valid['enhanced_hits_top3'].sum()
            enh_hits_top5 = enh_valid['enhanced_hits_top5'].sum()
            
            print(f"\n💎 ENHANCED SCANNER:")
            print(f"   📊 Total Picks: {enh_total_picks} (avg {enh_total_picks/len(enh_valid):.1f}/day)")
            print(f"   🥇 Top 3 Hit Rate: {enh_hits_top3/enh_total_picks*100:.1f}% ({enh_hits_top3}/{enh_total_picks})")
            print(f"   🥈 Top 5 Hit Rate: {enh_hits_top5/enh_total_picks*100:.1f}% ({enh_hits_top5}/{enh_total_picks})")
            print(f"   💰 Avg Return: {enh_valid['enhanced_avg_return'].mean():.2f}%")
            print(f"   📊 Avg Score: {enh_valid['enhanced_avg_score'].mean():.1f}")
        
        # Performance comparison
        if not orig_valid.empty and not enh_valid.empty:
            top3_improvement = (enh_hits_top3/enh_total_picks) - (orig_hits_top3/orig_total_picks)
            return_improvement = enh_valid['enhanced_avg_return'].mean() - orig_valid['original_avg_return'].mean()
            
            print(f"\n📈 ENHANCEMENT IMPACT:")
            print(f"   🎯 Top 3 Hit Rate: {top3_improvement*100:+.1f}%")
            print(f"   💰 Return Improvement: {return_improvement:+.2f}%")
            
            if top3_improvement > 0.02:  # 2% improvement
                print(f"   🚀 ENHANCED SCANNER SUPERIOR!")
            elif top3_improvement > 0:
                print(f"   ✅ ENHANCED SCANNER BETTER")
            else:
                print(f"   ⚠️ ENHANCEMENT NEEDS WORK")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Ultra-Fast 3-Stock Momentum Scanner Backtest')
    parser.add_argument('--start-year', type=int, default=2024,
                       help='Start year for backtesting')
    parser.add_argument('--end-year', type=int, default=2025,
                       help='End year for backtesting')
    parser.add_argument('--sample-size', type=int,
                       help='Sample size to limit computation')
    parser.add_argument('--export', type=str,
                       help='Export results to CSV file')
    
    args = parser.parse_args()
    
    try:
        backtester = UltraFastBacktest()
        
        results = backtester.run_ultra_fast_backtest(
            start_year=args.start_year,
            end_year=args.end_year,
            sample_size=args.sample_size
        )
        
        if not results.empty:
            backtester.analyze_and_display_results(results)
            
            if args.export:
                results.to_csv(args.export, index=False)
                logger.info(f"📁 Results exported to {args.export}")
            
            print(f"\n✅ Ultra-fast backtest completed!")
        else:
            print(f"\n⚠️ No results generated")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
