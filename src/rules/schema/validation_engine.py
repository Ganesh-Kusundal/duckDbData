"""
Rule Validation Engine

This module provides comprehensive validation for trading rules including:
- JSON Schema validation
- Semantic validation
- Business logic validation
- Security validation
"""

import json
import jsonschema
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from .rule_types import (
    RuleType, SignalType, ConfidenceMethod,
    TimeWindow, BreakoutConditions, CRPConditions, TechnicalConditions
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    error_type: str  # 'schema', 'semantic', 'security', 'business'


@dataclass
class ValidationResult:
    """Result of rule validation."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    metadata: Dict[str, Any]

    def add_error(self, field: str, message: str, error_type: str = 'semantic'):
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, error_type))
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)


class RuleValidator:
    """Comprehensive rule validation engine."""

    def __init__(self, schema_path: str = None):
        """
        Initialize the validator.

        Args:
            schema_path: Path to JSON schema file
        """
        if schema_path is None:
            schema_path = 'src/rules/schema/rule_schema.json'

        self.schema = self._load_schema(schema_path)
        self._validation_cache = {}

    def _load_schema(self, schema_path: str) -> Dict[str, Any]:
        """Load JSON schema from file."""
        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schema from {schema_path}: {e}")
            raise

    def validate_rule(self, rule: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete rule definition.

        Args:
            rule: Rule definition dictionary

        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            metadata={'validation_timestamp': datetime.now().isoformat()}
        )

        # 1. JSON Schema validation
        self._validate_schema(rule, result)

        # 2. Semantic validation
        if result.is_valid:
            self._validate_semantics(rule, result)

        # 3. Business logic validation
        if result.is_valid:
            self._validate_business_logic(rule, result)

        # 4. Security validation
        self._validate_security(rule, result)

        # Cache result for performance
        result.metadata['validation_duration_ms'] = 0  # Could be enhanced with timing

        return result

    def _validate_schema(self, rule: Dict[str, Any], result: ValidationResult):
        """Validate rule against JSON schema."""
        try:
            jsonschema.validate(rule, self.schema)
            result.metadata['schema_valid'] = True
        except jsonschema.ValidationError as e:
            result.add_error(
                field=e.absolute_path[0] if e.absolute_path else 'root',
                message=e.message,
                error_type='schema'
            )
            result.metadata['schema_valid'] = False
        except Exception as e:
            # Handle other JSON schema errors
            result.add_error(
                field='schema',
                message=f"Schema validation error: {str(e)}",
                error_type='schema'
            )
            result.metadata['schema_valid'] = False
        except jsonschema.SchemaError as e:
            result.add_error(
                field='schema',
                message=f"Invalid schema definition: {e.message}",
                error_type='schema'
            )

    def _validate_semantics(self, rule: Dict[str, Any], result: ValidationResult):
        """Validate semantic correctness of the rule."""
        # Validate rule_id format
        rule_id = rule.get('rule_id', '')
        if not rule_id.replace('-', '').replace('_', '').isalnum():
            result.add_error('rule_id', 'Rule ID must contain only alphanumeric characters, hyphens, and underscores')

        # Validate time window
        if 'time_window' in rule.get('conditions', {}):
            time_window = rule['conditions']['time_window']
            if not self._validate_time_window(time_window):
                result.add_error('conditions.time_window', 'Invalid time window format')

        # Validate rule type specific conditions
        rule_type = rule.get('rule_type')
        if rule_type == 'breakout':
            self._validate_breakout_conditions(rule, result)
        elif rule_type == 'crp':
            self._validate_crp_conditions(rule, result)
        elif rule_type == 'technical':
            self._validate_technical_conditions(rule, result)

        # Validate risk management parameters
        self._validate_risk_management(rule, result)

    def _validate_business_logic(self, rule: Dict[str, Any], result: ValidationResult):
        """Validate business logic constraints."""
        conditions = rule.get('conditions', {})

        # Ensure at least one condition is defined
        if not conditions:
            result.add_warning('Rule has no conditions defined')

        # Validate price ranges
        market_conditions = conditions.get('market_conditions', {})
        min_price = market_conditions.get('min_price', 0)
        max_price = market_conditions.get('max_price', float('inf'))

        if max_price != float('inf') and min_price >= max_price:
            result.add_error('market_conditions', 'Minimum price must be less than maximum price')

        # Validate volume ranges
        min_volume = market_conditions.get('min_volume', 0)
        max_volume = market_conditions.get('max_volume', float('inf'))

        if max_volume != float('inf') and min_volume >= max_volume:
            result.add_error('market_conditions', 'Minimum volume must be less than maximum volume')

        # Validate breakout conditions make sense
        breakout_conditions = conditions.get('breakout_conditions', {})
        if breakout_conditions:
            min_move = breakout_conditions.get('min_price_move_pct', 0)
            max_move = breakout_conditions.get('max_price_move_pct', 100)

            if min_move >= max_move:
                result.add_error('breakout_conditions', 'Minimum price move must be less than maximum')

        # Validate CRP conditions
        crp_conditions = conditions.get('crp_conditions', {})
        if crp_conditions:
            close_threshold = crp_conditions.get('close_threshold_pct', 0)
            range_threshold = crp_conditions.get('range_threshold_pct', 0)

            if close_threshold <= 0 or close_threshold > 50:
                result.add_error('crp_conditions.close_threshold_pct', 'Close threshold must be between 0 and 50')

            if range_threshold <= 0 or range_threshold > 100:
                result.add_error('crp_conditions.range_threshold_pct', 'Range threshold must be between 0 and 100')

    def _validate_security(self, rule: Dict[str, Any], result: ValidationResult):
        """Validate security aspects of the rule."""
        # Check for potentially dangerous patterns
        actions = rule.get('actions', {})

        # Validate webhook URLs
        alert_settings = actions.get('alert_settings', {})
        webhook_url = alert_settings.get('webhook_url')

        if webhook_url:
            if not webhook_url.startswith(('https://', 'http://')):
                result.add_error('actions.alert_settings.webhook_url', 'Webhook URL must use HTTP or HTTPS protocol')
            elif 'localhost' in webhook_url or '127.0.0.1' in webhook_url:
                result.add_warning('Local webhook URL detected - ensure proper network security')

        # Validate execution settings
        execution_settings = actions.get('execution_settings', {})
        if execution_settings.get('auto_execute', False):
            if not rule.get('metadata', {}).get('risk_assessment', {}).get('risk_level') == 'low':
                result.add_warning('Auto-execution enabled for non-low-risk rule - additional review recommended')

        # Check for reasonable limits
        risk_mgmt = actions.get('risk_management', {})
        max_position = risk_mgmt.get('max_position_size_pct', 0)
        if max_position > 50:
            result.add_warning('Maximum position size exceeds 50% - high risk exposure')

    def _validate_time_window(self, time_window: Dict[str, Any]) -> bool:
        """Validate time window format."""
        try:
            tw = TimeWindow(
                start=time_window.get('start', ''),
                end=time_window.get('end', '')
            )
            return tw.validate()
        except:
            return False

    def _validate_breakout_conditions(self, rule: Dict[str, Any], result: ValidationResult):
        """Validate breakout-specific conditions."""
        breakout_conditions = rule.get('conditions', {}).get('breakout_conditions', {})

        # Only validate if breakout_conditions exist
        if breakout_conditions:
            # Validate volume multiplier
            volume_mult = breakout_conditions.get('min_volume_multiplier')
            if volume_mult is not None and volume_mult < 1.0:
                result.add_error('breakout_conditions.min_volume_multiplier', 'Volume multiplier must be >= 1.0')

            # Validate price move percentages
            min_move = breakout_conditions.get('min_price_move_pct')
            if min_move is not None and (min_move <= 0 or min_move > 50):
                result.add_error('breakout_conditions.min_price_move_pct', 'Price move percentage must be between 0 and 50')

    def _validate_crp_conditions(self, rule: Dict[str, Any], result: ValidationResult):
        """Validate CRP-specific conditions."""
        conditions = rule.get('conditions', {}).get('crp_conditions', {})

        # Validate consolidation period
        consolidation = conditions.get('consolidation_period', 5)
        if consolidation < 1 or consolidation > 50:
            result.add_error('crp_conditions.consolidation_period', 'Consolidation period must be between 1 and 50 days')

        # Validate thresholds
        close_threshold = conditions.get('close_threshold_pct', 2.0)
        if close_threshold <= 0 or close_threshold > 10:
            result.add_error('crp_conditions.close_threshold_pct', 'Close threshold should typically be between 0.5 and 10')

    def _validate_technical_conditions(self, rule: Dict[str, Any], result: ValidationResult):
        """Validate technical indicator conditions."""
        conditions = rule.get('conditions', {}).get('technical_conditions', {})

        # Validate RSI settings
        rsi = conditions.get('rsi', {})
        if rsi:
            rsi_period = rsi.get('period', 14)
            if rsi_period < 2 or rsi_period > 100:
                result.add_error('technical_conditions.rsi.period', 'RSI period must be between 2 and 100')

            rsi_overbought = rsi.get('overbought', 70)
            rsi_oversold = rsi.get('oversold', 30)

            if rsi_overbought <= rsi_oversold:
                result.add_error('technical_conditions.rsi', 'RSI overbought level must be greater than oversold level')

        # Validate MACD settings
        macd = conditions.get('macd', {})
        if macd:
            fast = macd.get('fast_period', 12)
            slow = macd.get('slow_period', 26)
            signal = macd.get('signal_period', 9)

            if fast >= slow:
                result.add_error('technical_conditions.macd', 'MACD fast period must be less than slow period')

    def _validate_risk_management(self, rule: Dict[str, Any], result: ValidationResult):
        """Validate risk management parameters."""
        risk_mgmt = rule.get('actions', {}).get('risk_management', {})

        stop_loss = risk_mgmt.get('stop_loss_pct')
        take_profit = risk_mgmt.get('take_profit_pct')

        if stop_loss and take_profit and stop_loss >= take_profit:
            result.add_error('actions.risk_management', 'Stop loss must be less than take profit')

        max_drawdown = risk_mgmt.get('max_drawdown_pct')
        if max_drawdown and (max_drawdown <= 0 or max_drawdown > 100):
            result.add_error('actions.risk_management.max_drawdown_pct', 'Max drawdown must be between 0 and 100')

    def validate_rule_batch(self, rules: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """Validate multiple rules at once."""
        results = {}
        for rule in rules:
            rule_id = rule.get('rule_id', 'unknown')
            results[rule_id] = self.validate_rule(rule)
        return results

    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get summary statistics for batch validation."""
        total_rules = len(results)
        valid_rules = sum(1 for r in results.values() if r.is_valid)
        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())

        return {
            'total_rules': total_rules,
            'valid_rules': valid_rules,
            'invalid_rules': total_rules - valid_rules,
            'success_rate': valid_rules / total_rules if total_rules > 0 else 0,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'average_errors_per_rule': total_errors / total_rules if total_rules > 0 else 0,
            'average_warnings_per_rule': total_warnings / total_rules if total_rules > 0 else 0
        }
