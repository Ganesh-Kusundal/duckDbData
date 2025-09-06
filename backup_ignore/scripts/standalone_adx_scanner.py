#!/usr/bin/env python3
"""
Standalone ADX Enhanced Scanner v1.0

Standalone version of ADX enhanced scanner to avoid database lock conflicts.
This scanner runs independently with its own database connection.

Key Features:
1. Daily ADX Trend Strength Analysis
2. Directional Movement (DI+, DI-) Integration  
3. Multi-timeframe ADX Confirmation (1T + 1D)
4. Trend Strength Classification
5. ADX-based Signal Filtering
6. Momentum + Trend Strength Scoring

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
import duckdb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StandaloneADXScanner:
    """Standalone ADX enhanced scanner with independent database connection"""
    
    def __init__(self):
        """Initialize the standalone ADX scanner"""
        self.db_path = "data/financial_data.duckdb"
        self.connection = None
        
        # ADX-focused parameters
        self.params = {
            # ADX trend strength thresholds
            'adx_weak_trend': 20,               # Weak trend (< 20)
            'adx_moderate_trend': 25,           # Moderate trend (20-25)
            'adx_strong_trend': 30,             # Strong trend (25-30)
            'adx_very_strong_trend': 40,        # Very strong trend (30-40)
            'adx_extreme_trend': 50,            # Extreme trend (> 40)
            
            # Directional movement thresholds
            'di_dominance_threshold': 5,        # DI+ vs DI- difference for clear direction
            'di_strong_dominance': 10,          # Strong directional dominance
            'di_extreme_dominance': 15,         # Extreme directional dominance
            
            # Multi-timeframe confirmation
            'daily_adx_weight': 0.6,            # Daily ADX importance
            'intraday_adx_weight': 0.4,         # Intraday ADX importance
            'adx_alignment_bonus': 20,          # Bonus for timeframe alignment
            
            # Volume and momentum (ADX enhanced)
            'min_volume_threshold': 100000,     # Minimum volume
            'min_relative_volume': 1.2,         # Higher volume for trend confirmation
            'trending_volume_threshold': 2.0,   # Volume for trending markets
            
            # Price movement (trend-aware)
            'min_price_change': 0.2,            # Minimum movement
            'trending_momentum_threshold': 0.8, # Lower threshold in trending markets
            'strong_trend_momentum': 1.2,       # Momentum in strong trends
            
            # Quality filters
            'min_price': 25,                    # Minimum price
            'max_price': 1200,                  # Maximum price
            'min_minutes': 25,                  # Minimum activity
        }
    
    def connect_db(self):
        """Connect to database with retry logic"""
        if self.connection is None:
            try:
                self.connection = duckdb.connect(self.db_path)
                logger.info(f"Connected to DuckDB database: {self.db_path}")
                
                # Configure DuckDB for optimal performance
                self.connection.execute("SET memory_limit='4GB'")
                self.connection.execute("SET threads=4")
                
            except Exception as e:
                # If there's a lock conflict, wait and retry
                import time
                time.sleep(1.0)
                try:
                    self.connection = duckdb.connect(self.db_path)
                    logger.info(f"Connected to DuckDB database (retry): {self.db_path}")
                    
                    # Configure DuckDB for optimal performance
                    self.connection.execute("SET memory_limit='4GB'")
                    self.connection.execute("SET threads=4")
                except Exception as e2:
                    logger.error(f"Failed to connect to database: {e2}")
                    raise e2
        
        return self.connection
    
    def close_db(self):
        """Close database connection"""
        if self.connection:
            try:
                if not self.connection.closed:
                    self.connection.close()
                self.connection = None
                logger.info("Closed DuckDB connection")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
                self.connection = None
    
    def execute_query(self, query: str, params: list = None) -> pd.DataFrame:
        """Execute query and return DataFrame"""
        conn = self.connect_db()
        try:
            if params:
                return conn.execute(query, params).df()
            else:
                return conn.execute(query).df()
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise e
    
    def get_adx_enhanced_candidates(self, scan_date: date) -> pd.DataFrame:
        """Get candidates with ADX trend strength focus"""
        logger.info(f"🔍 ADX enhanced scanning for {scan_date}")
        
        query = '''
        WITH current_day_data AS (
            SELECT 
                symbol,
                COUNT(*) as minutes_active,
                SUM(volume) as total_volume_0950,
                AVG(volume) as avg_minute_volume,
                STDDEV(volume) as volume_stddev,
                
                -- Price data for trend analysis
                MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) as opening_price,
                MAX(CASE WHEN strftime('%H:%M', timestamp) = '09:50' THEN close END) as current_price,
                MAX(high) as session_high,
                MIN(low) as session_low,
                AVG(close) as avg_price,
                
                -- Trend momentum calculation
                (MAX(CASE WHEN strftime('%H:%M', timestamp) = '09:50' THEN close END) - 
                 MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END)) /
                 MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) * 100 as price_change_pct,
                
                -- Intraday trend strength indicators
                (MAX(high) - MIN(low)) / AVG(close) * 100 as session_volatility,
                
                -- Volume trend analysis
                MAX(volume) as max_minute_volume,
                MIN(volume) as min_minute_volume,
                
                -- Directional movement proxies (simplified for intraday DI calculation)
                AVG(CASE WHEN close > open THEN (high - open) END) as avg_positive_dm,
                AVG(CASE WHEN close < open THEN (open - low) END) as avg_negative_dm,
                
                -- Time-based volume analysis
                AVG(CASE WHEN strftime('%H:%M', timestamp) BETWEEN '09:15' AND '09:30' THEN volume END) as early_volume,
                AVG(CASE WHEN strftime('%H:%M', timestamp) BETWEEN '09:35' AND '09:50' THEN volume END) as late_volume,
                
                -- Trend consistency
                COUNT(CASE WHEN close > open THEN 1 END) as bullish_minutes,
                COUNT(CASE WHEN close < open THEN 1 END) as bearish_minutes
                
            FROM market_data 
            WHERE DATE(timestamp) = ?
                AND strftime('%H:%M', timestamp) <= '09:50'
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
            HAVING COUNT(*) >= ?
        ),
        
        daily_trend_context AS (
            SELECT 
                symbol,
                AVG(daily_vol) as avg_historical_volume,
                AVG(daily_range) as avg_historical_range,
                AVG(daily_momentum) as avg_historical_momentum,
                AVG(daily_volatility) as avg_historical_volatility,
                COUNT(*) as historical_days,
                
                -- Daily trend strength estimation (simulated ADX calculation)
                AVG(ABS(daily_momentum)) as avg_daily_movement,
                STDDEV(daily_momentum) as momentum_consistency,
                
                -- Directional bias over time
                COUNT(CASE WHEN daily_momentum > 0 THEN 1 END) / COUNT(*) * 100 as bullish_days_pct,
                COUNT(CASE WHEN daily_momentum < 0 THEN 1 END) / COUNT(*) * 100 as bearish_days_pct
                
            FROM (
                SELECT 
                    symbol,
                    DATE(timestamp) as trade_date,
                    SUM(volume) as daily_vol,
                    MAX(high) - MIN(low) as daily_range,
                    (MAX(CASE WHEN strftime('%H:%M', timestamp) = '15:29' THEN close END) - 
                     MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END)) /
                     MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) * 100 as daily_momentum,
                    (MAX(high) - MIN(low)) / AVG(close) * 100 as daily_volatility
                FROM market_data 
                WHERE DATE(timestamp) >= ? - INTERVAL '20 days'
                    AND DATE(timestamp) < ?
                GROUP BY symbol, DATE(timestamp)
            ) hist
            GROUP BY symbol
            HAVING COUNT(*) >= 10
        )
        
        SELECT 
            c.*,
            COALESCE(h.avg_historical_volume, c.total_volume_0950 * 0.8) as historical_avg_volume,
            COALESCE(h.avg_historical_range, c.session_high - c.session_low) as historical_avg_range,
            COALESCE(h.avg_daily_movement, ABS(c.price_change_pct)) as historical_avg_movement,
            COALESCE(h.momentum_consistency, 2.0) as historical_momentum_consistency,
            COALESCE(h.bullish_days_pct, 50.0) as historical_bullish_bias,
            COALESCE(h.bearish_days_pct, 50.0) as historical_bearish_bias,
            
            -- Key metrics
            c.total_volume_0950 / COALESCE(h.avg_historical_volume, c.total_volume_0950 * 0.8) as relative_volume,
            ABS(c.price_change_pct) as abs_momentum,
            
            -- Trend strength indicators
            (c.session_high - c.session_low) / COALESCE(h.avg_historical_range, c.session_high - c.session_low) as relative_range,
            
            -- Volume confirmation
            COALESCE(c.late_volume / NULLIF(c.early_volume, 0), 1.0) as volume_acceleration,
            c.max_minute_volume / c.avg_minute_volume as volume_spike_ratio,
            
            -- Directional strength
            c.bullish_minutes / CAST(c.minutes_active as FLOAT) as bullish_ratio,
            c.bearish_minutes / CAST(c.minutes_active as FLOAT) as bearish_ratio
            
        FROM current_day_data c
        LEFT JOIN daily_trend_context h ON c.symbol = h.symbol
        WHERE c.opening_price IS NOT NULL 
            AND c.current_price IS NOT NULL
            AND c.avg_price >= ?
            AND c.avg_price <= ?
            AND c.total_volume_0950 >= ?
        '''
        
        candidates = self.execute_query(query, [
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
        
        # ADX-enhanced filtering
        filtered = candidates[
            (candidates['abs_momentum'] >= self.params['min_price_change']) &
            (candidates['relative_volume'] >= self.params['min_relative_volume']) &
            (candidates['minutes_active'] >= self.params['min_minutes'])
        ].copy()
        
        return filtered
    
    def simulate_adx_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Simulate ADX and directional movement indicators"""
        
        # 1. Daily ADX (primary trend strength)
        # Simulate based on historical momentum consistency and movement
        df['daily_adx_14'] = np.clip(
            20 + (df['historical_avg_movement'] * 2) + 
            (10 / (df['historical_momentum_consistency'] + 0.1)), 
            10, 80
        )
        
        df['daily_adx_21'] = df['daily_adx_14'] * np.random.uniform(0.9, 1.1, len(df))
        
        # 2. Intraday ADX (current session trend strength)
        df['intraday_adx_14'] = np.clip(
            15 + (df['abs_momentum'] * 3) + (df['relative_range'] * 5),
            5, 70
        )
        
        # 3. Directional Indicators (DI+, DI-)
        # Daily DI+ and DI-
        df['daily_di_plus'] = np.where(
            df['historical_bullish_bias'] > 50,
            20 + (df['historical_bullish_bias'] - 50) * 0.6,
            20 - (50 - df['historical_bullish_bias']) * 0.4
        )
        
        df['daily_di_minus'] = np.where(
            df['historical_bearish_bias'] > 50,
            20 + (df['historical_bearish_bias'] - 50) * 0.6,
            20 - (50 - df['historical_bearish_bias']) * 0.4
        )
        
        # Intraday DI+ and DI-
        df['intraday_di_plus'] = np.where(
            df['price_change_pct'] > 0,
            15 + df['bullish_ratio'] * 30,
            10 + df['bullish_ratio'] * 20
        )
        
        df['intraday_di_minus'] = np.where(
            df['price_change_pct'] < 0,
            15 + df['bearish_ratio'] * 30,
            10 + df['bearish_ratio'] * 20
        )
        
        # 4. ADX-based trend classification
        df['daily_trend_strength'] = pd.cut(
            df['daily_adx_14'],
            bins=[0, self.params['adx_weak_trend'], self.params['adx_moderate_trend'], 
                  self.params['adx_strong_trend'], self.params['adx_very_strong_trend'], 100],
            labels=['WEAK', 'MODERATE', 'STRONG', 'VERY_STRONG', 'EXTREME']
        )
        
        df['intraday_trend_strength'] = pd.cut(
            df['intraday_adx_14'],
            bins=[0, self.params['adx_weak_trend'], self.params['adx_moderate_trend'], 
                  self.params['adx_strong_trend'], self.params['adx_very_strong_trend'], 100],
            labels=['WEAK', 'MODERATE', 'STRONG', 'VERY_STRONG', 'EXTREME']
        )
        
        # 5. Directional dominance
        df['daily_di_spread'] = df['daily_di_plus'] - df['daily_di_minus']
        df['intraday_di_spread'] = df['intraday_di_plus'] - df['intraday_di_minus']
        
        df['daily_direction'] = np.where(df['daily_di_spread'] > 0, 'BULLISH', 'BEARISH')
        df['intraday_direction'] = np.where(df['intraday_di_spread'] > 0, 'BULLISH', 'BEARISH')
        
        # 6. Multi-timeframe ADX alignment
        df['adx_alignment'] = (
            (df['daily_direction'] == df['intraday_direction']) &
            (df['daily_adx_14'] >= self.params['adx_moderate_trend']) &
            (df['intraday_adx_14'] >= self.params['adx_weak_trend'])
        ).astype(int)
        
        return df
    
    def calculate_adx_enhanced_scores(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Calculate ADX enhanced scores"""
        if candidates.empty:
            return candidates
        
        # Add ADX indicators
        df = self.simulate_adx_indicators(candidates)
        
        # 1. Daily Trend Strength Score (35% weight)
        daily_adx_score = np.where(
            df['daily_adx_14'] >= self.params['adx_extreme_trend'], 100,
            np.where(
                df['daily_adx_14'] >= self.params['adx_very_strong_trend'], 90,
                np.where(
                    df['daily_adx_14'] >= self.params['adx_strong_trend'], 75,
                    np.where(
                        df['daily_adx_14'] >= self.params['adx_moderate_trend'], 60,
                        np.where(
                            df['daily_adx_14'] >= self.params['adx_weak_trend'], 40,
                            20  # Very weak trend
                        )
                    )
                )
            )
        )
        
        # Daily directional strength bonus
        daily_di_bonus = np.where(
            abs(df['daily_di_spread']) >= self.params['di_extreme_dominance'], 20,
            np.where(
                abs(df['daily_di_spread']) >= self.params['di_strong_dominance'], 15,
                np.where(
                    abs(df['daily_di_spread']) >= self.params['di_dominance_threshold'], 10,
                    0
                )
            )
        )
        
        df['daily_trend_score'] = np.clip(daily_adx_score + daily_di_bonus, 0, 100)
        
        # 2. Intraday Trend Confirmation Score (25% weight)
        intraday_adx_score = np.clip(df['intraday_adx_14'] * 2, 0, 100)
        
        # Intraday directional alignment bonus
        intraday_alignment_bonus = np.where(
            (df['daily_direction'] == df['intraday_direction']) &
            (abs(df['intraday_di_spread']) >= self.params['di_dominance_threshold']),
            25, 0
        )
        
        df['intraday_trend_score'] = np.clip(intraday_adx_score + intraday_alignment_bonus, 0, 100)
        
        # 3. Volume Trend Confirmation Score (20% weight)
        volume_base_score = np.clip((df['relative_volume'] - 1) * 25, 0, 100)
        
        # Trending market volume bonus
        trending_volume_bonus = np.where(
            (df['daily_adx_14'] >= self.params['adx_strong_trend']) &
            (df['relative_volume'] >= self.params['trending_volume_threshold']),
            30, 0
        )
        
        df['volume_trend_score'] = np.clip(volume_base_score + trending_volume_bonus, 0, 100)
        
        # 4. Momentum Trend Alignment Score (20% weight)
        # Adjust momentum expectations based on trend strength
        momentum_threshold = np.where(
            df['daily_adx_14'] >= self.params['adx_strong_trend'],
            self.params['trending_momentum_threshold'],  # Lower threshold in strong trends
            self.params['min_price_change']  # Normal threshold in weak trends
        )
        
        momentum_score = np.clip(df['abs_momentum'] / momentum_threshold * 50, 0, 100)
        
        # Trend-momentum alignment bonus
        trend_momentum_bonus = np.where(
            ((df['daily_direction'] == 'BULLISH') & (df['price_change_pct'] > 0)) |
            ((df['daily_direction'] == 'BEARISH') & (df['price_change_pct'] < 0)),
            20, -10  # Penalty for counter-trend moves
        )
        
        df['momentum_trend_score'] = np.clip(momentum_score + trend_momentum_bonus, 0, 100)
        
        # Composite ADX Enhanced Score
        df['composite_score'] = (
            df['daily_trend_score'] * 0.35 +
            df['intraday_trend_score'] * 0.25 +
            df['volume_trend_score'] * 0.20 +
            df['momentum_trend_score'] * 0.20
        )
        
        # Multi-timeframe alignment bonus
        alignment_bonus = np.where(df['adx_alignment'] == 1, self.params['adx_alignment_bonus'], 0)
        df['composite_score'] = np.clip(df['composite_score'] + alignment_bonus, 0, 100)
        
        # ADX-based Signal Classification
        df['direction'] = np.where(df['price_change_pct'] > 0, 'BULLISH', 'BEARISH')
        df['signal'] = 'TRENDING'
        
        # Strong Trend Continuation
        strong_trend_continuation = (
            (df['daily_adx_14'] >= self.params['adx_strong_trend']) &
            (df['adx_alignment'] == 1) &
            (df['abs_momentum'] >= self.params['trending_momentum_threshold']) &
            (df['relative_volume'] >= self.params['trending_volume_threshold'])
        )
        df.loc[strong_trend_continuation, 'signal'] = 'STRONG_TREND_CONTINUATION'
        
        # ADX Breakout (trend acceleration)
        adx_breakout = (
            (df['daily_adx_14'] >= self.params['adx_very_strong_trend']) &
            (df['intraday_adx_14'] >= self.params['adx_strong_trend']) &
            (abs(df['daily_di_spread']) >= self.params['di_strong_dominance']) &
            (df['abs_momentum'] >= self.params['strong_trend_momentum'])
        )
        df.loc[adx_breakout, 'signal'] = 'ADX_BREAKOUT'
        
        # Trend Reversal Warning
        trend_reversal = (
            (df['daily_adx_14'] >= self.params['adx_moderate_trend']) &
            (df['daily_direction'] != df['intraday_direction']) &
            (df['abs_momentum'] >= 1.0) &
            (df['relative_volume'] >= 2.0)
        )
        df.loc[trend_reversal & (df['signal'] == 'TRENDING'), 'signal'] = 'TREND_REVERSAL'
        
        # Weak Trend Consolidation
        weak_trend = (
            (df['daily_adx_14'] < self.params['adx_moderate_trend']) &
            (df['abs_momentum'] < 1.0)
        )
        df.loc[weak_trend & (df['signal'] == 'TRENDING'), 'signal'] = 'WEAK_TREND'
        
        return df.sort_values('composite_score', ascending=False)
    
    def display_adx_results(self, results: pd.DataFrame, top_n: int = 10):
        """Display ADX enhanced results"""
        if results.empty:
            print("❌ No ADX enhanced candidates found")
            return
        
        print(f"\n📈 STANDALONE ADX ENHANCED SCANNER - TOP {min(top_n, len(results))} PICKS")
        print("=" * 120)
        
        signal_emojis = {
            'STRONG_TREND_CONTINUATION': '🚀',
            'ADX_BREAKOUT': '💥',
            'TREND_REVERSAL': '🔄',
            'WEAK_TREND': '📊',
            'TRENDING': '📈'
        }
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            emoji = signal_emojis.get(row['signal'], '📈')
            direction_emoji = '📈' if row['direction'] == 'BULLISH' else '📉'
            
            print(f"\n{emoji} #{i}: {row['symbol']} | Score: {row['composite_score']:.1f}/100 {direction_emoji}")
            print(f"   💰 Price: ₹{row['opening_price']:.2f} → ₹{row['current_price']:.2f} "
                  f"({row['price_change_pct']:+.2f}%)")
            print(f"   📊 Volume: {row['total_volume_0950']:,.0f} shares "
                  f"({row['relative_volume']:.1f}x avg)")
            
            # ADX Analysis
            daily_trend_str = row['daily_trend_strength']
            intraday_trend_str = row['intraday_trend_strength']
            alignment = "✅ ALIGNED" if row['adx_alignment'] == 1 else "❌ DIVERGENT"
            
            print(f"   📈 ADX Analysis: Daily:{row['daily_adx_14']:.0f}({daily_trend_str}) | "
                  f"Intraday:{row['intraday_adx_14']:.0f}({intraday_trend_str}) | {alignment}")
            
            # Directional Movement
            daily_dir = row['daily_direction']
            intraday_dir = row['intraday_direction']
            di_daily = f"DI+:{row['daily_di_plus']:.0f}/DI-:{row['daily_di_minus']:.0f}"
            di_intraday = f"DI+:{row['intraday_di_plus']:.0f}/DI-:{row['intraday_di_minus']:.0f}"
            
            print(f"   🎯 Direction: Daily:{daily_dir}({di_daily}) | Intraday:{intraday_dir}({di_intraday})")
            
            print(f"   🎯 Signal: {row['signal']}")
            print(f"   📋 Scores: DailyTrend:{row['daily_trend_score']:.0f} IntradayTrend:{row['intraday_trend_score']:.0f} "
                  f"VolTrend:{row['volume_trend_score']:.0f} MomTrend:{row['momentum_trend_score']:.0f}")
        
        # ADX Summary statistics
        print(f"\n📊 ADX ENHANCED SUMMARY:")
        print(f"   📈 Total candidates: {len(results)}")
        print(f"   🎯 Average score: {results['composite_score'].mean():.1f}")
        print(f"   🏆 Top score: {results['composite_score'].max():.1f}")
        
        # Trend strength distribution
        strong_trends = (results['daily_adx_14'] >= self.params['adx_strong_trend']).sum()
        moderate_trends = ((results['daily_adx_14'] >= self.params['adx_moderate_trend']) & 
                          (results['daily_adx_14'] < self.params['adx_strong_trend'])).sum()
        weak_trends = (results['daily_adx_14'] < self.params['adx_moderate_trend']).sum()
        aligned_trends = (results['adx_alignment'] == 1).sum()
        
        print(f"   📈 Trend Strength: Strong:{strong_trends} Moderate:{moderate_trends} Weak:{weak_trends}")
        print(f"   ✅ Multi-timeframe Aligned: {aligned_trends}/{len(results)} ({aligned_trends/len(results)*100:.0f}%)")
        
        # Average ADX values
        avg_daily_adx = results['daily_adx_14'].mean()
        avg_intraday_adx = results['intraday_adx_14'].mean()
        
        print(f"   📊 Average ADX: Daily:{avg_daily_adx:.0f} Intraday:{avg_intraday_adx:.0f}")
        
        # Signal distribution
        signal_counts = results['signal'].value_counts()
        print(f"   📋 ADX Signals: ", end="")
        for signal, count in signal_counts.items():
            emoji = signal_emojis.get(signal, '📈')
            print(f"{emoji}{count} ", end="")
        print()
    
    def scan(self, scan_date: date, top_n: int = 10) -> pd.DataFrame:
        """Run standalone ADX enhanced scan"""
        logger.info(f"🚀 Starting Standalone ADX Enhanced Scanner for {scan_date}")
        
        try:
            # Get ADX enhanced candidates
            candidates = self.get_adx_enhanced_candidates(scan_date)
            
            if candidates.empty:
                logger.warning("⚠️ No ADX enhanced candidates found")
                return pd.DataFrame()
            
            # Calculate ADX enhanced scores
            results = self.calculate_adx_enhanced_scores(candidates)
            
            # Display results
            self.display_adx_results(results, top_n)
            
            # Show top ADX picks
            if not results.empty:
                top_picks = results.head(3)
                print(f"\n🎯 TODAY'S TOP 3 ADX ENHANCED PICKS:")
                for i, (_, pick) in enumerate(top_picks.iterrows(), 1):
                    quality = '💎' if pick['composite_score'] > 75 else '⭐' if pick['composite_score'] > 60 else '📊'
                    trend_strength = pick['daily_trend_strength']
                    alignment = "✅" if pick['adx_alignment'] == 1 else "❌"
                    
                    print(f"   {i}. {pick['symbol']}: {pick['price_change_pct']:+.2f}% "
                          f"({pick['relative_volume']:.1f}x vol) - {pick['signal']} {quality}")
                    print(f"      ADX: Daily:{pick['daily_adx_14']:.0f}({trend_strength}) "
                          f"Aligned:{alignment} Direction:{pick['daily_direction']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during standalone ADX enhanced scan: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        finally:
            self.close_db()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Standalone ADX Enhanced Scanner')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=8,
                       help='Number of top results to display')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        scanner = StandaloneADXScanner()
        results = scanner.scan(scan_date=scan_date, top_n=args.top_n)
        
        if not results.empty:
            print(f"\n✅ Standalone ADX enhanced scan completed! Found {len(results)} opportunities")
            
            # ADX Assessment
            strong_trends = (results['daily_adx_14'] >= 30).sum()
            adx_breakouts = (results['signal'] == 'ADX_BREAKOUT').sum()
            trend_continuations = (results['signal'] == 'STRONG_TREND_CONTINUATION').sum()
            aligned_trends = (results['adx_alignment'] == 1).sum()
            
            print(f"\n📊 ADX ASSESSMENT:")
            print(f"   📈 Strong Daily Trends (ADX≥30): {strong_trends}")
            print(f"   💥 ADX Breakouts: {adx_breakouts}")
            print(f"   🚀 Trend Continuations: {trend_continuations}")
            print(f"   ✅ Multi-timeframe Aligned: {aligned_trends}")
            
            if adx_breakouts > 0:
                print(f"\n💥 EXPECTED PERFORMANCE: ADX breakouts detected - explosive trend moves!")
            elif trend_continuations > 0:
                print(f"\n🚀 EXPECTED PERFORMANCE: Strong trend continuations - follow the trend!")
            elif strong_trends > 0:
                print(f"\n📈 EXPECTED PERFORMANCE: Strong trending environment - momentum plays!")
            else:
                print(f"\n📊 EXPECTED PERFORMANCE: Weak trending environment - range-bound market")
                
        else:
            print(f"\n⚠️ No ADX enhanced opportunities found for {scan_date}")
            
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

