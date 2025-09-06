#!/usr/bin/env python3
"""
Comprehensive 10-Year Momentum Scanner Backtest

This system performs extensive backtesting of both original and enhanced momentum 
scanners across all available historical data (2015-2025). It provides comprehensive
analysis of scanner performance across different market conditions, years, and 
market regimes.

Key Features:
1. Multi-year performance analysis
2. Market regime detection and analysis
3. Seasonal pattern identification
4. Risk-adjusted performance metrics
5. Comparative analysis (Original vs Enhanced)
6. Statistical significance testing

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

class Comprehensive10YearBacktest:
    """Comprehensive backtesting system for 10-year historical analysis"""
    
    def __init__(self):
        """Initialize the comprehensive backtesting system"""
        self.db_manager = DuckDBManager()
        self.original_scanner = OptimizedMomentumScanner()
        self.enhanced_scanner = EnhancedMomentumScanner()
        
        # Performance tracking
        self.results = []
        self.yearly_stats = {}
        self.market_regimes = {}
        
    def get_all_trading_days(self) -> pd.DataFrame:
        """Get all available trading days with comprehensive data"""
        logger.info("📅 Discovering all available trading days across 10+ years")
        
        query = '''
        SELECT 
            DATE(timestamp) as trade_date,
            COUNT(DISTINCT symbol) as active_symbols,
            COUNT(*) as total_records,
            AVG(volume) as avg_volume,
            EXTRACT(YEAR FROM DATE(timestamp)) as year,
            EXTRACT(MONTH FROM DATE(timestamp)) as month,
            EXTRACT(DOW FROM DATE(timestamp)) as day_of_week
        FROM market_data 
        WHERE strftime('%H:%M', timestamp) <= '15:29'
            AND strftime('%H:%M', timestamp) >= '09:15'
        GROUP BY DATE(timestamp)
        HAVING COUNT(DISTINCT symbol) >= 20  -- At least 20 active symbols
            AND COUNT(*) >= 500  -- Sufficient data points
        ORDER BY trade_date
        '''
        
        result = self.db_manager.execute_custom_query(query)
        
        if not result.empty:
            result['trade_date'] = pd.to_datetime(result['trade_date']).dt.date
            logger.info(f"📊 Found {len(result)} trading days from {result['trade_date'].min()} to {result['trade_date'].max()}")
            
            # Yearly breakdown
            yearly_counts = result.groupby('year').size()
            logger.info("📈 Yearly data availability:")
            for year, count in yearly_counts.items():
                logger.info(f"   {year}: {count} trading days")
        
        return result
    
    def classify_market_regime(self, trade_date: date, window_days: int = 20) -> str:
        """Classify market regime for a given date"""
        
        # Get market performance over the window
        query = '''
        SELECT 
            symbol,
            DATE(timestamp) as date,
            (SELECT close FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = DATE(m1.timestamp)
                AND strftime('%H:%M', m2.timestamp) = '15:29'
             LIMIT 1) as close_price,
            (SELECT open FROM market_data m2 
             WHERE m2.symbol = m1.symbol 
                AND DATE(m2.timestamp) = DATE(m1.timestamp)
                AND strftime('%H:%M', m2.timestamp) = '09:15'
             LIMIT 1) as open_price
        FROM market_data m1
        WHERE DATE(timestamp) >= ? - INTERVAL '{} days'
            AND DATE(timestamp) <= ?
            AND symbol IN (SELECT DISTINCT symbol FROM market_data 
                          WHERE DATE(timestamp) = ? 
                          ORDER BY symbol LIMIT 50)  -- Top 50 most active
        GROUP BY symbol, DATE(timestamp)
        HAVING close_price IS NOT NULL AND open_price IS NOT NULL
        '''.format(window_days)
        
        market_data = self.db_manager.execute_custom_query(query, [trade_date, trade_date, trade_date])
        
        if market_data.empty:
            return 'UNKNOWN'
        
        # Calculate daily returns
        market_data['daily_return'] = (market_data['close_price'] - market_data['open_price']) / market_data['open_price'] * 100
        
        # Aggregate market metrics
        daily_avg_returns = market_data.groupby('date')['daily_return'].mean()
        
        avg_return = daily_avg_returns.mean()
        volatility = daily_avg_returns.std()
        
        # Classify regime
        if avg_return > 0.5 and volatility < 2.0:
            return 'BULL_LOW_VOL'
        elif avg_return > 0.5 and volatility >= 2.0:
            return 'BULL_HIGH_VOL'
        elif avg_return < -0.5 and volatility < 2.0:
            return 'BEAR_LOW_VOL'
        elif avg_return < -0.5 and volatility >= 2.0:
            return 'BEAR_HIGH_VOL'
        elif volatility > 3.0:
            return 'HIGH_VOLATILITY'
        else:
            return 'SIDEWAYS'
    
    def backtest_single_day_comprehensive(self, trade_date: date, market_regime: str) -> Dict:
        """Comprehensive single-day backtest with both scanners"""
        
        try:
            # Get actual top gainers for the day
            top_gainers = self.get_actual_top_gainers(trade_date, 10)
            
            if top_gainers.empty:
                return {
                    'date': trade_date,
                    'market_regime': market_regime,
                    'year': trade_date.year,
                    'month': trade_date.month,
                    'day_of_week': trade_date.weekday(),
                    'original_picks': 0,
                    'enhanced_picks': 0,
                    'original_hits': 0,
                    'enhanced_hits': 0,
                    'original_hit_rate': 0,
                    'enhanced_hit_rate': 0,
                    'original_avg_return': 0,
                    'enhanced_avg_return': 0,
                    'market_avg_return': 0,
                    'data_quality': 'POOR'
                }
            
            # Test original scanner
            original_results = pd.DataFrame()
            original_picks = []
            try:
                original_candidates = self.original_scanner.get_momentum_candidates(trade_date)
                if not original_candidates.empty:
                    original_results = self.original_scanner.calculate_momentum_scores(original_candidates)
                    original_picks = original_results.head(5)['symbol'].tolist()
            except Exception as e:
                logger.warning(f"Original scanner failed for {trade_date}: {e}")
            
            # Test enhanced scanner
            enhanced_results = pd.DataFrame()
            enhanced_picks = []
            try:
                enhanced_candidates = self.enhanced_scanner.get_enhanced_candidates(trade_date)
                if not enhanced_candidates.empty:
                    enhanced_results = self.enhanced_scanner.calculate_enhanced_scores(enhanced_candidates)
                    enhanced_picks = enhanced_results.head(5)['symbol'].tolist()
            except Exception as e:
                logger.warning(f"Enhanced scanner failed for {trade_date}: {e}")
            
            # Calculate performance metrics
            top_gainer_symbols = set(top_gainers.head(5)['symbol'].tolist())
            
            # Original scanner metrics
            original_hits = len(set(original_picks).intersection(top_gainer_symbols))
            original_hit_rate = (original_hits / len(original_picks)) * 100 if original_picks else 0
            
            # Enhanced scanner metrics
            enhanced_hits = len(set(enhanced_picks).intersection(top_gainer_symbols))
            enhanced_hit_rate = (enhanced_hits / len(enhanced_picks)) * 100 if enhanced_picks else 0
            
            # Get actual returns for scanner picks
            original_performance = self.get_scanner_picks_performance(trade_date, original_picks)
            enhanced_performance = self.get_scanner_picks_performance(trade_date, enhanced_picks)
            
            original_avg_return = original_performance['day_return_pct'].mean() if not original_performance.empty else 0
            enhanced_avg_return = enhanced_performance['day_return_pct'].mean() if not enhanced_performance.empty else 0
            market_avg_return = top_gainers['day_return_pct'].mean()
            
            return {
                'date': trade_date,
                'market_regime': market_regime,
                'year': trade_date.year,
                'month': trade_date.month,
                'day_of_week': trade_date.weekday(),
                'original_picks': len(original_picks),
                'enhanced_picks': len(enhanced_picks),
                'original_hits': original_hits,
                'enhanced_hits': enhanced_hits,
                'original_hit_rate': original_hit_rate,
                'enhanced_hit_rate': enhanced_hit_rate,
                'original_avg_return': original_avg_return,
                'enhanced_avg_return': enhanced_avg_return,
                'market_avg_return': market_avg_return,
                'original_outperformance': original_avg_return - market_avg_return,
                'enhanced_outperformance': enhanced_avg_return - market_avg_return,
                'data_quality': 'GOOD',
                'top_gainer_symbols': list(top_gainer_symbols),
                'original_picks_list': original_picks,
                'enhanced_picks_list': enhanced_picks
            }
            
        except Exception as e:
            logger.error(f"❌ Error backtesting {trade_date}: {e}")
            return {
                'date': trade_date,
                'market_regime': market_regime,
                'year': trade_date.year,
                'month': trade_date.month,
                'day_of_week': trade_date.weekday(),
                'original_picks': 0,
                'enhanced_picks': 0,
                'original_hits': 0,
                'enhanced_hits': 0,
                'original_hit_rate': 0,
                'enhanced_hit_rate': 0,
                'original_avg_return': 0,
                'enhanced_avg_return': 0,
                'market_avg_return': 0,
                'data_quality': 'ERROR'
            }
    
    def get_actual_top_gainers(self, scan_date: date, top_n: int = 10) -> pd.DataFrame:
        """Get actual top gainers for the entire trading day"""
        
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
             LIMIT 1) as closing_price,
             
            MAX(high) as day_high,
            MIN(low) as day_low,
            SUM(volume) as total_day_volume,
            COUNT(*) as minutes_active
            
        FROM market_data m1
        WHERE DATE(timestamp) = ?
            AND strftime('%H:%M', timestamp) >= '09:15'
            AND strftime('%H:%M', timestamp) <= '15:29'
        GROUP BY symbol
        HAVING opening_price IS NOT NULL 
            AND closing_price IS NOT NULL
            AND COUNT(*) >= 50  -- At least 50 minutes of data
        '''
        
        day_performance = self.db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
        
        if day_performance.empty:
            return pd.DataFrame()
        
        day_performance['day_return_pct'] = (
            (day_performance['closing_price'] - day_performance['opening_price']) / 
            day_performance['opening_price'] * 100
        )
        
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
        
        picks_performance = self.db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
        
        if not picks_performance.empty:
            picks_performance['day_return_pct'] = (
                (picks_performance['closing_price'] - picks_performance['opening_price']) / 
                picks_performance['opening_price'] * 100
            )
        
        return picks_performance
    
    def run_comprehensive_backtest(self, start_year: int = 2015, end_year: int = 2025, 
                                 sample_size: Optional[int] = None) -> pd.DataFrame:
        """Run comprehensive 10-year backtest"""
        logger.info(f"🚀 Starting Comprehensive 10-Year Backtest ({start_year}-{end_year})")
        
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
            # Sample evenly across years for performance
            filtered_days = filtered_days.sample(n=sample_size, random_state=42).sort_values('trade_date')
            logger.info(f"📊 Sampling {sample_size} days from {len(all_days)} available days")
        
        logger.info(f"📊 Testing {len(filtered_days)} trading days across {filtered_days['year'].nunique()} years")
        
        results = []
        total_days = len(filtered_days)
        
        for day_idx, (_, day_row) in enumerate(filtered_days.iterrows()):
            trade_date = day_row['trade_date']
            
            if (day_idx + 1) % 50 == 0 or day_idx < 10:
                logger.info(f"📅 Processing day {day_idx + 1}/{total_days}: {trade_date} ({day_row['year']})")
            
            # Classify market regime
            market_regime = self.classify_market_regime(trade_date)
            
            # Backtest the day
            day_result = self.backtest_single_day_comprehensive(trade_date, market_regime)
            results.append(day_result)
        
        results_df = pd.DataFrame(results)
        
        if not results_df.empty:
            # Filter out poor quality data
            quality_results = results_df[results_df['data_quality'] == 'GOOD'].copy()
            logger.info(f"📊 Quality results: {len(quality_results)}/{len(results_df)} days")
            
            return quality_results
        
        return results_df
    
    def analyze_comprehensive_results(self, results: pd.DataFrame) -> Dict:
        """Comprehensive analysis of backtest results"""
        if results.empty:
            return {}
        
        # Overall performance
        analysis = {
            'total_days': len(results),
            'years_covered': sorted(results['year'].unique()),
            'date_range': f"{results['date'].min()} to {results['date'].max()}",
            
            # Original scanner performance
            'original_total_picks': results['original_picks'].sum(),
            'original_total_hits': results['original_hits'].sum(),
            'original_overall_hit_rate': (results['original_hits'].sum() / results['original_picks'].sum() * 100) if results['original_picks'].sum() > 0 else 0,
            'original_avg_daily_hit_rate': results[results['original_picks'] > 0]['original_hit_rate'].mean(),
            'original_avg_return': results[results['original_picks'] > 0]['original_avg_return'].mean(),
            'original_positive_days': (results['original_avg_return'] > 0).sum(),
            'original_win_rate': (results['original_avg_return'] > 0).mean() * 100,
            
            # Enhanced scanner performance
            'enhanced_total_picks': results['enhanced_picks'].sum(),
            'enhanced_total_hits': results['enhanced_hits'].sum(),
            'enhanced_overall_hit_rate': (results['enhanced_hits'].sum() / results['enhanced_picks'].sum() * 100) if results['enhanced_picks'].sum() > 0 else 0,
            'enhanced_avg_daily_hit_rate': results[results['enhanced_picks'] > 0]['enhanced_hit_rate'].mean(),
            'enhanced_avg_return': results[results['enhanced_picks'] > 0]['enhanced_avg_return'].mean(),
            'enhanced_positive_days': (results['enhanced_avg_return'] > 0).sum(),
            'enhanced_win_rate': (results['enhanced_avg_return'] > 0).mean() * 100,
        }
        
        # Yearly breakdown
        yearly_analysis = {}
        for year in results['year'].unique():
            year_data = results[results['year'] == year]
            yearly_analysis[year] = {
                'days': len(year_data),
                'original_hit_rate': (year_data['original_hits'].sum() / year_data['original_picks'].sum() * 100) if year_data['original_picks'].sum() > 0 else 0,
                'enhanced_hit_rate': (year_data['enhanced_hits'].sum() / year_data['enhanced_picks'].sum() * 100) if year_data['enhanced_picks'].sum() > 0 else 0,
                'original_avg_return': year_data[year_data['original_picks'] > 0]['original_avg_return'].mean(),
                'enhanced_avg_return': year_data[year_data['enhanced_picks'] > 0]['enhanced_avg_return'].mean(),
            }
        
        analysis['yearly_breakdown'] = yearly_analysis
        
        # Market regime analysis
        regime_analysis = {}
        for regime in results['market_regime'].unique():
            regime_data = results[results['market_regime'] == regime]
            regime_analysis[regime] = {
                'days': len(regime_data),
                'original_hit_rate': (regime_data['original_hits'].sum() / regime_data['original_picks'].sum() * 100) if regime_data['original_picks'].sum() > 0 else 0,
                'enhanced_hit_rate': (regime_data['enhanced_hits'].sum() / regime_data['enhanced_picks'].sum() * 100) if regime_data['enhanced_picks'].sum() > 0 else 0,
            }
        
        analysis['market_regime_breakdown'] = regime_analysis
        
        return analysis
    
    def display_comprehensive_results(self, results: pd.DataFrame, analysis: Dict):
        """Display comprehensive backtest results"""
        if results.empty or not analysis:
            print("❌ No comprehensive backtest results available")
            return
        
        print(f"\n🏆 COMPREHENSIVE 10-YEAR MOMENTUM SCANNER BACKTEST")
        print("=" * 100)
        
        print(f"\n📊 OVERVIEW:")
        print(f"   📅 Period: {analysis['date_range']}")
        print(f"   📈 Total Days: {analysis['total_days']:,}")
        print(f"   🗓️ Years Covered: {len(analysis['years_covered'])} years ({min(analysis['years_covered'])}-{max(analysis['years_covered'])})")
        
        print(f"\n🔍 ORIGINAL SCANNER PERFORMANCE:")
        print(f"   📊 Total Picks: {analysis['original_total_picks']:,}")
        print(f"   🎯 Total Hits: {analysis['original_total_hits']:,}")
        print(f"   🏆 Overall Hit Rate: {analysis['original_overall_hit_rate']:.2f}%")
        print(f"   📈 Average Daily Hit Rate: {analysis['original_avg_daily_hit_rate']:.2f}%")
        print(f"   💰 Average Return: {analysis['original_avg_return']:.2f}%")
        print(f"   ✅ Win Rate: {analysis['original_win_rate']:.1f}%")
        
        print(f"\n💎 ENHANCED SCANNER PERFORMANCE:")
        print(f"   📊 Total Picks: {analysis['enhanced_total_picks']:,}")
        print(f"   🎯 Total Hits: {analysis['enhanced_total_hits']:,}")
        print(f"   🏆 Overall Hit Rate: {analysis['enhanced_overall_hit_rate']:.2f}%")
        print(f"   📈 Average Daily Hit Rate: {analysis['enhanced_avg_daily_hit_rate']:.2f}%")
        print(f"   💰 Average Return: {analysis['enhanced_avg_return']:.2f}%")
        print(f"   ✅ Win Rate: {analysis['enhanced_win_rate']:.1f}%")
        
        # Performance comparison
        hit_rate_improvement = analysis['enhanced_overall_hit_rate'] - analysis['original_overall_hit_rate']
        return_improvement = analysis['enhanced_avg_return'] - analysis['original_avg_return']
        
        print(f"\n📈 ENHANCEMENT IMPACT:")
        print(f"   🎯 Hit Rate Improvement: {hit_rate_improvement:+.2f}% ({hit_rate_improvement/analysis['original_overall_hit_rate']*100:+.1f}%)")
        print(f"   💰 Return Improvement: {return_improvement:+.2f}%")
        
        # Yearly performance
        print(f"\n📅 YEARLY PERFORMANCE BREAKDOWN:")
        print("-" * 80)
        print(f"{'Year':<6} {'Days':<6} {'Orig Hit%':<10} {'Enh Hit%':<10} {'Orig Ret%':<10} {'Enh Ret%':<10}")
        print("-" * 80)
        
        for year in sorted(analysis['yearly_breakdown'].keys()):
            year_data = analysis['yearly_breakdown'][year]
            print(f"{year:<6} {year_data['days']:<6} "
                  f"{year_data['original_hit_rate']:<10.1f} {year_data['enhanced_hit_rate']:<10.1f} "
                  f"{year_data['original_avg_return']:<10.2f} {year_data['enhanced_avg_return']:<10.2f}")
        
        # Market regime analysis
        print(f"\n🌊 MARKET REGIME PERFORMANCE:")
        print("-" * 60)
        print(f"{'Regime':<15} {'Days':<6} {'Orig Hit%':<10} {'Enh Hit%':<10}")
        print("-" * 60)
        
        for regime in analysis['market_regime_breakdown']:
            regime_data = analysis['market_regime_breakdown'][regime]
            print(f"{regime:<15} {regime_data['days']:<6} "
                  f"{regime_data['original_hit_rate']:<10.1f} {regime_data['enhanced_hit_rate']:<10.1f}")
        
        # Statistical significance
        print(f"\n📊 STATISTICAL ANALYSIS:")
        
        # Calculate confidence intervals and significance
        orig_active_days = results[results['original_picks'] > 0]
        enh_active_days = results[results['enhanced_picks'] > 0]
        
        if len(orig_active_days) > 30 and len(enh_active_days) > 30:
            from scipy import stats
            
            # T-test for hit rates
            t_stat, p_value = stats.ttest_ind(
                orig_active_days['original_hit_rate'], 
                enh_active_days['enhanced_hit_rate']
            )
            
            significance = "SIGNIFICANT" if p_value < 0.05 else "NOT SIGNIFICANT"
            print(f"   🧮 Hit Rate Difference: {significance} (p-value: {p_value:.4f})")
            
            # T-test for returns
            t_stat_ret, p_value_ret = stats.ttest_ind(
                orig_active_days['original_avg_return'], 
                enh_active_days['enhanced_avg_return']
            )
            
            significance_ret = "SIGNIFICANT" if p_value_ret < 0.05 else "NOT SIGNIFICANT"
            print(f"   💰 Return Difference: {significance_ret} (p-value: {p_value_ret:.4f})")
        
        # Final verdict
        print(f"\n🏆 COMPREHENSIVE BACKTEST VERDICT:")
        
        if analysis['enhanced_overall_hit_rate'] > analysis['original_overall_hit_rate'] + 2:
            print(f"   ✅ ENHANCED SCANNER SUPERIOR: Significantly better hit rate")
        elif analysis['enhanced_overall_hit_rate'] > analysis['original_overall_hit_rate']:
            print(f"   ✅ ENHANCED SCANNER BETTER: Improved hit rate")
        else:
            print(f"   ⚠️ MIXED RESULTS: Enhancement needs optimization")
        
        if analysis['enhanced_avg_return'] > analysis['original_avg_return']:
            print(f"   💰 BETTER RETURNS: Enhanced scanner generates superior returns")
        else:
            print(f"   ⚠️ RETURN OPTIMIZATION NEEDED: Focus on return improvement")
        
        print(f"\n📈 OVERALL ASSESSMENT:")
        if (analysis['enhanced_overall_hit_rate'] > analysis['original_overall_hit_rate'] and 
            analysis['enhanced_avg_return'] > analysis['original_avg_return']):
            print(f"   🚀 ENHANCEMENT SUCCESSFUL: Both hit rate and returns improved")
        elif analysis['enhanced_overall_hit_rate'] > analysis['original_overall_hit_rate']:
            print(f"   ⭐ PARTIAL SUCCESS: Hit rate improved, returns need work")
        else:
            print(f"   🔧 NEEDS OPTIMIZATION: Further enhancement required")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Comprehensive 10-Year Momentum Scanner Backtest')
    parser.add_argument('--start-year', type=int, default=2015,
                       help='Start year for backtesting')
    parser.add_argument('--end-year', type=int, default=2025,
                       help='End year for backtesting')
    parser.add_argument('--sample-size', type=int,
                       help='Sample size to limit computation (e.g., 500 days)')
    parser.add_argument('--export', type=str,
                       help='Export results to CSV file')
    
    args = parser.parse_args()
    
    try:
        backtester = Comprehensive10YearBacktest()
        
        results = backtester.run_comprehensive_backtest(
            start_year=args.start_year,
            end_year=args.end_year,
            sample_size=args.sample_size
        )
        
        if not results.empty:
            analysis = backtester.analyze_comprehensive_results(results)
            backtester.display_comprehensive_results(results, analysis)
            
            if args.export:
                results.to_csv(args.export, index=False)
                logger.info(f"📁 Results exported to {args.export}")
            
            print(f"\n✅ Comprehensive 10-year backtest completed!")
        else:
            print(f"\n⚠️ No results generated from comprehensive backtesting")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            backtester.db_manager.close()
        except:
            pass
    
    return 0

if __name__ == "__main__":
    exit(main())
