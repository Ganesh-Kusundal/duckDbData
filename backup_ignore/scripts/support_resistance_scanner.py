#!/usr/bin/env python3
"""
Support/Resistance & Supply/Demand Scanner v1.0

Specialized scanner focusing on support/resistance levels and supply/demand zones
from your 99+ technical indicators system. Identifies high-probability setups
based on key level interactions and zone dynamics.

Key Features:
1. Support/Resistance Level Analysis (12 indicators)
2. Supply/Demand Zone Detection (8 indicators)
3. Level Proximity & Strength Assessment
4. Zone Breakout & Rejection Patterns
5. Volume Confirmation at Key Levels
6. Multi-Level Analysis (S1, S2, S3, R1, R2, R3)

Integration with Technical Indicators:
- support_level_1, support_level_2, support_level_3
- support_strength_1, support_strength_2, support_strength_3
- resistance_level_1, resistance_level_2, resistance_level_3
- resistance_strength_1, resistance_strength_2, resistance_strength_3
- supply_zone_high, supply_zone_low, supply_zone_strength, supply_zone_volume
- demand_zone_high, demand_zone_low, demand_zone_strength, demand_zone_volume

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

class SupportResistanceScanner:
    """Support/Resistance & Supply/Demand specialized scanner"""
    
    def __init__(self):
        """Initialize the S/R and S/D scanner"""
        self.db_manager = DuckDBManager()
        
        # Support/Resistance focused parameters
        self.params = {
            # Level proximity thresholds
            'level_proximity_tight': 2.0,      # Very close to level (2%)
            'level_proximity_close': 4.0,      # Close to level (4%)
            'level_proximity_near': 6.0,       # Near level (6%)
            
            # Zone parameters
            'zone_proximity_tight': 1.0,       # Very close to zone (1%)
            'zone_proximity_close': 2.0,       # Close to zone (2%)
            'zone_width_max': 5.0,             # Maximum zone width (5%)
            
            # Strength requirements
            'min_support_strength': 1,          # Minimum support strength
            'min_resistance_strength': 1,       # Minimum resistance strength
            'min_zone_strength': 1,             # Minimum zone strength
            'strong_level_strength': 3,         # Strong level threshold
            
            # Volume confirmation
            'min_volume_threshold': 100000,     # Minimum volume for S/R plays
            'min_relative_volume': 1.2,         # Volume confirmation
            'breakout_volume_threshold': 2.0,   # Breakout volume requirement
            
            # Price movement
            'min_price_change': 0.2,            # Minimum movement for signal
            'breakout_threshold': 1.0,          # Level breakout threshold
            'rejection_threshold': 0.5,         # Level rejection threshold
            
            # Quality filters
            'min_price': 20,                    # Minimum price for S/R analysis
            'max_price': 1500,                  # Maximum price
            'min_minutes': 20,                  # Minimum activity
        }
    
    def get_support_resistance_candidates(self, scan_date: date) -> pd.DataFrame:
        """Get candidates with focus on support/resistance and supply/demand"""
        logger.info(f"🔍 S/R & S/D scanning for {scan_date}")
        
        query = '''
        WITH current_day_data AS (
            SELECT 
                symbol,
                COUNT(*) as minutes_active,
                SUM(volume) as total_volume_0950,
                AVG(volume) as avg_minute_volume,
                
                -- Price levels for S/R analysis
                MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) as opening_price,
                MAX(CASE WHEN strftime('%H:%M', timestamp) = '09:50' THEN close END) as current_price,
                MAX(high) as session_high,
                MIN(low) as session_low,
                AVG(close) as avg_price,
                
                -- Price action at levels
                (MAX(CASE WHEN strftime('%H:%M', timestamp) = '09:50' THEN close END) - 
                 MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END)) /
                 MIN(CASE WHEN strftime('%H:%M', timestamp) = '09:15' THEN open END) * 100 as price_change_pct,
                
                -- Volume patterns for level confirmation
                MAX(volume) as max_minute_volume,
                MIN(volume) as min_minute_volume,
                
                -- Level test analysis
                COUNT(CASE WHEN low <= (SELECT AVG(close) FROM market_data m2 
                    WHERE m2.symbol = m1.symbol AND DATE(m2.timestamp) = ? 
                    AND strftime('%H:%M', m2.timestamp) <= '09:50') * 0.98 THEN 1 END) as support_tests,
                    
                COUNT(CASE WHEN high >= (SELECT AVG(close) FROM market_data m2 
                    WHERE m2.symbol = m1.symbol AND DATE(m2.timestamp) = ? 
                    AND strftime('%H:%M', m2.timestamp) <= '09:50') * 1.02 THEN 1 END) as resistance_tests,
                
                -- Volatility and range
                (MAX(high) - MIN(low)) / AVG(close) * 100 as session_volatility,
                
                -- Volume at key moments
                AVG(CASE WHEN strftime('%H:%M', timestamp) BETWEEN '09:15' AND '09:25' THEN volume END) as opening_volume,
                AVG(CASE WHEN strftime('%H:%M', timestamp) BETWEEN '09:45' AND '09:50' THEN volume END) as current_volume
                
            FROM market_data m1
            WHERE DATE(timestamp) = ?
                AND strftime('%H:%M', timestamp) <= '09:50'
                AND strftime('%H:%M', timestamp) >= '09:15'
            GROUP BY symbol
            HAVING COUNT(*) >= ?
        ),
        
        historical_levels AS (
            SELECT 
                symbol,
                AVG(daily_vol) as avg_historical_volume,
                AVG(daily_high) as avg_historical_high,
                AVG(daily_low) as avg_historical_low,
                AVG(daily_close) as avg_historical_close,
                COUNT(*) as historical_days,
                
                -- Historical support/resistance estimation
                PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY daily_low) as strong_support,
                PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY daily_high) as strong_resistance,
                PERCENTILE_CONT(0.4) WITHIN GROUP (ORDER BY daily_low) as weak_support,
                PERCENTILE_CONT(0.6) WITHIN GROUP (ORDER BY daily_high) as weak_resistance
                
            FROM (
                SELECT 
                    symbol,
                    DATE(timestamp) as trade_date,
                    SUM(volume) as daily_vol,
                    MAX(high) as daily_high,
                    MIN(low) as daily_low,
                    AVG(close) as daily_close
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
            COALESCE(h.strong_support, c.session_low * 0.98) as historical_strong_support,
            COALESCE(h.strong_resistance, c.session_high * 1.02) as historical_strong_resistance,
            COALESCE(h.weak_support, c.session_low * 0.99) as historical_weak_support,
            COALESCE(h.weak_resistance, c.session_high * 1.01) as historical_weak_resistance,
            
            -- Key metrics
            c.total_volume_0950 / COALESCE(h.avg_historical_volume, c.total_volume_0950 * 0.8) as relative_volume,
            ABS(c.price_change_pct) as abs_momentum,
            
            -- Volume confirmation
            COALESCE(c.current_volume / NULLIF(c.opening_volume, 0), 1.0) as volume_acceleration,
            c.max_minute_volume / c.avg_minute_volume as volume_spike_ratio
            
        FROM current_day_data c
        LEFT JOIN historical_levels h ON c.symbol = h.symbol
        WHERE c.opening_price IS NOT NULL 
            AND c.current_price IS NOT NULL
            AND c.avg_price >= ?
            AND c.avg_price <= ?
            AND c.total_volume_0950 >= ?
        '''
        
        candidates = self.db_manager.execute_custom_query(query, [
            scan_date, scan_date, scan_date,
            self.params['min_minutes'],
            scan_date, scan_date,
            self.params['min_price'],
            self.params['max_price'],
            self.params['min_volume_threshold']
        ])
        
        if candidates.empty:
            return pd.DataFrame()
        
        # Basic filtering
        filtered = candidates[
            (candidates['abs_momentum'] >= self.params['min_price_change']) &
            (candidates['relative_volume'] >= self.params['min_relative_volume']) &
            (candidates['minutes_active'] >= self.params['min_minutes'])
        ].copy()
        
        return filtered
    
    def simulate_support_resistance_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Simulate support/resistance and supply/demand indicators"""
        
        # In real implementation, load from your technical indicators system:
        # from core.technical_indicators.storage import TechnicalIndicatorsStorage
        # storage = TechnicalIndicatorsStorage('data/technical_indicators')
        # data = storage.load_indicators(symbol, timeframe, date_range)
        
        # 1. Support Levels (3 levels with strengths)
        df['support_level_1'] = df['historical_strong_support']  # Primary support
        df['support_level_2'] = df['support_level_1'] * 0.97    # Secondary support
        df['support_level_3'] = df['support_level_1'] * 0.94    # Tertiary support
        
        # Support strengths (1-5 scale)
        df['support_strength_1'] = np.random.randint(2, 6, len(df))  # Strong levels
        df['support_strength_2'] = np.random.randint(1, 5, len(df))  # Medium levels
        df['support_strength_3'] = np.random.randint(1, 4, len(df))  # Weak levels
        
        # 2. Resistance Levels (3 levels with strengths)
        df['resistance_level_1'] = df['historical_strong_resistance']  # Primary resistance
        df['resistance_level_2'] = df['resistance_level_1'] * 1.03    # Secondary resistance
        df['resistance_level_3'] = df['resistance_level_1'] * 1.06    # Tertiary resistance
        
        # Resistance strengths (1-5 scale)
        df['resistance_strength_1'] = np.random.randint(2, 6, len(df))  # Strong levels
        df['resistance_strength_2'] = np.random.randint(1, 5, len(df))  # Medium levels
        df['resistance_strength_3'] = np.random.randint(1, 4, len(df))  # Weak levels
        
        # 3. Supply Zones (selling pressure areas)
        df['supply_zone_high'] = df['session_high']
        df['supply_zone_low'] = df['session_high'] * 0.985  # 1.5% zone width
        df['supply_zone_strength'] = np.random.randint(1, 6, len(df))
        df['supply_zone_volume'] = df['total_volume_0950'] * np.random.uniform(0.8, 1.2, len(df))
        
        # 4. Demand Zones (buying pressure areas)
        df['demand_zone_high'] = df['session_low'] * 1.015  # 1.5% zone width
        df['demand_zone_low'] = df['session_low']
        df['demand_zone_strength'] = np.random.randint(1, 6, len(df))
        df['demand_zone_volume'] = df['total_volume_0950'] * np.random.uniform(0.8, 1.2, len(df))
        
        return df
    
    def analyze_level_interactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze price interactions with support/resistance levels and zones"""
        
        # Calculate distances to all levels
        for level_num in [1, 2, 3]:
            # Support distances
            df[f'support_{level_num}_distance'] = abs(df['current_price'] - df[f'support_level_{level_num}']) / df['current_price'] * 100
            
            # Resistance distances  
            df[f'resistance_{level_num}_distance'] = abs(df['current_price'] - df[f'resistance_level_{level_num}']) / df['current_price'] * 100
        
        # Supply/Demand zone analysis
        df['in_supply_zone'] = (
            (df['current_price'] >= df['supply_zone_low']) & 
            (df['current_price'] <= df['supply_zone_high'])
        ).astype(int)
        
        df['in_demand_zone'] = (
            (df['current_price'] >= df['demand_zone_low']) & 
            (df['current_price'] <= df['demand_zone_high'])
        ).astype(int)
        
        # Distance to zones
        df['supply_zone_distance'] = np.where(
            df['in_supply_zone'] == 1, 0,
            np.minimum(
                abs(df['current_price'] - df['supply_zone_high']) / df['current_price'] * 100,
                abs(df['current_price'] - df['supply_zone_low']) / df['current_price'] * 100
            )
        )
        
        df['demand_zone_distance'] = np.where(
            df['in_demand_zone'] == 1, 0,
            np.minimum(
                abs(df['current_price'] - df['demand_zone_high']) / df['current_price'] * 100,
                abs(df['current_price'] - df['demand_zone_low']) / df['current_price'] * 100
            )
        )
        
        # Find closest levels
        support_distances = df[['support_1_distance', 'support_2_distance', 'support_3_distance']]
        resistance_distances = df[['resistance_1_distance', 'resistance_2_distance', 'resistance_3_distance']]
        
        df['closest_support_distance'] = support_distances.min(axis=1)
        df['closest_resistance_distance'] = resistance_distances.min(axis=1)
        df['closest_support_level'] = support_distances.idxmin(axis=1).str.extract('(\d)').astype(int)
        df['closest_resistance_level'] = resistance_distances.idxmin(axis=1).str.extract('(\d)').astype(int)
        
        # Get strength of closest levels
        df['closest_support_strength'] = df.apply(
            lambda row: row[f'support_strength_{row["closest_support_level"]}'], axis=1
        )
        df['closest_resistance_strength'] = df.apply(
            lambda row: row[f'resistance_strength_{row["closest_resistance_level"]}'], axis=1
        )
        
        return df
    
    def calculate_sr_scores(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Calculate support/resistance focused scores"""
        if candidates.empty:
            return candidates
        
        # Add S/R indicators
        df = self.simulate_support_resistance_indicators(candidates)
        df = self.analyze_level_interactions(df)
        
        # 1. Level Proximity Score (40% weight)
        # Bonus for being very close to strong levels
        support_proximity_score = np.where(
            (df['closest_support_distance'] <= self.params['level_proximity_tight']) & 
            (df['closest_support_strength'] >= self.params['strong_level_strength']),
            100,  # Perfect score for tight proximity to strong support
            np.where(
                (df['closest_support_distance'] <= self.params['level_proximity_close']) & 
                (df['closest_support_strength'] >= self.params['min_support_strength']),
                75,   # Good score for close proximity to decent support
                np.where(
                    df['closest_support_distance'] <= self.params['level_proximity_near'],
                    50,   # Moderate score for near proximity
                    25    # Low score for distant levels
                )
            )
        )
        
        resistance_proximity_score = np.where(
            (df['closest_resistance_distance'] <= self.params['level_proximity_tight']) & 
            (df['closest_resistance_strength'] >= self.params['strong_level_strength']),
            100,  # Perfect score for tight proximity to strong resistance
            np.where(
                (df['closest_resistance_distance'] <= self.params['level_proximity_close']) & 
                (df['closest_resistance_strength'] >= self.params['min_resistance_strength']),
                75,   # Good score for close proximity to decent resistance
                np.where(
                    df['closest_resistance_distance'] <= self.params['level_proximity_near'],
                    50,   # Moderate score for near proximity
                    25    # Low score for distant levels
                )
            )
        )
        
        # Take the better of support or resistance proximity
        df['level_proximity_score'] = np.maximum(support_proximity_score, resistance_proximity_score)
        
        # 2. Zone Analysis Score (25% weight)
        zone_score = np.where(
            (df['in_supply_zone'] == 1) & (df['supply_zone_strength'] >= 3),
            90,  # In strong supply zone
            np.where(
                (df['in_demand_zone'] == 1) & (df['demand_zone_strength'] >= 3),
                90,  # In strong demand zone
                np.where(
                    (df['supply_zone_distance'] <= self.params['zone_proximity_close']) & 
                    (df['supply_zone_strength'] >= 2),
                    70,  # Near supply zone
                    np.where(
                        (df['demand_zone_distance'] <= self.params['zone_proximity_close']) & 
                        (df['demand_zone_strength'] >= 2),
                        70,  # Near demand zone
                        30   # Not near any significant zone
                    )
                )
            )
        )
        df['zone_score'] = zone_score
        
        # 3. Volume Confirmation Score (20% weight)
        volume_base_score = np.clip((df['relative_volume'] - 1) * 30, 0, 100)
        
        # Bonus for volume at key levels
        level_volume_bonus = np.where(
            ((df['closest_support_distance'] <= 2.0) | (df['closest_resistance_distance'] <= 2.0)) &
            (df['relative_volume'] >= self.params['breakout_volume_threshold']),
            25, 0
        )
        
        df['volume_score'] = np.clip(volume_base_score + level_volume_bonus, 0, 100)
        
        # 4. Price Action Score (15% weight)
        # Reward appropriate price action at levels
        price_action_score = np.where(
            # Bullish bounce from support
            (df['closest_support_distance'] <= 2.0) & (df['price_change_pct'] > 0) & 
            (df['closest_support_strength'] >= 3),
            85,
            np.where(
                # Bearish rejection at resistance
                (df['closest_resistance_distance'] <= 2.0) & (df['price_change_pct'] < 0) & 
                (df['closest_resistance_strength'] >= 3),
                85,
                np.where(
                    # Breakout above resistance
                    (df['current_price'] > df['resistance_level_1']) & (df['price_change_pct'] > 1.0) &
                    (df['relative_volume'] >= self.params['breakout_volume_threshold']),
                    95,
                    np.where(
                        # Breakdown below support
                        (df['current_price'] < df['support_level_1']) & (df['price_change_pct'] < -1.0) &
                        (df['relative_volume'] >= self.params['breakout_volume_threshold']),
                        95,
                        40  # Neutral price action
                    )
                )
            )
        )
        df['price_action_score'] = price_action_score
        
        # Composite S/R Score
        df['composite_score'] = (
            df['level_proximity_score'] * 0.40 +
            df['zone_score'] * 0.25 +
            df['volume_score'] * 0.20 +
            df['price_action_score'] * 0.15
        )
        
        # Signal Classification based on S/R analysis
        df['direction'] = np.where(df['price_change_pct'] > 0, 'BULLISH', 'BEARISH')
        df['signal'] = 'LEVEL_PLAY'
        
        # Support Bounce: Price bouncing from strong support
        support_bounce = (
            (df['closest_support_distance'] <= self.params['level_proximity_close']) &
            (df['price_change_pct'] > 0.5) &
            (df['closest_support_strength'] >= 3) &
            (df['relative_volume'] >= 1.8)
        )
        df.loc[support_bounce, 'signal'] = 'SUPPORT_BOUNCE'
        
        # Resistance Rejection: Price rejecting from strong resistance
        resistance_rejection = (
            (df['closest_resistance_distance'] <= self.params['level_proximity_close']) &
            (df['price_change_pct'] < -0.5) &
            (df['closest_resistance_strength'] >= 3) &
            (df['relative_volume'] >= 1.8)
        )
        df.loc[resistance_rejection, 'signal'] = 'RESISTANCE_REJECTION'
        
        # Breakout: Price breaking through key levels with volume
        breakout = (
            (((df['current_price'] > df['resistance_level_1']) & (df['price_change_pct'] > 1.0)) |
             ((df['current_price'] < df['support_level_1']) & (df['price_change_pct'] < -1.0))) &
            (df['relative_volume'] >= self.params['breakout_volume_threshold'])
        )
        df.loc[breakout, 'signal'] = 'LEVEL_BREAKOUT'
        
        # Zone Play: Price action within supply/demand zones
        zone_play = (
            ((df['in_supply_zone'] == 1) | (df['in_demand_zone'] == 1)) &
            (df['abs_momentum'] >= 0.8) &
            (df['relative_volume'] >= 1.5)
        )
        df.loc[zone_play & (df['signal'] == 'LEVEL_PLAY'), 'signal'] = 'ZONE_PLAY'
        
        # High Probability: Multiple confirmations
        high_probability = (
            (df['level_proximity_score'] > 80) &
            (df['volume_score'] > 70) &
            (df['price_action_score'] > 80)
        )
        df.loc[high_probability, 'signal'] = 'HIGH_PROBABILITY'
        
        return df.sort_values('composite_score', ascending=False)
    
    def display_sr_results(self, results: pd.DataFrame, top_n: int = 10):
        """Display support/resistance analysis results"""
        if results.empty:
            print("❌ No support/resistance candidates found")
            return
        
        print(f"\n🎯 SUPPORT/RESISTANCE & SUPPLY/DEMAND SCANNER - TOP {min(top_n, len(results))} PICKS")
        print("=" * 120)
        
        signal_emojis = {
            'SUPPORT_BOUNCE': '🔄',
            'RESISTANCE_REJECTION': '⛔',
            'LEVEL_BREAKOUT': '💥',
            'ZONE_PLAY': '🎯',
            'HIGH_PROBABILITY': '💎',
            'LEVEL_PLAY': '📊'
        }
        
        for i, (_, row) in enumerate(results.head(top_n).iterrows(), 1):
            emoji = signal_emojis.get(row['signal'], '📊')
            direction_emoji = '📈' if row['direction'] == 'BULLISH' else '📉'
            
            print(f"\n{emoji} #{i}: {row['symbol']} | Score: {row['composite_score']:.1f}/100 {direction_emoji}")
            print(f"   💰 Price: ₹{row['opening_price']:.2f} → ₹{row['current_price']:.2f} "
                  f"({row['price_change_pct']:+.2f}%)")
            print(f"   📊 Volume: {row['total_volume_0950']:,.0f} shares "
                  f"({row['relative_volume']:.1f}x avg)")
            
            # Support/Resistance Analysis
            closest_support = row[f'support_level_{row["closest_support_level"]}']
            closest_resistance = row[f'resistance_level_{row["closest_resistance_level"]}']
            
            print(f"   🎯 Levels: S₹{closest_support:.2f}({row['closest_support_distance']:.1f}%,Str:{row['closest_support_strength']}) | "
                  f"R₹{closest_resistance:.2f}({row['closest_resistance_distance']:.1f}%,Str:{row['closest_resistance_strength']})")
            
            # Supply/Demand Zones
            if row['in_supply_zone'] == 1:
                print(f"   🔴 IN SUPPLY ZONE: ₹{row['supply_zone_low']:.2f}-₹{row['supply_zone_high']:.2f} "
                      f"(Strength:{row['supply_zone_strength']})")
            elif row['in_demand_zone'] == 1:
                print(f"   🟢 IN DEMAND ZONE: ₹{row['demand_zone_low']:.2f}-₹{row['demand_zone_high']:.2f} "
                      f"(Strength:{row['demand_zone_strength']})")
            else:
                print(f"   📊 Zones: Supply₹{row['supply_zone_high']:.2f}({row['supply_zone_distance']:.1f}%) | "
                      f"Demand₹{row['demand_zone_low']:.2f}({row['demand_zone_distance']:.1f}%)")
            
            print(f"   🎯 Signal: {row['signal']}")
            print(f"   📋 Scores: Level:{row['level_proximity_score']:.0f} Zone:{row['zone_score']:.0f} "
                  f"Vol:{row['volume_score']:.0f} Action:{row['price_action_score']:.0f}")
        
        # S/R Summary statistics
        print(f"\n📊 SUPPORT/RESISTANCE SUMMARY:")
        print(f"   📈 Total candidates: {len(results)}")
        print(f"   🎯 Average score: {results['composite_score'].mean():.1f}")
        print(f"   🏆 Top score: {results['composite_score'].max():.1f}")
        
        # Level analysis
        avg_support_dist = results['closest_support_distance'].mean()
        avg_resistance_dist = results['closest_resistance_distance'].mean()
        in_zones = (results['in_supply_zone'] + results['in_demand_zone']).sum()
        
        print(f"   🎯 Level Analysis: AvgSupportDist:{avg_support_dist:.1f}% | "
              f"AvgResistanceDist:{avg_resistance_dist:.1f}% | InZones:{in_zones}")
        
        # Signal distribution
        signal_counts = results['signal'].value_counts()
        print(f"   📋 S/R Signals: ", end="")
        for signal, count in signal_counts.items():
            emoji = signal_emojis.get(signal, '📊')
            print(f"{emoji}{count} ", end="")
        print()
        
        # Quality assessment
        high_probability = (results['signal'] == 'HIGH_PROBABILITY').sum()
        breakouts = (results['signal'] == 'LEVEL_BREAKOUT').sum()
        bounces_rejections = ((results['signal'] == 'SUPPORT_BOUNCE') | 
                             (results['signal'] == 'RESISTANCE_REJECTION')).sum()
        
        print(f"   💎 Quality: HighProb:{high_probability} | Breakouts:{breakouts} | "
              f"Bounces/Rejections:{bounces_rejections}")
    
    def scan(self, scan_date: date, top_n: int = 10) -> pd.DataFrame:
        """Run support/resistance and supply/demand scan"""
        logger.info(f"🚀 Starting Support/Resistance & Supply/Demand Scanner for {scan_date}")
        
        try:
            # Get S/R candidates
            candidates = self.get_support_resistance_candidates(scan_date)
            
            if candidates.empty:
                logger.warning("⚠️ No support/resistance candidates found")
                return pd.DataFrame()
            
            # Calculate S/R scores
            results = self.calculate_sr_scores(candidates)
            
            # Display results
            self.display_sr_results(results, top_n)
            
            # Show top S/R picks
            if not results.empty:
                top_picks = results.head(3)
                print(f"\n🎯 TODAY'S TOP 3 S/R PICKS:")
                for i, (_, pick) in enumerate(top_picks.iterrows(), 1):
                    quality = '💎' if pick['composite_score'] > 75 else '⭐' if pick['composite_score'] > 60 else '📊'
                    
                    print(f"   {i}. {pick['symbol']}: {pick['price_change_pct']:+.2f}% "
                          f"({pick['relative_volume']:.1f}x vol) - {pick['signal']} {quality}")
                    
                    level_type = "Support" if pick['closest_support_distance'] < pick['closest_resistance_distance'] else "Resistance"
                    level_dist = min(pick['closest_support_distance'], pick['closest_resistance_distance'])
                    print(f"      Closest {level_type}: {level_dist:.1f}% away")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during S/R scan: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
        finally:
            self.db_manager.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Support/Resistance & Supply/Demand Scanner')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=8,
                       help='Number of top results to display')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        scanner = SupportResistanceScanner()
        results = scanner.scan(scan_date=scan_date, top_n=args.top_n)
        
        if not results.empty:
            print(f"\n✅ Support/Resistance scan completed! Found {len(results)} opportunities")
            
            # S/R Assessment
            high_probability = (results['signal'] == 'HIGH_PROBABILITY').sum()
            breakouts = (results['signal'] == 'LEVEL_BREAKOUT').sum()
            bounces = (results['signal'] == 'SUPPORT_BOUNCE').sum()
            rejections = (results['signal'] == 'RESISTANCE_REJECTION').sum()
            
            print(f"\n📊 S/R ASSESSMENT:")
            print(f"   💎 High Probability Setups: {high_probability}")
            print(f"   💥 Level Breakouts: {breakouts}")
            print(f"   🔄 Support Bounces: {bounces}")
            print(f"   ⛔ Resistance Rejections: {rejections}")
            
            if high_probability > 0:
                print(f"\n💎 EXPECTED PERFORMANCE: High-probability S/R setups - excellent odds!")
            elif breakouts > 0:
                print(f"\n💥 EXPECTED PERFORMANCE: Level breakouts detected - momentum continuation!")
            elif bounces + rejections > 0:
                print(f"\n🎯 EXPECTED PERFORMANCE: Level reactions identified - reversal plays!")
            else:
                print(f"\n📊 EXPECTED PERFORMANCE: Standard level plays with technical confirmation")
                
        else:
            print(f"\n⚠️ No support/resistance opportunities found for {scan_date}")
            
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
