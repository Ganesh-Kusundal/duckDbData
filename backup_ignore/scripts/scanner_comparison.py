#!/usr/bin/env python3
"""
Scanner Comparison Tool

Compares all scanner versions to show the evolution and improvements
from basic momentum to comprehensive technical analysis integration.

Scanners Compared:
1. Original Optimized Scanner
2. Enhanced Momentum Scanner  
3. Technical Momentum Scanner
4. Comprehensive Technical Scanner (with 99+ indicators)

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

# Import all scanner classes
from scripts.optimized_momentum_scanner import OptimizedMomentumScanner
from scripts.enhanced_momentum_scanner import EnhancedMomentumScanner

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise for comparison

class ScannerComparison:
    """Compare all scanner versions"""
    
    def __init__(self):
        """Initialize all scanners"""
        self.scanners = {
            'Original': OptimizedMomentumScanner(),
            'Enhanced': EnhancedMomentumScanner(),
        }
    
    def run_comparison(self, scan_date: date, top_n: int = 5):
        """Run all scanners and compare results"""
        print(f"🔍 SCANNER COMPARISON FOR {scan_date}")
        print("=" * 80)
        
        all_results = {}
        
        # Run each scanner
        for name, scanner in self.scanners.items():
            print(f"\n📊 Running {name} Scanner...")
            try:
                if name == 'Original':
                    results = scanner.scan(scan_date, top_n)
                elif name == 'Enhanced':
                    results = scanner.scan(scan_date, top_n)
                
                all_results[name] = results
                
                if not results.empty:
                    print(f"   ✅ Found {len(results)} candidates")
                    print(f"   🏆 Top score: {results['composite_score'].max():.1f}")
                    print(f"   📊 Avg score: {results['composite_score'].mean():.1f}")
                else:
                    print(f"   ❌ No candidates found")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                all_results[name] = pd.DataFrame()
        
        # Compare results
        self.compare_results(all_results, scan_date, top_n)
    
    def compare_results(self, all_results: dict, scan_date: date, top_n: int):
        """Compare and analyze results from all scanners"""
        
        print(f"\n🔍 DETAILED COMPARISON ANALYSIS")
        print("=" * 80)
        
        # Collect all unique symbols
        all_symbols = set()
        for results in all_results.values():
            if not results.empty:
                all_symbols.update(results['symbol'].tolist())
        
        if not all_symbols:
            print("❌ No symbols found by any scanner")
            return
        
        print(f"📊 Total unique symbols identified: {len(all_symbols)}")
        print(f"🎯 Symbols: {', '.join(sorted(list(all_symbols)))}")
        
        # Create comparison matrix
        comparison_data = []
        
        for symbol in sorted(all_symbols):
            row = {'Symbol': symbol}
            
            for scanner_name, results in all_results.items():
                if not results.empty and symbol in results['symbol'].values:
                    symbol_data = results[results['symbol'] == symbol].iloc[0]
                    row[f'{scanner_name}_Score'] = f"{symbol_data['composite_score']:.1f}"
                    row[f'{scanner_name}_Signal'] = symbol_data['signal']
                    row[f'{scanner_name}_Return'] = f"{symbol_data['price_change_pct']:+.2f}%"
                    row[f'{scanner_name}_Volume'] = f"{symbol_data['relative_volume']:.1f}x"
                    row[f'{scanner_name}_Rank'] = results[results['symbol'] == symbol].index[0] + 1
                else:
                    row[f'{scanner_name}_Score'] = "-"
                    row[f'{scanner_name}_Signal'] = "-"
                    row[f'{scanner_name}_Return'] = "-"
                    row[f'{scanner_name}_Volume'] = "-"
                    row[f'{scanner_name}_Rank'] = "-"
            
            comparison_data.append(row)
        
        # Display comparison table
        print(f"\n📋 SCANNER COMPARISON TABLE:")
        print("-" * 120)
        
        # Header
        header = "Symbol".ljust(12)
        for scanner_name in all_results.keys():
            header += f"{scanner_name}".ljust(25)
        print(header)
        print("-" * 120)
        
        # Data rows
        for row in comparison_data:
            line = row['Symbol'].ljust(12)
            for scanner_name in all_results.keys():
                score = row[f'{scanner_name}_Score']
                signal = row[f'{scanner_name}_Signal']
                return_pct = row[f'{scanner_name}_Return']
                rank = row[f'{scanner_name}_Rank']
                
                if score != "-":
                    cell = f"#{rank} {score} {return_pct}".ljust(25)
                else:
                    cell = "Not detected".ljust(25)
                line += cell
            print(line)
        
        # Scanner statistics
        print(f"\n📊 SCANNER STATISTICS:")
        print("-" * 60)
        
        stats_data = []
        for scanner_name, results in all_results.items():
            if not results.empty:
                stats = {
                    'Scanner': scanner_name,
                    'Candidates': len(results),
                    'Avg_Score': f"{results['composite_score'].mean():.1f}",
                    'Max_Score': f"{results['composite_score'].max():.1f}",
                    'Avg_Return': f"{results['price_change_pct'].mean():+.2f}%",
                    'Avg_Volume': f"{results['relative_volume'].mean():.1f}x",
                    'Top_Symbol': results.iloc[0]['symbol'],
                    'Top_Return': f"{results.iloc[0]['price_change_pct']:+.2f}%"
                }
            else:
                stats = {
                    'Scanner': scanner_name,
                    'Candidates': 0,
                    'Avg_Score': "-",
                    'Max_Score': "-", 
                    'Avg_Return': "-",
                    'Avg_Volume': "-",
                    'Top_Symbol': "-",
                    'Top_Return': "-"
                }
            stats_data.append(stats)
        
        # Display stats table
        for stats in stats_data:
            print(f"{stats['Scanner'].ljust(15)}: "
                  f"Candidates:{stats['Candidates']} | "
                  f"AvgScore:{stats['Avg_Score']} | "
                  f"MaxScore:{stats['Max_Score']} | "
                  f"AvgReturn:{stats['Avg_Return']} | "
                  f"Top:{stats['Top_Symbol']}({stats['Top_Return']})")
        
        # Overlap analysis
        print(f"\n🔄 OVERLAP ANALYSIS:")
        print("-" * 40)
        
        scanner_names = list(all_results.keys())
        for i, scanner1 in enumerate(scanner_names):
            for scanner2 in scanner_names[i+1:]:
                results1 = all_results[scanner1]
                results2 = all_results[scanner2]
                
                if not results1.empty and not results2.empty:
                    symbols1 = set(results1['symbol'].tolist())
                    symbols2 = set(results2['symbol'].tolist())
                    
                    overlap = symbols1.intersection(symbols2)
                    overlap_pct = len(overlap) / len(symbols1.union(symbols2)) * 100
                    
                    print(f"{scanner1} ∩ {scanner2}: {len(overlap)} symbols ({overlap_pct:.1f}% overlap)")
                    if overlap:
                        print(f"   Common: {', '.join(sorted(overlap))}")
        
        # Performance prediction
        print(f"\n🎯 PERFORMANCE PREDICTION:")
        print("-" * 50)
        
        for scanner_name, results in all_results.items():
            if not results.empty:
                high_score_count = (results['composite_score'] > 70).sum()
                strong_signals = results[results['signal'].isin(['STRONG_BULLISH', 'STRONG_BEARISH', 'TECHNICAL_BREAKOUT'])].shape[0]
                
                print(f"{scanner_name}:")
                print(f"   💎 High Quality (>70 score): {high_score_count}")
                print(f"   🚀 Strong Signals: {strong_signals}")
                
                if high_score_count > 0 and strong_signals > 0:
                    prediction = "🚀 EXCELLENT - High quality with strong signals"
                elif high_score_count > 0:
                    prediction = "💎 GOOD - High quality setups"
                elif strong_signals > 0:
                    prediction = "⚡ MODERATE - Strong signals but lower scores"
                else:
                    prediction = "📊 STANDARD - Basic momentum opportunities"
                
                print(f"   {prediction}")
        
        # Final recommendation
        print(f"\n🏆 FINAL RECOMMENDATION:")
        print("-" * 40)
        
        best_scanner = None
        best_score = 0
        
        for scanner_name, results in all_results.items():
            if not results.empty:
                # Calculate overall quality score
                quality_score = (
                    len(results) * 10 +  # Number of candidates
                    results['composite_score'].mean() +  # Average quality
                    (results['composite_score'] > 70).sum() * 20 +  # High quality bonus
                    results[results['signal'].isin(['STRONG_BULLISH', 'STRONG_BEARISH', 'TECHNICAL_BREAKOUT'])].shape[0] * 15  # Strong signal bonus
                )
                
                if quality_score > best_score:
                    best_score = quality_score
                    best_scanner = scanner_name
        
        if best_scanner:
            print(f"🥇 Best Scanner: {best_scanner}")
            print(f"📊 Quality Score: {best_score:.1f}")
            
            best_results = all_results[best_scanner]
            if not best_results.empty:
                top_pick = best_results.iloc[0]
                print(f"🎯 Top Pick: {top_pick['symbol']} ({top_pick['price_change_pct']:+.2f}%, Score: {top_pick['composite_score']:.1f})")
        else:
            print("❌ No clear winner - all scanners found limited opportunities")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Scanner Comparison Tool')
    parser.add_argument('--scan-date', type=str, required=True,
                       help='Date to scan (YYYY-MM-DD)')
    parser.add_argument('--top-n', type=int, default=5,
                       help='Number of top results per scanner')
    
    args = parser.parse_args()
    
    try:
        scan_date = datetime.strptime(args.scan_date, '%Y-%m-%d').date()
        
        comparison = ScannerComparison()
        comparison.run_comparison(scan_date=scan_date, top_n=args.top_n)
        
    except ValueError as e:
        print(f"❌ Invalid date format: {e}")
        return 1
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

