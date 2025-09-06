#!/usr/bin/env python3
"""
Daily Momentum Scanner Runner

Simple script to run the optimized momentum scanner for today's date.
Perfect for daily use to find high momentum stocks by 09:50 AM.

Usage: python daily_momentum_scan.py

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

def main():
    """Run daily momentum scan for today"""
    today = date.today()
    
    print(f"🚀 DAILY MOMENTUM SCANNER - {today}")
    print("=" * 60)
    print(f"⏰ Scanning for high momentum stocks by 09:50 AM")
    print(f"📊 Using optimized parameters based on market analysis")
    
    scanner = OptimizedMomentumScanner()
    results = scanner.scan(scan_date=today, top_n=8)
    
    if not results.empty:
        print(f"\n🎯 TRADING RECOMMENDATIONS:")
        
        # Get top bullish and bearish picks
        bullish = results[results['direction'] == 'BULLISH'].head(2)
        bearish = results[results['direction'] == 'BEARISH'].head(2)
        
        if not bullish.empty:
            print(f"\n📈 TOP BULLISH MOMENTUM:")
            for _, row in bullish.iterrows():
                print(f"   🚀 {row['symbol']}: {row['price_change_pct']:+.2f}% "
                      f"({row['relative_volume']:.1f}x vol, Score: {row['composite_score']:.1f})")
        
        if not bearish.empty:
            print(f"\n📉 TOP BEARISH MOMENTUM:")
            for _, row in bearish.iterrows():
                print(f"   💥 {row['symbol']}: {row['price_change_pct']:+.2f}% "
                      f"({row['relative_volume']:.1f}x vol, Score: {row['composite_score']:.1f})")
        
        # Best overall pick
        best_pick = results.iloc[0]
        print(f"\n🏆 BEST OVERALL MOMENTUM PICK:")
        print(f"   {best_pick['symbol']}: {best_pick['price_change_pct']:+.2f}% "
              f"({best_pick['relative_volume']:.1f}x vol)")
        print(f"   Signal: {best_pick['signal']} | Score: {best_pick['composite_score']:.1f}/100")
        
    else:
        print(f"\n⚠️ No high momentum opportunities found for {today}")
        print(f"💡 Market may be in consolidation mode")
    
    print(f"\n✅ Daily momentum scan completed!")
    return 0

if __name__ == "__main__":
    exit(main())

