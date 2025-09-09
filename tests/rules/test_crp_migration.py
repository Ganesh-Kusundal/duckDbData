"""
Tests for CRP Scanner Migration

This module tests the migration of the CRPScanner to the rule-based system,
ensuring functional equivalence and performance compatibility.
"""

import pytest
import json
from datetime import date, time
from unittest.mock import Mock, patch, MagicMock

from src.rules.engine.rule_engine import RuleEngine
from src.rules.mappers.crp_mapper import CRPRuleMapper, RuleBasedCRPScanner
from src.rules.templates.crp_rules import CRPRuleTemplates
from src.rules.schema.rule_types import RuleType


class TestCRPRuleTemplates:
    """Test CRP rule template generation."""

    def test_standard_template_creation(self):
        """Test creation of standard CRP rule template."""
        rule = CRPRuleTemplates.get_standard_crp_rule()

        assert rule['rule_id'] == 'crp-standard'
        assert rule['rule_type'] == 'crp'
        assert rule['enabled'] is True
        assert rule['conditions']['crp_conditions']['close_threshold_pct'] == 2.0
        assert rule['conditions']['crp_conditions']['range_threshold_pct'] == 3.0
        assert rule['conditions']['market_conditions']['min_price'] == 50
        assert rule['conditions']['market_conditions']['max_price'] == 2000
        assert rule['actions']['signal_type'] == 'BUY'

    def test_aggressive_template_creation(self):
        """Test creation of aggressive CRP rule template."""
        rule = CRPRuleTemplates.get_aggressive_crp_rule()

        assert rule['rule_id'] == 'crp-aggressive'
        assert rule['priority'] == 60  # Higher priority
        assert rule['conditions']['crp_conditions']['close_threshold_pct'] == 1.5
        assert rule['conditions']['crp_conditions']['range_threshold_pct'] == 2.5
        assert rule['conditions']['crp_conditions']['min_volume'] == 75000
        assert rule['actions']['risk_management']['stop_loss_pct'] == 0.015

    def test_conservative_template_creation(self):
        """Test creation of conservative CRP rule template."""
        rule = CRPRuleTemplates.get_conservative_crp_rule()

        assert rule['rule_id'] == 'crp-conservative'
        assert rule['priority'] == 40  # Lower priority
        assert rule['conditions']['crp_conditions']['close_threshold_pct'] == 3.0
        assert rule['conditions']['crp_conditions']['range_threshold_pct'] == 4.0
        assert rule['conditions']['crp_conditions']['min_volume'] == 25000
        assert rule['actions']['risk_management']['stop_loss_pct'] == 0.025

    def test_high_probability_template_creation(self):
        """Test creation of high probability CRP rule template."""
        rule = CRPRuleTemplates.get_high_probability_crp_rule()

        assert rule['rule_id'] == 'crp-high-probability'
        assert rule['priority'] == 70  # Highest priority
        assert rule['conditions']['crp_conditions']['close_threshold_pct'] == 1.0
        assert rule['conditions']['crp_conditions']['range_threshold_pct'] == 2.0
        assert rule['conditions']['crp_conditions']['min_probability_score'] == 40.0
        assert rule['conditions']['crp_conditions']['min_total_score'] == 0.7

    def test_custom_template_creation(self):
        """Test creation of custom CRP rule template."""
        rule = CRPRuleTemplates.create_custom_crp_rule(
            rule_id='custom-crp',
            name='Custom CRP',
            close_threshold_pct=1.8,
            range_threshold_pct=2.8,
            min_volume=60000,
            min_stock_price=75,
            max_stock_price=2500,
            stop_loss_pct=0.018,
            take_profit_pct=0.07
        )

        assert rule['rule_id'] == 'custom-crp'
        assert rule['name'] == 'Custom CRP'
        assert rule['rule_type'] == 'crp'
        assert rule['conditions']['crp_conditions']['close_threshold_pct'] == 1.8
        assert rule['conditions']['crp_conditions']['range_threshold_pct'] == 2.8
        assert rule['conditions']['crp_conditions']['min_volume'] == 60000
        assert rule['conditions']['market_conditions']['min_price'] == 75
        assert rule['conditions']['market_conditions']['max_price'] == 2500
        assert rule['actions']['risk_management']['stop_loss_pct'] == 0.018
        assert rule['actions']['risk_management']['take_profit_pct'] == 0.07

    def test_all_templates_retrieval(self):
        """Test retrieval of all available templates."""
        templates = CRPRuleTemplates.get_all_templates()

        assert len(templates) == 4
        rule_ids = [t['rule_id'] for t in templates]
        assert 'crp-standard' in rule_ids
        assert 'crp-aggressive' in rule_ids
        assert 'crp-conservative' in rule_ids
        assert 'crp-high-probability' in rule_ids


class TestCRPRuleMapper:
    """Test CRP rule mapper functionality."""

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
        """Create CRP rule mapper."""
        return CRPRuleMapper(rule_engine)

    def test_load_default_rules(self, rule_mapper, rule_engine):
        """Test loading of default CRP rules."""
        rule_mapper.load_default_rules()

        # Should have called load_rules
        assert rule_engine.load_rules.called

        # Check that rules were loaded
        call_args = rule_engine.load_rules.call_args
        rules = call_args[0][0]  # First positional argument
        assert len(rules) == 4  # Standard, aggressive, conservative, high-probability

    def test_create_rule_from_config(self, rule_mapper):
        """Test creation of rule from original scanner config."""
        config = {
            'close_threshold_pct': 1.5,
            'range_threshold_pct': 2.5,
            'min_volume': 75000,
            'max_volume': 5000000,
            'min_price': 100,
            'max_price': 5000,
            'crp_cutoff_time': time(10, 0),
            'stop_loss_pct': 0.015,
            'take_profit_pct': 0.08,
            'max_position_size_pct': 8.0
        }

        rule = rule_mapper.create_rule_from_config(
            rule_id='config-based-crp',
            name='Config Based CRP Rule',
            config=config
        )

        assert rule['rule_id'] == 'config-based-crp'
        assert rule['name'] == 'Config Based CRP Rule'
        assert rule['rule_type'] == 'crp'
        assert rule['conditions']['crp_conditions']['close_threshold_pct'] == 1.5
        assert rule['conditions']['crp_conditions']['range_threshold_pct'] == 2.5
        assert rule['conditions']['market_conditions']['min_price'] == 100
        assert rule['conditions']['market_conditions']['max_price'] == 5000
        assert rule['conditions']['time_window']['end'] == '10:00'
        assert rule['actions']['risk_management']['stop_loss_pct'] == 0.015
        assert rule['actions']['risk_management']['take_profit_pct'] == 0.08

    def test_execute_crp_scan(self, rule_mapper, rule_engine):
        """Test execution of CRP scan."""
        # Setup mock response
        mock_batch_result = {
            'total_rules': 1,
            'successful_executions': 1,
            'failed_executions': 0,
            'total_signals': 2,
            'rule_results': {
                'test-crp-rule': {
                    'success': True,
                    'signals': [
                        {
                            'symbol': 'AAPL',
                            'signal_type': 'BUY',
                            'confidence': 0.85,
                            'price': 150.25,
                            'volume': 1250000,
                            'close_position': 'Near High',
                            'current_range_pct': 1.8,
                            'close_score': 0.4,
                            'range_score': 0.3,
                            'volume_score': 0.2,
                            'momentum_score': 0.1,
                            'rule_id': 'test-crp-rule'
                        }
                    ]
                }
            }
        }

        rule_engine.execute_rules_batch.return_value = mock_batch_result
        rule_engine.rules = {'test-crp-rule': {'rule_type': 'crp', 'enabled': True}}

        result = rule_mapper.execute_crp_scan(
            scan_date=date(2025, 9, 8),
            rule_ids=['test-crp-rule']
        )

        assert result['success'] is True
        assert result['total_rules'] == 1
        assert result['successful_executions'] == 1
        assert result['total_signals'] == 1

        # Check converted format
        signal = result['results'][0]
        assert signal['symbol'] == 'AAPL'
        assert signal['signal_type'] == 'BUY'
        assert signal['crp_probability_score'] == 85.0  # confidence * 100
        assert signal['close_position'] == 'Near High'

    def test_execute_date_range_scan(self, rule_mapper, rule_engine):
        """Test execution of date range CRP scan."""
        # Setup mock responses
        mock_single_result = {
            'success': True,
            'results': [
                {
                    'symbol': 'AAPL',
                    'crp_price': 150.0,
                    'crp_probability_score': 75.0,
                    'rule_id': 'test-crp-rule'
                }
            ]
        }

        with patch.object(rule_mapper, 'execute_crp_scan', return_value=mock_single_result):
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


class TestRuleBasedCRPScanner:
    """Test rule-based CRP scanner compatibility."""

    @pytest.fixture
    def rule_engine(self):
        """Create mock rule engine."""
        engine = Mock(spec=RuleEngine)
        return engine

    @pytest.fixture
    def rule_scanner(self, rule_engine):
        """Create rule-based CRP scanner."""
        return RuleBasedCRPScanner(rule_engine)

    def test_scanner_initialization(self, rule_scanner, rule_engine):
        """Test scanner initialization."""
        assert rule_scanner.scanner_name == "rule_based_crp"
        assert hasattr(rule_scanner, 'rule_mapper')

    def test_single_day_scan(self, rule_scanner):
        """Test single-day scan compatibility."""
        mock_result = {
            'success': True,
            'results': [
                {
                    'symbol': 'AAPL',
                    'crp_price': 150.0,
                    'crp_probability_score': 75.0
                }
            ]
        }

        with patch.object(rule_scanner.rule_mapper, 'execute_crp_scan', return_value=mock_result):
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
                    'crp_price': 150.0
                },
                {
                    'symbol': 'GOOGL',
                    'scan_date': date(2025, 9, 9),
                    'crp_price': 2800.0
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
        assert len(config['supported_rules']) == 4
        assert 'crp-standard' in config['supported_rules']


class TestCRPMigrationComparison:
    """Test comparison between original and rule-based CRP scanners."""

    def test_result_format_compatibility(self):
        """Test that rule-based results match original CRP scanner format."""
        # Mock rule engine result
        rule_result = {
            'success': True,
            'signals': [
                {
                    'symbol': 'AAPL',
                    'signal_type': 'BUY',
                    'confidence': 0.8,
                    'price': 150.25,
                    'volume': 1250000,
                    'close_position': 'Near High',
                    'current_range_pct': 1.8,
                    'close_score': 0.4,
                    'range_score': 0.3,
                    'volume_score': 0.2,
                    'momentum_score': 0.1,
                    'rule_id': 'crp-standard'
                }
            ]
        }

        # Create mapper and convert
        from src.rules.mappers.crp_mapper import CRPRuleMapper
        mapper = CRPRuleMapper(Mock())

        converted_results = mapper._convert_to_scanner_format({
            'rule_results': {
                'crp-standard': rule_result
            }
        })

        assert len(converted_results) == 1
        result = converted_results[0]

        # Check required fields exist
        required_fields = [
            'symbol', 'crp_price', 'current_volume', 'current_range_pct',
            'close_score', 'range_score', 'volume_score', 'momentum_score',
            'crp_probability_score', 'close_position'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Check data types and values
        assert result['symbol'] == 'AAPL'
        assert isinstance(result['crp_price'], (int, float))
        assert isinstance(result['crp_probability_score'], (int, float))
        assert result['crp_probability_score'] == 80.0  # confidence * 100
        assert result['close_position'] == 'Near High'
        assert result['close_score'] == 0.4
        assert result['range_score'] == 0.3


class TestCRPIntegrationWorkflow:
    """Test complete CRP integration workflow."""

    def test_template_to_rule_to_execution_flow(self):
        """Test the complete flow from template to execution."""
        # Create rule from template
        rule = CRPRuleTemplates.get_standard_crp_rule()

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
        assert loaded_rule['rule_type'] == 'crp'
        assert loaded_rule['enabled'] is True

        # Test rule execution (mock the database part)
        with patch.object(rule_engine, '_execute_query', return_value=[]):
            result = rule_engine.execute_rule(rule['rule_id'], date(2025, 9, 8))

            # Should not fail (even with no database results)
            assert 'success' in result
            assert result['rule_id'] == rule['rule_id']

    def test_multiple_crp_rule_execution(self):
        """Test execution of multiple CRP rules."""
        # Create multiple rules
        rules = [
            CRPRuleTemplates.get_standard_crp_rule(),
            CRPRuleTemplates.get_aggressive_crp_rule(),
            CRPRuleTemplates.get_conservative_crp_rule(),
            CRPRuleTemplates.get_high_probability_crp_rule()
        ]

        # Create rule engine and load rules
        rule_engine = RuleEngine()
        load_result = rule_engine.load_rules(rules)
        assert load_result['loaded_rules'] == 4

        # Execute all rules
        rule_ids = [rule['rule_id'] for rule in rules]

        with patch.object(rule_engine, '_execute_query', return_value=[]):
            batch_result = rule_engine.execute_rules_batch(
                rule_ids=rule_ids,
                scan_date=date(2025, 9, 8)
            )

            assert batch_result['total_rules'] == 4
            assert len(batch_result['rule_results']) == 4

            for rule_id in rule_ids:
                assert rule_id in batch_result['rule_results']
                rule_result = batch_result['rule_results'][rule_id]
                assert 'success' in rule_result


class TestCRPRuleScoringLogic:
    """Test CRP rule scoring logic and component calculations."""

    def test_crp_component_weights(self):
        """Test that CRP component weights add up correctly."""
        rule = CRPRuleTemplates.get_standard_crp_rule()
        crp_conditions = rule['conditions']['crp_conditions']

        total_weight = (
            crp_conditions['close_position_weight'] +
            crp_conditions['range_weight'] +
            crp_conditions['volume_weight'] +
            crp_conditions['momentum_weight']
        )

        assert abs(total_weight - 1.0) < 0.001, f"Component weights should sum to 1.0, got {total_weight}"

    def test_high_probability_rule_weights(self):
        """Test that high probability rule has adjusted weights."""
        rule = CRPRuleTemplates.get_high_probability_crp_rule()
        crp_conditions = rule['conditions']['crp_conditions']

        # High probability rule should have slightly different weight distribution
        assert crp_conditions['close_position_weight'] == 0.45
        assert crp_conditions['range_weight'] == 0.35
        assert crp_conditions['volume_weight'] == 0.15
        assert crp_conditions['momentum_weight'] == 0.05

        total_weight = (
            crp_conditions['close_position_weight'] +
            crp_conditions['range_weight'] +
            crp_conditions['volume_weight'] +
            crp_conditions['momentum_weight']
        )

        assert abs(total_weight - 1.0) < 0.001

    def test_conservative_vs_aggressive_thresholds(self):
        """Test that conservative and aggressive rules have appropriate thresholds."""
        conservative = CRPRuleTemplates.get_conservative_crp_rule()
        aggressive = CRPRuleTemplates.get_aggressive_crp_rule()

        # Conservative should have looser thresholds
        assert conservative['conditions']['crp_conditions']['close_threshold_pct'] > aggressive['conditions']['crp_conditions']['close_threshold_pct']
        assert conservative['conditions']['crp_conditions']['range_threshold_pct'] > aggressive['conditions']['crp_conditions']['range_threshold_pct']
        assert conservative['conditions']['crp_conditions']['min_volume'] < aggressive['conditions']['crp_conditions']['min_volume']

    def test_probability_score_thresholds(self):
        """Test that different rules have appropriate probability score thresholds."""
        standard = CRPRuleTemplates.get_standard_crp_rule()
        high_prob = CRPRuleTemplates.get_high_probability_crp_rule()

        # High probability rule should have higher minimum score
        assert high_prob['conditions']['crp_conditions']['min_probability_score'] > standard['conditions']['crp_conditions']['min_probability_score']
        assert high_prob['conditions']['crp_conditions']['min_total_score'] > standard['conditions']['crp_conditions']['min_total_score']


if __name__ == "__main__":
    # Run basic validation
    print("🔍 Running CRP migration validation...")

    # Test template creation
    rule = CRPRuleTemplates.get_standard_crp_rule()
    print(f"✅ Created CRP rule: {rule['rule_id']}")

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

    print("🎉 CRP migration validation complete!")
