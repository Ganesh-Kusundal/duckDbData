#!/usr/bin/env python3
"""
Breakout Scanner Test Script
=============================

This script replicates the functionality of the breakout_scanner_test.ipynb notebook
in a standalone Python script format for easier execution and testing.

Features:
- Initialize and configure the breakout scanner
- Test scanner with different date ranges and parameters
- Debug and troubleshoot scanner issues
- Compare different scanner configurations

Prerequisites:
- DuckDB database with market data
- Required Python packages installed
- Proper configuration files in place
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np

# Add project root to Python path
current_dir = Path.cwd()
if current_dir.name == 'scanner':
    # We're in notebook/scanner/
    project_root = current_dir.parent.parent
elif current_dir.name == 'notebook':
    # We're in notebook/
    project_root = current_dir.parent
else:
    # Assume we're in project root or another location
    project_root = current_dir

# Add paths to sys.path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

print(f"Current directory: {current_dir}")
print(f"Project root: {project_root}")
print(f"Added to sys.path: {project_root / 'src'}")

# Import project modules
from src.infrastructure.logging import setup_logging
from src.application.scanners.strategies.breakout_scanner import BreakoutScanner
from src.infrastructure.core.database import DuckDBManager
from src.infrastructure.config.settings import get_settings

# Setup logging
setup_logging()

print(f"Project root: {project_root}")
print(f"Python path includes: {project_root / 'src'}")
print("✅ Environment setup complete!")


def initialize_scanner():
    """Initialize and configure the breakout scanner"""
    print("\n🔧 Initializing Breakout Scanner...")

    # Get settings
    settings = get_settings()

    # Initialize database connection
    # Use the main database with all the data
    main_db_path = project_root / "data" / "financial_data.duckdb"
    print(f"Using database: {main_db_path}")
    db_manager = DuckDBManager(
        db_path=str(main_db_path)
    )

    # Initialize scanner
    scanner = BreakoutScanner(db_manager=db_manager)

    print(f"Database: {main_db_path}")
    print("Scanner initialized with config:")
    for key, value in scanner.config.items():
        print(f"  {key}: {value}")
    print("✅ Scanner initialization complete!")

    return scanner


def run_breakout_demo(scanner):
    """Run the breakout scanner demo with optimal configuration"""
    print("\n🚀 Quick Working Demo - Testing Optimal Configuration")

    # Apply optimal configuration
    scanner.config.update({
        'resistance_break_pct': 0.5,    # 0.5% breakout (reduced from 1.0%)
        'breakout_volume_ratio': 1.5,   # 1.5x volume (reduced from 2.0x)
        'consolidation_range_pct': 8.0, # 8.0% consolidation (increased from 3.0%)
        'min_price': 50,
        'max_price': 2000,
        'max_results': 50
    })

    print("⚙️ Applied optimal scanner configuration")
    print("📅 Testing on optimal dates (2025-09-01 to 2025-09-05)")

    # Test on optimal dates
    optimal_dates = [date(2025, 9, 1), date(2025, 9, 2), date(2025, 9, 3), date(2025, 9, 4), date(2025, 9, 5)]
    cutoff_time = time(9, 50)

    all_results = []
    for test_date in optimal_dates:
        print(f"\n📊 Testing {test_date}...")
        print("⚠️  Single-day scan mode (use scan_date_range() for full functionality)")
        try:
            results = scanner.scan(test_date, cutoff_time)
            if not results.empty:
                print(f"✅ Found {len(results)} stocks with breakout patterns")
                print(f"   ✅ Found {len(results)} breakout candidates")
                # Show top 3 for this date
                if 'breakout_score' in results.columns:
                    top_3 = results.nlargest(3, 'breakout_score')[['symbol', 'current_price', 'breakout_score', 'breakout_pct', 'volume_ratio']]
                    for _, row in top_3.iterrows():
                        print(".2f")
                all_results.append(results)
            else:
                print("   ⚠️ No breakout candidates found")
                print("   ❌ Error: \"['breakout_signal'] not in index\"")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Combine and show summary
    if all_results:
        combined_results = pd.concat(all_results, ignore_index=True)
        unique_results = combined_results.drop_duplicates(subset=['symbol'])
        if 'breakout_score' in unique_results.columns:
            top_overall = unique_results.nlargest(10, 'breakout_score')

            print("\n🎯 TOP 10 UNIQUE BREAKOUT CANDIDATES OVERALL:")
            for _, row in top_overall.iterrows():
                signal_emoji = "🔥"
                print(".2f")

            print(f"\n📈 SUMMARY: Found {len(unique_results)} unique stocks across {len(all_results)} dates")
            if 'breakout_signal' in combined_results.columns:
                print(f"🔥 Strong breakouts: {len(combined_results[combined_results['breakout_signal'] == 'STRONG_BREAKOUT'])}")
                print(f"⚡ Weak breakouts: {len(combined_results[combined_results['breakout_signal'] == 'WEAK_BREAKOUT'])}")

            # Save results
            combined_results.to_csv('notebook_breakout_results.csv', index=False)
            top_overall.to_csv('notebook_top10_breakouts.csv', index=False)
            print("\n💾 Results saved to CSV files")
    else:
        print("❌ No results found across all test dates")

    print("\n🎉 Breakout Scanner Demo Complete!")
    return all_results


def test_enhanced_features(scanner):
    """Test the enhanced date range functionality"""
    print("\n🆕 Testing Enhanced Features (Date Range Analysis)")

    try:
        # Test enhanced date range scanning
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 5)
        cutoff_time = time(9, 50)
        end_of_day_time = time(15, 15)

        print(f"📅 Scanning date range: {start_date} to {end_date}")
        print(f"⏰ Breakout cutoff: {cutoff_time}, End of day: {end_of_day_time}")

        # Use the enhanced scan_date_range method
        enhanced_results = scanner.scan_date_range(
            start_date=start_date,
            end_date=end_date,
            cutoff_time=cutoff_time,
            end_of_day_time=end_of_day_time
        )

        if enhanced_results:
            print(f"✅ Found {len(enhanced_results)} enhanced breakout results")

            # Display professional table
            scanner.display_results_table(
                enhanced_results,
                title=f"Enhanced Breakout Analysis: {start_date} to {end_date}"
            )

            # Export to CSV
            scanner.export_results(enhanced_results, "enhanced_breakout_test_results.csv")

            print("✅ Enhanced features test completed successfully!")
            return enhanced_results
        else:
            print("⚠️ No enhanced results found")
            return []

    except Exception as e:
        print(f"❌ Enhanced features test failed: {e}")
        return []


def main():
    """Main execution function"""
    print("🚀 BREAKOUT SCANNER TEST SCRIPT")
    print("=" * 50)

    try:
        # Step 1: Initialize scanner
        scanner = initialize_scanner()

        # Step 2: Run basic demo
        basic_results = run_breakout_demo(scanner)

        # Step 3: Test enhanced features
        enhanced_results = test_enhanced_features(scanner)

        # Summary
        print("\n📊 TEST SUMMARY")
        print("=" * 30)
        print(f"Basic scan results: {'✅' if basic_results else '❌'}")
        print(f"Enhanced scan results: {'✅' if enhanced_results else '❌'}")
        print("\n🎉 All tests completed!")

    except Exception as e:
        print(f"\n❌ Script execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
