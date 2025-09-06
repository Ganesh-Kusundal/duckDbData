#!/usr/bin/env python3
"""
Analytics Module Structure Tests
================================

Comprehensive tests for analytics module structure and integration.
"""

import sys
import os
import importlib
from pathlib import Path

def test_file_structure():
    """Test that all required files exist."""
    print("Testing file structure...")

    analytics_dir = Path(__file__).parent.parent

    required_files = [
        "core/__init__.py",
        "core/duckdb_connector.py",
        "core/pattern_analyzer.py",
        "rules/__init__.py",
        "rules/rule_engine.py",
        "rules/default_rules.json",
        "utils/__init__.py",
        "utils/data_processor.py",
        "utils/visualization.py",
        "dashboard/app.py",
        "queries/breakout_patterns.sql",
        "README.md",
        "requirements.txt",
        "run_dashboard.py",
        # Test structure
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/test_module_structure.py",
        "tests/core/test_duckdb_connector.py",
        "tests/core/test_pattern_analyzer.py",
        "tests/rules/test_rule_engine.py",
        "tests/utils/test_data_processor.py",
        "tests/utils/test_visualization.py",
        "tests/dashboard/test_app.py"
    ]

    missing_files = []
    for file_path in required_files:
        full_path = analytics_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_python_syntax():
    """Test that all Python files have valid syntax."""
    print("\nTesting Python syntax...")

    analytics_dir = Path(__file__).parent.parent

    python_files = [
        "core/__init__.py",
        "core/duckdb_connector.py",
        "core/pattern_analyzer.py",
        "rules/__init__.py",
        "rules/rule_engine.py",
        "utils/__init__.py",
        "utils/data_processor.py",
        "utils/visualization.py",
        "dashboard/app.py",
        "run_dashboard.py",
        # Test files
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/test_module_structure.py",
        "tests/core/test_duckdb_connector.py",
        "tests/core/test_pattern_analyzer.py",
        "tests/rules/test_rule_engine.py",
        "tests/utils/test_data_processor.py",
        "tests/utils/test_visualization.py",
        "tests/dashboard/test_app.py"
    ]

    syntax_errors = []
    for py_file in python_files:
        file_path = analytics_dir / py_file
        try:
            with open(file_path, 'r') as f:
                compile(f.read(), str(file_path), 'exec')
        except SyntaxError as e:
            syntax_errors.append(f"{py_file}: {e}")
        except Exception as e:
            syntax_errors.append(f"{py_file}: {e}")

    if syntax_errors:
        print(f"❌ Syntax errors: {syntax_errors}")
        return False
    else:
        print("✅ All Python files have valid syntax")
        return True

def test_imports():
    """Test that key components can be imported."""
    print("\nTesting component imports...")

    analytics_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(analytics_dir))

    import_tests = [
        ("core.duckdb_connector", "DuckDBAnalytics"),
        ("core.pattern_analyzer", "PatternAnalyzer"),
        ("rules.rule_engine", "RuleEngine", "TradingRule"),
        ("utils.data_processor", "DataProcessor"),
        ("utils.visualization", "AnalyticsVisualizer")
    ]

    failed_imports = []
    for import_test in import_tests:
        module_name = import_test[0]
        class_names = import_test[1:]

        try:
            module = importlib.import_module(module_name)
            for class_name in class_names:
                getattr(module, class_name)
        except Exception as e:
            failed_imports.append(f"{module_name}: {e}")

    if failed_imports:
        print(f"❌ Import failures: {failed_imports}")
        return False
    else:
        print("✅ All key components can be imported")
        return True

def test_dashboard_structure():
    """Test dashboard file structure."""
    print("\nTesting dashboard structure...")

    dashboard_path = Path(__file__).parent.parent / "dashboard" / "app.py"
    if dashboard_path.exists():
        # Check if it contains key components
        with open(dashboard_path, 'r') as f:
            content = f.read()
            required_components = ["streamlit", "analytics", "tab", "dashboard", "pattern"]

            missing_components = []
            for component in required_components:
                if component.lower() not in content.lower():
                    missing_components.append(component)

            if missing_components:
                print(f"❌ Dashboard missing components: {missing_components}")
                return False
            else:
                print("✅ Dashboard app.py found and contains expected content")
                return True
    else:
        print("❌ Dashboard app.py not found")
        return False

def test_test_structure():
    """Test that test structure is properly organized."""
    print("\nTesting test structure...")

    analytics_dir = Path(__file__).parent

    test_files = [
        "__init__.py",
        "conftest.py",
        "core/",
        "rules/",
        "utils/",
        "dashboard/"
    ]

    missing_tests = []
    for test_path in test_files:
        full_path = analytics_dir / test_path
        if not (full_path.exists() or (full_path.is_dir() and any(full_path.iterdir()))):
            missing_tests.append(test_path)

    if missing_tests:
        print(f"❌ Missing test components: {missing_tests}")
        return False
    else:
        print("✅ Test structure is properly organized")
        return True

def test_dependencies():
    """Test that required dependencies are specified."""
    print("\nTesting dependencies...")

    analytics_dir = Path(__file__).parent.parent
    requirements_path = analytics_dir / "requirements.txt"
    if requirements_path.exists():
        with open(requirements_path, 'r') as f:
            requirements = f.read().lower()

        required_deps = ["streamlit", "pandas", "duckdb", "plotly"]
        missing_deps = []

        for dep in required_deps:
            if dep not in requirements:
                missing_deps.append(dep)

        if missing_deps:
            print(f"❌ Missing dependencies: {missing_deps}")
            return False
        else:
            print("✅ All required dependencies specified")
            return True
    else:
        print("❌ requirements.txt not found")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Analytics Module Structure")
    print("=" * 50)

    tests = [
        ("File Structure", test_file_structure),
        ("Python Syntax", test_python_syntax),
        ("Component Imports", test_imports),
        ("Dashboard Structure", test_dashboard_structure),
        ("Test Structure", test_test_structure),
        ("Dependencies", test_dependencies)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All analytics structure tests passed!")
        print("\n🚀 Analytics module is ready!")
        print("   Run tests: python -m pytest tests/")
        print("   Run dashboard: python run_dashboard.py")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
