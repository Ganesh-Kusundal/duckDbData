#!/usr/bin/env python3
"""
Test script to verify DuckDBManager constructor works correctly.
"""

import sys
from pathlib import Path

def test_db_manager_constructor():
    """Test DuckDBManager constructor with correct parameters."""
    print("🗄️ Testing DuckDBManager constructor...")

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
        from src.infrastructure.config.settings import get_settings
        print("✅ Imports successful")

        # Get settings
        settings = get_settings()
        print(f"✅ Settings loaded, database path: {settings.database.path}")

        # Test constructor with correct parameter name
        db_manager = create_db_manager(
            db_path=settings.database.path
        )
        print("✅ DuckDBConnectionManager works with 'db_path' parameter")

        # Test that we can connect (optional, might fail if database doesn't exist)
        try:
            conn = db_manager.connect()
            print("✅ Database connection successful")
            db_manager.close()
        except Exception as e:
            print(f"⚠️  Database connection failed (expected if database doesn't exist): {e}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 DuckDBManager Constructor Test")
    print("=" * 40)

    success = test_db_manager_constructor()

    print("\\n" + "=" * 40)
    if success:
        print("🎉 DuckDBManager constructor test PASSED!")
        print("\\n💡 The notebook should now work correctly.")
        print("   The constructor accepts 'db_path', not 'database_path'")
    else:
        print("❌ DuckDBManager constructor test FAILED!")
        print("\\n🔧 Check the error messages above.")

if __name__ == "__main__":
    main()
