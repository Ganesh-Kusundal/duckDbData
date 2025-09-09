"""
Tests for Rule Schema Architecture

This module tests the rule schema validation, rule types, and schema utilities.
"""

import pytest
import json
from datetime import datetime

from src.rules.schema.rule_types import (
    RuleType, SignalType, ConfidenceMethod,
    TimeWindow, BreakoutConditions, CRPConditions
)
from src.rules.schema.validation_engine import RuleValidator, ValidationResult
from src.rules.schema.rule_schema import RuleSchema


class TestRuleTypes:
    """Test rule type definitions and enums."""

    def test_rule_type_enum(self):
        """Test RuleType enum values."""
        assert RuleType.BREAKOUT.value == "breakout"
        assert RuleType.CRP.value == "crp"
        assert RuleType.TECHNICAL.value == "technical"
        assert RuleType.VOLUME.value == "volume"

    def test_signal_type_enum(self):
        """Test SignalType enum values."""
        assert SignalType.BUY.value == "BUY"
        assert SignalType.SELL.value == "SELL"
        assert SignalType.HOLD.value == "HOLD"
        assert SignalType.ALERT.value == "ALERT"

    def test_confidence_method_enum(self):
        """Test ConfidenceMethod enum values."""
        assert ConfidenceMethod.WEIGHTED_AVERAGE.value == "weighted_average"
        assert ConfidenceMethod.MAX_CONDITION.value == "max_condition"
        assert ConfidenceMethod.MIN_CONDITION.value == "min_condition"

    def test_time_window_validation(self):
        """Test TimeWindow validation."""
        # Valid time window
        tw = TimeWindow(start="09:30", end="15:30")
        assert tw.validate()

        # Invalid time format
        tw_invalid = TimeWindow(start="9:30", end="15:30")
        assert not tw_invalid.validate()

        # Invalid time format 2
        tw_invalid2 = TimeWindow(start="25:30", end="15:30")
        assert not tw_invalid2.validate()


class TestRuleSchema:
    """Test rule schema utilities."""

    def test_create_breakout_rule_template(self):
        """Test breakout rule template creation."""
        rule = RuleSchema.create_breakout_rule_template(
            rule_id="test-breakout",
            name="Test Breakout Rule",
            min_volume_multiplier=2.0,
            min_price_move_pct=0.03
        )

        assert rule['rule_id'] == "test-breakout"
        assert rule['name'] == "Test Breakout Rule"
        assert rule['rule_type'] == "breakout"
        assert rule['conditions']['breakout_conditions']['min_volume_multiplier'] == 2.0
        assert rule['conditions']['breakout_conditions']['min_price_move_pct'] == 0.03

    def test_create_crp_rule_template(self):
        """Test CRP rule template creation."""
        rule = RuleSchema.create_crp_rule_template(
            rule_id="test-crp",
            name="Test CRP Rule",
            close_threshold_pct=1.5,
            range_threshold_pct=2.5
        )

        assert rule['rule_id'] == "test-crp"
        assert rule['rule_type'] == "crp"
        assert rule['conditions']['crp_conditions']['close_threshold_pct'] == 1.5
        assert rule['conditions']['crp_conditions']['range_threshold_pct'] == 2.5

    def test_create_technical_rule_template(self):
        """Test technical rule template creation."""
        rule = RuleSchema.create_technical_rule_template(
            rule_id="test-technical",
            name="Test Technical Rule",
            rsi_condition="oversold"
        )

        assert rule['rule_id'] == "test-technical"
        assert rule['rule_type'] == "technical"
        assert rule['conditions']['technical_conditions']['rsi']['condition'] == "oversold"
        assert rule['actions']['signal_type'] == "BUY"

    def test_create_volume_rule_template(self):
        """Test volume rule template creation."""
        rule = RuleSchema.create_volume_rule_template(
            rule_id="test-volume",
            name="Test Volume Rule",
            volume_multiplier=3.0
        )

        assert rule['rule_id'] == "test-volume"
        assert rule['rule_type'] == "volume"
        assert rule['conditions']['volume_conditions']['relative_volume'] == 3.0

    def test_get_rule_templates(self):
        """Test getting all rule templates."""
        templates = RuleSchema.get_rule_templates()

        assert 'breakout' in templates
        assert 'crp' in templates
        assert 'technical' in templates
        assert 'volume' in templates

        assert callable(templates['breakout'])
        assert callable(templates['crp'])

    def test_validate_rule_structure_valid(self):
        """Test validation of valid rule structure."""
        rule = RuleSchema.create_breakout_rule_template("valid-rule", "Valid Rule")
        errors = RuleSchema.validate_rule_structure(rule)

        assert len(errors) == 0

    def test_validate_rule_structure_missing_fields(self):
        """Test validation of rule with missing fields."""
        invalid_rule = {"rule_id": "test"}  # Missing required fields
        errors = RuleSchema.validate_rule_structure(invalid_rule)

        assert len(errors) > 0
        assert any("Missing required field" in error for error in errors)

    def test_validate_rule_structure_invalid_signal_type(self):
        """Test validation of rule with invalid signal type."""
        rule = RuleSchema.create_breakout_rule_template("test", "Test")
        rule['actions']['signal_type'] = "INVALID"
        errors = RuleSchema.validate_rule_structure(rule)

        assert len(errors) > 0
        assert any("Invalid signal_type" in error for error in errors)


class TestValidationEngine:
    """Test the rule validation engine."""

    @pytest.fixture
    def validator(self):
        """Create a rule validator instance."""
        return RuleValidator()

    def test_validate_valid_breakout_rule(self, validator):
        """Test validation of a valid breakout rule."""
        rule = RuleSchema.create_breakout_rule_template("valid-breakout", "Valid Breakout")
        result = validator.validate_rule(rule)

        assert result.is_valid
        assert len(result.errors) == 0
        assert 'schema_valid' in result.metadata

    def test_validate_invalid_rule_missing_required_field(self, validator):
        """Test validation of rule missing required field."""
        invalid_rule = {
            "rule_id": "test",
            "name": "Test Rule"
            # Missing rule_type, conditions, actions
        }
        result = validator.validate_rule(invalid_rule)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any(error.error_type == 'schema' for error in result.errors)

    def test_validate_business_logic_price_range(self, validator):
        """Test business logic validation for price ranges."""
        rule = RuleSchema.create_breakout_rule_template("test-price-range", "Test Price Range Validation")
        # Ensure market_conditions exists and set invalid range
        if 'market_conditions' not in rule['conditions']:
            rule['conditions']['market_conditions'] = {}
        rule['conditions']['market_conditions']['min_price'] = 100
        rule['conditions']['market_conditions']['max_price'] = 50  # Invalid: min > max

        result = validator.validate_rule(rule)

        assert not result.is_valid
        assert len(result.errors) > 0
        # Check that we have the expected error
        error_messages = [error.message for error in result.errors]
        assert any("Minimum price must be less than maximum price" in msg for msg in error_messages)

    def test_validate_breakout_conditions(self, validator):
        """Test breakout-specific condition validation."""
        rule = RuleSchema.create_breakout_rule_template("test-breakout-cond", "Test Breakout Conditions")
        rule['conditions']['breakout_conditions']['min_volume_multiplier'] = 0.5  # Invalid
        result = validator.validate_rule(rule)

        assert not result.is_valid
        assert len(result.errors) > 0
        # Check that we have the expected error
        error_messages = [error.message for error in result.errors]
        assert any("Volume multiplier must be >= 1.0" in msg for msg in error_messages)

    def test_validate_crp_conditions(self, validator):
        """Test CRP-specific condition validation."""
        rule = RuleSchema.create_crp_rule_template("test", "Test")
        rule['conditions']['crp_conditions']['close_threshold_pct'] = 15.0  # Too high
        result = validator.validate_rule(rule)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_validate_security_webhook_url(self, validator):
        """Test security validation for webhook URLs."""
        rule = RuleSchema.create_breakout_rule_template("test", "Test")
        rule['actions']['alert_settings'] = {
            'webhook_url': 'ftp://malicious.com'  # Invalid protocol
        }
        result = validator.validate_rule(rule)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("Webhook URL must use HTTP or HTTPS protocol" in error.message for error in result.errors)

    def test_validate_rule_batch(self, validator):
        """Test batch validation of multiple rules."""
        rules = [
            RuleSchema.create_breakout_rule_template("rule1", "Rule 1"),
            RuleSchema.create_crp_rule_template("rule2", "Rule 2"),
            {"rule_id": "invalid"}  # Invalid rule
        ]

        results = validator.validate_rule_batch(rules)

        assert len(results) == 3
        assert results['rule1'].is_valid
        assert results['rule2'].is_valid
        assert not results['invalid'].is_valid

    def test_get_validation_summary(self, validator):
        """Test validation summary generation."""
        results = {
            'valid1': ValidationResult(True, [], [], {}),
            'valid2': ValidationResult(True, [], [], {}),
            'invalid1': ValidationResult(False, [], [], {})
        }

        summary = validator.get_validation_summary(results)

        assert summary['total_rules'] == 3
        assert summary['valid_rules'] == 2
        assert summary['invalid_rules'] == 1
        assert summary['success_rate'] == 2/3

    def test_validation_warnings(self, validator):
        """Test that validation generates appropriate warnings."""
        rule = RuleSchema.create_breakout_rule_template("test-warnings", "Test Validation Warnings")
        # Add a risky configuration that should generate warnings
        if 'alert_settings' not in rule['actions']:
            rule['actions']['alert_settings'] = {}
        rule['actions']['alert_settings']['webhook_url'] = 'http://localhost:8080'  # Local URL warning

        if 'risk_management' not in rule['actions']:
            rule['actions']['risk_management'] = {}
        rule['actions']['risk_management']['max_position_size_pct'] = 60  # Too high warning

        result = validator.validate_rule(rule)

        assert result.is_valid  # Should still be valid
        assert len(result.warnings) >= 2  # Should have warnings for risky config
        # Check that we have the expected warnings
        warning_messages = [w for w in result.warnings]
        assert any("Local webhook URL detected" in msg for msg in warning_messages)
        assert any("Maximum position size exceeds 50%" in msg for msg in warning_messages)


class TestRuleExamples:
    """Test rule examples and templates."""

    def test_get_rule_examples(self):
        """Test getting rule examples."""
        examples = RuleSchema.get_rule_examples()

        assert 'breakout_example' in examples
        assert 'crp_example' in examples
        assert 'technical_example' in examples
        assert 'volume_example' in examples

        # Verify each example is structurally valid
        for example_name, example in examples.items():
            errors = RuleSchema.validate_rule_structure(example)
            assert len(errors) == 0, f"Example {example_name} has validation errors: {errors}"

    def test_rule_examples_completeness(self):
        """Test that examples include all required fields."""
        examples = RuleSchema.get_rule_examples()

        required_fields = ['rule_id', 'name', 'rule_type', 'conditions', 'actions']

        for example_name, example in examples.items():
            for field in required_fields:
                assert field in example, f"Example {example_name} missing required field: {field}"

    def test_rule_examples_uniqueness(self):
        """Test that examples have unique rule IDs."""
        examples = RuleSchema.get_rule_examples()
        rule_ids = [example['rule_id'] for example in examples.values()]

        assert len(rule_ids) == len(set(rule_ids)), "Rule examples must have unique IDs"
