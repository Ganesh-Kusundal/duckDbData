#!/usr/bin/env python3
"""
Simple Best Trading Scanner by 09:50 AM

A simplified but effective scanner to identify the best trading opportunities
based on volume, momentum, and price action by 09:50 AM.

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

class SimpleBestScanner:
    """Simple but effective best trading scanner"""
    
    def __init__(self):
        """Initialize the scanner"""
        self.db_manager = DuckDBManager()
    
    def get_trading_candidates(self, scan_date: date) -> pd.DataFrame:
        """Get all potential trading candidates with key metrics"""
        logger.info(f"📊 Analyzing trading candidates for {scan_date}...")
        
        query = '''
        WITH current_day_stats AS (
            SELECT 
                symbol,
                COUNT(*) as minutes_traded,
                SUM(volume) as total_volume,
                AVG(volume) as avg_minute_volume,
                MAX(volume) as max_minute_volume,
                MIN(volume) as min_minute_volume,
                
                -- Price metrics
                FIRST_VALUE(open) OVER (PARTITION BY symbol ORDER BY timestamp) as opening_price,
                LAST_VALUE(close) OVER (PARTITION BY symbol ORDER BY timestamp 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as current_price,
                MAX(high) as day_high,
                MIN(low) as day_low,
                AVG(close) as avg_price,
                
                -- Volume consistency
                STDDEV(volume) as volume_stddev
                
            FROM market_data 
            WHERE DATE(timestamp) = ?
                AND strftime('%H:%M', timestamp) <= '09:50'
            GROUP BY symbol
            HAVING COUNT(*) >= 25  -- At least 25 minutes of activity
        ),
        
        historical_comparison AS (
            SELECT 
                symbol,
                AVG(daily_volume) as avg_historical_volume
            FROM (
                SELECT 
                    symbol,
                    DATE(timestamp) as trade_date,
                    SUM(volume) as daily_volume
                FROM market_data 
                WHERE DATE(timestamp) >= ? - INTERVAL '14 days'
                    AND DATE(timestamp) < ?
                    AND strftime('%H:%M', timestamp) <= '09:50'
                GROUP BY symbol, DATE(timestamp)
            ) hist
            GROUP BY symbol
            HAVING COUNT(*) >= 7  -- At least 7 days of history
        )
        
        SELECT 
            c.*,
            COALESCE(h.avg_historical_volume, c.total_volume) as historical_avg_volume,
            c.total_volume / COALESCE(h.avg_historical_volume, c.total_volume) as relative_volume,
            
            -- Calculate price change percentage
            (c.current_price - c.opening_price) / c.opening_price * 100 as price_change_pct,
            
            -- Calculate volatility
            (c.day_high - c.day_low) / c.avg_price * 100 as volatility_pct,
            
            -- Volume consistency score (lower stddev = more consistent)
            CASE 
                WHEN c.volume_stddev = 0 THEN 100
                ELSE GREATEST(0, 100 - (c.volume_stddev / c.avg_minute_volume * 100))
            END as volume_consistency_score
            
        FROM current_day_stats c
        LEFT JOIN historical_comparison h ON c.symbol = h.symbol
        WHERE c.total_volume >= 50000  -- Minimum 50K volume
            AND c.avg_price >= 10      -- Minimum ₹10 price
            AND c.avg_price <= 3000    -- Maximum ₹3000 price
        '''
        
        return self.db_manager.execute_custom_query(query, [scan_date, scan_date, scan_date])
    
    def calculate_trading_scores(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive trading scores"""
        if data.empty:
            return data
        
        logger.info("🧮 Calculating trading scores...")
        
        df = data.copy()
        
        # 1. Volume Score (0-100) - Based on relative volume
        df['volume_score'] = np.clip(
            (df['relative_volume'] - 1) * 30, 0, 100
        )
        
        # 2. Momentum Score (0-100) - Based on price change
        df['momentum_score'] = np.clip(
            50 + (df['price_change_pct'] * 8), 0, 100
        )
        
        # 3. Volatility Score (0-100) - Sweet spot around 2-4%
        df['volatility_score'] = np.clip(
            100 - abs(df['volatility_pct'] - 3) * 15, 0, 100
        )
        
        # 4. Liquidity Score (0-100) - Based on total volume and consistency
        volume_percentile = df['total_volume'].rank(pct=True) * 100
        df['liquidity_score'] = (volume_percentile + df['volume_consistency_score']) / 2
        
        # Composite Score (weighted average)
        df['composite_score'] = (
            df['volume_score'] * 0.35 +
            df['momentum_score'] * 0.30 +
            df['volatility_score'] * 0.20 +
            df['liquidity_score'] * 0.15
        )
        
        # Trading Signal
        df['signal'] = 'HOLD'
        
        # Strong signals
        strong_buy_mask = (
            (df['price_change_pct'] > 2) & 
            (df['relative_volume'] > 3) & 
            (df['volatility_pct'] > 1.5)
        )
        df.loc[strong_buy_mask, 'signal'] = 'STRONG_BUY'
        
        strong_sell_mask = (
            (df['price_change_pct'] < -2) & 
            (df['relative_volume'] > 3) & 
            (df['volatility_pct'] > 1.5)
        )
        df.loc[strong_sell_mask, 'signal'] = 'STRONG_SELL'
        
        # Regular signals
        buy_mask = (
            (df['price_change_pct'] > 1) & 
            (df['relative_volume'] > 2) & 
            (~strong_buy_mask)
        )
        df.loc[buy_mask, 'signal'] = 'BUY'
        
        sell_mask = (
            (df['price_change_pct'] < -1) & 
            (df['relative_volume'] > 2) & 
            (~strong_sell_mask)
        )
        df.loc[sell_mask, 'signal'] = 'SELL'
        
        # Breakout signals
        breakout_mask = (
            (abs(df['price_change_pct']) > 0.5) & 
            (df['relative_volume'] > 1.5) & 
            (df['volatility_pct'] > 2) &
            (df['signal'] == 'HOLD')
        )
        df.loc[breakout_mask, 'signal'] = 'BREAKOUT'
        
        return df.sort_values('composite_score', ascending=False)
    
    def display_results(self, results: pd.DataFrame, top_n: int = 10):
        """Display formatted results"""
        if results.empty:
            print("❌ No qualifying stocks found")
            return
        
        print(f"\n🏆 TOP {min(top_n, len(results))} BEST TRADING STOCKS BY 09:50 AM")
        print("=" * 85)
        
        signal_emojis = {
            'STRONG_BUY': '🚀',
            'BUY': '📈',
            'BREAKOUT': '💥',
            'HOLD': '➡️',
            'SELL': '📉',
            'STRONG_SELL': '💀'
        }
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            emoji = signal_emojis.get(row['signal'], '❓')
            
            print(f"\n{emoji} #{i}: {row['symbol']} | Score: {row['composite_score']:.1f}/100")
            print(f"   💰 Price: ₹{row['opening_price']:.2f} → ₹{row['current_price']:.2f} "
                  f"({row['price_change_pct']:+.2f}%)")
            print(f"   📊 Volume: {row['total_volume']:,.0f} shares "
                  f"({row['relative_volume']:.1f}x avg)")
            print(f"   📈 Range: ₹{row['day_low']:.2f} - ₹{row['day_high']:.2f} "
                  f"({row['volatility_pct']:.2f}% volatility)")
            print(f"   🎯 Signal: {row['signal']}")
            print(f"   📋 Scores: Vol:{row['volume_score']:.0f} "
                  f"Mom:{row['momentum_score']:.0f} "
                  f"Vlt:{row['volatility_score']:.0f} "
                  f"Liq:{row['liquidity_score']:.0f}")
        
        # Summary statistics
        print(f"\n📊 SUMMARY STATISTICS:")
        print(f"   📈 Total candidates: {len(results)}")
        print(f"   🎯 Average score: {results['composite_score'].mean():.1f}")
        print(f"   🏆 Highest score: {results['composite_score'].max():.1f}")
        
        # Signal distribution
        signal_counts = results['signal'].value_counts()
        print(f"   📋 Signals: ", end="")
        for signal, count in signal_counts.items():
            emoji = signal_emojis.get(signal, '❓')
            print(f"{emoji}{signal}:{count} ", end="")
        print()
    
    def scan(self, scan_date: date, top_n: int = 10) -> pd.DataFrame:
        """Run the complete scan"""
        logger.info(f"🚀 Starting Simple Best Trading Scanner for {scan_date}")
        
        try:
            # Get trading candidates
            candidates = self.get_trading_candidates(scan_date)
            
            if candidates.empty:
                logger.warning("⚠️ No trading candidates found")
                return pd.DataFrame()
            
            # Calculate scores
            results = self.calculate_trading_scores(candidates)
            
            # Display results
            self.display_results(results, top_n)
            
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
    parser = argparse.ArgumentParser(description='Simple Best Trading Scanner')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top results to display')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        scanner = SimpleBestScanner()
        results = scanner.scan(scan_date=scan_date, top_n=args.top_n)
        
        if not results.empty:
            print(f"\n✅ Scan completed! Found {len(results)} trading opportunities")
        else:
            print(f"\n⚠️ No qualifying stocks found for {scan_date}")
            
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
