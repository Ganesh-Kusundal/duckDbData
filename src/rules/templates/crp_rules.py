"""
CRP (Close, Range, Pattern) Scanner Rules

This module contains predefined rule templates for CRP scanning.
Each rule captures the logic and parameters from the original CRPScanner.
"""

from typing import Dict, Any, List
from datetime import time
from ..schema.rule_schema import RuleSchema


class CRPRuleTemplates:
    """Templates for CRP scanner rules."""

    @staticmethod
    def get_standard_crp_rule(
        rule_id: str = "crp-standard",
        name: str = "Standard CRP Scanner",
        close_threshold_pct: float = 2.0,
        range_threshold_pct: float = 3.0,
        min_volume: int = 50000,
        max_volume: int = 5000000,
        min_price: float = 50.0,
        max_price: float = 2000.0,
        crp_cutoff_time: str = "09:45",
        description: str = "Standard CRP detection with balanced scoring"
    ) -> Dict[str, Any]:
        """Create a standard CRP rule based on the original scanner logic."""

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "crp",
            "enabled": True,
            "priority": 50,
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": crp_cutoff_time
                },
                "crp_conditions": {
                    "close_threshold_pct": close_threshold_pct,  # Max % difference for close near high/low
                    "range_threshold_pct": range_threshold_pct,   # Max % for narrow range
                    "min_volume": min_volume,
                    "max_volume": max_volume,
                    "close_position_weight": 0.4,  # 40% weight for close position
                    "range_weight": 0.3,           # 30% weight for range tightness
                    "volume_weight": 0.2,          # 20% weight for volume pattern
                    "momentum_weight": 0.1,        # 10% weight for momentum
                    "min_probability_score": 30.0, # Minimum CRP probability score
                    "min_total_score": 0.5         # Minimum total component score
                },
                "market_conditions": {
                    "min_price": min_price,
                    "max_price": max_price
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
                "created_at": "2025-09-08T23:00:00Z",
                "version": "1.0.0",
                "tags": ["crp", "close-range-pattern", "momentum"],
                "performance_expectations": {
                    "expected_win_rate": 0.70,
                    "expected_profit_factor": 1.9,
                    "expected_max_drawdown": 0.13
                },
                "risk_assessment": {
                    "risk_level": "medium",
                    "market_conditions": "sideways",
                    "liquidity_requirements": "medium",
                    "holding_period": "intraday"
                }
            }
        }

    @staticmethod
    def get_aggressive_crp_rule(
        rule_id: str = "crp-aggressive",
        name: str = "Aggressive CRP Scanner",
        close_threshold_pct: float = 1.5,  # Tighter close threshold
        range_threshold_pct: float = 2.5,  # Tighter range threshold
        min_volume: int = 75000,           # Higher volume requirement
        max_volume: int = 5000000,
        min_price: float = 100.0,          # Higher price floor
        max_price: float = 5000.0,         # Higher price ceiling
        crp_cutoff_time: str = "10:00",
        description: str = "Aggressive CRP detection with stricter criteria"
    ) -> Dict[str, Any]:
        """Create an aggressive CRP rule with stricter thresholds."""

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "crp",
            "enabled": True,
            "priority": 60,
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": crp_cutoff_time
                },
                "crp_conditions": {
                    "close_threshold_pct": close_threshold_pct,
                    "range_threshold_pct": range_threshold_pct,
                    "min_volume": min_volume,
                    "max_volume": max_volume,
                    "close_position_weight": 0.4,
                    "range_weight": 0.3,
                    "volume_weight": 0.2,
                    "momentum_weight": 0.1,
                    "min_probability_score": 35.0,  # Higher minimum score
                    "min_total_score": 0.6          # Higher minimum total score
                },
                "market_conditions": {
                    "min_price": min_price,
                    "max_price": max_price
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
                "created_at": "2025-09-08T23:00:00Z",
                "version": "1.0.0",
                "tags": ["crp", "aggressive", "high-volume"],
                "performance_expectations": {
                    "expected_win_rate": 0.75,
                    "expected_profit_factor": 2.2,
                    "expected_max_drawdown": 0.10
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
    def get_conservative_crp_rule(
        rule_id: str = "crp-conservative",
        name: str = "Conservative CRP Scanner",
        close_threshold_pct: float = 3.0,  # Looser close threshold
        range_threshold_pct: float = 4.0,  # Looser range threshold
        min_volume: int = 25000,           # Lower volume requirement
        max_volume: int = 5000000,
        min_price: float = 50.0,
        max_price: float = 1000.0,         # Lower price ceiling
        crp_cutoff_time: str = "09:45",
        description: str = "Conservative CRP detection with relaxed criteria"
    ) -> Dict[str, Any]:
        """Create a conservative CRP rule with relaxed thresholds."""

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "crp",
            "enabled": True,
            "priority": 40,
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": crp_cutoff_time
                },
                "crp_conditions": {
                    "close_threshold_pct": close_threshold_pct,
                    "range_threshold_pct": range_threshold_pct,
                    "min_volume": min_volume,
                    "max_volume": max_volume,
                    "close_position_weight": 0.4,
                    "range_weight": 0.3,
                    "volume_weight": 0.2,
                    "momentum_weight": 0.1,
                    "min_probability_score": 25.0,  # Lower minimum score
                    "min_total_score": 0.4          # Lower minimum total score
                },
                "market_conditions": {
                    "min_price": min_price,
                    "max_price": max_price
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
                "created_at": "2025-09-08T23:00:00Z",
                "version": "1.0.0",
                "tags": ["crp", "conservative", "low-risk"],
                "performance_expectations": {
                    "expected_win_rate": 0.65,
                    "expected_profit_factor": 1.6,
                    "expected_max_drawdown": 0.18
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
    def get_high_probability_crp_rule(
        rule_id: str = "crp-high-probability",
        name: str = "High Probability CRP Scanner",
        close_threshold_pct: float = 1.0,  # Very tight close threshold
        range_threshold_pct: float = 2.0,  # Very tight range threshold
        min_volume: int = 100000,          # High volume requirement
        max_volume: int = 5000000,
        min_price: float = 200.0,          # Higher price floor for quality
        max_price: float = 3000.0,
        crp_cutoff_time: str = "09:45",
        description: str = "High probability CRP detection with strict quality filters"
    ) -> Dict[str, Any]:
        """Create a high probability CRP rule with very strict criteria."""

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "crp",
            "enabled": True,
            "priority": 70,  # Highest priority
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": crp_cutoff_time
                },
                "crp_conditions": {
                    "close_threshold_pct": close_threshold_pct,
                    "range_threshold_pct": range_threshold_pct,
                    "min_volume": min_volume,
                    "max_volume": max_volume,
                    "close_position_weight": 0.45,  # Slightly higher close weight
                    "range_weight": 0.35,           # Higher range weight
                    "volume_weight": 0.15,          # Lower volume weight
                    "momentum_weight": 0.05,        # Lower momentum weight
                    "min_probability_score": 40.0,  # High minimum score
                    "min_total_score": 0.7          # High minimum total score
                },
                "market_conditions": {
                    "min_price": min_price,
                    "max_price": max_price
                }
            },
            "actions": {
                "signal_type": "BUY",
                "confidence_calculation": "weighted_average",
                "risk_management": {
                    "stop_loss_pct": 0.01,   # Very tight 1% stop loss
                    "take_profit_pct": 0.05, # Moderate 5% take profit target
                    "max_position_size_pct": 15.0  # Allow larger positions for high quality
                }
            },
            "metadata": {
                "author": "migration_team",
                "created_at": "2025-09-08T23:00:00Z",
                "version": "1.0.0",
                "tags": ["crp", "high-probability", "premium"],
                "performance_expectations": {
                    "expected_win_rate": 0.80,
                    "expected_profit_factor": 2.5,
                    "expected_max_drawdown": 0.08
                },
                "risk_assessment": {
                    "risk_level": "low",
                    "market_conditions": "bull",
                    "liquidity_requirements": "high",
                    "holding_period": "intraday"
                }
            }
        }

    @staticmethod
    def get_all_templates() -> List[Dict[str, Any]]:
        """Get all available CRP rule templates."""
        return [
            CRPRuleTemplates.get_standard_crp_rule(),
            CRPRuleTemplates.get_aggressive_crp_rule(),
            CRPRuleTemplates.get_conservative_crp_rule(),
            CRPRuleTemplates.get_high_probability_crp_rule()
        ]

    @staticmethod
    def create_custom_crp_rule(
        rule_id: str,
        name: str,
        close_threshold_pct: float = 2.0,
        range_threshold_pct: float = 3.0,
        min_volume: int = 50000,
        max_volume: int = 5000000,
        min_stock_price: float = 50.0,
        max_stock_price: float = 2000.0,
        crp_cutoff_time: str = "09:45",
        close_position_weight: float = 0.4,
        range_weight: float = 0.3,
        volume_weight: float = 0.2,
        momentum_weight: float = 0.1,
        min_probability_score: float = 30.0,
        min_total_score: float = 0.5,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.06,
        max_position_pct: float = 10.0,
        priority: int = 50,
        description: str = None
    ) -> Dict[str, Any]:
        """Create a custom CRP rule with user-specified parameters."""

        if description is None:
            description = f"Custom CRP rule with {close_threshold_pct}% close threshold and {range_threshold_pct}% range threshold"

        return {
            "rule_id": rule_id,
            "name": name,
            "description": description,
            "rule_type": "crp",
            "enabled": True,
            "priority": priority,
            "conditions": {
                "time_window": {
                    "start": "09:15",
                    "end": crp_cutoff_time
                },
                "crp_conditions": {
                    "close_threshold_pct": close_threshold_pct,
                    "range_threshold_pct": range_threshold_pct,
                    "min_volume": min_volume,
                    "max_volume": max_volume,
                    "close_position_weight": close_position_weight,
                    "range_weight": range_weight,
                    "volume_weight": volume_weight,
                    "momentum_weight": momentum_weight,
                    "min_probability_score": min_probability_score,
                    "min_total_score": min_total_score
                },
                "market_conditions": {
                    "min_price": min_stock_price,
                    "max_price": max_stock_price
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
                "created_at": "2025-09-08T23:00:00Z",
                "version": "1.0.0",
                "tags": ["crp", "custom"],
                "performance_expectations": {
                    "expected_win_rate": 0.70,
                    "expected_profit_factor": 1.9,
                    "expected_max_drawdown": 0.13
                },
                "risk_assessment": {
                    "risk_level": "medium",
                    "market_conditions": "sideways",
                    "liquidity_requirements": "medium",
                    "holding_period": "intraday"
                }
            }
        }


# Create default CRP rules file
def create_default_crp_rules_file():
    """Create the default CRP rules JSON file."""
    import json
    from pathlib import Path

    rules_dir = Path("src/rules/templates")
    rules_dir.mkdir(parents=True, exist_ok=True)

    templates = CRPRuleTemplates.get_all_templates()

    with open(rules_dir / "crp_rules.json", 'w') as f:
        json.dump(templates, f, indent=2)

    print(f"✅ Created CRP rules file with {len(templates)} templates")


if __name__ == "__main__":
    create_default_crp_rules_file()
