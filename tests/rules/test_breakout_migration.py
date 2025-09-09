"""
Tests for Breakout Scanner Migration

This module tests the migration of the BreakoutScanner to the rule-based system,
ensuring functional equivalence and performance compatibility.
"""

import pytest
import json
from datetime import date, time
from unittest.mock import Mock, patch, MagicMock

from src.rules.engine.rule_engine import RuleEngine
from src.rules.mappers.breakout_mapper import BreakoutRuleMapper, RuleBasedBreakoutScanner
from src.rules.templates.breakout_rules import BreakoutRuleTemplates
from src.rules.schema.rule_types import RuleType


class TestBreakoutRuleTemplates:
    """Test breakout rule template generation."""

    def test_standard_template_creation(self):
        """Test creation of standard breakout rule template."""
        rule = BreakoutRuleTemplates.get_standard_breakout_rule()

        assert rule['rule_id'] == 'breakout-standard'
        assert rule['rule_type'] == 'breakout'
        assert rule['enabled'] is True
        assert rule['conditions']['breakout_conditions']['min_volume_multiplier'] == 1.5
        assert rule['conditions']['market_conditions']['min_price'] == 50
        assert rule['conditions']['market_conditions']['max_price'] == 2000
        assert rule['actions']['signal_type'] == 'BUY'

    def test_aggressive_template_creation(self):
        """Test creation of aggressive breakout rule template."""
        rule = BreakoutRuleTemplates.get_aggressive_breakout_rule()

        assert rule['rule_id'] == 'breakout-aggressive'
        assert rule['priority'] == 60  # Higher priority
        assert rule['conditions']['breakout_conditions']['min_volume_multiplier'] == 2.0
        assert rule['conditions']['breakout_conditions']['min_price_move_pct'] == 1.0
        assert rule['actions']['risk_management']['stop_loss_pct'] == 0.015

    def test_conservative_template_creation(self):
        """Test creation of conservative breakout rule template."""
        rule = BreakoutRuleTemplates.get_conservative_breakout_rule()

        assert rule['rule_id'] == 'breakout-conservative'
        assert rule['priority'] == 40  # Lower priority
        assert rule['conditions']['breakout_conditions']['min_volume_multiplier'] == 1.2
        assert rule['conditions']['breakout_conditions']['min_price_move_pct'] == 0.3
        assert rule['actions']['risk_management']['stop_loss_pct'] == 0.025

    def test_custom_template_creation(self):
        """Test creation of custom breakout rule template."""
        rule = BreakoutRuleTemplates.create_custom_breakout_rule(
            rule_id='custom-breakout',
            name='Custom Breakout',
            volume_multiplier=3.0,
            min_price_move_pct=2.0,
            min_stock_price=100,
            max_stock_price=10000,
            stop_loss_pct=0.01,
            take_profit_pct=0.10
        )

        assert rule['rule_id'] == 'custom-breakout'
        assert rule['name'] == 'Custom Breakout'
        assert rule['conditions']['breakout_conditions']['min_volume_multiplier'] == 3.0
        assert rule['conditions']['breakout_conditions']['min_price_move_pct'] == 2.0
        assert rule['conditions']['market_conditions']['min_price'] == 100
        assert rule['conditions']['market_conditions']['max_price'] == 10000
        assert rule['actions']['risk_management']['stop_loss_pct'] == 0.01
        assert rule['actions']['risk_management']['take_profit_pct'] == 0.10

    def test_all_templates_retrieval(self):
        """Test retrieval of all available templates."""
        templates = BreakoutRuleTemplates.get_all_templates()

        assert len(templates) == 3
        rule_ids = [t['rule_id'] for t in templates]
        assert 'breakout-standard' in rule_ids
        assert 'breakout-aggressive' in rule_ids
        assert 'breakout-conservative' in rule_ids


class TestBreakoutRuleMapper:
    """Test breakout rule mapper functionality."""

    @pytest.fixture
    def rule_engine(self):
        """Create mock rule engine."""
        engine = Mock(spec=RuleEngine)
        engine.load_rules = Mock()
        engine.execute_rules_batch = Mock()
        engine.rules = {}
        return engine

    @pytest.fixture
    def rule_mapper(self, rule_engine):
        """Create breakout rule mapper."""
        return BreakoutRuleMapper(rule_engine)

    def test_load_default_rules(self, rule_mapper, rule_engine):
        """Test loading of default breakout rules."""
        rule_mapper.load_default_rules()

        # Should have called load_rules
        assert rule_engine.load_rules.called

        # Check that rules were loaded
        call_args = rule_engine.load_rules.call_args
        rules = call_args[0][0]  # First positional argument
        assert len(rules) == 3  # Standard, aggressive, conservative

    def test_create_rule_from_config(self, rule_mapper):
        """Test creation of rule from original scanner config."""
        config = {
            'breakout_volume_ratio': 2.0,
            'min_price': 100,
            'max_price': 5000,
            'min_volume': 20000,
            'breakout_cutoff_time': time(10, 0),
            'stop_loss_pct': 0.015,
            'take_profit_pct': 0.08,
            'max_position_size_pct': 8.0
        }

        rule = rule_mapper.create_rule_from_config(
            rule_id='config-based-rule',
            name='Config Based Rule',
            config=config
        )

        assert rule['rule_id'] == 'config-based-rule'
        assert rule['name'] == 'Config Based Rule'
        assert rule['rule_type'] == 'breakout'
        assert rule['conditions']['breakout_conditions']['min_volume_multiplier'] == 2.0
        assert rule['conditions']['market_conditions']['min_price'] == 100
        assert rule['conditions']['market_conditions']['max_price'] == 5000
        assert rule['conditions']['time_window']['end'] == '10:00'
        assert rule['actions']['risk_management']['stop_loss_pct'] == 0.015
        assert rule['actions']['risk_management']['take_profit_pct'] == 0.08

    def test_execute_breakout_scan(self, rule_mapper, rule_engine):
        """Test execution of breakout scan."""
        # Setup mock response
        mock_batch_result = {
            'total_rules': 1,
            'successful_executions': 1,
            'failed_executions': 0,
            'total_signals': 2,
            'rule_results': {
                'test-rule': {
                    'success': True,
                    'signals': [
                        {
                            'symbol': 'AAPL',
                            'signal_type': 'BUY',
                            'confidence': 0.8,
                            'price': 150.25,
                            'volume': 100000,
                            'rule_id': 'test-rule'
                        }
                    ]
                }
            }
        }

        rule_engine.execute_rules_batch.return_value = mock_batch_result
        rule_engine.rules = {'test-rule': {'rule_type': 'breakout', 'enabled': True}}

        result = rule_mapper.execute_breakout_scan(
            scan_date=date(2025, 9, 8),
            rule_ids=['test-rule']
        )

        assert result['success'] is True
        assert result['total_rules'] == 1
        assert result['successful_executions'] == 1
        assert result['total_signals'] == 1

        # Check converted format
        signal = result['results'][0]
        assert signal['symbol'] == 'AAPL'
        assert signal['signal_type'] == 'BUY'
        assert signal['probability_score'] == 80.0  # confidence * 100

    def test_execute_date_range_scan(self, rule_mapper, rule_engine):
        """Test execution of date range breakout scan."""
        # Setup mock responses
        mock_single_result = {
            'success': True,
            'results': [
                {
                    'symbol': 'AAPL',
                    'breakout_price': 150.0,
                    'probability_score': 75.0,
                    'rule_id': 'test-rule'
                }
            ]
        }

        with patch.object(rule_mapper, 'execute_breakout_scan', return_value=mock_single_result):
            result = rule_mapper.execute_date_range_scan(
                start_date=date(2025, 9, 8),
                end_date=date(2025, 9, 10)
            )

        assert result['success'] is True
        assert 'date_range' in result
        assert 'summary' in result
        assert 'results' in result
        assert 'daily_stats' in result

    def test_get_trading_days(self, rule_mapper):
        """Test trading days generation."""
        start_date = date(2025, 9, 8)  # Sunday
        end_date = date(2025, 9, 13)   # Friday

        trading_days = rule_mapper._get_trading_days(start_date, end_date)

        # Should include Monday (9/9), Tuesday (9/10), Wednesday (9/11), Thursday (9/12), Friday (9/13)
        # Should exclude Sunday (9/8) and Saturday (if any)
        assert len(trading_days) == 5
        assert all(day.weekday() < 5 for day in trading_days)  # All weekdays


class TestRuleBasedBreakoutScanner:
    """Test rule-based breakout scanner compatibility."""

    @pytest.fixture
    def rule_engine(self):
        """Create mock rule engine."""
        engine = Mock(spec=RuleEngine)
        return engine

    @pytest.fixture
    def rule_scanner(self, rule_engine):
        """Create rule-based breakout scanner."""
        return RuleBasedBreakoutScanner(rule_engine)

    def test_scanner_initialization(self, rule_scanner, rule_engine):
        """Test scanner initialization."""
        assert rule_scanner.scanner_name == "rule_based_breakout"
        assert hasattr(rule_scanner, 'rule_mapper')

    def test_single_day_scan(self, rule_scanner):
        """Test single-day scan compatibility."""
        mock_result = {
            'success': True,
            'results': [
                {
                    'symbol': 'AAPL',
                    'breakout_price': 150.0,
                    'probability_score': 75.0
                }
            ]
        }

        with patch.object(rule_scanner.rule_mapper, 'execute_breakout_scan', return_value=mock_result):
            results = rule_scanner.scan(date(2025, 9, 8))

        assert len(results) == 1
        assert results[0]['symbol'] == 'AAPL'

    def test_date_range_scan(self, rule_scanner):
        """Test date range scan compatibility."""
        mock_result = {
            'success': True,
            'results': [
                {
                    'symbol': 'AAPL',
                    'scan_date': date(2025, 9, 8),
                    'breakout_price': 150.0
                },
                {
                    'symbol': 'GOOGL',
                    'scan_date': date(2025, 9, 9),
                    'breakout_price': 2800.0
                }
            ]
        }

        with patch.object(rule_scanner.rule_mapper, 'execute_date_range_scan', return_value=mock_result):
            results = rule_scanner.scan_date_range(
                start_date=date(2025, 9, 8),
                end_date=date(2025, 9, 10)
            )

        assert len(results) == 2
        assert results[0]['symbol'] == 'AAPL'
        assert results[1]['symbol'] == 'GOOGL'

    def test_get_config(self, rule_scanner):
        """Test configuration retrieval."""
        config = rule_scanner.get_config()

        assert config['scanner_type'] == 'rule_based'
        assert 'supported_rules' in config
        assert len(config['supported_rules']) == 3
        assert 'breakout-standard' in config['supported_rules']


class TestMigrationComparison:
    """Test comparison between original and rule-based scanners."""

    def test_result_format_compatibility(self):
        """Test that rule-based results match original scanner format."""
        # Mock rule engine result
        rule_result = {
            'success': True,
            'signals': [
                {
                    'symbol': 'AAPL',
                    'signal_type': 'BUY',
                    'confidence': 0.8,
                    'price': 150.25,
                    'volume': 100000,
                    'rule_id': 'breakout-standard'
                }
            ]
        }

        # Create mapper and convert
        from src.rules.mappers.breakout_mapper import BreakoutRuleMapper
        mapper = BreakoutRuleMapper(Mock())

        converted_results = mapper._convert_to_scanner_format({
            'rule_results': {
                'breakout-standard': rule_result
            }
        })

        assert len(converted_results) == 1
        result = converted_results[0]

        # Check required fields exist
        required_fields = [
            'symbol', 'breakout_price', 'current_volume',
            'breakout_pct', 'volume_ratio', 'probability_score'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Check data types and values
        assert result['symbol'] == 'AAPL'
        assert isinstance(result['breakout_price'], (int, float))
        assert isinstance(result['probability_score'], (int, float))
        assert result['probability_score'] == 80.0  # confidence * 100


class TestIntegrationWorkflow:
    """Test complete integration workflow."""

    def test_template_to_rule_to_execution_flow(self):
        """Test the complete flow from template to execution."""
        # Create rule from template
        rule = BreakoutRuleTemplates.get_standard_breakout_rule()

        # Validate rule structure
        from src.rules.schema.rule_schema import RuleSchema
        errors = RuleSchema.validate_rule_structure(rule)
        assert len(errors) == 0, f"Rule structure validation failed: {errors}"

        # Create rule engine and load rule
        rule_engine = RuleEngine()

        load_result = rule_engine.load_rules([rule])
        assert load_result['loaded_rules'] == 1

        # Verify rule is loaded
        assert rule['rule_id'] in rule_engine.rules
        loaded_rule = rule_engine.rules[rule['rule_id']]
        assert loaded_rule['rule_type'] == 'breakout'
        assert loaded_rule['enabled'] is True

        # Test rule execution (mock the database part)
        with patch.object(rule_engine, '_execute_query', return_value=[]):
            result = rule_engine.execute_rule(rule['rule_id'], date(2025, 9, 8))

            # Should not fail (even with no database results)
            assert 'success' in result
            assert result['rule_id'] == rule['rule_id']

    def test_multiple_rule_execution(self):
        """Test execution of multiple breakout rules."""
        # Create multiple rules
        rules = [
            BreakoutRuleTemplates.get_standard_breakout_rule(),
            BreakoutRuleTemplates.get_aggressive_breakout_rule(),
            BreakoutRuleTemplates.get_conservative_breakout_rule()
        ]

        # Create rule engine and load rules
        rule_engine = RuleEngine()
        load_result = rule_engine.load_rules(rules)
        assert load_result['loaded_rules'] == 3

        # Execute all rules
        rule_ids = [rule['rule_id'] for rule in rules]

        with patch.object(rule_engine, '_execute_query', return_value=[]):
            batch_result = rule_engine.execute_rules_batch(
                rule_ids=rule_ids,
                scan_date=date(2025, 9, 8)
            )

            assert batch_result['total_rules'] == 3
            assert len(batch_result['rule_results']) == 3

            for rule_id in rule_ids:
                assert rule_id in batch_result['rule_results']
                rule_result = batch_result['rule_results'][rule_id]
                assert 'success' in rule_result


if __name__ == "__main__":
    # Run basic validation
    print("🔍 Running breakout migration validation...")

    # Test template creation
    rule = BreakoutRuleTemplates.get_standard_breakout_rule()
    print(f"✅ Created breakout rule: {rule['rule_id']}")

    # Test rule structure validation
    from src.rules.schema.rule_schema import RuleSchema
    errors = RuleSchema.validate_rule_structure(rule)
    if errors:
        print(f"❌ Rule structure errors: {errors}")
    else:
        print("✅ Rule structure validation passed")

    # Test rule engine loading
    rule_engine = RuleEngine()
    load_result = rule_engine.load_rules([rule])

    if load_result['loaded_rules'] == 1:
        print("✅ Rule loaded successfully into engine")
    else:
        print(f"❌ Rule loading failed: {load_result}")

    print("🎉 Breakout migration validation complete!")
