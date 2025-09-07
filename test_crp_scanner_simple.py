#!/usr/bin/env python3
"""
Simple CRP Scanner Test Script
Tests CRP scanner functionality with proper imports
"""

import sys
import os
from pathlib import Path
from datetime import date, time, timedelta

# Add project root to Python path
current_dir = Path.cwd()
project_root = current_dir
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

def main():
    """Test CRP scanner functionality."""
    print("🎯 CRP Scanner Simple Test")
    print("=" * 40)

    try:
        # Import CRP Scanner
        from src.application.scanners.strategies.crp_scanner import CRPScanner

        print("✅ CRP Scanner imported successfully!")

        # Initialize scanner
        scanner = CRPScanner()
        print("✅ CRP Scanner initialized successfully!")
        print(f"📊 Scanner name: {scanner.scanner_name}")

        # Display configuration
        print("\n🎯 CRP Scanner Configuration:")
        print(f"   Close Threshold: {scanner.config['close_threshold_pct']}%")
        print(f"   Range Threshold: {scanner.config['range_threshold_pct']}%")
        print(f"   Min Volume: {scanner.config['min_volume']:,}")
        print(f"   Max Results Per Day: {scanner.config['max_results_per_day']}")

        # Test basic functionality
        scan_date = date.today() - timedelta(days=1)
        print(f"\n📅 Test scan date: {scan_date}")

        # Get available symbols (test database connection)
        try:
            symbols = scanner.get_available_symbols()
            print(f"✅ Database connection successful! Found {len(symbols)} symbols")

            # Test single day scan
            print("\n🔍 Testing single day CRP scan...")
            results = scanner.scan(scan_date, time(9, 50))

            if not results.empty:
                print(f"✅ Found {len(results)} CRP patterns")
                print("\n📊 Top 3 CRP Results:")
                print(results.head(3).to_string(index=False))
            else:
                print("⚠️  No CRP patterns found (this is normal if no data matches criteria)")

        except Exception as db_error:
            print(f"⚠️  Database connection issue: {db_error}")
            print("💡 This might be expected if the database file doesn't exist or has no data")

        print("\n🎯 CRP Scanner Test Complete!")
        print("\n💡 To use in Jupyter notebooks, add this at the beginning of your cells:")
        print("""
import sys
from pathlib import Path

# Add project root to Python path
current_dir = Path.cwd()
if current_dir.name == 'scanner':
    project_root = current_dir.parent.parent
elif current_dir.name == 'notebook':
    project_root = current_dir.parent
else:
    project_root = current_dir

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Now you can import
from src.application.scanners.strategies.crp_scanner import CRPScanner
        """)

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n🔧 To fix import issues:")
        print("1. Make sure you're running from the project root directory")
        print("2. Or add the project root and src directory to Python path")
        print("3. Check that all required dependencies are installed")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
