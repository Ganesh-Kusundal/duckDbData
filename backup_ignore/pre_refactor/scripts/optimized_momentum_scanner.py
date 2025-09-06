#!/usr/bin/env python3
"""
Optimized Momentum Scanner by 09:50 AM

Based on analysis of high-volume stocks and market patterns, this scanner
identifies the best momentum opportunities by 09:50 AM using proven criteria.

Key Criteria (based on TATASTEEL, ASHOKLEY, ALOKINDS analysis):
1. High relative volume (2x+ average)
2. Strong price momentum (1%+ move)
3. Sufficient liquidity (100K+ volume)
4. Reasonable price range (₹10-₹2000)

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

class OptimizedMomentumScanner:
    """Optimized momentum scanner based on proven patterns"""
    
    def __init__(self):
        """Initialize the scanner with optimized parameters"""
        self.db_manager = DuckDBManager()
        
        # Optimized parameters based on analysis
        self.params = {
            'min_volume_threshold': 100000,    # 100K+ shares by 09:50
            'min_price_change': 1.0,           # 1%+ price movement
            'min_relative_volume': 2.0,        # 2x+ average volume
            'min_volatility': 1.5,             # 1.5%+ volatility
            'max_price': 2000,                 # Max ₹2000
            'min_price': 10,                   # Min ₹10
            'min_minutes': 30                  # At least 30 minutes active
        }
    
    def get_momentum_candidates(self, scan_date: date) -> pd.DataFrame:
        """Get momentum candidates by 09:50 AM"""
        logger.info(f"🔍 Scanning for momentum candidates on {scan_date}")
        
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
                AVG(close) as avg_price
                
            FROM market_data 
            WHERE DATE(timestamp) = ?
                AND strftime('%H:%M', timestamp) <= '09:50'
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
            HAVING COUNT(*) >= ?
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
                WHERE DATE(timestamp) >= ? - INTERVAL '7 days'
                    AND DATE(timestamp) < ?
                    AND strftime('%H:%M', timestamp) <= '09:50'
                    AND strftime('%H:%M', timestamp) >= '09:15'
                GROUP BY symbol, DATE(timestamp)
            ) daily_data
            GROUP BY symbol
            HAVING COUNT(*) >= 3
        )
        
        SELECT 
            c.*,
            COALESCE(h.avg_historical_volume, c.total_volume_0950 * 0.5) as historical_avg,
            c.total_volume_0950 / COALESCE(h.avg_historical_volume, c.total_volume_0950 * 0.5) as relative_volume,
            
            -- Price metrics
            (c.price_0950 - c.opening_price) / c.opening_price * 100 as price_change_pct,
            (c.high_0950 - c.low_0950) / c.avg_price * 100 as volatility_pct,
            
            -- Momentum score
            ABS((c.price_0950 - c.opening_price) / c.opening_price * 100) as abs_momentum
            
        FROM current_day_data c
        LEFT JOIN historical_volume h ON c.symbol = h.symbol
        WHERE c.opening_price IS NOT NULL 
            AND c.price_0950 IS NOT NULL
            AND c.avg_price >= ?
            AND c.avg_price <= ?
        '''
        
        candidates = self.db_manager.execute_custom_query(query, [
            scan_date, 
            self.params['min_minutes'],
            scan_date,
            scan_date,
            self.params['min_price'],
            self.params['max_price']
        ])
        
        if candidates.empty:
            return pd.DataFrame()
        
        # Apply filters
        filtered = candidates[
            (candidates['total_volume_0950'] >= self.params['min_volume_threshold']) &
            (candidates['abs_momentum'] >= self.params['min_price_change']) &
            (candidates['relative_volume'] >= self.params['min_relative_volume']) &
            (candidates['volatility_pct'] >= self.params['min_volatility'])
        ].copy()
        
        return filtered
    
    def calculate_momentum_scores(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive momentum scores"""
        if candidates.empty:
            return candidates
        
        df = candidates.copy()
        
        # Individual component scores (0-100)
        
        # 1. Volume Score - Higher relative volume = higher score
        df['volume_score'] = np.clip((df['relative_volume'] - 1) * 25, 0, 100)
        
        # 2. Momentum Score - Higher absolute price change = higher score
        df['momentum_score'] = np.clip(df['abs_momentum'] * 15, 0, 100)
        
        # 3. Volatility Score - Optimal volatility around 2-4%
        df['volatility_score'] = np.clip(100 - abs(df['volatility_pct'] - 3) * 20, 0, 100)
        
        # 4. Liquidity Score - Based on total volume
        volume_rank = df['total_volume_0950'].rank(pct=True) * 100
        df['liquidity_score'] = volume_rank
        
        # Composite Score (weighted)
        df['composite_score'] = (
            df['volume_score'] * 0.35 +      # Relative volume importance
            df['momentum_score'] * 0.30 +    # Price momentum
            df['liquidity_score'] * 0.20 +   # Total liquidity
            df['volatility_score'] * 0.15    # Volatility quality
        )
        
        # Direction and Signal
        df['direction'] = np.where(df['price_change_pct'] > 0, 'BULLISH', 'BEARISH')
        
        # Signal strength
        df['signal'] = 'MODERATE'
        
        strong_bullish = (
            (df['price_change_pct'] > 2) & 
            (df['relative_volume'] > 3) & 
            (df['direction'] == 'BULLISH')
        )
        df.loc[strong_bullish, 'signal'] = 'STRONG_BULLISH'
        
        strong_bearish = (
            (df['price_change_pct'] < -2) & 
            (df['relative_volume'] > 3) & 
            (df['direction'] == 'BEARISH')
        )
        df.loc[strong_bearish, 'signal'] = 'STRONG_BEARISH'
        
        breakout = (
            (df['abs_momentum'] > 1.5) & 
            (df['relative_volume'] > 2.5) & 
            (df['volatility_pct'] > 2.5)
        )
        df.loc[breakout & (df['signal'] == 'MODERATE'), 'signal'] = 'BREAKOUT'
        
        return df.sort_values('composite_score', ascending=False)
    
    def display_results(self, results: pd.DataFrame, top_n: int = 10):
        """Display formatted momentum scanner results"""
        if results.empty:
            print("❌ No momentum candidates found")
            return
        
        print(f"\n🚀 TOP {min(top_n, len(results))} MOMENTUM STOCKS BY 09:50 AM")
        print("=" * 90)
        
        signal_emojis = {
            'STRONG_BULLISH': '🚀',
            'STRONG_BEARISH': '💥',
            'BREAKOUT': '⚡',
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
            print(f"   🎯 Signal: {row['signal']} ({row['direction']})")
            print(f"   📋 Breakdown: Vol:{row['volume_score']:.0f} "
                  f"Mom:{row['momentum_score']:.0f} "
                  f"Liq:{row['liquidity_score']:.0f} "
                  f"Vlt:{row['volatility_score']:.0f}")
        
        # Summary statistics
        print(f"\n📊 SCAN SUMMARY:")
        print(f"   📈 Total momentum candidates: {len(results)}")
        print(f"   🎯 Average score: {results['composite_score'].mean():.1f}")
        print(f"   🏆 Top score: {results['composite_score'].max():.1f}")
        
        # Signal distribution
        signal_counts = results['signal'].value_counts()
        print(f"   📋 Signals: ", end="")
        for signal, count in signal_counts.items():
            emoji = signal_emojis.get(signal, '📊')
            print(f"{emoji}{count} ", end="")
        print()
        
        # Direction split
        bullish_count = (results['direction'] == 'BULLISH').sum()
        bearish_count = (results['direction'] == 'BEARISH').sum()
        print(f"   📈 Direction: 📈{bullish_count} Bullish | 📉{bearish_count} Bearish")
    
    def get_top_picks(self, results: pd.DataFrame, count: int = 3) -> List[Dict]:
        """Get top momentum picks with detailed info"""
        if results.empty:
            return []
        
        top_picks = []
        for _, row in results.head(count).iterrows():
            pick = {
                'symbol': row['symbol'],
                'score': row['composite_score'],
                'signal': row['signal'],
                'direction': row['direction'],
                'price_change_pct': row['price_change_pct'],
                'relative_volume': row['relative_volume'],
                'current_price': row['price_0950'],
                'volatility': row['volatility_pct']
            }
            top_picks.append(pick)
        
        return top_picks
    
    def scan(self, scan_date: date, top_n: int = 10) -> pd.DataFrame:
        """Run the complete momentum scan"""
        logger.info(f"🚀 Starting Optimized Momentum Scanner for {scan_date}")
        
        try:
            # Get momentum candidates
            candidates = self.get_momentum_candidates(scan_date)
            
            if candidates.empty:
                logger.warning("⚠️ No momentum candidates found")
                return pd.DataFrame()
            
            # Calculate scores
            results = self.calculate_momentum_scores(candidates)
            
            # Display results
            self.display_results(results, top_n)
            
            # Show top picks summary
            top_picks = self.get_top_picks(results, 3)
            if top_picks:
                print(f"\n🎯 TODAY'S TOP 3 MOMENTUM PICKS:")
                for i, pick in enumerate(top_picks, 1):
                    print(f"   {i}. {pick['symbol']}: {pick['price_change_pct']:+.2f}% "
                          f"({pick['relative_volume']:.1f}x vol) - {pick['signal']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during scan: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        finally:
            self.db_manager.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Optimized Momentum Scanner by 09:50 AM')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=8,
                       help='Number of top results to display')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        scanner = OptimizedMomentumScanner()
        results = scanner.scan(scan_date=scan_date, top_n=args.top_n)
        
        if not results.empty:
            print(f"\n✅ Momentum scan completed! Found {len(results)} opportunities")
        else:
            print(f"\n⚠️ No momentum opportunities found for {scan_date}")
            
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
