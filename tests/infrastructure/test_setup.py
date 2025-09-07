#!/usr/bin/env python3
"""
Quick test script to validate breakout scanner notebook setup.
Run this before opening the notebook to ensure everything is working.
"""

import sys
from pathlib import Path

def test_basic_imports():
    """Test basic required imports for the notebook."""
    print("🔧 Testing basic imports...")

    try:
        # Standard library imports
        import datetime
        import json
        import os
        print("✅ Standard library imports OK")

        # Data science imports
        import pandas as pd
        import numpy as np
        import plotly.graph_objects as go
        import plotly.express as px
        print("✅ Data science imports OK")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_project_structure():
    """Test that project structure is correct."""
    print("\\n📁 Testing project structure...")

    current_dir = Path.cwd()
    project_root = None

    if current_dir.name == 'scanner':
        # We're in notebook/scanner, need to go up two levels to project root
        project_root = current_dir.parent.parent
    else:
        # We're in the project root
        project_root = current_dir

    # Check if key directories exist
    required_dirs = ['src', 'configs', 'data']
    missing_dirs = []

    for dir_name in required_dirs:
        if not (project_root / dir_name).exists():
            missing_dirs.append(dir_name)

    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False

    # Check if key files exist
    required_files = [
        'src/infrastructure/logging/__init__.py',
        'src/application/scanners/strategies/breakout_scanner.py',
        'configs/config.yaml'
    ]
    missing_files = []

    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False

    print("✅ Project structure OK")
    print(f"   Project root: {project_root}")
    return True

def test_database_file():
    """Test that database file exists."""
    print("\\n🗄️ Testing database file...")

    current_dir = Path.cwd()
    project_root = current_dir.parent.parent if current_dir.name == 'scanner' else current_dir

    # Check for database files
    db_paths = [
        project_root / 'data' / 'financial_data.duckdb',
        project_root / 'financial_data.duckdb'
    ]

    for db_path in db_paths:
        if db_path.exists():
            print(f"✅ Database found: {db_path}")
            print(f"   Size: {db_path.stat().st_size:,} bytes")
            return True

    print("❌ No database file found")
    print("   Checked paths:")
    for db_path in db_paths:
        print(f"   - {db_path}")
    return False

def test_database_connection():
    """Test database connection."""
    print("\\n🗄️ Testing database connection...")

    try:
        from src.infrastructure.config.settings import get_settings
        from src.infrastructure.core.database import DuckDBManager

        settings = get_settings()
        db_manager = DuckDBManager(
            database_path=settings.database.path,
            read_only=True
        )

        # Simple test query
        test_query = "SELECT COUNT(*) as count FROM market_data LIMIT 1"
        result = db_manager.execute_custom_query(test_query)

        if not result.empty:
            print(f"✅ Database connection OK - Found {result.iloc[0]['count']} records")
            return True
        else:
            print("⚠️ Database connection OK but no data found")
            return True

    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Breakout Scanner Notebook Setup Test")
    print("=" * 50)

    tests = [
        ("Basic Import Test", test_basic_imports),
        ("Project Structure Test", test_project_structure),
        ("Database File Test", test_database_file),
        ("Database Connection Test", test_database_connection),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\\n{test_name}")
        print("-" * len(test_name))
        result = test_func()
        results.append((test_name, result))

    # Summary
    print("\\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\\n📊 Results: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\\n🎉 All tests passed! You can safely run the notebook.")
        print("\\n💡 To run the notebook:")
        print("   cd notebook/scanner")
        print("   jupyter notebook breakout_scanner_test.ipynb")
    else:
        print("\\n⚠️ Some tests failed. Please fix the issues before running the notebook.")
        print("\\n🔧 Common fixes:")
        print("   - Install missing packages: pip install -r requirements.txt")
        print("   - Check database path in configuration")
        print("   - Verify Python path includes project src directory")

if __name__ == "__main__":
    main()
