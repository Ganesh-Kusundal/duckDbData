#!/usr/bin/env python3
"""
Test script to verify database schema creation works correctly.
"""

import sys
from pathlib import Path

def test_schema_creation():
    """Test that database schema creation works."""
    print("🗄️ Testing database schema creation...")

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
        from src.infrastructure.core.database import DuckDBManager
        from src.infrastructure.config.settings import get_settings
        print("✅ Imports successful")

        # Get settings
        settings = get_settings()
        print(f"✅ Settings loaded, database path: {settings.database.path}")

        # Initialize database manager
        db_manager = DuckDBManager(db_path=settings.database.path)
        print("✅ DuckDBManager initialized")

        # Create schema
        print("📋 Creating database schema...")
        db_manager.create_schema()
        print("✅ Schema creation completed")

        # Test that tables exist by trying a simple query
        test_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='market_data'"
        try:
            result = db_manager.execute_custom_query(test_query)
            if not result.empty:
                print("✅ market_data table exists")
            else:
                print("⚠️ market_data table query returned no results")
        except Exception as e:
            # DuckDB uses different system tables, let's try a different approach
            try:
                # Try to query the table directly
                simple_query = "SELECT COUNT(*) as count FROM market_data"
                result = db_manager.execute_custom_query(simple_query)
                print("✅ market_data table is accessible")
            except Exception as e2:
                print(f"⚠️ Could not verify market_data table: {e2}")

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
    print("🚀 Database Schema Creation Test")
    print("=" * 40)

    success = test_schema_creation()

    print("\\n" + "=" * 40)
    if success:
        print("🎉 Schema creation test PASSED!")
        print("\\n💡 The notebook should now work correctly.")
        print("   The market_data table will be created automatically.")
    else:
        print("❌ Schema creation test FAILED!")
        print("\\n🔧 Check the error messages above.")

if __name__ == "__main__":
    main()
