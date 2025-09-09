#!/usr/bin/env python3
"""
Demonstration of the Unified Rule-Based Scanner System

This script demonstrates the complete rule-based scanner system including:
- Rule loading and validation
- Dynamic query generation
- Signal generation
- Performance monitoring
"""

import json
from datetime import date, time
from src.rules.engine.rule_engine import RuleEngine
from src.rules.engine.execution_pipeline import ExecutionPipeline
from src.rules.schema.rule_schema import RuleSchema


def main():
    """Demonstrate the rule engine functionality."""
    print("🚀 Unified Rule-Based Scanner System Demo")
    print("=" * 50)

    # 1. Create sample rules
    print("\n📝 Creating Sample Rules...")

    breakout_rule = RuleSchema.create_breakout_rule_template(
        rule_id="demo-breakout",
        name="Demo Breakout Scanner",
        min_volume_multiplier=1.5,
        min_price_move_pct=0.025
    )

    crp_rule = RuleSchema.create_crp_rule_template(
        rule_id="demo-crp",
        name="Demo CRP Scanner",
        close_threshold_pct=2.0,
        range_threshold_pct=3.0
    )

    technical_rule = RuleSchema.create_technical_rule_template(
        rule_id="demo-technical",
        name="Demo RSI Scanner",
        rsi_condition="oversold"
    )

    rules = [breakout_rule, crp_rule, technical_rule]
    print(f"✅ Created {len(rules)} sample rules")

    # 2. Initialize Rule Engine
    print("\n🔧 Initializing Rule Engine...")
    rule_engine = RuleEngine()
    print("✅ Rule engine initialized")

    # 3. Load and validate rules
    print("\n📤 Loading Rules...")
    load_result = rule_engine.load_rules(rules)

    print(f"📊 Load Results:")
    print(f"   - Total rules: {load_result['total_rules']}")
    print(f"   - Loaded rules: {load_result['loaded_rules']}")
    print(f"   - Failed rules: {load_result['failed_rules']}")

    if load_result['validation_errors']:
        print("   - Validation errors:")
        for error in load_result['validation_errors']:
            print(f"     * {error['rule']}: {error['errors'][0]}")

    if load_result['warnings']:
        print("   - Warnings:")
        for warning in load_result['warnings']:
            print(f"     * {warning['rule']}: {warning['warnings'][0]}")

    # 4. Demonstrate rule execution
    print("\n🎯 Executing Rules...")
    scan_date = date(2025, 9, 8)

    for rule in rules:
        print(f"\n🔍 Executing rule: {rule['name']}")

        # Mock the database query execution
        import unittest.mock
        with unittest.mock.patch.object(rule_engine, '_execute_query') as mock_query:
            # Mock different results based on rule type
            if rule['rule_type'] == 'breakout':
                mock_query.return_value = [{
                    'symbol': 'AAPL',
                    'timestamp': '2025-09-08T10:30:00',
                    'price': 150.25,
                    'volume': 2500000,
                    'price_change_pct': 2.5,
                    'volume_multiplier': 2.1
                }]
            elif rule['rule_type'] == 'crp':
                mock_query.return_value = [{
                    'symbol': 'MSFT',
                    'timestamp': '2025-09-08T09:45:00',
                    'price': 305.75,
                    'volume': 1200000,
                    'close_position': 'near_high',
                    'distance_from_mid': 0.02
                }]
            else:  # technical
                mock_query.return_value = [{
                    'symbol': 'GOOGL',
                    'timestamp': '2025-09-08T11:00:00',
                    'price': 2800.50,
                    'volume': 800000,
                    'rsi': 25.5
                }]

            result = rule_engine.execute_rule(rule['rule_id'], scan_date)

            if result['success']:
                print(f"   ✅ Success: {result['signals_generated']} signals generated")
                for signal in result['signals']:
                    print(f"      📊 Signal: {signal['symbol']} {signal['signal_type']} "
                          f"(confidence: {signal['confidence']:.2f})")
            else:
                print(f"   ❌ Failed: {result['error']}")

    # 5. Show engine statistics
    print("\n📈 Engine Statistics:")
    stats = rule_engine.get_engine_stats()
    print(f"   - Total rules loaded: {stats['total_rules']}")
    print(f"   - Total executions: {stats['total_executions']}")
    print(f"   - Total signals generated: {stats['total_signals_generated']}")
    print(f"   - Query cache stats: {stats['query_cache_stats']['cache_size']} cached queries")

    # 6. Demonstrate batch execution
    print("\n🔄 Demonstrating Batch Execution...")
    pipeline = ExecutionPipeline()

    # Load rules into pipeline
    pipeline.rule_engine.load_rules(rules)
    pipeline.loaded_rules = [rule['rule_id'] for rule in rules]

    # Mock batch execution
    with unittest.mock.patch.object(pipeline.rule_engine, 'execute_rules_batch') as mock_batch:
        mock_batch.return_value = {
            'total_rules': 3,
            'successful_executions': 3,
            'failed_executions': 0,
            'total_signals': 5,
            'rule_results': {
                'demo-breakout': {'success': True, 'signals': [{'symbol': 'AAPL'}]},
                'demo-crp': {'success': True, 'signals': [{'symbol': 'MSFT'}]},
                'demo-technical': {'success': True, 'signals': [{'symbol': 'GOOGL'}]}
            }
        }

        batch_result = pipeline.execute_pipeline(scan_date)

        print("📊 Batch Results:")
        print(f"   - Total rules: {batch_result.total_rules}")
        print(f"   - Successful executions: {batch_result.executed_rules}")
        print(f"   - Total signals: {batch_result.total_signals}")
        print(f"   - Execution time: {batch_result.execution_time_ms:.2f}ms")

    # 7. Show pipeline statistics
    print("\n📊 Pipeline Statistics:")
    pipeline_stats = pipeline.get_pipeline_stats()
    print(f"   - Total executions: {pipeline_stats.get('total_executions', 0)}")
    print(f"   - Success rate: {pipeline_stats.get('success_rate', 0):.1%}")
    print(f"   - Average signals per execution: {pipeline_stats.get('avg_signals_per_execution', 0):.1f}")

    # 8. Demonstrate rule export
    print("\n💾 Exporting Results...")
    json_export = pipeline.export_results(batch_result, 'json')
    print(f"   - JSON export length: {len(json_export)} characters")

    csv_export = pipeline.export_results(batch_result, 'csv')
    print(f"   - CSV export length: {len(csv_export)} characters")

    print("\n🎉 Demo Complete!")
    print("\n💡 Key Benefits of the Rule-Based System:")
    print("   ✅ Flexible rule creation without code changes")
    print("   ✅ Dynamic SQL query generation")
    print("   ✅ Comprehensive validation and error handling")
    print("   ✅ Built-in performance monitoring")
    print("   ✅ Batch processing capabilities")
    print("   ✅ Easy rule management and deployment")


if __name__ == "__main__":
    main()
