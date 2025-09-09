#!/usr/bin/env python3
"""
Enhanced Rule Validation Framework Demo

This script demonstrates the comprehensive validation capabilities
including cross-rule validation, performance validation, environment
validation, and comprehensive reporting.
"""

import json
from datetime import date, time
from src.rules.engine.rule_engine import RuleEngine
from src.rules.validation.enhanced_validator import EnhancedRuleValidator, ValidationReport
from src.rules.templates.breakout_rules import BreakoutRuleTemplates
from src.rules.templates.crp_rules import CRPRuleTemplates


def main():
    """Demonstrate enhanced validation framework."""
    print("🔍 Enhanced Rule Validation Framework Demo")
    print("=" * 60)

    # 1. Create a comprehensive set of test rules with various issues
    print("\n📝 Creating Test Rules with Validation Issues...")

    rules = [
        # Valid rules
        BreakoutRuleTemplates.get_standard_breakout_rule(),
        CRPRuleTemplates.get_standard_crp_rule(),

        # Rule with performance issues
        {
            'rule_id': 'problematic-performance',
            'name': 'Problematic Performance Rule',
            'rule_type': 'breakout',
            'conditions': {
                'time_window': {'start': '09:15', 'end': '09:50'},
                'breakout_conditions': {'min_price_move_pct': 1.0}
            },
            'actions': {'signal_type': 'BUY'},
            'metadata': {
                'performance_expectations': {
                    'expected_win_rate': 0.98,  # Unrealistically high
                    'expected_max_drawdown': 0.85,  # Too high
                    'expected_profit_factor': 0.8  # Below breakeven
                },
                'risk_assessment': {
                    'risk_level': 'high',
                    'holding_period': 'position'  # High risk + long holding = bad combo
                }
            }
        },

        # Rule with missing required fields
        {
            'rule_id': 'incomplete-rule',
            'name': 'Incomplete Rule'
            # Missing rule_type, conditions, actions - will fail validation
        },

        # Duplicate rule (same ID)
        {
            'rule_id': 'duplicate-rule',
            'name': 'First Duplicate',
            'rule_type': 'breakout',
            'conditions': {'time_window': {'start': '09:15', 'end': '09:50'}},
            'actions': {'signal_type': 'BUY'}
        },
        {
            'rule_id': 'duplicate-rule',  # Same ID as above
            'name': 'Second Duplicate',
            'rule_type': 'crp',
            'conditions': {'time_window': {'start': '09:15', 'end': '09:50'}},
            'actions': {'signal_type': 'SELL'}
        },

        # Resource-intensive rule
        {
            'rule_id': 'resource-heavy',
            'name': 'Resource Heavy Rule',
            'rule_type': 'technical',
            'conditions': {
                'symbols': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA'],  # Many symbols
                'technical_conditions': {
                    'rsi': {'period': 14},
                    'macd': {'fast_period': 12},
                    'bollinger_bands': {'period': 20},
                    'moving_averages': {'sma_20': True, 'ema_12': True}
                }
            },
            'actions': {'signal_type': 'BUY'}
        },

        # Rule with security issues
        {
            'rule_id': 'security-issue',
            'name': 'Security Issue Rule',
            'rule_type': 'breakout',
            'conditions': {'time_window': {'start': '09:15', 'end': '09:50'}},
            'actions': {
                'signal_type': 'BUY',
                'alert_settings': {
                    'webhook_url': 'http://localhost:8080/webhook',  # Localhost URL
                    'auto_execute': True
                },
                'execution_settings': {
                    'auto_execute': True  # Auto-execution without risk assessment
                }
            }
        }
    ]

    print(f"✅ Created {len(rules)} test rules with various validation scenarios")

    # 2. Initialize enhanced validator
    print("\n🔧 Initializing Enhanced Validation Framework...")
    rule_engine = RuleEngine()
    validator = EnhancedRuleValidator(rule_engine)
    print("✅ Enhanced validator initialized")

    # 3. Run comprehensive validation
    print("\n🎯 Running Comprehensive Validation...")
    report = validator.validate_comprehensive(rules, include_environment_checks=True)

    print("📊 Validation Complete!")
    print(f"   Total Rules: {report.summary['total_rules']}")
    print(f"   Valid Rules: {report.summary['valid_rules']}")
    print(f"   Invalid Rules: {report.summary['invalid_rules']}")
    print(f"   Success Rate: {report.summary['validation_success_rate']:.1%}")
    print(f"   Overall Status: {report.summary['overall_status']}")

    # 4. Display detailed validation results
    print("\n📋 Detailed Validation Results:")
    print("=" * 50)

    # Individual rule validation
    print("\n🔍 Individual Rule Validation:")
    for rule_id, result in report.rule_reports.items():
        status = "✅ PASS" if result.is_valid else "❌ FAIL"
        errors = len(result.errors)
        warnings = len(result.warnings)
        print(f"   {rule_id}: {status} (Errors: {errors}, Warnings: {warnings})")

        if result.errors:
            for error in result.errors[:2]:  # Show first 2 errors
                print(f"     ❌ {error.field}: {error.message}")

    # Cross-rule issues
    print(f"\n🔗 Cross-Rule Issues: {len(report.cross_rule_issues)}")
    for issue in report.cross_rule_issues[:3]:  # Show first 3
        severity_icon = "🔴" if issue['type'] == 'error' else "🟡" if issue['type'] == 'warning' else "ℹ️"
        print(f"   {severity_icon} {issue['category'].title()}: {issue['message'][:60]}...")

    # Performance warnings
    print(f"\n📈 Performance Warnings: {len(report.performance_warnings)}")
    for warning in report.performance_warnings[:3]:  # Show first 3
        print(f"   ⚠️  {warning[:60]}...")

    # Environment checks
    print(f"\n🖥️  Environment Checks:")
    env = report.environment_checks
    if 'rules_by_type' in env:
        print(f"   Rules by Type: {env['rules_by_type']}")
    if 'warnings' in env and env['warnings']:
        print(f"   Warnings: {len(env['warnings'])}")
        for warning in env['warnings'][:2]:
            print(f"     ⚠️  {warning}")
    if 'errors' in env and env['errors']:
        print(f"   Errors: {len(env['errors'])}")
        for error in env['errors'][:2]:
            print(f"     ❌ {error}")

    # 5. Display recommendations
    print(f"\n💡 Actionable Recommendations: {len(report.recommendations)}")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"   {i}. {rec}")

    # 6. Demonstrate validation report export
    print("\n💾 Validation Report Export:")
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name

    try:
        validator.export_validation_report(report, temp_file)
        file_size = os.path.getsize(temp_file)
        print(f"   ✅ Report exported to: {temp_file}")
        print(f"   📊 File size: {file_size} bytes")

        # Show sample of exported JSON
        with open(temp_file, 'r') as f:
            exported_data = json.load(f)

        print("   📄 Report structure:")
        print(f"      - Summary: {len(exported_data.get('summary', {}))} metrics")
        print(f"      - Rule Reports: {len(exported_data.get('rule_reports', {}))} rules")
        print(f"      - Cross-rule Issues: {len(exported_data.get('cross_rule_issues', []))} issues")
        print(f"      - Recommendations: {len(exported_data.get('recommendations', []))} items")

    finally:
        os.unlink(temp_file)

    # 7. Demonstrate different validation scenarios
    print("\n🎭 Validation Scenario Demonstrations:")

    # Single rule validation
    print("\n   🔸 Single Rule Validation:")
    single_rule = BreakoutRuleTemplates.get_standard_breakout_rule()
    single_report = validator.validate_single_rule_comprehensive(single_rule)
    print(f"      Rule: {single_rule['rule_id']}")
    print(f"      Status: {'✅ PASS' if single_report.summary['overall_status'] == 'PASS' else '❌ FAIL'}")

    # Performance-focused validation
    print("\n   🔸 Performance Validation Example:")
    perf_rule = {
        'rule_id': 'perf-test',
        'name': 'Performance Test Rule',
        'rule_type': 'breakout',
        'conditions': {'time_window': {'start': '09:15', 'end': '09:50'}},
        'actions': {'signal_type': 'BUY'},
        'metadata': {
            'performance_expectations': {
                'expected_win_rate': 0.75,  # Good
                'expected_max_drawdown': 0.25,  # Reasonable
                'expected_profit_factor': 1.5  # Good
            }
        }
    }

    perf_warnings = validator.performance_validator.validate_performance_expectations(perf_rule)
    print(f"      Performance Warnings: {len(perf_warnings)}")
    if perf_warnings:
        for warning in perf_warnings:
            print(f"         ⚠️  {warning['message']}")
    else:
        print("         ✅ No performance issues detected")

    # 8. Validation statistics
    print("\n📊 Validation Statistics:")
    print(f"   Total Rules Processed: {report.summary['total_rules']}")
    print(f"   Rules with Warnings: {sum(1 for r in report.rule_reports.values() if r.warnings)}")
    print(f"   Rules with Errors: {sum(1 for r in report.rule_reports.values() if not r.is_valid)}")
    print(f"   Cross-Rule Issues Found: {len(report.cross_rule_issues)}")
    print(f"   Performance Warnings: {len(report.performance_warnings)}")

    # 9. Summary and benefits
    print("\n🎉 Enhanced Validation Framework Benefits:")
    print("   ✅ Comprehensive rule validation (schema, semantic, business logic)")
    print("   ✅ Cross-rule consistency checking (duplicates, conflicts, overlaps)")
    print("   ✅ Performance expectation validation (realistic targets)")
    print("   ✅ Security and environment validation")
    print("   ✅ Automated actionable recommendations")
    print("   ✅ Detailed JSON export for integration")
    print("   ✅ Modular design for custom validation rules")
    print("   ✅ Performance monitoring and optimization insights")

    print("\n🎯 Validation Framework Complete!")
    print("   The enhanced validation system provides comprehensive rule quality assurance")
    print("   and helps maintain high standards across the trading rule ecosystem.")


if __name__ == "__main__":
    main()
