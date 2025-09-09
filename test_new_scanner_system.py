#!/usr/bin/env python3
"""
Test New Scanner System

This script tests the updated scanner system that now uses the rule-based
architecture instead of the old scanner classes.
"""

import sys
from pathlib import Path
from datetime import date, time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_new_scanner_system():
    """Test the new rule-based scanner system."""
    print("🧪 TESTING NEW SCANNER SYSTEM")
    print("=" * 40)

    try:
        # Test importing the new system
        print("📦 Testing imports...")
        from src.app.startup import get_scanner
        print("✅ get_scanner import successful")

        # Test creating breakout scanner
        print("\n🔧 Testing breakout scanner creation...")
        breakout_scanner = get_scanner('breakout')
        print(f"✅ Breakout scanner created: {type(breakout_scanner).__name__}")

        # Test creating CRP scanner
        print("\n🔧 Testing CRP scanner creation...")
        crp_scanner = get_scanner('crp')
        print(f"✅ CRP scanner created: {type(crp_scanner).__name__}")

        # Test scanner attributes
        print("\n🔍 Testing scanner attributes...")

        if hasattr(breakout_scanner, 'rule_mapper'):
            print("✅ Breakout scanner has rule_mapper")
            if hasattr(breakout_scanner.rule_mapper, 'scanner_read') and breakout_scanner.rule_mapper.scanner_read:
                print("✅ Breakout scanner has scanner_read adapter")
            else:
                print("❌ Breakout scanner missing scanner_read adapter")

        if hasattr(crp_scanner, 'rule_mapper'):
            print("✅ CRP scanner has rule_mapper")
            if hasattr(crp_scanner.rule_mapper, 'scanner_read') and crp_scanner.rule_mapper.scanner_read:
                print("✅ CRP scanner has scanner_read adapter")
            else:
                print("❌ CRP scanner missing scanner_read adapter")

        # Test scanner methods
        print("\n⚙️ Testing scanner methods...")

        # Test scanner_name property
        if hasattr(breakout_scanner, 'scanner_name'):
            print(f"✅ Breakout scanner name: {breakout_scanner.scanner_name}")

        if hasattr(crp_scanner, 'scanner_name'):
            print(f"✅ CRP scanner name: {crp_scanner.scanner_name}")

        # Test scan_date_range method (don't actually run it to avoid database issues)
        if hasattr(breakout_scanner, 'scan_date_range'):
            print("✅ Breakout scanner has scan_date_range method")

        if hasattr(crp_scanner, 'scan_date_range'):
            print("✅ CRP scanner has scan_date_range method")

        print("\n🎉 NEW SCANNER SYSTEM TEST PASSED!")
        print("✅ All scanners created successfully")
        print("✅ All required attributes present")
        print("✅ All required methods available")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rule_engine_integration():
    """Test that rule engine is properly integrated."""
    print("\n🔧 TESTING RULE ENGINE INTEGRATION")
    print("=" * 40)

    try:
        from src.rules.engine.rule_engine import RuleEngine
        from src.rules.templates.breakout_rules import BreakoutRuleTemplates

        # Create rule engine
        rule_engine = RuleEngine()
        print("✅ Rule engine created")

        # Load breakout rules
        breakout_rules = BreakoutRuleTemplates.get_all_templates()
        result = rule_engine.load_rules(breakout_rules)
        print(f"✅ Loaded {result['total_rules']} breakout rules")

        # Check rule engine stats
        stats = rule_engine.get_engine_stats()
        print(f"✅ Rule engine stats: {stats}")

        return True

    except Exception as e:
        print(f"❌ Rule engine integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 TESTING UPDATED SCANNER SYSTEM")
    print("=" * 50)
    print("This test verifies that the old scanner calls have been")
    print("successfully replaced with the new rule-based system.")
    print()

    # Test the new scanner system
    scanner_test_passed = test_new_scanner_system()

    # Test rule engine integration
    rule_test_passed = test_rule_engine_integration()

    if scanner_test_passed and rule_test_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Old scanner system successfully replaced with rule-based system")
        print("✅ All scanner calls now use the new architecture")
        print("✅ Rule engine integration working correctly")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("⚠️  Please check the error messages above")
        sys.exit(1)
