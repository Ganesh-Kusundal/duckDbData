#!/usr/bin/env python3
"""
Test script to verify connection to the correct database with market_data table.
"""

import sys
from pathlib import Path

def test_correct_database():
    """Test connection to the main database that has the market_data table."""
    print("🗄️ Testing connection to main database...")

    # Setup path (same as notebook)
    current_dir = Path.cwd()
    if current_dir.name == 'scanner':
        project_root = current_dir.parent.parent
    elif current_dir.name == 'notebook':
        project_root = current_dir.parent
    else:
        project_root = current_dir

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(project_root / 'src') not in sys.path:
        sys.path.insert(0, str(project_root / 'src'))

    try:
        # Import the classes
        from src.infrastructure.core.singleton_database import create_db_manager
        print("✅ Imports successful")

        # Use the main database path
        main_db_path = project_root / "data" / "financial_data.duckdb"
        print(f"📍 Database path: {main_db_path}")
        print(f"📊 Database size: {main_db_path.stat().st_size:,} bytes")

        # Initialize database manager
        db_manager = create_db_manager(db_path=str(main_db_path))
        print("✅ DuckDBConnectionManager initialized")

        # Test basic query
        print("🔍 Testing market_data table...")
        test_query = "SELECT COUNT(*) as total_records FROM market_data"
        result = db_manager.execute_custom_query(test_query)

        if not result.empty:
            total_records = result.iloc[0]['total_records']
            print(f"✅ market_data table exists with {total_records:,} records")
        else:
            print("❌ No records found in market_data table")

        # Test getting some sample data
        sample_query = "SELECT symbol, date_partition, COUNT(*) as records FROM market_data GROUP BY symbol, date_partition ORDER BY date_partition DESC, records DESC LIMIT 5"
        sample_result = db_manager.execute_custom_query(sample_query)

        if not sample_result.empty:
            print("✅ Sample data retrieved:")
            for _, row in sample_result.iterrows():
                print(f"   {row['symbol']} on {row['date_partition']}: {row['records']} records")
        else:
            print("⚠️ No sample data available")

        # Close connection
        db_manager.close()
        print("✅ Database connection closed")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Correct Database Connection Test")
    print("=" * 45)

    success = test_correct_database()

    print("\\n" + "=" * 45)
    if success:
        print("🎉 Database connection test PASSED!")
        print("\\n💡 The notebook should now work correctly.")
        print("   It will connect to the main database with all market data.")
    else:
        print("❌ Database connection test FAILED!")
        print("\\n🔧 Check the error messages above.")

if __name__ == "__main__":
    main()
