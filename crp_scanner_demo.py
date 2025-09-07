#!/usr/bin/env python3
"""
CRP Scanner Demo Script
Demonstrates how to use the CRP scanner for intraday stock selection
"""

from datetime import date, time, timedelta
from src.application.scanners.strategies.crp_scanner import CRPScanner
from src.infrastructure.core.database import DuckDBManager
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


def main():
    """Main demo function for CRP scanner."""
    print("🎯 CRP Scanner Demo")
    print("=" * 50)

    try:
        # Initialize database manager and CRP scanner
        db_manager = DuckDBManager()
        crp_scanner = CRPScanner(db_manager=db_manager)

        # Display scanner configuration
        print("\n📋 CRP Scanner Configuration:")
        print(f"   Close Threshold: {crp_scanner.config['close_threshold_pct']}%")
        print(f"   Range Threshold: {crp_scanner.config['range_threshold_pct']}%")
        print(f"   Min Volume: {crp_scanner.config['min_volume']:,}")
        print(f"   Price Range: ₹{crp_scanner.config['min_price']} - ₹{crp_scanner.config['max_price']}")
        print(f"   Max Results Per Day: {crp_scanner.config['max_results_per_day']}")

        # Define scan parameters
        today = date.today()
        yesterday = today - timedelta(days=1)
        scan_date = yesterday  # Use yesterday for demo (adjust as needed)
        cutoff_time = time(9, 50)  # CRP detection time
        end_of_day_time = time(15, 15)  # End of day time

        print(f"\n📅 Scan Date: {scan_date}")
        print(f"⏰ CRP Detection Time: {cutoff_time}")
        print(f"🏁 End of Day Time: {end_of_day_time}")

        # Option 1: Single day scan (backward compatibility)
        print("\n🔍 Performing Single Day CRP Scan...")
        single_day_results = crp_scanner.scan(scan_date, cutoff_time)

        if not single_day_results.empty:
            print(f"✅ Found {len(single_day_results)} CRP patterns")
            print("\n📊 Top CRP Results:")
            print(single_day_results.head().to_string(index=False))
        else:
            print("⚠️  No CRP patterns found for single day scan")

        # Option 2: Date range scan with end-of-day analysis
        print("\n📈 Performing Date Range CRP Analysis...")
        start_date = scan_date - timedelta(days=4)  # 5-day window
        end_date = scan_date

        print(f"   Date Range: {start_date} to {end_date}")

        range_results = crp_scanner.scan_date_range(
            start_date=start_date,
            end_date=end_date,
            cutoff_time=cutoff_time,
            end_of_day_time=end_of_day_time
        )

        if range_results:
            print(f"✅ Found {len(range_results)} CRP opportunities across {len(set(r['scan_date'] for r in range_results))} days")

            # Display comprehensive results table
            crp_scanner.display_results_table(range_results, "CRP Scanner Demo Results")

            # Export results to CSV
            export_filename = f"crp_scanner_demo_{today.strftime('%Y%m%d')}.csv"
            crp_scanner.export_results(range_results, export_filename)

        else:
            print("⚠️  No CRP patterns found in the date range")

        print("\n🎯 CRP Pattern Explanation:")
        print("   C - Close: Stock closes near its high or low")
        print("   R - Range: Trading range is narrow/tight")
        print("   P - Pattern: Combines volume, momentum, and probability scoring")
        print("\n💡 Higher CRP Probability Score = Better pattern quality")
        print("💡 'Near High'/'Near Low' indicates close position")
        print("💡 Lower 'Current Range%' indicates tighter consolidation")

    except Exception as e:
        print(f"❌ Error in CRP scanner demo: {e}")
        import traceback
        traceback.print_exc()

    print("\n🎯 CRP Scanner Demo Complete!")


def show_crp_examples():
    """Show examples of CRP pattern scenarios."""
    print("\n📚 CRP Pattern Examples:")
    print("=" * 50)

    examples = [
        {
            'scenario': 'High Probability CRP',
            'close_position': 'Near High',
            'range_pct': 1.2,
            'volume_score': 'High',
            'momentum': 'Positive',
            'probability': 95.0
        },
        {
            'scenario': 'Medium Probability CRP',
            'close_position': 'Near Low',
            'range_pct': 2.5,
            'volume_score': 'Medium',
            'momentum': 'Neutral',
            'probability': 75.0
        },
        {
            'scenario': 'Low Probability CRP',
            'close_position': 'Mid Range',
            'range_pct': 4.8,
            'volume_score': 'Low',
            'momentum': 'Negative',
            'probability': 45.0
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['scenario']}")
        print(f"   Close Position: {example['close_position']}")
        print(f"   Range: {example['range_pct']}%")
        print(f"   Volume: {example['volume_score']}")
        print(f"   Momentum: {example['momentum']}")
        print(f"   CRP Probability: {example['probability']}%")


if __name__ == "__main__":
    # Check if we should show examples only
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        show_crp_examples()
    else:
        main()
        show_crp_examples()
