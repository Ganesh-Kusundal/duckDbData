#!/usr/bin/env python3
"""
Enhanced Daily Scanner Runner

Runs both original and enhanced momentum scanners, compares results,
and provides comprehensive analysis for daily trading decisions.

Author: AI Assistant
Date: 2025-09-03
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import date
from optimized_momentum_scanner import OptimizedMomentumScanner
from enhanced_momentum_scanner import EnhancedMomentumScanner
import pandas as pd

def compare_scanners(original_results: pd.DataFrame, enhanced_results: pd.DataFrame):
    """Compare results from both scanners"""
    print(f"\n🔄 SCANNER COMPARISON ANALYSIS")
    print("=" * 60)
    
    # Basic comparison
    orig_count = len(original_results) if not original_results.empty else 0
    enh_count = len(enhanced_results) if not enhanced_results.empty else 0
    
    print(f"📊 Candidates Found:")
    print(f"   Original Scanner: {orig_count}")
    print(f"   Enhanced Scanner: {enh_count}")
    
    if orig_count == 0 and enh_count == 0:
        print(f"   🔍 Both scanners found no opportunities - low momentum day")
        return
    
    # Symbol overlap analysis
    orig_symbols = set(original_results['symbol'].tolist()) if not original_results.empty else set()
    enh_symbols = set(enhanced_results['symbol'].tolist()) if not enhanced_results.empty else set()
    
    overlap = orig_symbols.intersection(enh_symbols)
    orig_only = orig_symbols - enh_symbols
    enh_only = enh_symbols - orig_symbols
    
    print(f"\n🎯 Symbol Analysis:")
    print(f"   Common picks: {list(overlap)} ({len(overlap)})")
    print(f"   Original only: {list(orig_only)} ({len(orig_only)})")
    print(f"   Enhanced only: {list(enh_only)} ({len(enh_only)})")
    
    # Score comparison for common picks
    if overlap and not original_results.empty and not enhanced_results.empty:
        print(f"\n📈 Score Comparison (Common Picks):")
        for symbol in overlap:
            orig_score = original_results[original_results['symbol'] == symbol]['composite_score'].iloc[0]
            enh_score = enhanced_results[enhanced_results['symbol'] == symbol]['composite_score'].iloc[0]
            score_diff = enh_score - orig_score
            
            print(f"   {symbol}: Original {orig_score:.1f} → Enhanced {enh_score:.1f} "
                  f"({score_diff:+.1f})")
    
    # Quality analysis
    if not enhanced_results.empty:
        high_quality = (enhanced_results['composite_score'] > 70).sum()
        medium_quality = ((enhanced_results['composite_score'] > 50) & 
                         (enhanced_results['composite_score'] <= 70)).sum()
        
        print(f"\n💎 Enhanced Quality Breakdown:")
        print(f"   High Quality (70+): {high_quality}")
        print(f"   Medium Quality (50-70): {medium_quality}")
        print(f"   Standard Quality (<50): {enh_count - high_quality - medium_quality}")

def generate_trading_recommendations(original_results: pd.DataFrame, enhanced_results: pd.DataFrame):
    """Generate comprehensive trading recommendations"""
    print(f"\n🎯 TRADING RECOMMENDATIONS")
    print("=" * 60)
    
    # Combine and rank all opportunities
    all_picks = []
    
    # Add original scanner picks
    if not original_results.empty:
        for _, row in original_results.head(3).iterrows():
            all_picks.append({
                'symbol': row['symbol'],
                'scanner': 'Original',
                'score': row['composite_score'],
                'signal': row['signal'],
                'price_change': row['price_change_pct'],
                'relative_volume': row['relative_volume'],
                'priority': 'MEDIUM'
            })
    
    # Add enhanced scanner picks
    if not enhanced_results.empty:
        for _, row in enhanced_results.head(3).iterrows():
            # Check if already in list from original scanner
            existing = next((p for p in all_picks if p['symbol'] == row['symbol']), None)
            
            if existing:
                # Update with enhanced data
                existing['scanner'] = 'Both'
                existing['enhanced_score'] = row['composite_score']
                existing['priority'] = 'HIGH' if row['composite_score'] > 60 else 'MEDIUM'
            else:
                all_picks.append({
                    'symbol': row['symbol'],
                    'scanner': 'Enhanced',
                    'score': row['composite_score'],
                    'signal': row['signal'],
                    'price_change': row['price_change_pct'],
                    'relative_volume': row['relative_volume'],
                    'priority': 'HIGH' if row['composite_score'] > 60 else 'MEDIUM'
                })
    
    if not all_picks:
        print(f"⚠️ No trading opportunities identified")
        print(f"💡 Consider waiting for better market conditions")
        return
    
    # Sort by priority and score
    priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
    all_picks.sort(key=lambda x: (priority_order[x['priority']], x['score']), reverse=True)
    
    print(f"🏆 TOP TRADING OPPORTUNITIES:")
    
    for i, pick in enumerate(all_picks[:5], 1):
        priority_emoji = '🔥' if pick['priority'] == 'HIGH' else '⭐' if pick['priority'] == 'MEDIUM' else '📊'
        scanner_emoji = '🎯' if pick['scanner'] == 'Both' else '🔍'
        
        print(f"\n{priority_emoji} #{i}: {pick['symbol']} ({pick['scanner']} Scanner) {scanner_emoji}")
        print(f"   📈 Movement: {pick['price_change']:+.2f}% | Volume: {pick['relative_volume']:.1f}x")
        print(f"   🎯 Signal: {pick['signal']} | Score: {pick['score']:.1f}")
        print(f"   🔥 Priority: {pick['priority']}")
        
        if 'enhanced_score' in pick:
            print(f"   💎 Enhanced Score: {pick['enhanced_score']:.1f}")
    
    # Trading strategy recommendations
    print(f"\n📋 TRADING STRATEGY:")
    
    high_priority_count = sum(1 for p in all_picks if p['priority'] == 'HIGH')
    bullish_count = sum(1 for p in all_picks if p['price_change'] > 0)
    bearish_count = len(all_picks) - bullish_count
    
    if high_priority_count >= 2:
        print(f"   🚀 AGGRESSIVE: Multiple high-quality opportunities available")
        print(f"   💰 Position Size: Standard (2-3% per trade)")
        print(f"   ⏰ Entry: Immediate on market open or pullback")
    elif high_priority_count == 1:
        print(f"   ⭐ SELECTIVE: One high-quality opportunity identified")
        print(f"   💰 Position Size: Conservative (1-2% per trade)")
        print(f"   ⏰ Entry: Wait for confirmation or better entry")
    else:
        print(f"   📊 CAUTIOUS: Only moderate opportunities available")
        print(f"   💰 Position Size: Small (0.5-1% per trade)")
        print(f"   ⏰ Entry: Paper trade or very small positions")
    
    print(f"\n📊 Market Sentiment: {bullish_count} Bullish | {bearish_count} Bearish")
    
    if bullish_count > bearish_count:
        print(f"   📈 Bias: BULLISH - Look for long opportunities")
    elif bearish_count > bullish_count:
        print(f"   📉 Bias: BEARISH - Consider short opportunities or wait")
    else:
        print(f"   ⚖️ Bias: NEUTRAL - Mixed signals, trade carefully")

def main():
    """Main function"""
    today = date.today()
    
    print(f"🚀 ENHANCED DAILY MOMENTUM SCANNER - {today}")
    print("=" * 80)
    print(f"⏰ Comprehensive analysis using dual scanner approach")
    print(f"🎯 Target: High momentum stocks by 09:50 AM")
    
    # Run original scanner
    print(f"\n" + "="*50)
    print(f"🔍 RUNNING ORIGINAL SCANNER")
    print(f"="*50)
    
    original_scanner = OptimizedMomentumScanner()
    original_results = original_scanner.scan(scan_date=today, top_n=5)
    
    # Run enhanced scanner
    print(f"\n" + "="*50)
    print(f"💎 RUNNING ENHANCED SCANNER v2.0")
    print(f"="*50)
    
    enhanced_scanner = EnhancedMomentumScanner()
    enhanced_results = enhanced_scanner.scan(scan_date=today, top_n=5)
    
    # Compare results
    compare_scanners(original_results, enhanced_results)
    
    # Generate recommendations
    generate_trading_recommendations(original_results, enhanced_results)
    
    print(f"\n✅ Enhanced daily momentum analysis completed!")
    print(f"🎯 Ready for trading decisions based on comprehensive scanner analysis")
    
    return 0

if __name__ == "__main__":
    exit(main())
