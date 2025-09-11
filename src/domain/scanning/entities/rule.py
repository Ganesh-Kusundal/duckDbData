"""
Scanning Rule Entity

This module defines the Rule entity for the Scanning domain.
Rules represent scanning strategies and criteria used to generate signals.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from domain.shared.exceptions import DomainException


class RuleType(Enum):
    """Types of scanning rules."""
    BREAKOUT = "breakout"
    CONSOLIDATION = "consolidation"
    TREND = "trend"
    VOLUME = "volume"
    MOMENTUM = "momentum"
    REVERSAL = "reversal"
    TECHNICAL = "technical"
    PATTERN = "pattern"


class RuleStatus(Enum):
    """Rule status states."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    TESTING = "testing"


@dataclass(frozen=True)
class RuleId:
    """Value object for Rule ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("RuleId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'RuleId':
        """Generate a new unique RuleId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class RuleName:
    """Value object for Rule Name."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("RuleName must be a non-empty string")
        if len(self.value) > 100:
            raise DomainException("RuleName cannot exceed 100 characters")


@dataclass(frozen=True)
class RuleLogic:
    """Value object for rule logic and conditions."""
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate rule logic."""
        if not self.conditions:
            raise DomainException("Rule must have at least one condition")
        if not self.actions:
            raise DomainException("Rule must have at least one action")

        # Validate condition structure
        for condition in self.conditions:
            if 'type' not in condition:
                raise DomainException("Each condition must have a 'type' field")
            if 'operator' not in condition:
                raise DomainException("Each condition must have an 'operator' field")

        # Validate action structure
        for action in self.actions:
            if 'type' not in action:
                raise DomainException("Each action must have a 'type' field")

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get a rule parameter with optional default."""
        return self.parameters.get(key, default)

    def add_condition(self, condition: Dict[str, Any]) -> 'RuleLogic':
        """Add a condition to the rule logic."""
        new_conditions = self.conditions + [condition]
        return RuleLogic(
            conditions=new_conditions,
            actions=self.actions,
            parameters=self.parameters
        )

    def add_action(self, action: Dict[str, Any]) -> 'RuleLogic':
        """Add an action to the rule logic."""
        new_actions = self.actions + [action]
        return RuleLogic(
            conditions=self.conditions,
            actions=new_actions,
            parameters=self.parameters
        )


@dataclass(frozen=True)
class PerformanceMetrics:
    """Value object for rule performance metrics."""
    total_signals: int = 0
    successful_signals: int = 0
    win_rate: Decimal = Decimal('0')
    avg_return: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    sharpe_ratio: Optional[Decimal] = None

    def __post_init__(self):
        """Validate performance metrics."""
        if self.total_signals < 0:
            raise DomainException("Total signals cannot be negative")
        if self.successful_signals < 0:
            raise DomainException("Successful signals cannot be negative")
        if self.successful_signals > self.total_signals:
            raise DomainException("Successful signals cannot exceed total signals")
        if not (0 <= self.win_rate <= 1):
            raise DomainException("Win rate must be between 0 and 1")

    def update_from_signals(self, signals: List[Dict[str, Any]]) -> 'PerformanceMetrics':
        """Update metrics from signal results."""
        if not signals:
            return self

        total_signals = len(signals)
        successful_signals = sum(1 for s in signals if s.get('success', False))

        win_rate = Decimal(str(successful_signals / total_signals)) if total_signals > 0 else Decimal('0')

        # Calculate average return (simplified)
        returns = [Decimal(str(s.get('return', 0))) for s in signals]
        avg_return = sum(returns) / len(returns) if returns else Decimal('0')

        return PerformanceMetrics(
            total_signals=total_signals,
            successful_signals=successful_signals,
            win_rate=win_rate,
            avg_return=avg_return,
            max_drawdown=self.max_drawdown,
            sharpe_ratio=self.sharpe_ratio
        )

    def is_profitable(self) -> bool:
        """Check if rule is profitable."""
        return self.avg_return > 0

    def get_performance_rating(self) -> str:
        """Get performance rating."""
        if self.win_rate >= Decimal('0.7') and self.avg_return > Decimal('0.05'):
            return "EXCELLENT"
        elif self.win_rate >= Decimal('0.6') and self.avg_return > Decimal('0.02'):
            return "GOOD"
        elif self.win_rate >= Decimal('0.5') and self.avg_return > 0:
            return "FAIR"
        elif self.avg_return > 0:
            return "POOR"
        else:
            return "LOSS"


@dataclass
class Rule:
    """
    Rule aggregate root.

    Represents a scanning rule with its logic, parameters,
    and performance metrics.
    """
    id: RuleId
    name: RuleName
    rule_type: RuleType
    logic: RuleLogic
    status: RuleStatus = RuleStatus.ACTIVE
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_executed_at: Optional[datetime] = None
    execution_count: int = 0

    def __post_init__(self):
        """Validate rule after initialization."""
        if self.description and len(self.description) > 500:
            raise DomainException("Rule description cannot exceed 500 characters")

    def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute the rule against market data.

        Args:
            market_data: Market data to evaluate

        Returns:
            Signal data if conditions are met, None otherwise
        """
        if self.status != RuleStatus.ACTIVE:
            return None

        # Evaluate conditions
        if self._evaluate_conditions(market_data):
            signal = self._execute_actions(market_data)
            self._update_execution_stats()
            return signal

        return None

    def _evaluate_conditions(self, market_data: Dict[str, Any]) -> bool:
        """Evaluate rule conditions against market data."""
        for condition in self.logic.conditions:
            if not self._evaluate_condition(condition, market_data):
                return False
        return True

    def _evaluate_condition(self, condition: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """Evaluate a single condition."""
        condition_type = condition['type']
        operator = condition['operator']
        value = condition.get('value')
        field = condition.get('field')

        # Get the actual value from market data
        actual_value = self._get_field_value(market_data, field) if field else value

        # Apply operator
        if operator == 'equals':
            return actual_value == value
        elif operator == 'not_equals':
            return actual_value != value
        elif operator == 'greater_than':
            return actual_value > value
        elif operator == 'less_than':
            return actual_value < value
        elif operator == 'greater_equal':
            return actual_value >= value
        elif operator == 'less_equal':
            return actual_value <= value
        elif operator == 'contains':
            return value in actual_value if isinstance(actual_value, (list, str)) else False
        else:
            raise DomainException(f"Unsupported operator: {operator}")

    def _execute_actions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute rule actions and generate signal."""
        signal = {
            'rule_id': self.id.value,
            'rule_name': self.name.value,
            'rule_type': self.rule_type.value,
            'timestamp': datetime.utcnow(),
            'market_data': market_data
        }

        for action in self.logic.actions:
            action_type = action['type']

            if action_type == 'generate_signal':
                signal.update({
                    'signal_type': action.get('signal_type', 'BUY'),
                    'confidence': action.get('confidence', 0.5),
                    'strength': action.get('strength', 'MODERATE')
                })
            elif action_type == 'set_parameters':
                signal.update(action.get('parameters', {}))

        return signal

    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value from data dictionary."""
        if not field_path:
            return None

        keys = field_path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _update_execution_stats(self) -> None:
        """Update execution statistics."""
        self.execution_count += 1
        self.last_executed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        """Activate the rule."""
        self.status = RuleStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Deactivate the rule."""
        self.status = RuleStatus.INACTIVE
        self.updated_at = datetime.utcnow()

    def is_active(self) -> bool:
        """Check if rule is active."""
        return self.status == RuleStatus.ACTIVE

    def add_tag(self, tag: str) -> None:
        """Add a tag to the rule."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the rule."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.utcnow()

    def update_performance(self, signals: List[Dict[str, Any]]) -> None:
        """Update performance metrics from signal results."""
        self.performance_metrics = self.performance_metrics.update_from_signals(signals)
        self.updated_at = datetime.utcnow()

    def get_performance_rating(self) -> str:
        """Get performance rating."""
        return self.performance_metrics.get_performance_rating()
