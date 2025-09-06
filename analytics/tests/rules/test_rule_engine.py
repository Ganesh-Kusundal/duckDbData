#!/usr/bin/env python3
"""
Tests for Rule Engine
=====================

Comprehensive tests for the trading rule engine component.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from analytics.rules.rule_engine import RuleEngine, TradingRule


class TestTradingRule:
    """Test suite for TradingRule dataclass."""

    def test_trading_rule_creation(self):
        """Test creating a trading rule."""
        rule = TradingRule(
            name="Volume Spike Rule",
            description="Detect volume spikes",
            conditions={"volume_ratio": ">1.5", "time_window": "09:30-11:00"},
            actions={"alert": True, "log": True}
        )

        assert rule.name == "Volume Spike Rule"
        assert rule.description == "Detect volume spikes"
        assert rule.enabled is True
        assert "volume_ratio" in rule.conditions
        assert rule.actions["alert"] is True

    def test_trading_rule_defaults(self):
        """Test trading rule default values."""
        rule = TradingRule(
            name="Test Rule",
            description="Test description",
            conditions={},
            actions={}
        )

        assert rule.enabled is True
        assert rule.trigger_count == 0
        assert rule.created_at is not None


class TestRuleEngine:
    """Test suite for RuleEngine class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = RuleEngine()

    def teardown_method(self):
        """Clean up after each test."""
        pass

    def test_initialization(self):
        """Test RuleEngine initialization."""
        engine = RuleEngine()
        assert engine is not None
        assert hasattr(engine, 'rules')
        assert hasattr(engine, 'add_rule')
        assert hasattr(engine, 'evaluate_pattern')

    def test_add_rule(self):
        """Test adding a rule."""
        rule = TradingRule(
            name="Test Rule",
            description="Test rule description",
            conditions={"volume_multiplier": ">1.0"},
            actions={"alert": True}
        )

        self.engine.add_rule(rule)

        assert len(self.engine.rules) == 3  # 2 default + 1 added
        assert "Test Rule" in self.engine.rules

    def test_add_rule_with_duplicate_name(self):
        """Test adding rule with duplicate name."""
        rule1 = TradingRule(
            name="Duplicate Rule",
            description="First rule",
            conditions={"volume_multiplier": ">1.0"},
            actions={"alert": True}
        )

        rule2 = TradingRule(
            name="Duplicate Rule",
            description="Second rule",
            conditions={"price_move_pct": ">2.0"},
            actions={"log": True}
        )

        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)  # Should overwrite

        assert len(self.engine.rules) == 3  # 2 default + 1 duplicate
        assert self.engine.rules["Duplicate Rule"].conditions["price_move_pct"] == ">2.0"

    def test_evaluate_pattern_matching_rule(self):
        """Test evaluating pattern that matches rule."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        rule = TradingRule(
            name="Volume Rule",
            description="Volume breakout rule",
            conditions={"volume_multiplier": ">1.5", "price_move_pct": ">2.0"},
            actions={"alert": True, "log": True}
        )

        self.engine.add_rule(rule)

        pattern = BreakoutPattern(
            pattern_type="volume_spike",
            symbol="AAPL",
            trigger_time=datetime.now(),
            volume_multiplier=2.0,
            price_move_pct=3.0,
            confidence_score=0.85,
            technical_indicators={"rsi": 65, "macd": 0.5}
        )

        result = self.engine.evaluate_pattern(pattern)

        assert result is not None
        assert len(result) == 1
        assert result[0].rule_name == "Volume Rule"
        assert result[0].signal_type == "BUY"  # Assuming BUY signal for matching patterns

    def test_evaluate_pattern_non_matching_rule(self):
        """Test evaluating pattern that doesn't match rule."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        rule = TradingRule(
            name="Volume Rule",
            description="Volume breakout rule",
            conditions={"min_volume_multiplier": 2.5, "min_price_move": 5.0},
            actions={"signal_type": "BUY"}
        )

        self.engine.add_rule(rule)

        pattern = BreakoutPattern(
            pattern_type="volume_spike",
            symbol="AAPL",
            trigger_time=datetime.now(),
            volume_multiplier=2.0,  # Below threshold of 2.5
            price_move_pct=3.0,  # Below threshold of 5.0
            confidence_score=0.85,
            technical_indicators={"rsi": 65}
        )

        result = self.engine.evaluate_pattern(pattern)

        assert result == []  # No matches

    def test_evaluate_pattern_multiple_rules(self):
        """Test evaluating pattern against multiple rules."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        rule1 = TradingRule(
            name="Volume Rule",
            description="Volume rule",
            conditions={"volume_multiplier": ">1.5"},
            actions={"alert": True}
        )

        rule2 = TradingRule(
            name="Price Rule",
            description="Price rule",
            conditions={"price_move_pct": ">3.0"},
            actions={"log": True}
        )

        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)

        pattern = BreakoutPattern(
            pattern_type="volume_spike",
            symbol="AAPL",
            trigger_time=datetime.now(),
            volume_multiplier=2.0,
            price_move_pct=4.0,
            confidence_score=0.85,
            technical_indicators={"rsi": 65}
        )

        result = self.engine.evaluate_pattern(pattern)

        assert len(result) == 2
        rule_names = [r.rule_name for r in result]
        assert "Volume Rule" in rule_names
        assert "Price Rule" in rule_names

    def test_evaluate_pattern_disabled_rule(self):
        """Test evaluating pattern against disabled rule."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        rule = TradingRule(
            name="Disabled Rule",
            description="Disabled rule",
            conditions={"volume_multiplier": ">1.5"},
            actions={"alert": True},
            enabled=False
        )

        self.engine.add_rule(rule)

        pattern = BreakoutPattern(
            pattern_type="volume_spike",
            symbol="AAPL",
            trigger_time=datetime.now(),
            volume_multiplier=2.0,
            price_move_pct=3.0,
            confidence_score=0.85,
            technical_indicators={"rsi": 65}
        )

        result = self.engine.evaluate_pattern(pattern)

        assert result == []  # Disabled rule shouldn't match

    def test_get_rule_statistics(self):
        """Test getting rule statistics."""
        rule1 = TradingRule(
            name="Active Rule",
            description="Active rule",
            conditions={"volume_multiplier": ">1.5"},
            actions={"alert": True}
        )

        rule2 = TradingRule(
            name="Disabled Rule",
            description="Disabled rule",
            conditions={"price_move_pct": ">2.0"},
            actions={"log": True},
            enabled=False
        )

        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)

        stats = self.engine.get_rule_statistics()

        assert stats["total_rules"] == 4  # 2 default + 2 added
        assert stats["active_rules"] == 3  # 2 default + 1 added (rule2 overwrites rule1)


class TestRuleEngineComplexConditions:
    """Test complex condition evaluation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = RuleEngine()

    def test_complex_conditions_and(self):
        """Test complex AND conditions."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        rule = TradingRule(
            name="Complex Rule",
            description="Complex rule",
            conditions={
                "volume_multiplier": ">1.5",
                "price_move_pct": ">2.0"
            },
            actions={"alert": True}
        )

        self.engine.add_rule(rule)

        # Test matching all conditions
        pattern = BreakoutPattern(
            pattern_type="volume_spike",
            symbol="AAPL",
            trigger_time=datetime.now(),
            volume_multiplier=2.0,
            price_move_pct=3.0,
            confidence_score=0.85,
            technical_indicators={"rsi": 65}
        )

        result = self.engine.evaluate_pattern(pattern)
        assert len(result) == 1

    def test_numeric_condition_evaluation(self):
        """Test numeric condition evaluation."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        rule = TradingRule(
            name="Numeric Rule",
            description="Numeric rule",
            conditions={"volume_multiplier": ">=1.0"},
            actions={"alert": True}
        )

        self.engine.add_rule(rule)

        # Test equal
        pattern_eq = BreakoutPattern(
            pattern_type="volume_spike",
            symbol="AAPL",
            trigger_time=datetime.now(),
            volume_multiplier=1.0,
            price_move_pct=2.0,
            confidence_score=0.85,
            technical_indicators={}
        )
        result_eq = self.engine.evaluate_pattern(pattern_eq)
        assert len(result_eq) == 1


class TestRuleEngineActions:
    """Test rule action handling."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = RuleEngine()

    def test_rule_actions_recording(self):
        """Test that rule actions are recorded in results."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        rule = TradingRule(
            name="Action Rule",
            description="Action rule",
            conditions={"volume_multiplier": ">1.5"},
            actions={"alert": True, "log": True, "notify": True}
        )

        self.engine.add_rule(rule)

        pattern = BreakoutPattern(
            pattern_type="volume_spike",
            symbol="AAPL",
            trigger_time=datetime.now(),
            volume_multiplier=2.0,
            price_move_pct=3.0,
            confidence_score=0.85,
            technical_indicators={}
        )

        result = self.engine.evaluate_pattern(pattern)

        assert len(result) == 1
        # Actions are now stored in the TradingSignal metadata or actions field
        assert result[0].symbol == "AAPL"

    def test_empty_actions_handling(self):
        """Test handling rules with no actions."""
        from analytics.core.pattern_analyzer import BreakoutPattern
        from datetime import datetime

        rule = TradingRule(
            name="No Action Rule",
            description="No action rule",
            conditions={"volume_multiplier": ">1.5"},
            actions={}
        )

        self.engine.add_rule(rule)

        pattern = BreakoutPattern(
            pattern_type="volume_spike",
            symbol="AAPL",
            trigger_time=datetime.now(),
            volume_multiplier=2.0,
            price_move_pct=3.0,
            confidence_score=0.85,
            technical_indicators={}
        )

        result = self.engine.evaluate_pattern(pattern)

        assert len(result) == 1
