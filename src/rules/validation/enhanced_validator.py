"""
Enhanced Rule Validation Framework

This module provides advanced rule validation capabilities including:
- Cross-rule validation and dependency checking
- Performance validation and backtest requirements
- Environment validation and resource checking
- Rule consistency and versioning validation
- Advanced business logic validation
- Comprehensive validation reporting
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import re

from ..engine.rule_engine import RuleEngine
from ..schema.validation_engine import RuleValidator, ValidationResult, ValidationError
from ..schema.rule_types import RuleType

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    summary: Dict[str, Any] = field(default_factory=dict)
    rule_reports: Dict[str, ValidationResult] = field(default_factory=dict)
    cross_rule_issues: List[Dict[str, Any]] = field(default_factory=list)
    performance_warnings: List[str] = field(default_factory=list)
    environment_checks: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RuleDependency:
    """Represents a rule dependency."""
    rule_id: str
    dependency_type: str  # 'requires', 'conflicts', 'enhances', 'supersedes'
    target_rule_id: str
    reason: str
    severity: str  # 'error', 'warning', 'info'


class CrossRuleValidator:
    """Validates relationships between rules."""

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine
        self.dependencies: Dict[str, List[RuleDependency]] = {}

    def validate_cross_rule_consistency(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate consistency across multiple rules."""
        issues = []

        # Check for duplicate rule IDs
        rule_ids = [rule.get('rule_id') for rule in rules]
        duplicates = set([x for x in rule_ids if rule_ids.count(x) > 1])
        for duplicate in duplicates:
            issues.append({
                'type': 'error',
                'category': 'consistency',
                'message': f'Duplicate rule ID found: {duplicate}',
                'affected_rules': [duplicate],
                'severity': 'high'
            })

        # Check for conflicting conditions
        issues.extend(self._check_condition_conflicts(rules))

        # Check for overlapping signal types
        issues.extend(self._check_signal_overlaps(rules))

        # Check for resource conflicts
        issues.extend(self._check_resource_conflicts(rules))

        return issues

    def _check_condition_conflicts(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for conflicting conditions between rules."""
        issues = []

        for i, rule1 in enumerate(rules):
            for j, rule2 in enumerate(rules[i+1:], i+1):
                rule1_id = rule1.get('rule_id')
                rule2_id = rule2.get('rule_id')

                # Check for identical conditions (potential redundancy)
                if self._conditions_similar(rule1, rule2):
                    issues.append({
                        'type': 'warning',
                        'category': 'redundancy',
                        'message': f'Rules {rule1_id} and {rule2_id} have very similar conditions',
                        'affected_rules': [rule1_id, rule2_id],
                        'severity': 'medium'
                    })

                # Check for mutually exclusive conditions
                if self._conditions_mutually_exclusive(rule1, rule2):
                    issues.append({
                        'type': 'info',
                        'category': 'logic',
                        'message': f'Rules {rule1_id} and {rule2_id} have mutually exclusive conditions',
                        'affected_rules': [rule1_id, rule2_id],
                        'severity': 'low'
                    })

        return issues

    def _check_signal_overlaps(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for overlapping signal types that might conflict."""
        issues = []

        signal_groups = {}
        for rule in rules:
            rule_id = rule.get('rule_id')
            signal_type = rule.get('actions', {}).get('signal_type')
            rule_type = rule.get('rule_type')

            if signal_type:
                key = f"{signal_type}_{rule_type}"
                if key not in signal_groups:
                    signal_groups[key] = []
                signal_groups[key].append(rule_id)

        # Check for too many rules of same type generating same signal
        for signal_key, rule_ids in signal_groups.items():
            if len(rule_ids) > 5:
                issues.append({
                    'type': 'warning',
                    'category': 'performance',
                    'message': f'Too many rules ({len(rule_ids)}) generating {signal_key} signals',
                    'affected_rules': rule_ids,
                    'severity': 'medium'
                })

        return issues

    def _check_resource_conflicts(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for potential resource conflicts between rules."""
        issues = []

        # Check for rules that might compete for same symbols
        symbol_usage = {}
        for rule in rules:
            rule_id = rule.get('rule_id')
            symbols = rule.get('conditions', {}).get('symbols', [])

            if not symbols:  # Empty symbols means all symbols
                for other_rule_id, other_symbols in symbol_usage.items():
                    if not other_symbols:  # Both target all symbols
                        issues.append({
                            'type': 'warning',
                            'category': 'resources',
                            'message': f'Rules {rule_id} and {other_rule_id} both target all symbols',
                            'affected_rules': [rule_id, other_rule_id],
                            'severity': 'medium'
                        })
                symbol_usage[rule_id] = []
            else:
                for symbol in symbols:
                    if symbol in symbol_usage:
                        issues.append({
                            'type': 'info',
                            'category': 'resources',
                            'message': f'Symbol {symbol} targeted by multiple rules',
                            'affected_rules': [rule_id, symbol_usage[symbol]],
                            'severity': 'low'
                        })
                    else:
                        symbol_usage[symbol] = rule_id

        return issues

    def _conditions_similar(self, rule1: Dict[str, Any], rule2: Dict[str, Any]) -> bool:
        """Check if two rules have very similar conditions."""
        conditions1 = rule1.get('conditions', {})
        conditions2 = rule2.get('conditions', {})

        # Compare key condition parameters
        params_to_check = [
            ('market_conditions.min_price', 'market_conditions.max_price'),
            ('breakout_conditions.min_price_move_pct',),
            ('crp_conditions.close_threshold_pct', 'crp_conditions.range_threshold_pct'),
            ('time_window.start', 'time_window.end')
        ]

        similarity_score = 0
        total_params = 0

        for param_group in params_to_check:
            for param in param_group:
                val1 = self._get_nested_value(conditions1, param)
                val2 = self._get_nested_value(conditions2, param)

                if val1 is not None and val2 is not None:
                    total_params += 1
                    if abs(val1 - val2) < 0.1:  # Within 10% tolerance
                        similarity_score += 1

        return total_params > 0 and (similarity_score / total_params) > 0.8

    def _conditions_mutually_exclusive(self, rule1: Dict[str, Any], rule2: Dict[str, Any]) -> bool:
        """Check if two rules have mutually exclusive conditions."""
        # Example: Bullish breakout vs Bearish reversal
        rule1_signal = rule1.get('actions', {}).get('signal_type')
        rule2_signal = rule2.get('actions', {}).get('signal_type')

        if rule1_signal and rule2_signal:
            # BUY vs SELL signals are not necessarily mutually exclusive
            # but could be if they target the same conditions
            pass

        return False  # Simplified for now

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[float]:
        """Get nested dictionary value by dot-separated path."""
        keys = path.split('.')
        current = data

        try:
            for key in keys:
                current = current[key]
            return float(current) if isinstance(current, (int, float)) else None
        except (KeyError, TypeError, ValueError):
            return None


class PerformanceValidator:
    """Validates rule performance expectations and requirements."""

    def __init__(self):
        self.backtest_requirements = {
            'minimum_win_rate': 0.30,
            'maximum_win_rate': 0.95,
            'minimum_profit_factor': 1.0,
            'maximum_drawdown_limit': 0.50,
            'minimum_backtest_period_months': 6
        }

    def validate_performance_expectations(self, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate performance expectations against realistic benchmarks."""
        warnings = []
        metadata = rule.get('metadata', {})
        performance = metadata.get('performance_expectations', {})

        if not performance:
            warnings.append({
                'type': 'warning',
                'message': 'Rule has no performance expectations defined',
                'field': 'metadata.performance_expectations'
            })
            return warnings

        # Validate win rate
        win_rate = performance.get('expected_win_rate')
        if win_rate is not None:
            if win_rate < self.backtest_requirements['minimum_win_rate']:
                warnings.append({
                    'type': 'warning',
                    'message': f'Expected win rate {win_rate:.1%} is below minimum {self.backtest_requirements["minimum_win_rate"]:.1%}',
                    'field': 'metadata.performance_expectations.expected_win_rate'
                })
            elif win_rate > self.backtest_requirements['maximum_win_rate']:
                warnings.append({
                    'type': 'warning',
                    'message': f'Expected win rate {win_rate:.1%} seems unrealistically high',
                    'field': 'metadata.performance_expectations.expected_win_rate'
                })

        # Validate profit factor
        profit_factor = performance.get('expected_profit_factor')
        if profit_factor is not None and profit_factor < self.backtest_requirements['minimum_profit_factor']:
            warnings.append({
                'type': 'warning',
                'message': f'Expected profit factor {profit_factor:.2f} is below breakeven',
                'field': 'metadata.performance_expectations.expected_profit_factor'
            })

        # Validate maximum drawdown
        max_drawdown = performance.get('expected_max_drawdown')
        if max_drawdown is not None and max_drawdown > self.backtest_requirements['maximum_drawdown_limit']:
            warnings.append({
                'type': 'warning',
                'message': f'Expected max drawdown {max_drawdown:.1%} exceeds recommended limit',
                'field': 'metadata.performance_expectations.expected_max_drawdown'
            })

        # Validate backtest period
        backtest_period = performance.get('backtest_period_months')
        if backtest_period is not None and backtest_period < self.backtest_requirements['minimum_backtest_period_months']:
            warnings.append({
                'type': 'warning',
                'message': f'Backtest period {backtest_period} months is too short for reliable results',
                'field': 'metadata.performance_expectations.backtest_period_months'
            })

        return warnings

    def validate_risk_assessment(self, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate risk assessment parameters."""
        warnings = []
        metadata = rule.get('metadata', {})
        risk = metadata.get('risk_assessment', {})

        if not risk:
            warnings.append({
                'type': 'warning',
                'message': 'Rule has no risk assessment defined',
                'field': 'metadata.risk_assessment'
            })
            return warnings

        risk_level = risk.get('risk_level')
        market_conditions = risk.get('market_conditions')
        holding_period = risk.get('holding_period')

        # Validate risk level vs holding period
        if risk_level == 'high' and holding_period == 'position':
            warnings.append({
                'type': 'warning',
                'message': 'High-risk rule with long holding period may expose to excessive risk',
                'field': 'metadata.risk_assessment'
            })

        # Validate market condition compatibility
        if market_conditions == 'bull' and rule.get('actions', {}).get('signal_type') == 'SELL':
            warnings.append({
                'type': 'info',
                'message': 'SELL signal in bull market conditions may have limited opportunities',
                'field': 'metadata.risk_assessment.market_conditions'
            })

        return warnings


class EnvironmentValidator:
    """Validates environment and resource requirements."""

    def __init__(self):
        self.resource_limits = {
            'max_rules_per_type': 10,
            'max_total_rules': 50,
            'max_memory_mb_per_rule': 100,
            'max_cpu_percent_per_rule': 5
        }

    def validate_environment_requirements(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that environment can support the rules."""
        checks = {
            'total_rules': len(rules),
            'rules_by_type': {},
            'resource_usage': {},
            'compatibility': {},
            'warnings': [],
            'errors': []
        }

        # Count rules by type
        for rule in rules:
            rule_type = rule.get('rule_type', 'unknown')
            checks['rules_by_type'][rule_type] = checks['rules_by_type'].get(rule_type, 0) + 1

        # Check rule limits
        if checks['total_rules'] > self.resource_limits['max_total_rules']:
            checks['errors'].append(f'Total rules ({checks["total_rules"]}) exceeds limit ({self.resource_limits["max_total_rules"]})')

        for rule_type, count in checks['rules_by_type'].items():
            if count > self.resource_limits['max_rules_per_type']:
                checks['warnings'].append(f'Too many {rule_type} rules ({count}) - may impact performance')

        # Check for resource-intensive rules
        resource_intensive_rules = []
        for rule in rules:
            if self._is_resource_intensive(rule):
                resource_intensive_rules.append(rule.get('rule_id'))

        if resource_intensive_rules:
            checks['warnings'].append(f'Resource-intensive rules detected: {resource_intensive_rules}')

        # Check database connectivity (placeholder)
        checks['compatibility']['database'] = self._check_database_compatibility(rules)

        return checks

    def _is_resource_intensive(self, rule: Dict[str, Any]) -> bool:
        """Check if rule is likely to be resource intensive."""
        conditions = rule.get('conditions', {})

        # Complex technical conditions
        technical = conditions.get('technical_conditions', {})
        if len(technical) > 3:
            return True

        # Large symbol sets
        symbols = conditions.get('symbols', [])
        if len(symbols) > 100:
            return True

        # Complex breakout conditions
        breakout = conditions.get('breakout_conditions', {})
        if len(breakout) > 5:
            return True

        return False

    def _check_database_compatibility(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check database compatibility requirements."""
        compatibility = {
            'supported': True,
            'warnings': [],
            'required_features': set()
        }

        for rule in rules:
            rule_type = rule.get('rule_type')

            if rule_type == 'technical':
                compatibility['required_features'].add('technical_indicators')
            elif rule_type == 'volume':
                compatibility['required_features'].add('volume_analysis')
            elif rule_type == 'breakout':
                compatibility['required_features'].add('price_action_analysis')
            elif rule_type == 'crp':
                compatibility['required_features'].add('pattern_recognition')

        # Check for advanced features that might not be available
        advanced_features = {'machine_learning', 'real_time_data', 'options_data'}
        for feature in advanced_features:
            if feature in compatibility['required_features']:
                compatibility['warnings'].append(f'Advanced feature required: {feature}')

        return compatibility


class EnhancedRuleValidator:
    """Main enhanced validation framework."""

    def __init__(self, rule_engine: RuleEngine, schema_path: str = None):
        self.rule_validator = RuleValidator(schema_path)
        self.cross_validator = CrossRuleValidator(rule_engine)
        self.performance_validator = PerformanceValidator()
        self.environment_validator = EnvironmentValidator()
        self.rule_engine = rule_engine

    def validate_comprehensive(
        self,
        rules: List[Dict[str, Any]],
        include_environment_checks: bool = True
    ) -> ValidationReport:
        """Perform comprehensive validation of rules."""

        report = ValidationReport()

        # 1. Individual rule validation
        individual_results = self.rule_validator.validate_rule_batch(rules)
        report.rule_reports = individual_results

        # 2. Cross-rule validation
        cross_issues = self.cross_validator.validate_cross_rule_consistency(rules)
        report.cross_rule_issues = cross_issues

        # 3. Performance validation
        for rule in rules:
            rule_id = rule.get('rule_id')
            perf_warnings = self.performance_validator.validate_performance_expectations(rule)
            risk_warnings = self.performance_validator.validate_risk_assessment(rule)

            report.performance_warnings.extend([
                f"{rule_id}: {w['message']}" for w in perf_warnings + risk_warnings
            ])

        # 4. Environment validation
        if include_environment_checks:
            env_checks = self.environment_validator.validate_environment_requirements(rules)
            report.environment_checks = env_checks

        # 5. Generate summary
        report.summary = self._generate_summary(report, rules)

        # 6. Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def validate_single_rule_comprehensive(self, rule: Dict[str, Any]) -> ValidationReport:
        """Validate a single rule comprehensively."""
        return self.validate_comprehensive([rule], include_environment_checks=False)

    def _generate_summary(self, report: ValidationReport, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate validation summary."""
        total_rules = len(rules)
        valid_rules = sum(1 for r in report.rule_reports.values() if r.is_valid)
        total_errors = sum(len(r.errors) for r in report.rule_reports.values())
        total_warnings = sum(len(r.warnings) for r in report.rule_reports.values())

        # Count cross-rule issues by severity
        error_issues = [i for i in report.cross_rule_issues if i['type'] == 'error']
        warning_issues = [i for i in report.cross_rule_issues if i['type'] == 'warning']

        summary = {
            'total_rules': total_rules,
            'valid_rules': valid_rules,
            'invalid_rules': total_rules - valid_rules,
            'validation_success_rate': valid_rules / total_rules if total_rules > 0 else 0,
            'total_individual_errors': total_errors,
            'total_individual_warnings': total_warnings,
            'cross_rule_errors': len(error_issues),
            'cross_rule_warnings': len(warning_issues),
            'performance_warnings': len(report.performance_warnings),
            'environment_warnings': len(report.environment_checks.get('warnings', [])),
            'environment_errors': len(report.environment_checks.get('errors', [])),
            'overall_status': 'PASS' if valid_rules == total_rules and not error_issues else 'FAIL'
        }

        return summary

    def _generate_recommendations(self, report: ValidationReport) -> List[str]:
        """Generate actionable recommendations based on validation results."""
        recommendations = []

        summary = report.summary

        # Basic validation issues
        if summary['invalid_rules'] > 0:
            recommendations.append(f"Fix validation errors in {summary['invalid_rules']} rules before deployment")

        # Cross-rule issues
        if summary['cross_rule_errors'] > 0:
            recommendations.append("Address cross-rule conflicts that may cause execution issues")

        if summary['cross_rule_warnings'] > 0:
            recommendations.append("Review cross-rule warnings for potential optimization opportunities")

        # Performance issues
        if summary['performance_warnings'] > 0:
            recommendations.append("Review performance expectations to ensure realistic targets")

        # Environment issues
        if summary['environment_errors']:
            recommendations.append("Address environment compatibility issues before deployment")

        if summary['environment_warnings']:
            recommendations.append("Consider environment optimizations for better performance")

        # Rule count recommendations
        if summary['total_rules'] > 20:
            recommendations.append("Consider consolidating rules to improve maintainability")

        if summary['total_rules'] < 3:
            recommendations.append("Consider adding more diverse rules for better coverage")

        return recommendations

    def export_validation_report(self, report: ValidationReport, output_path: str):
        """Export validation report to file."""
        report_data = {
            'summary': report.summary,
            'rule_reports': {
                rule_id: {
                    'is_valid': result.is_valid,
                    'errors': [{'field': e.field, 'message': e.message, 'type': e.error_type} for e in result.errors],
                    'warnings': result.warnings,
                    'metadata': result.metadata
                }
                for rule_id, result in report.rule_reports.items()
            },
            'cross_rule_issues': report.cross_rule_issues,
            'performance_warnings': report.performance_warnings,
            'environment_checks': report.environment_checks,
            'recommendations': report.recommendations,
            'generated_at': report.generated_at
        }

        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"Validation report exported to {output_path}")

    def get_validation_stats(self, reports: List[ValidationReport]) -> Dict[str, Any]:
        """Get aggregate statistics across multiple validation reports."""
        if not reports:
            return {}

        total_reports = len(reports)
        avg_success_rate = sum(r.summary.get('validation_success_rate', 0) for r in reports) / total_reports
        total_errors = sum(r.summary.get('total_individual_errors', 0) for r in reports)
        total_warnings = sum(r.summary.get('total_individual_warnings', 0) for r in reports)

        return {
            'total_validation_runs': total_reports,
            'average_success_rate': avg_success_rate,
            'total_errors_across_runs': total_errors,
            'total_warnings_across_runs': total_warnings,
            'most_common_error_types': {},  # Could be enhanced with error analysis
            'validation_trends': {}  # Could track validation quality over time
        }
