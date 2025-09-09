"""
Breakout Scanner Rules

This module contains predefined rule templates for breakout scanning.
Each rule captures the logic and parameters from the original BreakoutScanner.
"""

from typing import Dict, Any, List
from datetime import time
from ..schema.rule_schema import RuleSchema


class BreakoutRuleTemplates:
    """Templates for breakout scanner rules."""

    @staticmethod
    def get_standard_breakout_rule(
        rule_id: str = "breakout-standard",
        name: str = "Standard Breakout Scanner",
        volume_multiplier: float = 1.5,
        min_price: float = 50.0,
        max_price: float = 2000.0,
        breakout_cutoff_time: str = "09:50",
        description: str = "Standard breakout detection with volume confirmation"
    ) -> Dict[str, Any]:
        """Create a standard breakout rule based on the original scanner logic."""

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "breakout",
            "enabled": True,
            "priority": 50,
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": breakout_cutoff_time
                },
                "breakout_conditions": {
                    "min_price_move_pct": 0.5,  # 0.5% breakout above close
                    "max_price_move_pct": 10.0,  # Maximum reasonable breakout
                    "min_volume_multiplier": volume_multiplier,
                    "volume_comparison_period": 5,  # 5-day average
                    "breakout_direction": "up"
                },
                "market_conditions": {
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_volume": 10000  # Minimum volume for consideration
                }
            },
            "actions": {
                "signal_type": "BUY",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": 0.02,  # 2% stop loss
                    "take_profit_pct": 0.06,  # 6% take profit
                    "max_position_size_pct": 10.0  # Max 10% of portfolio
                }
            },
            "metadata": {
                "author": "migration_team",
                "created_at": "2025-09-08T22:00:00Z",
                "version": "1.0.0",
                "tags": ["breakout", "volume", "momentum"],
                "performance_expectations": {
                    "expected_win_rate": 0.65,
                    "expected_profit_factor": 1.8,
                    "expected_max_drawdown": 0.15
                },
                "risk_assessment": {
                    "risk_level": "medium",
                    "market_conditions": "bull",
                    "liquidity_requirements": "medium",
                    "holding_period": "intraday"
                }
            }
        }

    @staticmethod
    def get_aggressive_breakout_rule(
        rule_id: str = "breakout-aggressive",
        name: str = "Aggressive Breakout Scanner",
        volume_multiplier: float = 2.0,
        min_price: float = 100.0,
        max_price: float = 5000.0,
        breakout_cutoff_time: str = "10:00",
        description: str = "Aggressive breakout detection with higher volume requirements"
    ) -> Dict[str, Any]:
        """Create an aggressive breakout rule with higher thresholds."""

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "breakout",
            "enabled": True,
            "priority": 60,
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": breakout_cutoff_time
                },
                "breakout_conditions": {
                    "min_price_move_pct": 1.0,  # 1% breakout above close
                    "max_price_move_pct": 8.0,  # Maximum reasonable breakout
                    "min_volume_multiplier": volume_multiplier,
                    "volume_comparison_period": 5,
                    "breakout_direction": "up"
                },
                "market_conditions": {
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_volume": 25000  # Higher minimum volume
                }
            },
            "actions": {
                "signal_type": "BUY",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": 0.015,  # Tighter 1.5% stop loss
                    "take_profit_pct": 0.08,  # Higher 8% take profit target
                    "max_position_size_pct": 8.0  # Slightly smaller position
                }
            },
            "metadata": {
                "author": "migration_team",
                "created_at": "2025-09-08T22:00:00Z",
                "version": "1.0.0",
                "tags": ["breakout", "aggressive", "high-volume"],
                "performance_expectations": {
                    "expected_win_rate": 0.70,
                    "expected_profit_factor": 2.1,
                    "expected_max_drawdown": 0.12
                },
                "risk_assessment": {
                    "risk_level": "medium",
                    "market_conditions": "bull",
                    "liquidity_requirements": "high",
                    "holding_period": "intraday"
                }
            }
        }

    @staticmethod
    def get_conservative_breakout_rule(
        rule_id: str = "breakout-conservative",
        name: str = "Conservative Breakout Scanner",
        volume_multiplier: float = 1.2,
        min_price: float = 50.0,
        max_price: float = 1000.0,
        breakout_cutoff_time: str = "09:45",
        description: str = "Conservative breakout detection with lower thresholds"
    ) -> Dict[str, Any]:
        """Create a conservative breakout rule with lower thresholds."""

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "breakout",
            "enabled": True,
            "priority": 40,
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": breakout_cutoff_time
                },
                "breakout_conditions": {
                    "min_price_move_pct": 0.3,  # 0.3% breakout above close
                    "max_price_move_pct": 15.0,  # Allow larger breakouts
                    "min_volume_multiplier": volume_multiplier,
                    "volume_comparison_period": 5,
                    "breakout_direction": "up"
                },
                "market_conditions": {
                    "min_price": min_price,
                    "max_price": max_price,
                    "min_volume": 5000  # Lower minimum volume
                }
            },
            "actions": {
                "signal_type": "BUY",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": 0.025,  # Wider 2.5% stop loss
                    "take_profit_pct": 0.04,  # Lower 4% take profit target
                    "max_position_size_pct": 12.0  # Larger position size allowed
                }
            },
            "metadata": {
                "author": "migration_team",
                "created_at": "2025-09-08T22:00:00Z",
                "version": "1.0.0",
                "tags": ["breakout", "conservative", "low-risk"],
                "performance_expectations": {
                    "expected_win_rate": 0.60,
                    "expected_profit_factor": 1.5,
                    "expected_max_drawdown": 0.20
                },
                "risk_assessment": {
                    "risk_level": "low",
                    "market_conditions": "sideways",
                    "liquidity_requirements": "low",
                    "holding_period": "intraday"
                }
            }
        }

    @staticmethod
    def get_all_templates() -> List[Dict[str, Any]]:
        """Get all available breakout rule templates."""
        return [
            BreakoutRuleTemplates.get_standard_breakout_rule(),
            BreakoutRuleTemplates.get_aggressive_breakout_rule(),
            BreakoutRuleTemplates.get_conservative_breakout_rule()
        ]

    @staticmethod
    def create_custom_breakout_rule(
        rule_id: str,
        name: str,
        volume_multiplier: float = 1.5,
        min_price_move_pct: float = 0.5,
        max_price_move_pct: float = 10.0,
        min_stock_price: float = 50.0,
        max_stock_price: float = 2000.0,
        min_volume: int = 10000,
        breakout_cutoff_time: str = "09:50",
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.06,
        max_position_pct: float = 10.0,
        priority: int = 50,
        description: str = None
    ) -> Dict[str, Any]:
        """Create a custom breakout rule with user-specified parameters."""

        if description is None:
            description = f"Custom breakout rule with {volume_multiplier}x volume and {min_price_move_pct}% minimum move"

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "breakout",
            "enabled": True,
            "priority": priority,
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": breakout_cutoff_time
                },
                "breakout_conditions": {
                    "min_price_move_pct": min_price_move_pct,
                    "max_price_move_pct": max_price_move_pct,
                    "min_volume_multiplier": volume_multiplier,
                    "volume_comparison_period": 5,
                    "breakout_direction": "up"
                },
                "market_conditions": {
                    "min_price": min_stock_price,
                    "max_price": max_stock_price,
                    "min_volume": min_volume
                }
            },
            "actions": {
                "signal_type": "BUY",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": stop_loss_pct,
                    "take_profit_pct": take_profit_pct,
                    "max_position_size_pct": max_position_pct
                }
            },
            "metadata": {
                "author": "custom_rule_generator",
                "created_at": "2025-09-08T22:00:00Z",
                "version": "1.0.0",
                "tags": ["breakout", "custom"],
                "performance_expectations": {
                    "expected_win_rate": 0.65,
                    "expected_profit_factor": 1.8,
                    "expected_max_drawdown": 0.15
                },
                "risk_assessment": {
                    "risk_level": "medium",
                    "market_conditions": "bull",
                    "liquidity_requirements": "medium",
                    "holding_period": "intraday"
                }
            }
        }


# Create default rule templates file
def create_default_breakout_rules_file():
    """Create the default breakout rules JSON file."""
    import json
    from pathlib import Path

    rules_dir = Path("src/rules/templates")
    rules_dir.mkdir(parents=True, exist_ok=True)

    templates = BreakoutRuleTemplates.get_all_templates()

    with open(rules_dir / "breakout_rules.json", 'w') as f:
        json.dump(templates, f, indent=2)

    print(f"✅ Created breakout rules file with {len(templates)} templates")


if __name__ == "__main__":
    create_default_breakout_rules_file()
