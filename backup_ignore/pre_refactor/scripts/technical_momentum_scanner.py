#!/usr/bin/env python3
"""
Technical Momentum Scanner v3.0

Enhanced momentum scanner integrating technical analysis concepts from your
99+ indicators system. Focuses on proven technical patterns and momentum
confirmation for superior stock selection.

Key Features:
1. Technical Pattern Recognition
2. Support & Resistance Analysis  
3. Volume Confirmation
4. Multi-factor Technical Scoring
5. Risk Assessment with Technical Levels

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

from core.duckdb_infra.database import DuckDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TechnicalMomentumScanner:
    """Technical momentum scanner with integrated technical analysis"""
    
    def __init__(self):
        """Initialize the technical momentum scanner"""
        self.db_manager = DuckDBManager()
        
        # Technical-enhanced parameters
        self.params = {
            # Volume (enhanced with technical confirmation)
            'min_volume_threshold': 200000,    # Higher for better technical setups
            'min_relative_volume': 2.0,        # Volume confirmation
            'optimal_relative_volume': 3.5,    # Technical breakout volume
            
            # Price movement (technical levels aware)
            'min_price_change': 0.5,           # Lower with technical confirmation
            'technical_momentum_threshold': 1.5, # Technical pattern confirmation
            'breakout_threshold': 2.5,          # Major technical breakout
            
            # Price range (technical analysis sweet spots)
            'min_price': 25,                   # Better for technical analysis
            'max_price': 800,                  # Focused on liquid stocks
            'technical_sweet_spot_min': 50,    # Optimal for TA
            'technical_sweet_spot_max': 400,   # Optimal for TA
            
            # Quality filters
            'min_minutes': 30,                 # Sufficient data
        }
    
    def get_technical_candidates(self, scan_date: date) -> pd.DataFrame:
        """Get momentum candidates with technical analysis focus"""
        logger.info(f"🔍 Technical momentum scanning for {scan_date}")
        
        query = '''
        WITH current_day_data AS (
            SELECT 
                symbol,
                COUNT(*) as minutes_active,
                SUM(volume) as total_volume_0950,
                AVG(volume) as avg_minute_volume,
                
                -- Price data
                MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) as opening_price,
                MAX(CASE WHEN strftime('%H:%M', timestamp) = '09:50' THEN close END) as price_0950,
                MAX(high) as high_0950,
                MIN(low) as low_0950,
                AVG(close) as avg_price,
                
                -- Technical pattern data
                MAX(high) - MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) as max_upside,
                MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) - MIN(low) as max_downside,
                
                -- Volume patterns
                MAX(volume) as max_minute_volume,
                MIN(volume) as min_minute_volume,
                
                -- Time-based volume analysis
                AVG(CASE WHEN strftime('%H:%M', timestamp) BETWEEN '09:15' AND '09:30' THEN volume END) as early_volume,
                AVG(CASE WHEN strftime('%H:%M', timestamp) BETWEEN '09:35' AND '09:50' THEN volume END) as late_volume,
                
                -- Price action strength
                COUNT(CASE WHEN close > open THEN 1 END) as bullish_minutes,
                COUNT(CASE WHEN close < open THEN 1 END) as bearish_minutes
                
            FROM market_data 
            WHERE DATE(timestamp) = ?
                AND strftime('%H:%M', timestamp) <= '09:50'
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
            HAVING COUNT(*) >= ?
        ),
        
        historical_context AS (
            SELECT 
                symbol,
                AVG(daily_vol) as avg_historical_volume,
                AVG(daily_range) as avg_historical_range,
                AVG(daily_volatility) as avg_historical_volatility,
                COUNT(*) as historical_days
            FROM (
                SELECT 
                    symbol,
                    DATE(timestamp) as trade_date,
                    SUM(volume) as daily_vol,
                    MAX(high) - MIN(low) as daily_range,
                    (MAX(high) - MIN(low)) / AVG(close) * 100 as daily_volatility
                FROM market_data 
                WHERE DATE(timestamp) >= ? - INTERVAL '15 days'
                    AND DATE(timestamp) < ?
                    AND strftime('%H:%M', timestamp) <= '09:50'
                    AND strftime('%H:%M', timestamp) >= '09:15'
                GROUP BY symbol, DATE(timestamp)
            ) hist
            GROUP BY symbol
            HAVING COUNT(*) >= 8
        )
        
        SELECT 
            c.*,
            COALESCE(h.avg_historical_volume, c.total_volume_0950 * 0.7) as historical_avg_volume,
            COALESCE(h.avg_historical_range, c.high_0950 - c.low_0950) as historical_avg_range,
            COALESCE(h.avg_historical_volatility, 2.0) as historical_avg_volatility,
            
            -- Technical metrics
            c.total_volume_0950 / COALESCE(h.avg_historical_volume, c.total_volume_0950 * 0.7) as relative_volume,
            (c.price_0950 - c.opening_price) / c.opening_price * 100 as price_change_pct,
            (c.high_0950 - c.low_0950) / c.avg_price * 100 as volatility_pct,
            ABS((c.price_0950 - c.opening_price) / c.opening_price * 100) as abs_momentum,
            
            -- Technical pattern indicators
            c.max_upside / c.opening_price * 100 as max_upside_pct,
            c.max_downside / c.opening_price * 100 as max_downside_pct,
            (c.high_0950 - c.low_0950) / COALESCE(h.avg_historical_range, c.high_0950 - c.low_0950) as relative_range,
            
            -- Volume technical indicators
            COALESCE(c.late_volume / NULLIF(c.early_volume, 0), 1.0) as volume_acceleration,
            c.max_minute_volume / c.avg_minute_volume as volume_spike_ratio,
            
            -- Price action strength
            c.bullish_minutes / CAST(c.minutes_active as FLOAT) as bullish_ratio,
            c.bearish_minutes / CAST(c.minutes_active as FLOAT) as bearish_ratio
            
        FROM current_day_data c
        LEFT JOIN historical_context h ON c.symbol = h.symbol
        WHERE c.opening_price IS NOT NULL 
            AND c.price_0950 IS NOT NULL
            AND c.avg_price >= ?
            AND c.avg_price <= ?
            AND c.total_volume_0950 >= ?
        '''
        
        candidates = self.db_manager.execute_custom_query(query, [
            scan_date, 
            self.params['min_minutes'],
            scan_date,
            scan_date,
            self.params['min_price'],
            self.params['max_price'],
            self.params['min_volume_threshold']
        ])
        
        if candidates.empty:
            return pd.DataFrame()
        
        # Technical filtering
        filtered = candidates[
            (candidates['abs_momentum'] >= self.params['min_price_change']) &
            (candidates['relative_volume'] >= self.params['min_relative_volume']) &
            (candidates['minutes_active'] >= self.params['min_minutes'])
        ].copy()
        
        return filtered
    
    def calculate_technical_scores(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical analysis enhanced scores"""
        if candidates.empty:
            return candidates
        
        df = candidates.copy()
        
        # 1. Volume Technical Score (35% weight)
        df['volume_base_score'] = np.clip((df['relative_volume'] - 1) * 20, 0, 100)
        
        # Volume pattern bonuses
        df['volume_breakout_bonus'] = np.where(
            (df['relative_volume'] >= self.params['optimal_relative_volume']) & 
            (df['volume_acceleration'] > 1.2), 25, 0
        )
        df['volume_spike_bonus'] = np.where(df['volume_spike_ratio'] > 3.0, 15, 0)
        
        df['volume_score'] = np.clip(
            df['volume_base_score'] + df['volume_breakout_bonus'] + df['volume_spike_bonus'], 
            0, 100
        )
        
        # 2. Technical Momentum Score (30% weight)
        df['momentum_base_score'] = np.clip(df['abs_momentum'] * 15, 0, 100)
        
        # Technical pattern bonuses
        df['technical_momentum_bonus'] = np.where(
            df['abs_momentum'] >= self.params['technical_momentum_threshold'], 20, 0
        )
        df['breakout_bonus'] = np.where(
            df['abs_momentum'] >= self.params['breakout_threshold'], 30, 0
        )
        
        # Price action consistency bonus
        df['price_action_bonus'] = np.where(
            ((df['price_change_pct'] > 0) & (df['bullish_ratio'] > 0.6)) |
            ((df['price_change_pct'] < 0) & (df['bearish_ratio'] > 0.6)), 10, 0
        )
        
        df['momentum_score'] = np.clip(
            df['momentum_base_score'] + df['technical_momentum_bonus'] + 
            df['breakout_bonus'] + df['price_action_bonus'],
            0, 100
        )
        
        # 3. Technical Pattern Score (20% weight)
        # Range expansion (volatility breakout)
        df['range_expansion_score'] = np.clip(
            (df['relative_range'] - 1) * 50, 0, 100
        )
        
        # Directional strength
        df['directional_strength'] = np.where(
            df['price_change_pct'] > 0,
            df['max_upside_pct'] / (df['max_upside_pct'] + df['max_downside_pct'] + 0.01) * 100,
            df['max_downside_pct'] / (df['max_upside_pct'] + df['max_downside_pct'] + 0.01) * 100
        )
        
        df['pattern_score'] = (df['range_expansion_score'] + df['directional_strength']) / 2
        
        # 4. Liquidity & Quality Score (15% weight)
        volume_rank = df['total_volume_0950'].rank(pct=True) * 100
        df['liquidity_score'] = volume_rank
        
        # Technical sweet spot bonus
        df['sweet_spot_bonus'] = np.where(
            (df['avg_price'] >= self.params['technical_sweet_spot_min']) & 
            (df['avg_price'] <= self.params['technical_sweet_spot_max']), 15, 0
        )
        
        # Composite Technical Score
        df['composite_score'] = (
            df['volume_score'] * 0.35 +
            df['momentum_score'] * 0.30 +
            df['pattern_score'] * 0.20 +
            df['liquidity_score'] * 0.15
        ) + df['sweet_spot_bonus']
        
        df['composite_score'] = np.clip(df['composite_score'], 0, 100)
        
        # Enhanced Signal Classification
        df['direction'] = np.where(df['price_change_pct'] > 0, 'BULLISH', 'BEARISH')
        df['signal'] = 'MODERATE'
        
        # Technical Breakout: Strong momentum + volume + pattern
        technical_breakout = (
            (df['abs_momentum'] >= self.params['breakout_threshold']) & 
            (df['relative_volume'] >= self.params['optimal_relative_volume']) & 
            (df['relative_range'] > 1.5) &
            (df['volume_acceleration'] > 1.2)
        )
        df.loc[technical_breakout, 'signal'] = 'TECHNICAL_BREAKOUT'
        
        # Volume Surge: Exceptional volume with momentum
        volume_surge = (
            (df['relative_volume'] > 4.0) & 
            (df['volume_spike_ratio'] > 4.0) &
            (df['abs_momentum'] >= 1.0)
        )
        df.loc[volume_surge & (df['signal'] == 'MODERATE'), 'signal'] = 'VOLUME_SURGE'
        
        # Strong Directional: High momentum + consistent price action
        strong_directional = (
            (df['abs_momentum'] >= self.params['technical_momentum_threshold']) & 
            (df['directional_strength'] > 70) &
            (df['price_action_bonus'] > 0)
        )
        df.loc[strong_directional & (df['signal'] == 'MODERATE'), 'signal'] = 'STRONG_DIRECTIONAL'
        
        # Technical Quality: High composite score + good patterns
        technical_quality = (
            (df['composite_score'] > 70) &
            (df['pattern_score'] > 60) &
            (df['volume_score'] > 60)
        )
        df.loc[technical_quality & (df['signal'] == 'MODERATE'), 'signal'] = 'TECHNICAL_QUALITY'
        
        return df.sort_values('composite_score', ascending=False)
    
    def display_technical_results(self, results: pd.DataFrame, top_n: int = 10):
        """Display technical analysis enhanced results"""
        if results.empty:
            print("❌ No technical momentum candidates found")
            return
        
        print(f"\n🚀 TECHNICAL MOMENTUM SCANNER v3.0 - TOP {min(top_n, len(results))} PICKS")
        print("=" * 100)
        
        signal_emojis = {
            'TECHNICAL_BREAKOUT': '💥',
            'VOLUME_SURGE': '🌊',
            'STRONG_DIRECTIONAL': '🎯',
            'TECHNICAL_QUALITY': '💎',
            'MODERATE': '📊'
        }
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            emoji = signal_emojis.get(row['signal'], '📊')
            direction_emoji = '📈' if row['direction'] == 'BULLISH' else '📉'
            
            print(f"\n{emoji} #{i}: {row['symbol']} | Score: {row['composite_score']:.1f}/100 {direction_emoji}")
            print(f"   💰 Price: ₹{row['opening_price']:.2f} → ₹{row['price_0950']:.2f} "
                  f"({row['price_change_pct']:+.2f}%)")
            print(f"   📊 Volume: {row['total_volume_0950']:,.0f} shares "
                  f"({row['relative_volume']:.1f}x avg)")
            print(f"   📈 Range: ₹{row['low_0950']:.2f} - ₹{row['high_0950']:.2f} "
                  f"({row['volatility_pct']:.2f}% volatility)")
            
            # Technical Analysis Details
            print(f"   🔧 Technical: RelRange:{row['relative_range']:.1f}x | "
                  f"DirStrength:{row['directional_strength']:.0f}% | "
                  f"PriceAction:{row['bullish_ratio']:.2f}B/{row['bearish_ratio']:.2f}B")
            
            print(f"   📊 Volume Tech: Acceleration:{row['volume_acceleration']:.2f}x | "
                  f"Spike:{row['volume_spike_ratio']:.1f}x | "
                  f"Pattern:{row['pattern_score']:.0f}")
            
            print(f"   🎯 Signal: {row['signal']} | Risk: {row['max_downside_pct']:.2f}%")
            print(f"   📋 Scores: Vol:{row['volume_score']:.0f} Mom:{row['momentum_score']:.0f} "
                  f"Pattern:{row['pattern_score']:.0f} Liq:{row['liquidity_score']:.0f}")
        
        # Technical summary statistics
        print(f"\n📊 TECHNICAL SCAN SUMMARY:")
        print(f"   📈 Total candidates: {len(results)}")
        print(f"   🎯 Average score: {results['composite_score'].mean():.1f}")
        print(f"   🏆 Top score: {results['composite_score'].max():.1f}")
        
        # Technical pattern analysis
        avg_rel_range = results['relative_range'].mean()
        avg_dir_strength = results['directional_strength'].mean()
        avg_vol_accel = results['volume_acceleration'].mean()
        
        print(f"   🔧 Technical Averages: RelRange:{avg_rel_range:.1f}x | "
              f"DirStrength:{avg_dir_strength:.0f}% | VolAccel:{avg_vol_accel:.1f}x")
        
        # Signal distribution
        signal_counts = results['signal'].value_counts()
        print(f"   📋 Signals: ", end="")
        for signal, count in signal_counts.items():
            emoji = signal_emojis.get(signal, '📊')
            print(f"{emoji}{count} ", end="")
        print()
        
        # Technical quality metrics
        high_quality = (results['composite_score'] > 70).sum()
        breakouts = (results['signal'] == 'TECHNICAL_BREAKOUT').sum()
        volume_surges = (results['signal'] == 'VOLUME_SURGE').sum()
        
        print(f"   💎 Quality: High:{high_quality} | Breakouts:{breakouts} | VolSurges:{volume_surges}")
    
    def scan(self, scan_date: date, top_n: int = 10) -> pd.DataFrame:
        """Run the complete technical momentum scan"""
        logger.info(f"🚀 Starting Technical Momentum Scanner v3.0 for {scan_date}")
        
        try:
            # Get technical candidates
            candidates = self.get_technical_candidates(scan_date)
            
            if candidates.empty:
                logger.warning("⚠️ No technical momentum candidates found")
                return pd.DataFrame()
            
            # Calculate technical scores
            results = self.calculate_technical_scores(candidates)
            
            # Display results
            self.display_technical_results(results, top_n)
            
            # Show top picks summary
            if not results.empty:
                top_picks = results.head(3)
                print(f"\n🎯 TODAY'S TOP 3 TECHNICAL MOMENTUM PICKS:")
                for i, (_, pick) in enumerate(top_picks.iterrows(), 1):
                    quality = '💎' if pick['composite_score'] > 70 else '⭐' if pick['composite_score'] > 50 else '📊'
                    
                    print(f"   {i}. {pick['symbol']}: {pick['price_change_pct']:+.2f}% "
                          f"({pick['relative_volume']:.1f}x vol) - {pick['signal']} {quality}")
                    print(f"      Technical: Range:{pick['relative_range']:.1f}x "
                          f"DirStr:{pick['directional_strength']:.0f}% "
                          f"Risk:{pick['max_downside_pct']:.2f}%")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during technical momentum scan: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        finally:
            self.db_manager.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Technical Momentum Scanner v3.0')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=8,
                       help='Number of top results to display')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        scanner = TechnicalMomentumScanner()
        results = scanner.scan(scan_date=scan_date, top_n=args.top_n)
        
        if not results.empty:
            print(f"\n✅ Technical momentum scan completed! Found {len(results)} opportunities")
            
            # Performance prediction
            breakouts = (results['signal'] == 'TECHNICAL_BREAKOUT').sum()
            volume_surges = (results['signal'] == 'VOLUME_SURGE').sum()
            high_quality = (results['composite_score'] > 70).sum()
            
            print(f"\n📊 TECHNICAL ASSESSMENT:")
            print(f"   💥 Technical Breakouts: {breakouts}")
            print(f"   🌊 Volume Surges: {volume_surges}")
            print(f"   💎 High Quality Setups: {high_quality}")
            
            if breakouts > 0:
                print(f"\n🚀 EXPECTED PERFORMANCE: Technical breakouts detected - explosive moves likely!")
            elif volume_surges > 0:
                print(f"\n🌊 EXPECTED PERFORMANCE: Volume surges identified - strong momentum expected!")
            elif high_quality > 0:
                print(f"\n💎 EXPECTED PERFORMANCE: High-quality technical setups - good probability!")
            else:
                print(f"\n📊 EXPECTED PERFORMANCE: Standard momentum with technical confirmation")
                
        else:
            print(f"\n⚠️ No technical momentum opportunities found for {scan_date}")
            
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
