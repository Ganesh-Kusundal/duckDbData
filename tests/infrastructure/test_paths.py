#!/usr/bin/env python3
"""
Test script to validate path setup for the notebook.
"""

import sys
from pathlib import Path

def test_path_setup():
    """Test the path setup logic from the notebook."""
    print("🔍 Testing path setup logic...")

    # Simulate the notebook's path setup logic
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")
    print(f"Current directory name: {current_dir.name}")

    if current_dir.name == 'scanner':
        # We're in notebook/scanner/
        project_root = current_dir.parent.parent
        print("✅ Detected: Running from notebook/scanner/")
    elif current_dir.name == 'notebook':
        # We're in notebook/
        project_root = current_dir.parent
        print("✅ Detected: Running from notebook/")
    else:
        # Assume we're in project root or another location
        project_root = current_dir
        print("⚠️  Detected: Running from unknown location, assuming project root")

    print(f"Project root: {project_root}")
    print(f"Expected src path: {project_root / 'src'}")

    # Test if src directory exists
    src_path = project_root / 'src'
    if src_path.exists():
        print("✅ src directory found")
    else:
        print("❌ src directory not found")
        return False

    # Test if we can add to sys.path
    original_path = sys.path.copy()
    try:
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(src_path))

        print(f"✅ Added to sys.path: {project_root}")
        print(f"✅ Added to sys.path: {src_path}")

        # Test if we can import a simple module
        try:
            # Try to import the src module
            import src
            print("✅ src module import successful")
            return True
        except ImportError as e:
            print(f"❌ src module import failed: {e}")

            # Try alternative import
            try:
                from src.infrastructure import config
                print("✅ Alternative import successful")
                return True
            except ImportError as e2:
                print(f"❌ Alternative import also failed: {e2}")
                return False

    finally:
        # Restore original path
        sys.path = original_path
        print("✅ Restored original sys.path")

def main():
    print("🚀 Path Setup Test")
    print("=" * 30)

    success = test_path_setup()

    print("\\n" + "=" * 30)
    if success:
        print("🎉 Path setup test PASSED!")
        print("\\n💡 The notebook should now work correctly.")
    else:
        print("❌ Path setup test FAILED!")
        print("\\n🔧 Troubleshooting:")
        print("1. Make sure you're running from notebook/scanner/")
        print("2. Check that the src directory exists in the project root")
        print("3. Verify the project structure matches expectations")

if __name__ == "__main__":
    main()
