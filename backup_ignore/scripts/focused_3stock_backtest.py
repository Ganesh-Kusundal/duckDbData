#!/usr/bin/env python3
"""
Focused 3-Stock Multi-threaded Backtest

High-performance backtesting system targeting only the top 3 stocks per day
from each scanner. This focused approach should improve hit rates by concentrating
on the highest-quality momentum opportunities.

Key Features:
1. Top 3 stocks only per scanner per day
2. Multi-threaded processing for speed
3. Focused quality over quantity approach
4. Enhanced precision metrics

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
import threading
import concurrent.futures
from queue import Queue
import time
warnings.filterwarnings('ignore')

from core.duckdb_infra.database import DuckDBManager
from optimized_momentum_scanner import OptimizedMomentumScanner
from enhanced_momentum_scanner import EnhancedMomentumScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Focused3StockBacktest:
    """Focused backtesting system targeting top 3 stocks per day"""
    
    def __init__(self, max_workers: int = 4):
        """Initialize the focused backtesting system"""
        self.max_workers = max_workers
        self.results_queue = Queue()
        self.progress_lock = threading.Lock()
        self.processed_days = 0
        self.total_days = 0
        self.start_time = None
        
        # Focus on top 3 stocks only
        self.TOP_N_PICKS = 3
        
    def create_thread_safe_scanners(self):
        """Create thread-safe scanner instances"""
        return {
            'db_manager': DuckDBManager(),
            'original_scanner': OptimizedMomentumScanner(),
            'enhanced_scanner': EnhancedMomentumScanner()
        }
    
    def get_all_trading_days(self) -> pd.DataFrame:
        """Get all available trading days"""
        logger.info("📅 Discovering all available trading days")
        
        db_manager = DuckDBManager()
        
        query = '''
        SELECT 
            DATE(timestamp) as trade_date,
            COUNT(DISTINCT symbol) as active_symbols,
            COUNT(*) as total_records,
            EXTRACT(YEAR FROM DATE(timestamp)) as year,
            EXTRACT(MONTH FROM DATE(timestamp)) as month
        FROM market_data 
        WHERE strftime('%H:%M', timestamp) <= '15:29'
            AND strftime('%H:%M', timestamp) >= '09:15'
        GROUP BY DATE(timestamp)
        HAVING COUNT(DISTINCT symbol) >= 20
            AND COUNT(*) >= 500
        ORDER BY trade_date
        '''
        
        result = db_manager.execute_custom_query(query)
        db_manager.close()
        
        if not result.empty:
            result['trade_date'] = pd.to_datetime(result['trade_date']).dt.date
            logger.info(f"📊 Found {len(result)} trading days from {result['trade_date'].min()} to {result['trade_date'].max()}")
        
        return result
    
    def get_actual_top_gainers(self, db_manager: DuckDBManager, scan_date: date, top_n: int = 10) -> pd.DataFrame:
        """Get actual top gainers for a specific date"""
        
        query = '''
        SELECT 
            symbol,
            (SELECT open FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:15'
             LIMIT 1) as opening_price,
             
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '15:29'
             LIMIT 1) as closing_price
             
        FROM market_data m1
        WHERE DATE(timestamp) = ?
            AND strftime('%H:%M', timestamp) >= '09:15'
            AND strftime('%H:%M', timestamp) <= '15:29'
        GROUP BY symbol
        HAVING opening_price IS NOT NULL 
            AND closing_price IS NOT NULL
        '''
        
        day_performance = db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
        
        if day_performance.empty:
            return pd.DataFrame()
        
        day_performance['day_return_pct'] = (
            (day_performance['closing_price'] - day_performance['opening_price']) / 
            day_performance['opening_price'] * 100
        )
        
        return day_performance.sort_values('day_return_pct', ascending=False).head(top_n)
    
    def get_scanner_picks_performance(self, db_manager: DuckDBManager, scan_date: date, scanner_picks: List[str]) -> pd.DataFrame:
        """Get performance of scanner picks"""
        if not scanner_picks:
            return pd.DataFrame()
        
        symbol_list = "', '".join(scanner_picks)
        
        query = f'''
        SELECT 
            symbol,
            (SELECT open FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '09:15'
             LIMIT 1) as opening_price,
             
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = ?
                AND strftime('%H:%M', m2.timestamp) = '15:29'
             LIMIT 1) as closing_price
             
        FROM market_data m1
        WHERE DATE(timestamp) = ?
            AND symbol IN ('{symbol_list}')
        GROUP BY symbol
        '''
        
        picks_performance = db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
        
        if not picks_performance.empty:
            picks_performance['day_return_pct'] = (
                (picks_performance['closing_price'] - picks_performance['opening_price']) / 
                picks_performance['opening_price'] * 100
            )
        
        return picks_performance
    
    def backtest_single_day_focused(self, trade_date: date, thread_id: int) -> Dict:
        """Worker function to backtest a single day with top 3 focus"""
        
        # Create thread-local scanners and DB connection
        thread_resources = self.create_thread_safe_scanners()
        db_manager = thread_resources['db_manager']
        original_scanner = thread_resources['original_scanner']
        enhanced_scanner = thread_resources['enhanced_scanner']
        
        try:
            # Get actual top gainers
            top_gainers = self.get_actual_top_gainers(db_manager, trade_date, 10)
            
            if top_gainers.empty:
                return {
                    'date': trade_date,
                    'year': trade_date.year,
                    'month': trade_date.month,
                    'original_picks': 0,
                    'enhanced_picks': 0,
                    'original_hits': 0,
                    'enhanced_hits': 0,
                    'original_hit_rate': 0,
                    'enhanced_hit_rate': 0,
                    'original_avg_return': 0,
                    'enhanced_avg_return': 0,
                    'market_avg_return': 0,
                    'data_quality': 'POOR',
                    'thread_id': thread_id
                }
            
            # Test original scanner - TOP 3 ONLY
            original_picks = []
            original_scores = []
            try:
                original_candidates = original_scanner.get_momentum_candidates(trade_date)
                if not original_candidates.empty:
                    original_results = original_scanner.calculate_momentum_scores(original_candidates)
                    top_original = original_results.head(self.TOP_N_PICKS)
                    original_picks = top_original['symbol'].tolist()
                    original_scores = top_original['composite_score'].tolist()
            except Exception as e:
                logger.warning(f"Thread {thread_id}: Original scanner failed for {trade_date}: {e}")
            
            # Test enhanced scanner - TOP 3 ONLY
            enhanced_picks = []
            enhanced_scores = []
            try:
                enhanced_candidates = enhanced_scanner.get_enhanced_candidates(trade_date)
                if not enhanced_candidates.empty:
                    enhanced_results = enhanced_scanner.calculate_enhanced_scores(enhanced_candidates)
                    top_enhanced = enhanced_results.head(self.TOP_N_PICKS)
                    enhanced_picks = top_enhanced['symbol'].tolist()
                    enhanced_scores = top_enhanced['composite_score'].tolist()
            except Exception as e:
                logger.warning(f"Thread {thread_id}: Enhanced scanner failed for {trade_date}: {e}")
            
            # Calculate performance metrics - focus on top 3 and top 5 gainers
            top_3_gainer_symbols = set(top_gainers.head(3)['symbol'].tolist())
            top_5_gainer_symbols = set(top_gainers.head(5)['symbol'].tolist())
            
            # Hit rates for top 3 gainers
            original_hits_top3 = len(set(original_picks).intersection(top_3_gainer_symbols))
            enhanced_hits_top3 = len(set(enhanced_picks).intersection(top_3_gainer_symbols))
            
            # Hit rates for top 5 gainers
            original_hits_top5 = len(set(original_picks).intersection(top_5_gainer_symbols))
            enhanced_hits_top5 = len(set(enhanced_picks).intersection(top_5_gainer_symbols))
            
            original_hit_rate_top3 = (original_hits_top3 / len(original_picks)) * 100 if original_picks else 0
            enhanced_hit_rate_top3 = (enhanced_hits_top3 / len(enhanced_picks)) * 100 if enhanced_picks else 0
            
            original_hit_rate_top5 = (original_hits_top5 / len(original_picks)) * 100 if original_picks else 0
            enhanced_hit_rate_top5 = (enhanced_hits_top5 / len(enhanced_picks)) * 100 if enhanced_picks else 0
            
            # Returns
            original_performance = self.get_scanner_picks_performance(db_manager, trade_date, original_picks)
            enhanced_performance = self.get_scanner_picks_performance(db_manager, trade_date, enhanced_picks)
            
            original_avg_return = original_performance['day_return_pct'].mean() if not original_performance.empty else 0
            enhanced_avg_return = enhanced_performance['day_return_pct'].mean() if not enhanced_performance.empty else 0
            market_avg_return = top_gainers['day_return_pct'].mean()
            
            # Best pick performance
            original_best_return = original_performance['day_return_pct'].max() if not original_performance.empty else 0
            enhanced_best_return = enhanced_performance['day_return_pct'].max() if not enhanced_performance.empty else 0
            
            # Average scores
            original_avg_score = np.mean(original_scores) if original_scores else 0
            enhanced_avg_score = np.mean(enhanced_scores) if enhanced_scores else 0
            
            return {
                'date': trade_date,
                'year': trade_date.year,
                'month': trade_date.month,
                'original_picks': len(original_picks),
                'enhanced_picks': len(enhanced_picks),
                
                # Top 3 gainer hits
                'original_hits_top3': original_hits_top3,
                'enhanced_hits_top3': enhanced_hits_top3,
                'original_hit_rate_top3': original_hit_rate_top3,
                'enhanced_hit_rate_top3': enhanced_hit_rate_top3,
                
                # Top 5 gainer hits
                'original_hits_top5': original_hits_top5,
                'enhanced_hits_top5': enhanced_hits_top5,
                'original_hit_rate_top5': original_hit_rate_top5,
                'enhanced_hit_rate_top5': enhanced_hit_rate_top5,
                
                # Returns
                'original_avg_return': original_avg_return,
                'enhanced_avg_return': enhanced_avg_return,
                'market_avg_return': market_avg_return,
                'original_outperformance': original_avg_return - market_avg_return,
                'enhanced_outperformance': enhanced_avg_return - market_avg_return,
                
                # Best picks
                'original_best_return': original_best_return,
                'enhanced_best_return': enhanced_best_return,
                
                # Quality metrics
                'original_avg_score': original_avg_score,
                'enhanced_avg_score': enhanced_avg_score,
                
                'data_quality': 'GOOD',
                'thread_id': thread_id,
                'top_3_gainer_symbols': list(top_3_gainer_symbols),
                'top_5_gainer_symbols': list(top_5_gainer_symbols),
                'original_picks_list': original_picks,
                'enhanced_picks_list': enhanced_picks
            }
            
        except Exception as e:
            logger.error(f"Thread {thread_id}: Error backtesting {trade_date}: {e}")
            return {
                'date': trade_date,
                'year': trade_date.year,
                'month': trade_date.month,
                'original_picks': 0,
                'enhanced_picks': 0,
                'original_hits_top3': 0,
                'enhanced_hits_top3': 0,
                'original_hit_rate_top3': 0,
                'enhanced_hit_rate_top3': 0,
                'original_hits_top5': 0,
                'enhanced_hits_top5': 0,
                'original_hit_rate_top5': 0,
                'enhanced_hit_rate_top5': 0,
                'original_avg_return': 0,
                'enhanced_avg_return': 0,
                'market_avg_return': 0,
                'data_quality': 'ERROR',
                'thread_id': thread_id
            }
        finally:
            # Clean up thread resources
            try:
                db_manager.close()
            except:
                pass
    
    def update_progress(self):
        """Thread-safe progress update"""
        with self.progress_lock:
            self.processed_days += 1
            
            if self.start_time:
                elapsed = time.time() - self.start_time
                progress = self.processed_days / self.total_days
                eta = (elapsed / progress - elapsed) if progress > 0 else 0
                
                if self.processed_days % 20 == 0 or self.processed_days <= 5:
                    logger.info(f"📊 Progress: {self.processed_days}/{self.total_days} "
                              f"({progress*100:.1f}%) - ETA: {eta/60:.1f} minutes")
    
    def run_focused_backtest(self, start_year: int = 2024, end_year: int = 2025, 
                           sample_size: Optional[int] = None) -> pd.DataFrame:
        """Run focused 3-stock backtest"""
        logger.info(f"🚀 Starting Focused 3-Stock Backtest ({start_year}-{end_year})")
        logger.info(f"🎯 Targeting TOP {self.TOP_N_PICKS} stocks per scanner per day")
        logger.info(f"🧵 Using {self.max_workers} worker threads")
        
        # Get all trading days
        all_days = self.get_all_trading_days()
        
        if all_days.empty:
            logger.error("❌ No trading days found")
            return pd.DataFrame()
        
        # Filter by year range
        filtered_days = all_days[
            (all_days['year'] >= start_year) & 
            (all_days['year'] <= end_year)
        ].copy()
        
        if sample_size and len(filtered_days) > sample_size:
            filtered_days = filtered_days.sample(n=sample_size, random_state=42).sort_values('trade_date')
            logger.info(f"📊 Sampling {sample_size} days from {len(all_days)} available days")
        
        self.total_days = len(filtered_days)
        self.processed_days = 0
        self.start_time = time.time()
        
        logger.info(f"📊 Processing {self.total_days} trading days across {filtered_days['year'].nunique()} years")
        
        # Prepare trading dates list
        trading_dates = filtered_days['trade_date'].tolist()
        
        # Multi-threaded processing
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_date = {
                executor.submit(self.backtest_single_day_focused, trade_date, i % self.max_workers): trade_date 
                for i, trade_date in enumerate(trading_dates)
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_date):
                trade_date = future_to_date[future]
                try:
                    result = future.result()
                    results.append(result)
                    self.update_progress()
                except Exception as e:
                    logger.error(f"❌ Task failed for {trade_date}: {e}")
                    self.update_progress()
        
        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        
        if not results_df.empty:
            # Filter out poor quality data
            quality_results = results_df[results_df['data_quality'] == 'GOOD'].copy()
            
            total_time = time.time() - self.start_time
            logger.info(f"✅ Focused 3-stock backtest completed in {total_time/60:.1f} minutes")
            logger.info(f"📊 Quality results: {len(quality_results)}/{len(results_df)} days")
            
            return quality_results
        
        return results_df
    
    def analyze_focused_results(self, results: pd.DataFrame) -> Dict:
        """Analyze focused backtest results"""
        if results.empty:
            return {}
        
        analysis = {
            'total_days': len(results),
            'years_covered': sorted(results['year'].unique()),
            'date_range': f"{results['date'].min()} to {results['date'].max()}",
            
            # Original scanner performance - Top 3 gainers
            'original_total_picks': results['original_picks'].sum(),
            'original_total_hits_top3': results['original_hits_top3'].sum(),
            'original_overall_hit_rate_top3': (results['original_hits_top3'].sum() / results['original_picks'].sum() * 100) if results['original_picks'].sum() > 0 else 0,
            'original_avg_daily_hit_rate_top3': results[results['original_picks'] > 0]['original_hit_rate_top3'].mean(),
            
            # Original scanner performance - Top 5 gainers
            'original_total_hits_top5': results['original_hits_top5'].sum(),
            'original_overall_hit_rate_top5': (results['original_hits_top5'].sum() / results['original_picks'].sum() * 100) if results['original_picks'].sum() > 0 else 0,
            'original_avg_daily_hit_rate_top5': results[results['original_picks'] > 0]['original_hit_rate_top5'].mean(),
            
            # Enhanced scanner performance - Top 3 gainers
            'enhanced_total_picks': results['enhanced_picks'].sum(),
            'enhanced_total_hits_top3': results['enhanced_hits_top3'].sum(),
            'enhanced_overall_hit_rate_top3': (results['enhanced_hits_top3'].sum() / results['enhanced_picks'].sum() * 100) if results['enhanced_picks'].sum() > 0 else 0,
            'enhanced_avg_daily_hit_rate_top3': results[results['enhanced_picks'] > 0]['enhanced_hit_rate_top3'].mean(),
            
            # Enhanced scanner performance - Top 5 gainers
            'enhanced_total_hits_top5': results['enhanced_hits_top5'].sum(),
            'enhanced_overall_hit_rate_top5': (results['enhanced_hits_top5'].sum() / results['enhanced_picks'].sum() * 100) if results['enhanced_picks'].sum() > 0 else 0,
            'enhanced_avg_daily_hit_rate_top5': results[results['enhanced_picks'] > 0]['enhanced_hit_rate_top5'].mean(),
            
            # Returns
            'original_avg_return': results[results['original_picks'] > 0]['original_avg_return'].mean(),
            'enhanced_avg_return': results[results['enhanced_picks'] > 0]['enhanced_avg_return'].mean(),
            'original_win_rate': (results['original_avg_return'] > 0).mean() * 100,
            'enhanced_win_rate': (results['enhanced_avg_return'] > 0).mean() * 100,
            
            # Best picks
            'original_best_avg': results[results['original_picks'] > 0]['original_best_return'].mean(),
            'enhanced_best_avg': results[results['enhanced_picks'] > 0]['enhanced_best_return'].mean(),
            
            # Quality scores
            'original_avg_score': results[results['original_picks'] > 0]['original_avg_score'].mean(),
            'enhanced_avg_score': results[results['enhanced_picks'] > 0]['enhanced_avg_score'].mean(),
        }
        
        return analysis
    
    def display_focused_results(self, results: pd.DataFrame, analysis: Dict):
        """Display focused backtest results"""
        if results.empty or not analysis:
            print("❌ No focused backtest results available")
            return
        
        print(f"\n🎯 FOCUSED 3-STOCK MOMENTUM SCANNER BACKTEST")
        print("=" * 80)
        
        print(f"\n📊 OVERVIEW:")
        print(f"   📅 Period: {analysis['date_range']}")
        print(f"   📈 Total Days: {analysis['total_days']:,}")
        print(f"   🗓️ Years: {len(analysis['years_covered'])} years ({min(analysis['years_covered'])}-{max(analysis['years_covered'])})")
        print(f"   🎯 Focus: TOP 3 stocks per scanner per day")
        print(f"   🧵 Processing: Multi-threaded ({self.max_workers} workers)")
        
        print(f"\n🔍 ORIGINAL SCANNER PERFORMANCE:")
        print(f"   📊 Total Picks: {analysis['original_total_picks']:,} (avg {analysis['original_total_picks']/analysis['total_days']:.1f}/day)")
        print(f"   🥇 Top 3 Gainer Hits: {analysis['original_total_hits_top3']:,}")
        print(f"   🏆 Top 3 Hit Rate: {analysis['original_overall_hit_rate_top3']:.2f}%")
        print(f"   🥈 Top 5 Gainer Hits: {analysis['original_total_hits_top5']:,}")
        print(f"   🏅 Top 5 Hit Rate: {analysis['original_overall_hit_rate_top5']:.2f}%")
        print(f"   💰 Average Return: {analysis['original_avg_return']:.2f}%")
        print(f"   🌟 Best Pick Avg: {analysis['original_best_avg']:.2f}%")
        print(f"   📊 Avg Quality Score: {analysis['original_avg_score']:.1f}")
        print(f"   ✅ Win Rate: {analysis['original_win_rate']:.1f}%")
        
        print(f"\n💎 ENHANCED SCANNER PERFORMANCE:")
        print(f"   📊 Total Picks: {analysis['enhanced_total_picks']:,} (avg {analysis['enhanced_total_picks']/analysis['total_days']:.1f}/day)")
        print(f"   🥇 Top 3 Gainer Hits: {analysis['enhanced_total_hits_top3']:,}")
        print(f"   🏆 Top 3 Hit Rate: {analysis['enhanced_overall_hit_rate_top3']:.2f}%")
        print(f"   🥈 Top 5 Gainer Hits: {analysis['enhanced_total_hits_top5']:,}")
        print(f"   🏅 Top 5 Hit Rate: {analysis['enhanced_overall_hit_rate_top5']:.2f}%")
        print(f"   💰 Average Return: {analysis['enhanced_avg_return']:.2f}%")
        print(f"   🌟 Best Pick Avg: {analysis['enhanced_best_avg']:.2f}%")
        print(f"   📊 Avg Quality Score: {analysis['enhanced_avg_score']:.1f}")
        print(f"   ✅ Win Rate: {analysis['enhanced_win_rate']:.1f}%")
        
        # Performance comparison
        top3_improvement = analysis['enhanced_overall_hit_rate_top3'] - analysis['original_overall_hit_rate_top3']
        top5_improvement = analysis['enhanced_overall_hit_rate_top5'] - analysis['original_overall_hit_rate_top5']
        return_improvement = analysis['enhanced_avg_return'] - analysis['original_avg_return']
        
        print(f"\n📈 FOCUSED ENHANCEMENT IMPACT:")
        print(f"   🥇 Top 3 Hit Rate: {top3_improvement:+.2f}% ({top3_improvement/analysis['original_overall_hit_rate_top3']*100:+.1f}%)")
        print(f"   🥈 Top 5 Hit Rate: {top5_improvement:+.2f}% ({top5_improvement/analysis['original_overall_hit_rate_top5']*100:+.1f}%)")
        print(f"   💰 Return Improvement: {return_improvement:+.2f}%")
        
        # Precision analysis
        print(f"\n🎯 PRECISION ANALYSIS:")
        orig_precision_top3 = analysis['original_overall_hit_rate_top3']
        enh_precision_top3 = analysis['enhanced_overall_hit_rate_top3']
        
        print(f"   🔍 Original Scanner Precision: {orig_precision_top3:.1f}% (top 3 gainers)")
        print(f"   💎 Enhanced Scanner Precision: {enh_precision_top3:.1f}% (top 3 gainers)")
        
        if enh_precision_top3 > orig_precision_top3 + 2:
            print(f"   🚀 EXCELLENT: Enhanced scanner shows superior precision!")
        elif enh_precision_top3 > orig_precision_top3:
            print(f"   ✅ GOOD: Enhanced scanner improves precision")
        else:
            print(f"   ⚠️ MIXED: Precision improvement needed")
        
        # Final verdict
        print(f"\n🏆 FOCUSED 3-STOCK BACKTEST VERDICT:")
        
        if (analysis['enhanced_overall_hit_rate_top3'] > analysis['original_overall_hit_rate_top3'] and 
            analysis['enhanced_avg_return'] > analysis['original_avg_return']):
            print(f"   🚀 ENHANCED SCANNER SUPERIOR: Better precision AND returns")
        elif analysis['enhanced_overall_hit_rate_top3'] > analysis['original_overall_hit_rate_top3']:
            print(f"   ✅ ENHANCED SCANNER BETTER: Improved precision")
        else:
            print(f"   🔧 NEEDS OPTIMIZATION: Focus on top-tier opportunities")
        
        if analysis['enhanced_avg_return'] > analysis['original_avg_return']:
            print(f"   💰 BETTER RETURNS: Enhanced scanner generates superior returns")
        
        # Success rate summary
        print(f"\n📊 SUCCESS RATE SUMMARY:")
        print(f"   🎯 Targeting top 3 gainers: {max(analysis['original_overall_hit_rate_top3'], analysis['enhanced_overall_hit_rate_top3']):.1f}% hit rate")
        print(f"   📈 Expected daily picks: 3 per scanner")
        print(f"   🏆 Best scanner: {'Enhanced' if analysis['enhanced_overall_hit_rate_top3'] > analysis['original_overall_hit_rate_top3'] else 'Original'}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Focused 3-Stock Momentum Scanner Backtest')
    parser.add_argument('--start-year', type=int, default=2024,
                       help='Start year for backtesting')
    parser.add_argument('--end-year', type=int, default=2025,
                       help='End year for backtesting')
    parser.add_argument('--sample-size', type=int,
                       help='Sample size to limit computation')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of worker threads (default: 4)')
    parser.add_argument('--export', type=str,
                       help='Export results to CSV file')
    
    args = parser.parse_args()
    
    try:
        backtester = Focused3StockBacktest(max_workers=args.workers)
        
        results = backtester.run_focused_backtest(
            start_year=args.start_year,
            end_year=args.end_year,
            sample_size=args.sample_size
        )
        
        if not results.empty:
            analysis = backtester.analyze_focused_results(results)
            backtester.display_focused_results(results, analysis)
            
            if args.export:
                results.to_csv(args.export, index=False)
                logger.info(f"📁 Results exported to {args.export}")
            
            print(f"\n✅ Focused 3-stock backtest completed!")
        else:
            print(f"\n⚠️ No results generated from backtesting")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

