#!/usr/bin/env python3
"""
Best Trading Stock Scanner by 09:50 AM

This advanced scanner combines multiple criteria to identify the best stocks
for intraday trading based on early market activity (09:15 - 09:50 AM).

Scoring Criteria:
1. Relative Volume (40% weight) - Higher than average volume
2. Price Momentum (25% weight) - Strong directional movement
3. Volatility (20% weight) - Sufficient price range for trading
4. Liquidity (15% weight) - Consistent trading activity

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BestTradingScanner:
    """Advanced scanner to identify best trading opportunities by 09:50 AM"""
    
    def __init__(self):
        """Initialize the scanner"""
        self.db_manager = DuckDBManager()
        
        # Scoring weights
        self.weights = {
            'relative_volume': 0.40,
            'momentum': 0.25,
            'volatility': 0.20,
            'liquidity': 0.15
        }
        
        # Minimum thresholds for consideration
        self.min_thresholds = {
            'min_volume': 10000,      # Minimum 10K shares by 09:50
            'min_price': 10.0,        # Minimum ₹10 stock price
            'max_price': 5000.0,      # Maximum ₹5000 stock price
            'min_trades': 20,         # Minimum 20 minutes of activity
            'min_relative_volume': 1.2 # At least 1.2x average volume
        }
    
    def get_historical_averages(self, lookback_days: int = 14) -> pd.DataFrame:
        """Calculate historical volume averages for comparison"""
        logger.info(f"📊 Calculating {lookback_days}-day historical averages...")
        
        query = '''
        SELECT 
            symbol,
            AVG(daily_volume) as avg_volume_14d,
            AVG(daily_volatility) as avg_volatility_14d,
            AVG(daily_trades) as avg_trades_14d
        FROM (
            SELECT 
                symbol,
                DATE(timestamp) as trade_date,
                SUM(volume) as daily_volume,
                (MAX(high) - MIN(low)) / AVG(close) * 100 as daily_volatility,
                COUNT(*) as daily_trades
            FROM market_data 
            WHERE DATE(timestamp) >= CURRENT_DATE - INTERVAL '{} days'
                AND DATE(timestamp) < CURRENT_DATE
                AND strftime('%H:%M', timestamp) <= '09:50'
            GROUP BY symbol, DATE(timestamp)
            HAVING COUNT(*) >= 20  -- At least 20 minutes of data
        ) daily_stats
        GROUP BY symbol
        HAVING COUNT(*) >= {}  -- At least half the lookback period
        '''.format(lookback_days + 1, lookback_days // 2)
        
        return self.db_manager.execute_custom_query(query)
    
    def get_current_day_data(self, scan_date: date) -> pd.DataFrame:
        """Get current day data up to 09:50 AM"""
        logger.info(f"📊 Analyzing current day data for {scan_date}...")
        
        query = '''
        SELECT 
            symbol,
            COUNT(*) as trades_count,
            SUM(volume) as total_volume,
            MIN(open) as day_open,
            MAX(high) as day_high,
            MIN(low) as day_low,
            
            -- Get first and last prices for momentum calculation
            FIRST_VALUE(open) OVER (PARTITION BY symbol ORDER BY timestamp) as opening_price,
            LAST_VALUE(close) OVER (PARTITION BY symbol ORDER BY timestamp 
                ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as current_price,
            
            -- Price statistics
            AVG(close) as avg_price,
            STDDEV(close) as price_stddev,
            
            -- Volume distribution
            MAX(volume) as max_minute_volume,
            MIN(volume) as min_minute_volume,
            AVG(volume) as avg_minute_volume,
            
            -- Time-based metrics
            MIN(strftime('%H:%M', timestamp)) as first_trade_time,
            MAX(strftime('%H:%M', timestamp)) as last_trade_time
            
        FROM market_data 
        WHERE DATE(timestamp) = ?
            AND strftime('%H:%M', timestamp) <= '09:50'
        GROUP BY symbol
        HAVING COUNT(*) >= 20  -- At least 20 minutes of activity
        '''
        
        return self.db_manager.execute_custom_query(query, [scan_date])
    
    def calculate_scores(self, current_data: pd.DataFrame, historical_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive trading scores"""
        logger.info("🧮 Calculating trading scores...")
        
        # Merge current and historical data
        merged = current_data.merge(historical_data, on='symbol', how='inner')
        
        if merged.empty:
            logger.warning("⚠️ No data available for scoring")
            return pd.DataFrame()
        
        # Calculate individual scores (0-100 scale)
        scores = merged.copy()
        
        # 1. Relative Volume Score (40% weight)
        scores['relative_volume'] = scores['total_volume'] / scores['avg_volume_14d']
        scores['volume_score'] = np.clip(
            (scores['relative_volume'] - 1) * 25, 0, 100
        )
        
        # 2. Momentum Score (25% weight)
        scores['price_change_pct'] = (
            (scores['current_price'] - scores['opening_price']) / scores['opening_price'] * 100
        )
        scores['momentum_score'] = np.clip(
            50 + (scores['price_change_pct'] * 10), 0, 100
        )
        
        # 3. Volatility Score (20% weight)
        scores['current_volatility'] = (
            (scores['day_high'] - scores['day_low']) / scores['avg_price'] * 100
        )
        scores['volatility_score'] = np.clip(
            scores['current_volatility'] * 20, 0, 100
        )
        
        # 4. Liquidity Score (15% weight)
        scores['liquidity_consistency'] = (
            scores['min_minute_volume'] / scores['avg_minute_volume']
        )
        scores['liquidity_score'] = np.clip(
            scores['liquidity_consistency'] * 100, 0, 100
        )
        
        # Calculate composite score
        scores['composite_score'] = (
            scores['volume_score'] * self.weights['relative_volume'] +
            scores['momentum_score'] * self.weights['momentum'] +
            scores['volatility_score'] * self.weights['volatility'] +
            scores['liquidity_score'] * self.weights['liquidity']
        )
        
        # Apply minimum thresholds
        mask = (
            (scores['total_volume'] >= self.min_thresholds['min_volume']) &
            (scores['avg_price'] >= self.min_thresholds['min_price']) &
            (scores['avg_price'] <= self.min_thresholds['max_price']) &
            (scores['trades_count'] >= self.min_thresholds['min_trades']) &
            (scores['relative_volume'] >= self.min_thresholds['min_relative_volume'])
        )
        
        qualified_scores = scores[mask].copy()
        
        if qualified_scores.empty:
            logger.warning("⚠️ No stocks meet minimum qualification criteria")
            return pd.DataFrame()
        
        # Add trading signals
        qualified_scores['signal'] = 'NEUTRAL'
        qualified_scores.loc[
            (qualified_scores['price_change_pct'] > 1) & 
            (qualified_scores['relative_volume'] > 2), 'signal'
        ] = 'STRONG_BUY'
        qualified_scores.loc[
            (qualified_scores['price_change_pct'] > 0.5) & 
            (qualified_scores['relative_volume'] > 1.5), 'signal'
        ] = 'BUY'
        qualified_scores.loc[
            (qualified_scores['price_change_pct'] < -1) & 
            (qualified_scores['relative_volume'] > 2), 'signal'
        ] = 'STRONG_SELL'
        qualified_scores.loc[
            (qualified_scores['price_change_pct'] < -0.5) & 
            (qualified_scores['relative_volume'] > 1.5), 'signal'
        ] = 'SELL'
        
        return qualified_scores.sort_values('composite_score', ascending=False)
    
    def format_results(self, results: pd.DataFrame, top_n: int = 10) -> None:
        """Format and display results"""
        if results.empty:
            print("❌ No qualifying stocks found")
            return
        
        print(f"\n🏆 TOP {min(top_n, len(results))} BEST TRADING OPPORTUNITIES BY 09:50 AM")
        print("=" * 80)
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            signal_emoji = {
                'STRONG_BUY': '🚀',
                'BUY': '📈',
                'NEUTRAL': '➡️',
                'SELL': '📉',
                'STRONG_SELL': '💥'
            }.get(row['signal'], '❓')
            
            print(f"\n{signal_emoji} RANK {i}: {row['symbol']} (Score: {row['composite_score']:.1f}/100)")
            print(f"   💰 Price: ₹{row['opening_price']:.2f} → ₹{row['current_price']:.2f} "
                  f"({row['price_change_pct']:+.2f}%)")
            print(f"   📊 Volume: {row['total_volume']:,.0f} shares "
                  f"({row['relative_volume']:.1f}x average)")
            print(f"   📈 Volatility: {row['current_volatility']:.2f}% "
                  f"(Range: ₹{row['day_low']:.2f} - ₹{row['day_high']:.2f})")
            print(f"   🎯 Signal: {row['signal']}")
            print(f"   📋 Breakdown: Vol:{row['volume_score']:.0f} "
                  f"Mom:{row['momentum_score']:.0f} "
                  f"Vol:{row['volatility_score']:.0f} "
                  f"Liq:{row['liquidity_score']:.0f}")
    
    def export_results(self, results: pd.DataFrame, filename: str) -> None:
        """Export results to CSV"""
        if results.empty:
            logger.warning("No results to export")
            return
        
        # Select key columns for export
        export_columns = [
            'symbol', 'composite_score', 'signal',
            'opening_price', 'current_price', 'price_change_pct',
            'total_volume', 'relative_volume',
            'current_volatility', 'trades_count',
            'volume_score', 'momentum_score', 'volatility_score', 'liquidity_score'
        ]
        
        export_data = results[export_columns].copy()
        export_data.to_csv(filename, index=False)
        logger.info(f"📁 Results exported to {filename}")
    
    def scan(self, scan_date: date, lookback_days: int = 14, top_n: int = 10, 
             export_file: Optional[str] = None) -> pd.DataFrame:
        """Run the complete best trading scanner"""
        logger.info(f"🚀 Starting Best Trading Scanner for {scan_date}")
        
        try:
            # Get historical averages
            historical_data = self.get_historical_averages(lookback_days)
            if historical_data.empty:
                logger.error("❌ No historical data available")
                return pd.DataFrame()
            
            # Get current day data
            current_data = self.get_current_day_data(scan_date)
            if current_data.empty:
                logger.error("❌ No current day data available")
                return pd.DataFrame()
            
            # Calculate scores
            results = self.calculate_scores(current_data, historical_data)
            
            # Display results
            self.format_results(results, top_n)
            
            # Export if requested
            if export_file:
                self.export_results(results, export_file)
            
            # Summary statistics
            if not results.empty:
                print(f"\n📊 SCAN SUMMARY:")
                print(f"   📈 Total qualified stocks: {len(results)}")
                print(f"   🎯 Average score: {results['composite_score'].mean():.1f}")
                print(f"   🏆 Top score: {results['composite_score'].max():.1f}")
                print(f"   📊 Strong signals: {len(results[results['signal'].isin(['STRONG_BUY', 'STRONG_SELL'])])}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during scan: {e}")
            return pd.DataFrame()
        finally:
            self.db_manager.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Best Trading Stock Scanner by 09:50 AM')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--lookback-days', type=int, default=14,
                       help='Days to look back for historical averages')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top results to display')
    parser.add_argument('--export', type=str,
                       help='Export results to CSV file')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        scanner = BestTradingScanner()
        results = scanner.scan(
            scan_date=scan_date,
            lookback_days=args.lookback_days,
            top_n=args.top_n,
            export_file=args.export
        )
        
        if not results.empty:
            print(f"\n✅ Scan completed successfully!")
            print(f"🎯 Found {len(results)} qualified trading opportunities")
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
