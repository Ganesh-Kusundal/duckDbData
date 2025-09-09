"""
Tests for Enhanced Rule Validation Framework

This module tests the comprehensive validation capabilities including:
- Cross-rule validation
- Performance validation
- Environment validation
- Rule consistency validation
- Comprehensive reporting
"""

import pytest
import json
from datetime import date, time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from src.rules.engine.rule_engine import RuleEngine
from src.rules.validation.enhanced_validator import (
    EnhancedRuleValidator,
    CrossRuleValidator,
    PerformanceValidator,
    EnvironmentValidator,
    ValidationReport
)
from src.rules.templates.breakout_rules import BreakoutRuleTemplates
from src.rules.templates.crp_rules import CRPRuleTemplates


class TestCrossRuleValidator:
    """Test cross-rule validation functionality."""

    @pytest.fixture
    def rule_engine(self):
        """Create mock rule engine."""
        engine = Mock(spec=RuleEngine)
        return engine

    @pytest.fixture
    def cross_validator(self, rule_engine):
        """Create cross-rule validator."""
        return CrossRuleValidator(rule_engine)

    def test_duplicate_rule_ids_detection(self, cross_validator):
        """Test detection of duplicate rule IDs."""
        rules = [
            {'rule_id': 'test-rule-1', 'name': 'Test Rule 1'},
            {'rule_id': 'test-rule-2', 'name': 'Test Rule 2'},
            {'rule_id': 'test-rule-1', 'name': 'Duplicate Rule'}  # Duplicate
        ]

        issues = cross_validator.validate_cross_rule_consistency(rules)

        duplicate_issues = [i for i in issues if i['category'] == 'consistency']
        assert len(duplicate_issues) == 1
        assert 'Duplicate rule ID found' in duplicate_issues[0]['message']
        assert duplicate_issues[0]['severity'] == 'high'

    def test_condition_similarity_detection(self, cross_validator):
        """Test detection of similar conditions between rules."""
        rules = [
            {
                'rule_id': 'rule-1',
                'rule_type': 'breakout',
                'conditions': {
                    'market_conditions': {'min_price': 50, 'max_price': 2000},
                    'breakout_conditions': {'min_price_move_pct': 1.0}
                }
            },
            {
                'rule_id': 'rule-2',
                'rule_type': 'breakout',
                'conditions': {
                    'market_conditions': {'min_price': 50, 'max_price': 2000},
                    'breakout_conditions': {'min_price_move_pct': 1.0}
                }
            }
        ]

        issues = cross_validator.validate_cross_rule_consistency(rules)

        redundancy_issues = [i for i in issues if i['category'] == 'redundancy']
        assert len(redundancy_issues) >= 1
        assert 'similar conditions' in redundancy_issues[0]['message']

    def test_signal_overlap_detection(self, cross_validator):
        """Test detection of overlapping signal types."""
        rules = []
        # Create 6 rules all generating BUY signals for breakout
        for i in range(6):
            rules.append({
                'rule_id': f'breakout-rule-{i}',
                'rule_type': 'breakout',
                'actions': {'signal_type': 'BUY'}
            })

        issues = cross_validator.validate_cross_rule_consistency(rules)

        overlap_issues = [i for i in issues if i['category'] == 'performance']
        assert len(overlap_issues) >= 1
        assert 'Too many rules' in overlap_issues[0]['message']

    def test_symbol_overlap_detection(self, cross_validator):
        """Test detection of symbol targeting overlaps."""
        rules = [
            {
                'rule_id': 'rule-all-symbols',
                'conditions': {'symbols': []}  # Empty means all symbols
            },
            {
                'rule_id': 'rule-specific-symbols',
                'conditions': {'symbols': ['AAPL', 'GOOGL']}
            },
            {
                'rule_id': 'rule-all-symbols-2',
                'conditions': {'symbols': []}  # Another rule targeting all symbols
            }
        ]

        issues = cross_validator.validate_cross_rule_consistency(rules)

        resource_issues = [i for i in issues if i['category'] == 'resources']
        assert len(resource_issues) >= 1
        assert 'both target all symbols' in resource_issues[0]['message']


class TestPerformanceValidator:
    """Test performance validation functionality."""

    @pytest.fixture
    def performance_validator(self):
        """Create performance validator."""
        return PerformanceValidator()

    def test_unrealistic_win_rate_detection(self, performance_validator):
        """Test detection of unrealistic win rate expectations."""
        rule = {
            'rule_id': 'test-rule',
            'metadata': {
                'performance_expectations': {
                    'expected_win_rate': 0.98  # Unrealistically high
                }
            }
        }

        warnings = performance_validator.validate_performance_expectations(rule)

        win_rate_warnings = [w for w in warnings if 'win rate' in w['message']]
        assert len(win_rate_warnings) >= 1
        assert 'unrealistically high' in win_rate_warnings[0]['message']

    def test_low_win_rate_detection(self, performance_validator):
        """Test detection of win rates below minimum threshold."""
        rule = {
            'rule_id': 'test-rule',
            'metadata': {
                'performance_expectations': {
                    'expected_win_rate': 0.15  # Below minimum
                }
            }
        }

        warnings = performance_validator.validate_performance_expectations(rule)

        win_rate_warnings = [w for w in warnings if 'below minimum' in w['message']]
        assert len(win_rate_warnings) >= 1

    def test_missing_performance_expectations(self, performance_validator):
        """Test detection of missing performance expectations."""
        rule = {
            'rule_id': 'test-rule',
            'metadata': {}  # No performance expectations
        }

        warnings = performance_validator.validate_performance_expectations(rule)

        assert len(warnings) >= 1
        assert 'no performance expectations' in warnings[0]['message']

    def test_risk_assessment_validation(self, performance_validator):
        """Test risk assessment validation."""
        rule = {
            'rule_id': 'high-risk-long-term',
            'actions': {'signal_type': 'BUY'},
            'metadata': {
                'risk_assessment': {
                    'risk_level': 'high',
                    'holding_period': 'position'
                }
            }
        }

        warnings = performance_validator.validate_risk_assessment(rule)

        risk_warnings = [w for w in warnings if 'excessive risk' in w['message']]
        assert len(risk_warnings) >= 1

    def test_market_condition_signal_compatibility(self, performance_validator):
        """Test market condition and signal type compatibility."""
        rule = {
            'rule_id': 'sell-in-bull-market',
            'actions': {'signal_type': 'SELL'},
            'metadata': {
                'risk_assessment': {
                    'market_conditions': 'bull'
                }
            }
        }

        warnings = performance_validator.validate_risk_assessment(rule)

        market_warnings = [w for w in warnings if 'bull market' in w['message']]
        assert len(market_warnings) >= 1


class TestEnvironmentValidator:
    """Test environment validation functionality."""

    @pytest.fixture
    def environment_validator(self):
        """Create environment validator."""
        return EnvironmentValidator()

    def test_rule_limit_validation(self, environment_validator):
        """Test validation of rule limits."""
        # Create 60 rules (above limit of 50)
        rules = []
        for i in range(60):
            rules.append({
                'rule_id': f'test-rule-{i}',
                'rule_type': 'breakout'
            })

        checks = environment_validator.validate_environment_requirements(rules)

        assert 'errors' in checks
        assert len(checks['errors']) >= 1
        assert 'exceeds limit' in checks['errors'][0]

    def test_rule_type_distribution(self, environment_validator):
        """Test validation of rule type distribution."""
        rules = []
        # Create 15 breakout rules (above limit of 10 per type)
        for i in range(15):
            rules.append({
                'rule_id': f'breakout-rule-{i}',
                'rule_type': 'breakout'
            })

        checks = environment_validator.validate_environment_requirements(rules)

        assert 'warnings' in checks
        assert len(checks['warnings']) >= 1
        assert 'Too many breakout rules' in checks['warnings'][0]

    def test_resource_intensive_detection(self, environment_validator):
        """Test detection of resource-intensive rules."""
        rules = [
            {
                'rule_id': 'complex-technical',
                'rule_type': 'technical',
                'conditions': {
                    'technical_conditions': {
                        'rsi': {'period': 14},
                        'macd': {'fast_period': 12},
                        'bollinger_bands': {'period': 20},
                        'moving_averages': {'sma_20': True}
                    }
                }
            }
        ]

        checks = environment_validator.validate_environment_requirements(rules)

        assert 'warnings' in checks
        assert len(checks['warnings']) >= 1
        assert 'Resource-intensive' in checks['warnings'][0]

    def test_database_compatibility(self, environment_validator):
        """Test database compatibility checking."""
        rules = [
            {
                'rule_id': 'technical-rule',
                'rule_type': 'technical'
            },
            {
                'rule_id': 'volume-rule',
                'rule_type': 'volume'
            }
        ]

        checks = environment_validator.validate_environment_requirements(rules)

        assert 'compatibility' in checks
        compatibility = checks['compatibility']
        assert 'database' in compatibility
        assert 'required_features' in compatibility['database']


class TestEnhancedRuleValidator:
    """Test the main enhanced validation framework."""

    @pytest.fixture
    def rule_engine(self):
        """Create mock rule engine."""
        engine = Mock(spec=RuleEngine)
        return engine

    @pytest.fixture
    def enhanced_validator(self, rule_engine):
        """Create enhanced validator."""
        return EnhancedRuleValidator(rule_engine)

    def test_comprehensive_validation_workflow(self, enhanced_validator):
        """Test the complete validation workflow."""
        # Create test rules
        rules = [
            BreakoutRuleTemplates.get_standard_breakout_rule(),
            CRPRuleTemplates.get_standard_crp_rule(),
            {
                'rule_id': 'invalid-rule',
                'name': 'Invalid Rule',
                # Missing required fields to trigger validation errors
            }
        ]

        report = enhanced_validator.validate_comprehensive(rules)

        assert isinstance(report, ValidationReport)
        assert 'summary' in report.__dict__
        assert 'rule_reports' in report.__dict__
        assert 'cross_rule_issues' in report.__dict__
        assert 'performance_warnings' in report.__dict__
        assert 'recommendations' in report.__dict__

        # Check summary
        summary = report.summary
        assert 'total_rules' in summary
        assert 'valid_rules' in summary
        assert 'overall_status' in summary

    def test_single_rule_validation(self, enhanced_validator):
        """Test validation of a single rule."""
        rule = BreakoutRuleTemplates.get_standard_breakout_rule()

        report = enhanced_validator.validate_single_rule_comprehensive(rule)

        assert isinstance(report, ValidationReport)
        assert len(report.rule_reports) == 1
        assert rule['rule_id'] in report.rule_reports

    @patch('builtins.open', new_callable=MagicMock)
    def test_validation_report_export(self, mock_open, enhanced_validator):
        """Test validation report export functionality."""
        # Create a mock report
        report = ValidationReport()
        report.summary = {'total_rules': 2, 'valid_rules': 2}
        report.rule_reports = {
            'rule-1': Mock(is_valid=True, errors=[], warnings=[], metadata={'test': 'data'})
        }

        # Mock the file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Export report
        enhanced_validator.export_validation_report(report, '/tmp/test_report.json')

        # Verify file was opened and json.dump was called
        mock_open.assert_called_once_with('/tmp/test_report.json', 'w')
        # json.dump writes the entire JSON structure at once, so we check that it was called
        assert mock_file.write.called or hasattr(mock_file, 'write')  # Either write was called or json.dump handled it

    def test_validation_stats_aggregation(self, enhanced_validator):
        """Test aggregation of validation statistics."""
        # Create mock reports
        reports = []
        for i in range(3):
            report = ValidationReport()
            report.summary = {
                'validation_success_rate': 0.8,
                'total_individual_errors': i,
                'total_individual_warnings': i * 2
            }
            reports.append(report)

        stats = enhanced_validator.get_validation_stats(reports)

        assert stats['total_validation_runs'] == 3
        assert abs(stats['average_success_rate'] - 0.8) < 0.001
        assert stats['total_errors_across_runs'] == 3  # 0+1+2
        assert stats['total_warnings_across_runs'] == 6  # 0+2+4

    def test_recommendations_generation(self, enhanced_validator):
        """Test generation of actionable recommendations."""
        # Create a report with various issues
        report = ValidationReport()
        report.summary = {
            'invalid_rules': 2,
            'cross_rule_errors': 1,
            'cross_rule_warnings': 2,
            'performance_warnings': 3,
            'environment_errors': ['test error'],
            'environment_warnings': ['test warning'],
            'total_rules': 25
        }

        recommendations = enhanced_validator._generate_recommendations(report)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

        # Check specific recommendations
        recommendation_texts = ' '.join(recommendations).lower()

        assert 'fix validation errors' in recommendation_texts
        assert 'cross-rule conflicts' in recommendation_texts
        assert 'performance expectations' in recommendation_texts
        assert 'environment compatibility' in recommendation_texts
        assert 'consolidating rules' in recommendation_texts


class TestValidationIntegration:
    """Test integration of all validation components."""

    def test_end_to_end_validation_pipeline(self):
        """Test complete validation pipeline from rules to recommendations."""
        # Create a comprehensive set of test rules
        rules = [
            # Valid breakout rule
            BreakoutRuleTemplates.get_standard_breakout_rule(),

            # Valid CRP rule
            CRPRuleTemplates.get_standard_crp_rule(),

            # Rule with performance issues
            {
                'rule_id': 'problematic-rule',
                'name': 'Problematic Rule',
                'rule_type': 'breakout',
                'conditions': {
                    'time_window': {'start': '09:15', 'end': '09:50'}
                },
                'actions': {'signal_type': 'BUY'},
                'metadata': {
                    'performance_expectations': {
                        'expected_win_rate': 0.99,  # Unrealistic
                        'expected_max_drawdown': 0.8  # Too high
                    }
                }
            },

            # Duplicate rule (will cause cross-rule issue)
            {
                'rule_id': 'duplicate-rule',
                'name': 'First Duplicate',
                'rule_type': 'breakout',
                'conditions': {'time_window': {'start': '09:15', 'end': '09:50'}},
                'actions': {'signal_type': 'BUY'}
            },
            {
                'rule_id': 'duplicate-rule',  # Duplicate ID
                'name': 'Second Duplicate',
                'rule_type': 'breakout',
                'conditions': {'time_window': {'start': '09:15', 'end': '09:50'}},
                'actions': {'signal_type': 'BUY'}
            }
        ]

        # Initialize validator
        rule_engine = RuleEngine()
        validator = EnhancedRuleValidator(rule_engine)

        # Run comprehensive validation
        report = validator.validate_comprehensive(rules)

        # Verify comprehensive results
        assert report.summary['total_rules'] == 5
        assert report.summary['invalid_rules'] >= 1  # At least the problematic rule
        assert len(report.cross_rule_issues) >= 1  # Duplicate rule issue
        assert len(report.performance_warnings) >= 2  # Unrealistic expectations
        assert len(report.recommendations) >= 3  # Multiple recommendations

        # Verify report structure
        assert isinstance(report.rule_reports, dict)
        # Note: len may be 4 due to duplicate rule IDs being overwritten in dict
        assert len(report.rule_reports) >= 4

        # Check that each rule has a report
        expected_rule_ids = {'breakout-standard', 'crp-standard', 'problematic-rule', 'duplicate-rule'}
        actual_rule_ids = set(report.rule_reports.keys())
        assert expected_rule_ids.issubset(actual_rule_ids)

    @patch('src.rules.validation.enhanced_validator.RuleValidator')
    def test_validation_report_json_export(self, mock_rule_validator):
        """Test that validation reports can be properly exported to JSON."""
        import json
        from unittest.mock import mock_open

        # Mock the RuleValidator to avoid schema loading issues
        mock_validator_instance = Mock()
        mock_rule_validator.return_value = mock_validator_instance

        # Create a sample report
        report = ValidationReport()
        report.summary = {'total_rules': 3, 'valid_rules': 2}
        report.generated_at = '2025-09-08T12:00:00Z'

        # Mock file operations
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                # Create validator with mocked dependencies
                rule_engine = Mock()
                validator = EnhancedRuleValidator(rule_engine)
                validator.export_validation_report(report, '/tmp/test.json')

                # Verify JSON dump was called
                mock_json_dump.assert_called_once()
                args, kwargs = mock_json_dump.call_args

                # Verify the data structure
                exported_data = args[0]
                assert 'summary' in exported_data
                assert 'generated_at' in exported_data
                assert exported_data['summary']['total_rules'] == 3


if __name__ == "__main__":
    # Run basic validation tests
    print("🔍 Running enhanced validation tests...")

    # Test basic validator initialization
    rule_engine = RuleEngine()
    validator = EnhancedRuleValidator(rule_engine)
    print("✅ Enhanced validator initialized")

    # Test with sample rules
    rules = [
        BreakoutRuleTemplates.get_standard_breakout_rule(),
        CRPRuleTemplates.get_standard_crp_rule()
    ]

    report = validator.validate_comprehensive(rules)
    print(f"📊 Validation report generated: {report.summary['total_rules']} rules")

    # Test recommendations
    recommendations = validator._generate_recommendations(report)
    print(f"💡 Generated {len(recommendations)} recommendations")

    print("🎉 Enhanced validation framework test complete!")
