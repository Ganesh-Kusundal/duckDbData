#!/usr/bin/env python3
"""
Complete Scanner Suite v1.0

Comprehensive scanner suite that runs all scanner types and provides
a unified analysis using your 99+ technical indicators system.

Scanner Types:
1. Momentum Scanner (Original)
2. Enhanced Momentum Scanner  
3. Support/Resistance Scanner (NEW)
4. Combined Technical Analysis

Integration Features:
- Support & Resistance Levels (12 indicators)
- Supply & Demand Zones (8 indicators)
- Momentum & Volume Analysis
- Multi-scanner consensus
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

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

class CompleteScannerSuite:
    """Complete scanner suite with all analysis types"""
    
    def __init__(self):
        """Initialize all scanners"""
        self.scanners = {
            'Momentum': OptimizedMomentumScanner(),
            'Enhanced': EnhancedMomentumScanner(),
            'SupportResistance': SupportResistanceScanner()
        }
        
        # Consensus parameters
        self.consensus_params = {
            'min_scanners_agreement': 2,        # Minimum scanners for consensus
            'momentum_weight': 0.35,            # Momentum scanner weight
            'enhanced_weight': 0.35,            # Enhanced scanner weight
            'sr_weight': 0.30,                  # S/R scanner weight
            'consensus_bonus': 15,              # Bonus for multi-scanner agreement
        }
    
    def run_all_scanners(self, scan_date: date, top_n: int = 10):
        """Run all scanners and collect results"""
        print(f"🚀 COMPLETE SCANNER SUITE FOR {scan_date}")
        print("=" * 80)
        
        all_results = {}
        
        # Run each scanner
        for name, scanner in self.scanners.items():
            print(f"\n📊 Running {name} Scanner...")
            try:
                if name == 'Momentum':
                    results = scanner.scan(scan_date, top_n * 2)  # Get more for analysis
                elif name == 'Enhanced':
                    results = scanner.scan(scan_date, top_n * 2)
                elif name == 'SupportResistance':
                    results = scanner.scan(scan_date, top_n * 2)
                
                all_results[name] = results
                
                if not results.empty:
                    print(f"   ✅ Found {len(results)} candidates")
                    print(f"   🏆 Top score: {results['composite_score'].max():.1f}")
                    print(f"   📊 Avg score: {results['composite_score'].mean():.1f}")
                    
                    # Show top signals
                    top_signals = results['signal'].value_counts().head(3)
                    print(f"   🎯 Top signals: {dict(top_signals)}")
                else:
                    print(f"   ❌ No candidates found")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                all_results[name] = pd.DataFrame()
        
        return all_results
    
    def create_consensus_analysis(self, all_results: dict, scan_date: date) -> pd.DataFrame:
        """Create consensus analysis from all scanner results"""
        
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
            
            # Calculate consensus metrics
            row['scanner_count'] = scanner_count
            row['avg_score'] = np.mean(scanner_scores) if scanner_scores else 0
            row['max_score'] = max(scanner_scores) if scanner_scores else 0
            row['avg_return'] = np.mean(scanner_returns) if scanner_returns else 0
            row['avg_volume'] = np.mean(scanner_volumes) if scanner_volumes else 0
            
            # Weighted consensus score
            weighted_score = (
                row['momentum_score'] * self.consensus_params['momentum_weight'] +
                row['enhanced_score'] * self.consensus_params['enhanced_weight'] +
                row['sr_score'] * self.consensus_params['sr_weight']
            )
            
            # Consensus bonus
            if scanner_count >= self.consensus_params['min_scanners_agreement']:
                weighted_score += self.consensus_params['consensus_bonus']
            
            row['consensus_score'] = weighted_score
            
            # Consensus signal classification
            strong_signals = ['STRONG_BULLISH', 'STRONG_BEARISH', 'TECHNICAL_BREAKOUT', 
                            'LEVEL_BREAKOUT', 'HIGH_PROBABILITY', 'SUPPORT_BOUNCE', 'RESISTANCE_REJECTION']
            
            signal_strength = sum(1 for sig in scanner_signals if sig in strong_signals)
            
            if scanner_count >= 3 and signal_strength >= 2:
                row['consensus_signal'] = 'TRIPLE_CONSENSUS'
            elif scanner_count >= 2 and signal_strength >= 1:
                row['consensus_signal'] = 'DUAL_CONSENSUS'
            elif scanner_count >= 2:
                row['consensus_signal'] = 'MULTI_SCANNER'
            else:
                row['consensus_signal'] = 'SINGLE_SCANNER'
            
            consensus_data.append(row)
        
        # Create DataFrame and sort by consensus score
        consensus_df = pd.DataFrame(consensus_data)
        consensus_df = consensus_df.sort_values('consensus_score', ascending=False)
        
        return consensus_df
    
    def display_consensus_results(self, consensus_df: pd.DataFrame, top_n: int = 10):
        """Display consensus analysis results"""
        if consensus_df.empty:
            print("❌ No consensus analysis available")
            return
        
        print(f"\n🎯 CONSENSUS ANALYSIS - TOP {min(top_n, len(consensus_df))} PICKS")
        print("=" * 120)
        
        consensus_emojis = {
            'TRIPLE_CONSENSUS': '🔥',
            'DUAL_CONSENSUS': '⚡',
            'MULTI_SCANNER': '📊',
            'SINGLE_SCANNER': '📈'
        }
        
        for i, (_, row) in enumerate(consensus_df.head(top_n).iterrows(), 1):
            emoji = consensus_emojis.get(row['consensus_signal'], '📊')
            direction_emoji = '📈' if row['avg_return'] > 0 else '📉'
            
            print(f"\n{emoji} #{i}: {row['symbol']} | Consensus Score: {row['consensus_score']:.1f} {direction_emoji}")
            print(f"   💰 Avg Return: {row['avg_return']:+.2f}% | Avg Volume: {row['avg_volume']:.1f}x")
            print(f"   📊 Scanner Agreement: {row['scanner_count']}/3 scanners")
            
            # Individual scanner results
            scanner_results = []
            if row['momentum_score'] > 0:
                scanner_results.append(f"Momentum:#{row['momentum_rank']}({row['momentum_score']:.0f},{row['momentum_signal']})")
            if row['enhanced_score'] > 0:
                scanner_results.append(f"Enhanced:#{row['enhanced_rank']}({row['enhanced_score']:.0f},{row['enhanced_signal']})")
            if row['sr_score'] > 0:
                scanner_results.append(f"S/R:#{row['sr_rank']}({row['sr_score']:.0f},{row['sr_signal']})")
            
            print(f"   🔍 Scanner Details: {' | '.join(scanner_results)}")
            print(f"   🎯 Consensus Signal: {row['consensus_signal']}")
        
        # Consensus summary
        print(f"\n📊 CONSENSUS SUMMARY:")
        print(f"   📈 Total symbols analyzed: {len(consensus_df)}")
        print(f"   🎯 Average consensus score: {consensus_df['consensus_score'].mean():.1f}")
        print(f"   🏆 Top consensus score: {consensus_df['consensus_score'].max():.1f}")
        
        # Agreement analysis
        triple_consensus = (consensus_df['consensus_signal'] == 'TRIPLE_CONSENSUS').sum()
        dual_consensus = (consensus_df['consensus_signal'] == 'DUAL_CONSENSUS').sum()
        multi_scanner = (consensus_df['consensus_signal'] == 'MULTI_SCANNER').sum()
        
        print(f"   🔥 Triple Consensus: {triple_consensus}")
        print(f"   ⚡ Dual Consensus: {dual_consensus}")
        print(f"   📊 Multi-Scanner: {multi_scanner}")
        
        # Scanner participation
        momentum_picks = (consensus_df['momentum_score'] > 0).sum()
        enhanced_picks = (consensus_df['enhanced_score'] > 0).sum()
        sr_picks = (consensus_df['sr_score'] > 0).sum()
        
        print(f"   📋 Scanner Participation: Momentum:{momentum_picks} Enhanced:{enhanced_picks} S/R:{sr_picks}")
    
    def generate_recommendations(self, consensus_df: pd.DataFrame):
        """Generate final recommendations based on consensus analysis"""
        if consensus_df.empty:
            print("\n❌ No recommendations available")
            return
        
        print(f"\n🏆 FINAL RECOMMENDATIONS:")
        print("=" * 60)
        
        # Top consensus picks
        top_consensus = consensus_df[consensus_df['consensus_signal'].isin(['TRIPLE_CONSENSUS', 'DUAL_CONSENSUS'])]
        
        if not top_consensus.empty:
            print(f"🔥 HIGH CONFIDENCE PICKS:")
            for i, (_, pick) in enumerate(top_consensus.head(3).iterrows(), 1):
                confidence = "🔥 HIGHEST" if pick['consensus_signal'] == 'TRIPLE_CONSENSUS' else "⚡ HIGH"
                print(f"   {i}. {pick['symbol']}: {pick['avg_return']:+.2f}% - {confidence} CONFIDENCE")
                print(f"      Consensus Score: {pick['consensus_score']:.1f} | Scanners: {pick['scanner_count']}/3")
        
        # Momentum leaders
        momentum_leaders = consensus_df[consensus_df['momentum_score'] > 60].head(2)
        if not momentum_leaders.empty:
            print(f"\n🚀 MOMENTUM LEADERS:")
            for i, (_, pick) in enumerate(momentum_leaders.iterrows(), 1):
                print(f"   {i}. {pick['symbol']}: {pick['momentum_return']:+.2f}% "
                      f"(Score: {pick['momentum_score']:.0f}, Signal: {pick['momentum_signal']})")
        
        # S/R opportunities
        sr_opportunities = consensus_df[consensus_df['sr_score'] > 55].head(2)
        if not sr_opportunities.empty:
            print(f"\n🎯 SUPPORT/RESISTANCE PLAYS:")
            for i, (_, pick) in enumerate(sr_opportunities.iterrows(), 1):
                print(f"   {i}. {pick['symbol']}: {pick['sr_return']:+.2f}% "
                      f"(Score: {pick['sr_score']:.0f}, Signal: {pick['sr_signal']})")
        
        # Risk assessment
        print(f"\n🛡️ RISK ASSESSMENT:")
        high_consensus = (consensus_df['consensus_score'] > 70).sum()
        strong_momentum = (consensus_df['momentum_score'] > 60).sum()
        level_plays = (consensus_df['sr_score'] > 55).sum()
        
        if high_consensus > 0:
            print(f"   ✅ {high_consensus} high-consensus opportunities (lower risk)")
        if strong_momentum > 0:
            print(f"   🚀 {strong_momentum} strong momentum plays (trend following)")
        if level_plays > 0:
            print(f"   🎯 {level_plays} technical level plays (mean reversion)")
        
        # Market condition assessment
        avg_return = consensus_df['avg_return'].mean()
        bullish_count = (consensus_df['avg_return'] > 0).sum()
        bearish_count = (consensus_df['avg_return'] < 0).sum()
        
        print(f"\n📊 MARKET CONDITION:")
        print(f"   📈 Bullish signals: {bullish_count}")
        print(f"   📉 Bearish signals: {bearish_count}")
        print(f"   ⚖️ Average return: {avg_return:+.2f}%")
        
        if avg_return > 0.5:
            print(f"   🟢 BULLISH MARKET - Favor momentum plays")
        elif avg_return < -0.5:
            print(f"   🔴 BEARISH MARKET - Favor short setups and support bounces")
        else:
            print(f"   🟡 NEUTRAL MARKET - Focus on high-consensus picks")
    
    def run_complete_analysis(self, scan_date: date, top_n: int = 10):
        """Run complete scanner suite analysis"""
        logger.info(f"🚀 Starting Complete Scanner Suite for {scan_date}")
        
        try:
            # Run all scanners
            all_results = self.run_all_scanners(scan_date, top_n)
            
            # Create consensus analysis
            consensus_df = self.create_consensus_analysis(all_results, scan_date)
            
            # Display results
            if not consensus_df.empty:
                self.display_consensus_results(consensus_df, top_n)
                self.generate_recommendations(consensus_df)
            else:
                print("\n❌ No consensus analysis possible - insufficient data")
            
            return consensus_df
            
        except Exception as e:
            logger.error(f"❌ Error in complete analysis: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Complete Scanner Suite')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=8,
                       help='Number of top results to display')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        suite = CompleteScannerSuite()
        results = suite.run_complete_analysis(scan_date=scan_date, top_n=args.top_n)
        
        if not results.empty:
            print(f"\n✅ Complete scanner suite analysis completed!")
            print(f"📊 Analyzed {len(results)} symbols across 3 scanner types")
            
            # Final summary
            high_confidence = (results['consensus_signal'].isin(['TRIPLE_CONSENSUS', 'DUAL_CONSENSUS'])).sum()
            print(f"🎯 High confidence opportunities: {high_confidence}")
            
        else:
            print(f"\n⚠️ Complete scanner suite found limited opportunities for {scan_date}")
            
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
