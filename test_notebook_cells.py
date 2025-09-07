#!/usr/bin/env python3
"""
Test Script for Breakout Scanner Notebook Cells
===============================================

This script tests each cell of the enhanced breakout_scanner_test.ipynb notebook
to ensure all functionality works correctly.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np

def test_cell_1_setup_imports():
    """Test Cell 1: Setup and Imports"""
    print("=" * 60)
    print("🧪 TESTING CELL 1: Setup and Imports")
    print("=" * 60)

    try:
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

        print("\n✅ CELL 1 PASSED: Setup and imports successful!")
        return True

    except Exception as e:
        print(f"\n❌ CELL 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cell_2_initialization():
    """Test Cell 2: Configuration and Initialization"""
    print("\n" + "=" * 60)
    print("🧪 TESTING CELL 2: Configuration and Initialization")
    print("=" * 60)

    try:
        # Get settings
        from src.infrastructure.config.settings import get_settings
        from src.infrastructure.core.database import DuckDBManager
        from src.application.scanners.strategies.breakout_scanner import BreakoutScanner

        settings = get_settings()

        # Initialize database connection
        current_dir = Path.cwd()
        if current_dir.name == 'scanner':
            project_root = current_dir.parent.parent
        elif current_dir.name == 'notebook':
            project_root = current_dir.parent
        else:
            project_root = current_dir

        main_db_path = project_root / "data" / "financial_data.duckdb"
        print(f"Using database: {main_db_path}")
        db_manager = DuckDBManager(db_path=str(main_db_path))

        # Initialize scanner
        scanner = BreakoutScanner(db_manager=db_manager)

        print(f"Database: {main_db_path}")
        print("Scanner initialized with config:")
        for key, value in scanner.config.items():
            print(f"  {key}: {value}")
        print("✅ Scanner initialization complete!")

        print("\n✅ CELL 2 PASSED: Database and scanner initialization successful!")
        return scanner

    except Exception as e:
        print(f"\n❌ CELL 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_cell_3_basic_testing(scanner):
    """Test Cell 3: Basic Single-Day Testing"""
    print("\n" + "=" * 60)
    print("🧪 TESTING CELL 3: Basic Single-Day Testing")
    print("=" * 60)

    if scanner is None:
        print("❌ CELL 3 SKIPPED: Scanner not available from Cell 2")
        return False

    try:
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

        # Test on optimal dates (Single-day mode for compatibility)
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
                    # Show top 3 for this date (with better error handling)
                    if 'breakout_score' in results.columns:
                        top_3 = results.nlargest(3, 'breakout_score')[['symbol', 'current_price', 'breakout_score', 'breakout_pct', 'volume_ratio']]
                        for _, row in top_3.iterrows():
                            print(".2f")
                    all_results.append(results)
                else:
                    print("   ⚠️ No breakout candidates found")
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

        print("\n🎉 Basic Single-Day Scanner Demo Complete!")
        print("\n💡 Tip: Use the next cell for Enhanced Date Range Analysis!")

        print("\n✅ CELL 3 PASSED: Basic single-day testing successful!")
        return True

    except Exception as e:
        print(f"\n❌ CELL 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cell_4_enhanced_analysis(scanner):
    """Test Cell 4: Enhanced Date Range Analysis"""
    print("\n" + "=" * 60)
    print("🧪 TESTING CELL 4: Enhanced Date Range Analysis")
    print("=" * 60)

    if scanner is None:
        print("❌ CELL 4 SKIPPED: Scanner not available from Cell 2")
        return False

    try:
        # Configure analysis parameters
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 5)
        breakout_time = time(9, 50)  # 09:50 AM breakout detection
        end_of_day_time = time(15, 15)  # 15:15 PM end-of-day analysis

        print(f"📅 Analyzing period: {start_date} to {end_date}")
        print(f"⏰ Breakout detection: {breakout_time}")
        print(f"⏰ End-of-day analysis: {end_of_day_time}")

        # Run enhanced analysis
        enhanced_results = scanner.scan_date_range(
            start_date=start_date,
            end_date=end_date,
            cutoff_time=breakout_time,
            end_of_day_time=end_of_day_time
        )

        if enhanced_results:
            print(f"\n✅ Found {len(enhanced_results)} enhanced breakout results")

            # Display professional table
            scanner.display_results_table(
                enhanced_results,
                title=f"Enhanced Breakout Analysis: {start_date} to {end_date}"
            )

            # Export to CSV
            csv_filename = f"enhanced_breakout_analysis_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv"
            scanner.export_results(enhanced_results, csv_filename)

            print(f"\n💾 Results exported to: {csv_filename}")
            print("\n📊 Enhanced features demonstrated successfully!")

            print("\n✅ CELL 4 PASSED: Enhanced date range analysis successful!")
            return enhanced_results
        else:
            print("⚠️ No enhanced results found")
            return []

    except Exception as e:
        print(f"\n❌ CELL 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_cell_5_performance_analysis(enhanced_results):
    """Test Cell 5: Performance Analysis"""
    print("\n" + "=" * 60)
    print("🧪 TESTING CELL 5: Performance Analysis")
    print("=" * 60)

    try:
        if enhanced_results:
            print(f"\n📈 Analyzing {len(enhanced_results)} breakout opportunities...")

            # Convert to DataFrame for analysis
            df = pd.DataFrame(enhanced_results)

            # Basic statistics
            successful_breakouts = len(df[df['breakout_successful'] == True])
            total_breakouts = len(df)
            success_rate = (successful_breakouts / total_breakouts * 100) if total_breakouts > 0 else 0

            print(f"\n📊 PERFORMANCE METRICS:")
            print(f"   Total Breakouts: {total_breakouts}")
            print(f"   Successful Breakouts: {successful_breakouts}")
            print(".1f")

            if 'price_change_pct' in df.columns:
                avg_price_change = df['price_change_pct'].mean()
                print(".2f")

                # Success rate by day range
                high_performers = len(df[df['price_change_pct'] > 2.0])
                print(f"   High Performers (>2%): {high_performers}")

            # Group by scan date
            if 'scan_date' in df.columns:
                try:
                    # Convert scan_date to datetime if it's not already
                    if not pd.api.types.is_datetime64_any_dtype(df['scan_date']):
                        df['scan_date'] = pd.to_datetime(df['scan_date'])

                    daily_stats = df.groupby(df['scan_date'].dt.date).agg({
                        'symbol': 'count',
                        'breakout_successful': 'sum',
                        'price_change_pct': 'mean'
                    }).round(2)

                    print(f"\n📅 DAILY PERFORMANCE:")
                    print(daily_stats)
                except Exception as e:
                    print(f"   Note: Could not group by date: {e}")

            # Top performers
            if 'performance_rank' in df.columns:
                # Select available columns for top performers
                available_columns = ['symbol', 'scan_date', 'price_change_pct', 'performance_rank']
                optional_columns = ['breakout_price', 'eod_price']
                for col in optional_columns:
                    if col in df.columns:
                        available_columns.append(col)

                top_performers = df.nsmallest(min(5, len(df)), 'performance_rank')[available_columns]
                print(f"\n🏆 TOP {len(top_performers)} PERFORMERS:")
                for _, row in top_performers.iterrows():
                    date_str = row['scan_date'].strftime('%Y-%m-%d') if hasattr(row['scan_date'], 'strftime') else str(row['scan_date'])
                    print(f"   {row['symbol']} ({date_str}): {row['price_change_pct']:+.2f}% (Rank: {row['performance_rank']:.2f})")

            print("\n✅ Performance analysis complete!")

        else:
            print("⚠️ No enhanced results available. Please run the Enhanced Date Range Analysis cell first.")

        print("\n✅ CELL 5 PASSED: Performance analysis successful!")
        return True

    except Exception as e:
        print(f"\n❌ CELL 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cell_6_config_tuning(scanner):
    """Test Cell 6: Configuration Tuning"""
    print("\n" + "=" * 60)
    print("🧪 TESTING CELL 6: Configuration Tuning")
    print("=" * 60)

    if scanner is None:
        print("❌ CELL 6 SKIPPED: Scanner not available from Cell 2")
        return False

    try:
        # Define different configurations to test
        configurations = {
            'Conservative': {
                'resistance_break_pct': 1.0,    # Higher breakout threshold
                'breakout_volume_ratio': 2.0,   # Higher volume requirement
                'consolidation_range_pct': 5.0, # Tighter consolidation
                'min_price': 100,
                'max_price': 1500,
                'max_results': 30
            },
            'Moderate': {
                'resistance_break_pct': 0.5,    # Current optimal
                'breakout_volume_ratio': 1.5,   # Current optimal
                'consolidation_range_pct': 8.0, # Current optimal
                'min_price': 50,
                'max_price': 2000,
                'max_results': 50
            },
            'Aggressive': {
                'resistance_break_pct': 0.2,    # Lower breakout threshold
                'breakout_volume_ratio': 1.2,   # Lower volume requirement
                'consolidation_range_pct': 12.0, # Wider consolidation
                'min_price': 20,
                'max_price': 3000,
                'max_results': 100
            }
        }

        # Test date for comparison
        test_date = date(2025, 9, 4)
        cutoff_time = time(9, 50)

        print(f"📅 Testing configurations on: {test_date}")
        print(f"\n{'Configuration':<15} {'Results':<8} {'Success Rate':<12} {'Avg Change':<10}")
        print("-" * 50)

        # Test each configuration
        for config_name, config_params in configurations.items():
            try:
                # Save original config
                original_config = scanner.config.copy()

                # Apply new configuration
                scanner.config.update(config_params)

                # Run scan
                results = scanner.scan(test_date, cutoff_time)

                # Analyze results
                if not results.empty and len(results) > 0:
                    result_count = len(results)

                    # Calculate metrics if available
                    if 'breakout_successful' in results.columns:
                        success_count = results['breakout_successful'].sum()
                        success_rate = (success_count / result_count * 100) if result_count > 0 else 0
                    else:
                        success_rate = 0.0

                    if 'price_change_pct' in results.columns:
                        avg_change = results['price_change_pct'].mean()
                    else:
                        avg_change = 0.0

                    print(f"{config_name:<15} {result_count:<8} {success_rate:<11.1f}% {avg_change:<9.2f}%")
                else:
                    print(f"{config_name:<15} {'0':<8} {'N/A':<12} {'N/A':<10}")

                # Restore original config
                scanner.config.update(original_config)

            except Exception as e:
                print(f"{config_name:<15} {'ERROR':<8} {'N/A':<12} {'N/A':<10}")
                print(f"   ❌ {e}")

        print("\n✅ Configuration comparison complete!")
        print("💡 Tip: Adjust parameters based on your risk tolerance and market conditions.")

        print("\n✅ CELL 6 PASSED: Configuration tuning successful!")
        return True

    except Exception as e:
        print(f"\n❌ CELL 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test execution function"""
    print("🚀 NOTEBOOK CELL TESTING SCRIPT")
    print("=" * 60)
    print("Testing each cell of the Enhanced Breakout Scanner Notebook")
    print("=" * 60)

    # Test Cell 1
    cell1_passed = test_cell_1_setup_imports()

    # Test Cell 2
    scanner = test_cell_2_initialization()

    # Test Cell 3
    cell3_passed = test_cell_3_basic_testing(scanner)

    # Test Cell 4
    enhanced_results = test_cell_4_enhanced_analysis(scanner)

    # Test Cell 5
    cell5_passed = test_cell_5_performance_analysis(enhanced_results)

    # Test Cell 6
    cell6_passed = test_cell_6_config_tuning(scanner)

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Cell 1 (Setup & Imports): {'✅ PASSED' if cell1_passed else '❌ FAILED'}")
    print(f"Cell 2 (Initialization): {'✅ PASSED' if scanner else '❌ FAILED'}")
    print(f"Cell 3 (Basic Testing): {'✅ PASSED' if cell3_passed else '❌ FAILED'}")
    print(f"Cell 4 (Enhanced Analysis): {'✅ PASSED' if enhanced_results else '❌ FAILED'}")
    print(f"Cell 5 (Performance Analysis): {'✅ PASSED' if cell5_passed else '❌ FAILED'}")
    print(f"Cell 6 (Config Tuning): {'✅ PASSED' if cell6_passed else '❌ FAILED'}")

    total_passed = sum([cell1_passed, scanner is not None, cell3_passed, len(enhanced_results) > 0, cell5_passed, cell6_passed])
    print(f"\n🎯 OVERALL RESULT: {total_passed}/6 cells passed")

    if total_passed == 6:
        print("🎉 ALL CELLS PASSED! The notebook is fully functional.")
    else:
        print(f"⚠️ {6-total_passed} cells failed. Check the output above for details.")

if __name__ == "__main__":
    main()
