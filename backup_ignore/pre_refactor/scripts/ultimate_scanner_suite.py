#!/usr/bin/env python3
"""
Ultimate Scanner Suite v1.0

Complete scanner suite integrating ALL scanner types with your 99+ technical indicators:
1. Momentum Scanner (Original)
2. Enhanced Momentum Scanner
3. Support/Resistance Scanner
4. ADX Enhanced Scanner (NEW)
5. Ultimate Consensus Analysis

Features:
- Multi-scanner consensus with ADX confirmation
- Daily ADX trend strength analysis
- Support/Resistance level integration
- Supply/Demand zone analysis
- Professional signal classification
- Risk-adjusted recommendations

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
from datetime import datetime, date
import argparse

# Import all scanners
from scripts.optimized_momentum_scanner import OptimizedMomentumScanner
from scripts.enhanced_momentum_scanner import EnhancedMomentumScanner
from scripts.support_resistance_scanner import SupportResistanceScanner
from scripts.adx_enhanced_scanner import ADXEnhancedScanner

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

class UltimateScannerSuite:
    """Ultimate scanner suite with all analysis types including ADX"""
    
    def __init__(self):
        """Initialize all scanners"""
        self.scanners = {
            'Momentum': OptimizedMomentumScanner(),
            'Enhanced': EnhancedMomentumScanner(),
            'SupportResistance': SupportResistanceScanner(),
            'ADX': ADXEnhancedScanner()
        }
        
        # Ultimate consensus parameters
        self.consensus_params = {
            'min_scanners_agreement': 2,        # Minimum scanners for consensus
            'momentum_weight': 0.25,            # Momentum scanner weight
            'enhanced_weight': 0.25,            # Enhanced scanner weight
            'sr_weight': 0.25,                  # S/R scanner weight
            'adx_weight': 0.25,                 # ADX scanner weight
            'consensus_bonus': 20,              # Bonus for multi-scanner agreement
            'adx_confirmation_bonus': 15,       # Bonus for ADX trend confirmation
        }
    
    def run_all_scanners(self, scan_date: date, top_n: int = 10):
        """Run all scanners including ADX enhanced"""
        print(f"🚀 ULTIMATE SCANNER SUITE FOR {scan_date}")
        print("=" * 80)
        
        all_results = {}
        
        # Run each scanner with proper connection management
        for name, scanner in self.scanners.items():
            print(f"\n📊 Running {name} Scanner...")
            try:
                # Ensure any existing connections are closed
                if hasattr(scanner, 'db_manager') and hasattr(scanner.db_manager, 'connection'):
                    try:
                        scanner.db_manager.close()
                    except:
                        pass
                
                results = scanner.scan(scan_date, top_n * 2)  # Get more for analysis
                all_results[name] = results
                
                # Force close connection after scan
                if hasattr(scanner, 'db_manager'):
                    try:
                        scanner.db_manager.close()
                    except:
                        pass
                
                if not results.empty:
                    print(f"   ✅ Found {len(results)} candidates")
                    print(f"   🏆 Top score: {results['composite_score'].max():.1f}")
                    print(f"   📊 Avg score: {results['composite_score'].mean():.1f}")
                    
                    # Show top signals
                    top_signals = results['signal'].value_counts().head(3)
                    print(f"   🎯 Top signals: {dict(top_signals)}")
                    
                    # ADX specific info
                    if name == 'ADX' and 'daily_adx_14' in results.columns:
                        strong_trends = (results['daily_adx_14'] >= 30).sum()
                        aligned = (results['adx_alignment'] == 1).sum() if 'adx_alignment' in results.columns else 0
                        print(f"   📈 Strong trends: {strong_trends} | Aligned: {aligned}")
                else:
                    print(f"   ❌ No candidates found")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                all_results[name] = pd.DataFrame()
                
                # Ensure connection is closed even on error
                if hasattr(scanner, 'db_manager'):
                    try:
                        scanner.db_manager.close()
                    except:
                        pass
        
        return all_results
    
    def create_ultimate_consensus(self, all_results: dict, scan_date: date) -> pd.DataFrame:
        """Create ultimate consensus analysis from all scanners including ADX"""
        
        # Collect all unique symbols
        all_symbols = set()
        for results in all_results.values():
            if not results.empty:
                all_symbols.update(results['symbol'].tolist())
        
        if not all_symbols:
            return pd.DataFrame()
        
        consensus_data = []
        
        for symbol in all_symbols:
            row = {'symbol': symbol}
            
            # Collect data from each scanner
            scanner_scores = []
            scanner_signals = []
            scanner_returns = []
            scanner_volumes = []
            scanner_count = 0
            
            # Momentum Scanner
            if not all_results['Momentum'].empty and symbol in all_results['Momentum']['symbol'].values:
                momentum_data = all_results['Momentum'][all_results['Momentum']['symbol'] == symbol].iloc[0]
                row['momentum_score'] = momentum_data['composite_score']
                row['momentum_signal'] = momentum_data['signal']
                row['momentum_return'] = momentum_data['price_change_pct']
                row['momentum_volume'] = momentum_data['relative_volume']
                row['momentum_rank'] = all_results['Momentum'][all_results['Momentum']['symbol'] == symbol].index[0] + 1
                scanner_scores.append(momentum_data['composite_score'])
                scanner_signals.append(momentum_data['signal'])
                scanner_returns.append(momentum_data['price_change_pct'])
                scanner_volumes.append(momentum_data['relative_volume'])
                scanner_count += 1
            else:
                row['momentum_score'] = 0
                row['momentum_signal'] = 'NONE'
                row['momentum_return'] = 0
                row['momentum_volume'] = 0
                row['momentum_rank'] = 999
            
            # Enhanced Scanner
            if not all_results['Enhanced'].empty and symbol in all_results['Enhanced']['symbol'].values:
                enhanced_data = all_results['Enhanced'][all_results['Enhanced']['symbol'] == symbol].iloc[0]
                row['enhanced_score'] = enhanced_data['composite_score']
                row['enhanced_signal'] = enhanced_data['signal']
                row['enhanced_return'] = enhanced_data['price_change_pct']
                row['enhanced_volume'] = enhanced_data['relative_volume']
                row['enhanced_rank'] = all_results['Enhanced'][all_results['Enhanced']['symbol'] == symbol].index[0] + 1
                scanner_scores.append(enhanced_data['composite_score'])
                scanner_signals.append(enhanced_data['signal'])
                scanner_returns.append(enhanced_data['price_change_pct'])
                scanner_volumes.append(enhanced_data['relative_volume'])
                scanner_count += 1
            else:
                row['enhanced_score'] = 0
                row['enhanced_signal'] = 'NONE'
                row['enhanced_return'] = 0
                row['enhanced_volume'] = 0
                row['enhanced_rank'] = 999
            
            # Support/Resistance Scanner
            if not all_results['SupportResistance'].empty and symbol in all_results['SupportResistance']['symbol'].values:
                sr_data = all_results['SupportResistance'][all_results['SupportResistance']['symbol'] == symbol].iloc[0]
                row['sr_score'] = sr_data['composite_score']
                row['sr_signal'] = sr_data['signal']
                row['sr_return'] = sr_data['price_change_pct']
                row['sr_volume'] = sr_data['relative_volume']
                row['sr_rank'] = all_results['SupportResistance'][all_results['SupportResistance']['symbol'] == symbol].index[0] + 1
                scanner_scores.append(sr_data['composite_score'])
                scanner_signals.append(sr_data['signal'])
                scanner_returns.append(sr_data['price_change_pct'])
                scanner_volumes.append(sr_data['relative_volume'])
                scanner_count += 1
            else:
                row['sr_score'] = 0
                row['sr_signal'] = 'NONE'
                row['sr_return'] = 0
                row['sr_volume'] = 0
                row['sr_rank'] = 999
            
            # ADX Enhanced Scanner
            if not all_results['ADX'].empty and symbol in all_results['ADX']['symbol'].values:
                adx_data = all_results['ADX'][all_results['ADX']['symbol'] == symbol].iloc[0]
                row['adx_score'] = adx_data['composite_score']
                row['adx_signal'] = adx_data['signal']
                row['adx_return'] = adx_data['price_change_pct']
                row['adx_volume'] = adx_data['relative_volume']
                row['adx_rank'] = all_results['ADX'][all_results['ADX']['symbol'] == symbol].index[0] + 1
                
                # ADX specific metrics
                if 'daily_adx_14' in adx_data:
                    row['daily_adx'] = adx_data['daily_adx_14']
                    row['daily_trend_strength'] = adx_data['daily_trend_strength']
                    row['adx_aligned'] = adx_data.get('adx_alignment', 0)
                    row['daily_direction'] = adx_data.get('daily_direction', 'NEUTRAL')
                else:
                    row['daily_adx'] = 20
                    row['daily_trend_strength'] = 'MODERATE'
                    row['adx_aligned'] = 0
                    row['daily_direction'] = 'NEUTRAL'
                
                scanner_scores.append(adx_data['composite_score'])
                scanner_signals.append(adx_data['signal'])
                scanner_returns.append(adx_data['price_change_pct'])
                scanner_volumes.append(adx_data['relative_volume'])
                scanner_count += 1
            else:
                row['adx_score'] = 0
                row['adx_signal'] = 'NONE'
                row['adx_return'] = 0
                row['adx_volume'] = 0
                row['adx_rank'] = 999
                row['daily_adx'] = 20
                row['daily_trend_strength'] = 'WEAK'
                row['adx_aligned'] = 0
                row['daily_direction'] = 'NEUTRAL'
            
            # Calculate ultimate consensus metrics
            row['scanner_count'] = scanner_count
            row['avg_score'] = np.mean(scanner_scores) if scanner_scores else 0
            row['max_score'] = max(scanner_scores) if scanner_scores else 0
            row['avg_return'] = np.mean(scanner_returns) if scanner_returns else 0
            row['avg_volume'] = np.mean(scanner_volumes) if scanner_volumes else 0
            
            # Ultimate weighted consensus score
            weighted_score = (
                row['momentum_score'] * self.consensus_params['momentum_weight'] +
                row['enhanced_score'] * self.consensus_params['enhanced_weight'] +
                row['sr_score'] * self.consensus_params['sr_weight'] +
                row['adx_score'] * self.consensus_params['adx_weight']
            )
            
            # Consensus bonuses
            if scanner_count >= self.consensus_params['min_scanners_agreement']:
                weighted_score += self.consensus_params['consensus_bonus']
            
            # ADX confirmation bonus
            if row['daily_adx'] >= 25 and row['adx_aligned'] == 1:
                weighted_score += self.consensus_params['adx_confirmation_bonus']
            
            row['ultimate_consensus_score'] = weighted_score
            
            # Ultimate signal classification
            strong_signals = ['STRONG_BULLISH', 'STRONG_BEARISH', 'TECHNICAL_BREAKOUT', 
                            'LEVEL_BREAKOUT', 'HIGH_PROBABILITY', 'SUPPORT_BOUNCE', 
                            'RESISTANCE_REJECTION', 'ADX_BREAKOUT', 'STRONG_TREND_CONTINUATION']
            
            signal_strength = sum(1 for sig in scanner_signals if sig in strong_signals)
            adx_confirmation = row['daily_adx'] >= 25 and row['adx_aligned'] == 1
            
            if scanner_count >= 4 and signal_strength >= 2 and adx_confirmation:
                row['ultimate_signal'] = 'ULTIMATE_CONSENSUS'
            elif scanner_count >= 3 and signal_strength >= 2:
                row['ultimate_signal'] = 'TRIPLE_CONSENSUS'
            elif scanner_count >= 3 and adx_confirmation:
                row['ultimate_signal'] = 'ADX_CONFIRMED'
            elif scanner_count >= 2 and signal_strength >= 1:
                row['ultimate_signal'] = 'DUAL_CONSENSUS'
            elif scanner_count >= 2:
                row['ultimate_signal'] = 'MULTI_SCANNER'
            else:
                row['ultimate_signal'] = 'SINGLE_SCANNER'
            
            consensus_data.append(row)
        
        # Create DataFrame and sort by ultimate consensus score
        consensus_df = pd.DataFrame(consensus_data)
        consensus_df = consensus_df.sort_values('ultimate_consensus_score', ascending=False)
        
        return consensus_df
    
    def display_ultimate_results(self, consensus_df: pd.DataFrame, top_n: int = 10):
        """Display ultimate consensus analysis results"""
        if consensus_df.empty:
            print("❌ No ultimate consensus analysis available")
            return
        
        print(f"\n🏆 ULTIMATE CONSENSUS ANALYSIS - TOP {min(top_n, len(consensus_df))} PICKS")
        print("=" * 130)
        
        ultimate_emojis = {
            'ULTIMATE_CONSENSUS': '👑',
            'TRIPLE_CONSENSUS': '🔥',
            'ADX_CONFIRMED': '📈',
            'DUAL_CONSENSUS': '⚡',
            'MULTI_SCANNER': '📊',
            'SINGLE_SCANNER': '📈'
        }
        
        for i, (_, row) in enumerate(consensus_df.head(top_n).iterrows(), 1):
            emoji = ultimate_emojis.get(row['ultimate_signal'], '📊')
            direction_emoji = '📈' if row['avg_return'] > 0 else '📉'
            
            print(f"\n{emoji} #{i}: {row['symbol']} | Ultimate Score: {row['ultimate_consensus_score']:.1f} {direction_emoji}")
            print(f"   💰 Avg Return: {row['avg_return']:+.2f}% | Avg Volume: {row['avg_volume']:.1f}x")
            print(f"   📊 Scanner Agreement: {row['scanner_count']}/4 scanners")
            
            # ADX Analysis
            adx_status = "✅ STRONG" if row['daily_adx'] >= 30 else "📊 MODERATE" if row['daily_adx'] >= 25 else "📉 WEAK"
            alignment = "✅ ALIGNED" if row['adx_aligned'] == 1 else "❌ DIVERGENT"
            print(f"   📈 ADX: {row['daily_adx']:.0f}({adx_status}) | {row['daily_trend_strength']} | {alignment} | {row['daily_direction']}")
            
            # Individual scanner results
            scanner_results = []
            if row['momentum_score'] > 0:
                scanner_results.append(f"Mom:#{row['momentum_rank']}({row['momentum_score']:.0f},{row['momentum_signal']})")
            if row['enhanced_score'] > 0:
                scanner_results.append(f"Enh:#{row['enhanced_rank']}({row['enhanced_score']:.0f},{row['enhanced_signal']})")
            if row['sr_score'] > 0:
                scanner_results.append(f"S/R:#{row['sr_rank']}({row['sr_score']:.0f},{row['sr_signal']})")
            if row['adx_score'] > 0:
                scanner_results.append(f"ADX:#{row['adx_rank']}({row['adx_score']:.0f},{row['adx_signal']})")
            
            print(f"   🔍 Scanner Details: {' | '.join(scanner_results)}")
            print(f"   🎯 Ultimate Signal: {row['ultimate_signal']}")
        
        # Ultimate summary
        print(f"\n📊 ULTIMATE SUMMARY:")
        print(f"   📈 Total symbols analyzed: {len(consensus_df)}")
        print(f"   🎯 Average ultimate score: {consensus_df['ultimate_consensus_score'].mean():.1f}")
        print(f"   🏆 Top ultimate score: {consensus_df['ultimate_consensus_score'].max():.1f}")
        
        # Ultimate agreement analysis
        ultimate_consensus = (consensus_df['ultimate_signal'] == 'ULTIMATE_CONSENSUS').sum()
        triple_consensus = (consensus_df['ultimate_signal'] == 'TRIPLE_CONSENSUS').sum()
        adx_confirmed = (consensus_df['ultimate_signal'] == 'ADX_CONFIRMED').sum()
        dual_consensus = (consensus_df['ultimate_signal'] == 'DUAL_CONSENSUS').sum()
        
        print(f"   👑 Ultimate Consensus: {ultimate_consensus}")
        print(f"   🔥 Triple Consensus: {triple_consensus}")
        print(f"   📈 ADX Confirmed: {adx_confirmed}")
        print(f"   ⚡ Dual Consensus: {dual_consensus}")
        
        # Scanner participation
        momentum_picks = (consensus_df['momentum_score'] > 0).sum()
        enhanced_picks = (consensus_df['enhanced_score'] > 0).sum()
        sr_picks = (consensus_df['sr_score'] > 0).sum()
        adx_picks = (consensus_df['adx_score'] > 0).sum()
        
        print(f"   📋 Scanner Participation: Mom:{momentum_picks} Enh:{enhanced_picks} S/R:{sr_picks} ADX:{adx_picks}")
        
        # ADX trend analysis
        strong_adx = (consensus_df['daily_adx'] >= 30).sum()
        moderate_adx = ((consensus_df['daily_adx'] >= 25) & (consensus_df['daily_adx'] < 30)).sum()
        aligned_adx = (consensus_df['adx_aligned'] == 1).sum()
        
        print(f"   📈 ADX Analysis: Strong:{strong_adx} Moderate:{moderate_adx} Aligned:{aligned_adx}")
    
    def generate_ultimate_recommendations(self, consensus_df: pd.DataFrame):
        """Generate ultimate recommendations based on comprehensive analysis"""
        if consensus_df.empty:
            print("\n❌ No ultimate recommendations available")
            return
        
        print(f"\n👑 ULTIMATE RECOMMENDATIONS:")
        print("=" * 70)
        
        # Ultimate consensus picks
        ultimate_picks = consensus_df[consensus_df['ultimate_signal'] == 'ULTIMATE_CONSENSUS']
        
        if not ultimate_picks.empty:
            print(f"👑 ULTIMATE CONSENSUS PICKS (Highest Confidence):")
            for i, (_, pick) in enumerate(ultimate_picks.head(3).iterrows(), 1):
                print(f"   {i}. {pick['symbol']}: {pick['avg_return']:+.2f}% - 👑 ULTIMATE CONFIDENCE")
                print(f"      Score: {pick['ultimate_consensus_score']:.1f} | Scanners: {pick['scanner_count']}/4 | "
                      f"ADX: {pick['daily_adx']:.0f}({pick['daily_trend_strength']})")
        
        # Triple consensus with ADX
        triple_adx = consensus_df[
            (consensus_df['ultimate_signal'] == 'TRIPLE_CONSENSUS') | 
            (consensus_df['ultimate_signal'] == 'ADX_CONFIRMED')
        ]
        if not triple_adx.empty:
            print(f"\n🔥 HIGH CONFIDENCE PICKS:")
            for i, (_, pick) in enumerate(triple_adx.head(3).iterrows(), 1):
                confidence = "🔥 TRIPLE" if pick['ultimate_signal'] == 'TRIPLE_CONSENSUS' else "📈 ADX CONFIRMED"
                print(f"   {i}. {pick['symbol']}: {pick['avg_return']:+.2f}% - {confidence}")
                print(f"      Score: {pick['ultimate_consensus_score']:.1f} | ADX: {pick['daily_adx']:.0f}")
        
        # Strong ADX trends
        strong_trends = consensus_df[consensus_df['daily_adx'] >= 30].head(3)
        if not strong_trends.empty:
            print(f"\n📈 STRONG TREND PLAYS (ADX ≥ 30):")
            for i, (_, pick) in enumerate(strong_trends.iterrows(), 1):
                print(f"   {i}. {pick['symbol']}: {pick['avg_return']:+.2f}% "
                      f"(ADX: {pick['daily_adx']:.0f}, Direction: {pick['daily_direction']})")
        
        # Risk assessment
        print(f"\n🛡️ ULTIMATE RISK ASSESSMENT:")
        high_consensus = (consensus_df['ultimate_consensus_score'] > 80).sum()
        strong_adx_count = (consensus_df['daily_adx'] >= 30).sum()
        aligned_count = (consensus_df['adx_aligned'] == 1).sum()
        
        if high_consensus > 0:
            print(f"   ✅ {high_consensus} ultimate high-consensus opportunities (lowest risk)")
        if strong_adx_count > 0:
            print(f"   📈 {strong_adx_count} strong trending opportunities (trend following)")
        if aligned_count > 0:
            print(f"   🎯 {aligned_count} multi-timeframe aligned setups (higher probability)")
        
        # Market condition with ADX
        avg_return = consensus_df['avg_return'].mean()
        avg_adx = consensus_df['daily_adx'].mean()
        bullish_count = (consensus_df['avg_return'] > 0).sum()
        bearish_count = (consensus_df['avg_return'] < 0).sum()
        
        print(f"\n📊 ULTIMATE MARKET CONDITION:")
        print(f"   📈 Bullish signals: {bullish_count}")
        print(f"   📉 Bearish signals: {bearish_count}")
        print(f"   ⚖️ Average return: {avg_return:+.2f}%")
        print(f"   📈 Average ADX: {avg_adx:.0f}")
        
        if avg_adx >= 30:
            print(f"   🚀 STRONG TRENDING MARKET - Follow momentum and ADX signals")
        elif avg_adx >= 25:
            print(f"   📈 MODERATE TRENDING MARKET - Favor trend-following strategies")
        else:
            print(f"   📊 RANGE-BOUND MARKET - Focus on S/R levels and high-consensus picks")
    
    def run_ultimate_analysis(self, scan_date: date, top_n: int = 10):
        """Run ultimate scanner suite analysis"""
        logger.info(f"🚀 Starting Ultimate Scanner Suite for {scan_date}")
        
        try:
            # Run all scanners
            all_results = self.run_all_scanners(scan_date, top_n)
            
            # Create ultimate consensus analysis
            consensus_df = self.create_ultimate_consensus(all_results, scan_date)
            
            # Display results
            if not consensus_df.empty:
                self.display_ultimate_results(consensus_df, top_n)
                self.generate_ultimate_recommendations(consensus_df)
            else:
                print("\n❌ No ultimate consensus analysis possible - insufficient data")
            
            return consensus_df
            
        except Exception as e:
            logger.error(f"❌ Error in ultimate analysis: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Ultimate Scanner Suite')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=8,
                       help='Number of top results to display')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        suite = UltimateScannerSuite()
        results = suite.run_ultimate_analysis(scan_date=scan_date, top_n=args.top_n)
        
        if not results.empty:
            print(f"\n✅ Ultimate scanner suite analysis completed!")
            print(f"📊 Analyzed {len(results)} symbols across 4 scanner types")
            
            # Ultimate summary
            ultimate_consensus = (results['ultimate_signal'] == 'ULTIMATE_CONSENSUS').sum()
            high_confidence = (results['ultimate_signal'].isin(['ULTIMATE_CONSENSUS', 'TRIPLE_CONSENSUS', 'ADX_CONFIRMED'])).sum()
            strong_adx = (results['daily_adx'] >= 30).sum()
            
            print(f"👑 Ultimate consensus opportunities: {ultimate_consensus}")
            print(f"🎯 High confidence opportunities: {high_confidence}")
            print(f"📈 Strong ADX trends: {strong_adx}")
            
        else:
            print(f"\n⚠️ Ultimate scanner suite found limited opportunities for {scan_date}")
            
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
