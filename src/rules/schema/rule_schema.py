"""
Rule Schema Helper

This module provides utilities for working with the rule schema and creating rule templates.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .rule_types import (
    RuleType, SignalType, ConfidenceMethod,
    TimeWindow, BreakoutConditions, CRPConditions, TechnicalConditions,
    RiskManagement, AlertSettings, ExecutionSettings, RuleMetadata
)


class RuleSchema:
    """Helper class for working with rule schemas and templates."""

    @staticmethod
    def create_breakout_rule_template(
        rule_id: str,
        name: str,
        min_volume_multiplier: float = 1.5,
        min_price_move_pct: float = 0.02,
        time_window_start: str = "09:35",
        time_window_end: str = "10:30"
    ) -> Dict[str, Any]:
        """Create a breakout rule template."""
        return {
            "rule_id": rule_id,
            "name": name,
            "description": f"Breakout scanner with {min_volume_multiplier}x volume and {min_price_move_pct*100}% price move",
            "rule_type": "breakout",
            "enabled": True,
            "priority": 50,
            "conditions": {
                "time_window": {
                    "start": time_window_start,
                    "end": time_window_end
                },
                "breakout_conditions": {
                    "min_price_move_pct": min_price_move_pct,
                    "max_price_move_pct": 0.10,
                    "min_volume_multiplier": min_volume_multiplier,
                    "volume_comparison_period": 10,
                    "breakout_direction": "up"
                },
                "market_conditions": {
                    "min_price": 50,
                    "max_price": 2000,
                    "min_volume": 50000
                }
            },
            "actions": {
                "signal_type": "BUY",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": min_price_move_pct * 0.5,
                    "take_profit_pct": min_price_move_pct * 2.0,
                    "max_position_size_pct": 10
                }
            },
            "metadata": {
                "author": "rule_generator",
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "tags": ["breakout", "volume", "momentum"]
            }
        }

    @staticmethod
    def create_crp_rule_template(
        rule_id: str,
        name: str,
        close_threshold_pct: float = 2.0,
        range_threshold_pct: float = 3.0,
        time_window_start: str = "09:45",
        time_window_end: str = "10:30"
    ) -> Dict[str, Any]:
        """Create a CRP rule template."""
        return {
            "rule_id": rule_id,
            "name": name,
            "description": f"CRP scanner with {close_threshold_pct}% close threshold and {range_threshold_pct}% range threshold",
            "rule_type": "crp",
            "enabled": True,
            "priority": 45,
            "conditions": {
                "time_window": {
                    "start": time_window_start,
                    "end": time_window_end
                },
                "crp_conditions": {
                    "close_threshold_pct": close_threshold_pct,
                    "range_threshold_pct": range_threshold_pct,
                    "consolidation_period": 5,
                    "close_position_preference": "any"
                },
                "market_conditions": {
                    "min_price": 50,
                    "max_price": 2000,
                    "min_volume": 25000
                }
            },
            "actions": {
                "signal_type": "BUY",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": 0.02,
                    "take_profit_pct": 0.06,
                    "max_position_size_pct": 5
                }
            },
            "metadata": {
                "author": "rule_generator",
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "tags": ["crp", "pattern", "consolidation"]
            }
        }

    @staticmethod
    def create_technical_rule_template(
        rule_id: str,
        name: str,
        rsi_condition: str = "oversold",
        time_window_start: str = "09:35",
        time_window_end: str = "15:15"
    ) -> Dict[str, Any]:
        """Create a technical analysis rule template."""
        return {
            "rule_id": rule_id,
            "name": name,
            "description": f"Technical scanner with RSI {rsi_condition} condition",
            "rule_type": "technical",
            "enabled": True,
            "priority": 40,
            "conditions": {
                "time_window": {
                    "start": time_window_start,
                    "end": time_window_end
                },
                "technical_conditions": {
                    "rsi": {
                        "period": 14,
                        "overbought": 70,
                        "oversold": 30,
                        "condition": rsi_condition
                    }
                },
                "market_conditions": {
                    "min_price": 100,
                    "max_price": 5000,
                    "min_volume": 100000
                }
            },
            "actions": {
                "signal_type": "BUY" if rsi_condition == "oversold" else "SELL",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": 0.03,
                    "take_profit_pct": 0.09,
                    "max_position_size_pct": 5
                }
            },
            "metadata": {
                "author": "rule_generator",
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "tags": ["technical", "rsi", "momentum"]
            }
        }

    @staticmethod
    def create_volume_rule_template(
        rule_id: str,
        name: str,
        volume_multiplier: float = 2.0,
        time_window_start: str = "09:35",
        time_window_end: str = "10:30"
    ) -> Dict[str, Any]:
        """Create a volume-based rule template."""
        return {
            "rule_id": rule_id,
            "name": name,
            "description": f"Volume scanner with {volume_multiplier}x volume spike",
            "rule_type": "volume",
            "enabled": True,
            "priority": 35,
            "conditions": {
                "time_window": {
                    "start": time_window_start,
                    "end": time_window_end
                },
                "volume_conditions": {
                    "min_volume": 100000,
                    "volume_trend": "increasing",
                    "relative_volume": volume_multiplier
                },
                "market_conditions": {
                    "min_price": 50,
                    "max_price": 2000
                }
            },
            "actions": {
                "signal_type": "BUY",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": 0.025,
                    "take_profit_pct": 0.075,
                    "max_position_size_pct": 8
                }
            },
            "metadata": {
                "author": "rule_generator",
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "tags": ["volume", "momentum", "breakout"]
            }
        }

    @classmethod
    def get_rule_templates(cls) -> Dict[str, callable]:
        """Get all available rule templates."""
        return {
            'breakout': cls.create_breakout_rule_template,
            'crp': cls.create_crp_rule_template,
            'technical': cls.create_technical_rule_template,
            'volume': cls.create_volume_rule_template
        }

    @staticmethod
    def save_rule_to_file(rule: Dict[str, Any], filename: str):
        """Save a rule to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(rule, f, indent=2, default=str)

    @staticmethod
    def load_rule_from_file(filename: str) -> Dict[str, Any]:
        """Load a rule from a JSON file."""
        with open(filename, 'r') as f:
            return json.load(f)

    @staticmethod
    def validate_rule_structure(rule: Dict[str, Any]) -> List[str]:
        """Basic structural validation of a rule."""
        errors = []

        required_fields = ['rule_id', 'name', 'rule_type', 'conditions', 'actions']
        for field in required_fields:
            if field not in rule:
                errors.append(f"Missing required field: {field}")

        if 'rule_type' in rule:
            valid_types = ['breakout', 'crp', 'technical', 'volume', 'momentum', 'reversal', 'trend', 'custom']
            if rule['rule_type'] not in valid_types:
                errors.append(f"Invalid rule_type: {rule['rule_type']}. Must be one of {valid_types}")

        if 'conditions' in rule:
            conditions = rule['conditions']
            if 'time_window' in conditions:
                tw = conditions['time_window']
                if not ('start' in tw and 'end' in tw):
                    errors.append("time_window must have 'start' and 'end' fields")

        if 'actions' in rule:
            actions = rule['actions']
            if 'signal_type' not in actions:
                errors.append("Missing required field in actions: signal_type")
            else:
                valid_signals = ['BUY', 'SELL', 'HOLD', 'ALERT']
                if actions['signal_type'] not in valid_signals:
                    errors.append(f"Invalid signal_type: {actions['signal_type']}. Must be one of {valid_signals}")

        return errors

    @staticmethod
    def get_rule_examples() -> Dict[str, Dict[str, Any]]:
        """Get example rules for each type."""
        return {
            'breakout_example': RuleSchema.create_breakout_rule_template(
                'breakout-volume-1.5x',
                'Volume Breakout Scanner',
                min_volume_multiplier=1.5,
                min_price_move_pct=0.025
            ),
            'crp_example': RuleSchema.create_crp_rule_template(
                'crp-high-confidence',
                'High Confidence CRP Scanner',
                close_threshold_pct=1.5,
                range_threshold_pct=2.5
            ),
            'technical_example': RuleSchema.create_technical_rule_template(
                'rsi-oversold-bounce',
                'RSI Oversold Bounce Scanner',
                rsi_condition='oversold'
            ),
            'volume_example': RuleSchema.create_volume_rule_template(
                'volume-spike-2x',
                'Volume Spike Scanner',
                volume_multiplier=2.0
            )
        }
