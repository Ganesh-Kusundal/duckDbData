"""
Tests for Rule Engine Core

This module tests the rule engine functionality including:
- Rule loading and validation
- Query building and execution
- Signal generation
- Performance monitoring
"""

import pytest
import json
from datetime import date, time, datetime
from unittest.mock import Mock, patch

from src.rules.engine.rule_engine import RuleEngine
from src.rules.engine.query_builder import QueryBuilder
from src.rules.engine.signal_generator import SignalGenerator, TradingSignal
from src.rules.engine.context_manager import ExecutionContext, ContextManager
from src.rules.schema.rule_types import RuleType, SignalType


class TestQueryBuilder:
    """Test query builder functionality."""

    def test_build_breakout_query(self):
        """Test breakout query building."""
        builder = QueryBuilder()

        conditions = {
            'time_window': {'start': '09:35', 'end': '10:30'},
            'breakout_conditions': {
                'min_volume_multiplier': 1.5,
                'min_price_move_pct': 0.02
            }
        }

        query, params = builder.build_query(
            rule_type=RuleType.BREAKOUT,
            conditions=conditions,
            scan_date=date(2025, 9, 8)
        )

        assert 'breakout' in query.lower()
        assert 'volume_multiplier' in query
        assert 'price_change_pct' in query
        assert len(params) > 0
        assert isinstance(params[0], str)  # Date parameter

    def test_build_crp_query(self):
        """Test CRP query building."""
        builder = QueryBuilder()

        conditions = {
            'crp_conditions': {
                'close_threshold_pct': 2.0,
                'range_threshold_pct': 3.0
            }
        }

        query, params = builder.build_query(
            rule_type=RuleType.CRP,
            conditions=conditions,
            scan_date=date(2025, 9, 8)
        )

        assert 'crp' in query.lower()
        assert 'close_position' in query
        assert 'consolidation_range_pct' in query
        assert len(params) > 0

    def test_query_caching(self):
        """Test query caching functionality."""
        builder = QueryBuilder()

        conditions = {'breakout_conditions': {'min_volume_multiplier': 2.0}}
        scan_date = date(2025, 9, 8)

        # First call
        query1, params1 = builder.build_query(
            rule_type=RuleType.BREAKOUT,
            conditions=conditions,
            scan_date=scan_date
        )

        # Second call with same parameters
        query2, params2 = builder.build_query(
            rule_type=RuleType.BREAKOUT,
            conditions=conditions,
            scan_date=scan_date
        )

        assert query1 == query2
        assert params1 == params2

        # Check cache stats
        stats = builder.get_cache_stats()
        assert stats['cache_size'] >= 1


class TestSignalGenerator:
    """Test signal generator functionality."""

    def test_generate_signal(self):
        """Test signal generation."""
        generator = SignalGenerator()

        signal = generator.generate_signal(
            rule_id='test-rule',
            symbol='AAPL',
            signal_type=SignalType.BUY,
            confidence=0.8,
            market_data={'close': 150.25, 'volume': 1000000},
            risk_management={'stop_loss_pct': 0.02}
        )

        assert signal.symbol == 'AAPL'
        assert signal.rule_id == 'test-rule'
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence == 0.8
        assert signal.price == 150.25
        assert signal.volume == 1000000
        assert signal.stop_loss is not None

    def test_signal_validation(self):
        """Test signal validation."""
        signal = TradingSignal(
            symbol='AAPL',
            rule_id='test',
            signal_type=SignalType.BUY,
            confidence=0.8,
            price=150.0
        )

        errors = signal.validate_signal()
        assert len(errors) == 0  # Should be valid

    def test_invalid_signal_confidence(self):
        """Test invalid signal confidence."""
        with pytest.raises(ValueError):
            TradingSignal(
                symbol='AAPL',
                rule_id='test',
                signal_type=SignalType.BUY,
                confidence=1.5  # Invalid confidence
            )

    def test_signal_serialization(self):
        """Test signal serialization."""
        signal = TradingSignal(
            symbol='AAPL',
            rule_id='test',
            signal_type=SignalType.BUY,
            confidence=0.8,
            price=150.0
        )

        # Test to_dict
        signal_dict = signal.to_dict()
        assert signal_dict['symbol'] == 'AAPL'
        assert signal_dict['signal_type'] == 'BUY'

        # Test from_dict
        restored_signal = TradingSignal.from_dict(signal_dict)
        assert restored_signal.symbol == signal.symbol
        assert restored_signal.confidence == signal.confidence


class TestContextManager:
    """Test context manager functionality."""

    def test_create_context(self):
        """Test context creation."""
        manager = ContextManager()

        context = manager.create_context(
            scan_date=date(2025, 9, 8),
            start_time=time(9, 30),
            end_time=time(15, 30),
            symbols=['AAPL', 'GOOGL']
        )

        assert context.scan_date == date(2025, 9, 8)
        assert context.start_time == time(9, 30)
        assert context.end_time == time(15, 30)
        assert context.symbols == ['AAPL', 'GOOGL']

    def test_time_window_validation(self):
        """Test time window validation in context."""
        context = ExecutionContext(
            scan_date=date(2025, 9, 8),
            start_time=time(9, 30),
            end_time=time(15, 30)
        )

        assert context.is_time_in_window(time(10, 0))
        assert context.is_time_in_window(time(15, 30))
        assert not context.is_time_in_window(time(16, 0))

    def test_symbol_filtering(self):
        """Test symbol filtering."""
        context = ExecutionContext(
            scan_date=date(2025, 9, 8),
            symbols=['AAPL', 'GOOGL']
        )

        assert context.should_process_symbol('AAPL')
        assert not context.should_process_symbol('MSFT')

    def test_performance_tracking(self):
        """Test performance metrics tracking."""
        context = ExecutionContext(scan_date=date(2025, 9, 8))

        # Record some metrics
        context.record_query_execution('test_query', 50.0)
        context.record_signal_generation('test_rule', 0.8)

        # Finalize metrics
        context.finalize_metrics()

        assert context.performance_metrics['queries_executed'] == 1
        assert context.performance_metrics['signals_generated'] == 1
        assert 'execution_time_ms' in context.performance_metrics


class TestRuleEngine:
    """Test rule engine functionality."""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection."""
        return Mock()

    @pytest.fixture
    def rule_engine(self, mock_db_connection):
        """Create rule engine instance."""
        return RuleEngine(db_connection=mock_db_connection)

    def test_load_rules(self, rule_engine):
        """Test rule loading."""
        rules = [
            {
                "rule_id": "test-breakout",
                "name": "Test Breakout Rule",
                "rule_type": "breakout",
                "conditions": {
                    "breakout_conditions": {
                        "min_volume_multiplier": 1.5
                    }
                },
                "actions": {
                    "signal_type": "BUY"
                },
                "metadata": {
                    "author": "test",
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0.0"
                }
            }
        ]

        result = rule_engine.load_rules(rules)

        assert result['total_rules'] == 1
        assert result['loaded_rules'] == 1
        assert result['failed_rules'] == 0
        assert 'test-breakout' in rule_engine.rules

    def test_execute_rule_success(self, rule_engine):
        """Test successful rule execution."""
        # Load a test rule
        rules = [{
            "rule_id": "test-breakout",
            "name": "Test Breakout",
            "rule_type": "breakout",
            "conditions": {},
            "actions": {"signal_type": "BUY"},
            "metadata": {"author": "test", "created_at": datetime.now().isoformat(), "version": "1.0.0"}
        }]

        rule_engine.load_rules(rules)

        # Mock the database execution
        with patch.object(rule_engine, '_execute_query') as mock_query:
            mock_query.return_value = [{
                'symbol': 'AAPL',
                'timestamp': '2025-09-08T10:30:00',
                'price': 150.25,
                'volume': 1000000,
                'price_change_pct': 2.5,
                'volume_multiplier': 2.1
            }]

            result = rule_engine.execute_rule('test-breakout', date(2025, 9, 8))

            assert result['success']
            assert result['rule_id'] == 'test-breakout'
            assert len(result['signals']) > 0

    def test_execute_rule_not_found(self, rule_engine):
        """Test execution of non-existent rule."""
        result = rule_engine.execute_rule('non-existent-rule', date(2025, 9, 8))

        assert not result['success']
        assert 'not found' in result['error']

    def test_rule_statistics(self, rule_engine):
        """Test rule statistics tracking."""
        rules = [{
            "rule_id": "test-rule",
            "name": "Test Rule",
            "rule_type": "breakout",
            "conditions": {},
            "actions": {"signal_type": "BUY"},
            "metadata": {"author": "test", "created_at": datetime.now().isoformat(), "version": "1.0.0"}
        }]

        rule_engine.load_rules(rules)

        # Get initial stats
        stats = rule_engine.get_rule_stats('test-rule')
        assert stats['execution_count'] == 0

        # Execute rule
        with patch.object(rule_engine, '_execute_query', return_value=[]):
            rule_engine.execute_rule('test-rule', date(2025, 9, 8))

        # Check updated stats
        stats = rule_engine.get_rule_stats('test-rule')
        assert stats['execution_count'] == 1

    def test_engine_statistics(self, rule_engine):
        """Test engine-level statistics."""
        stats = rule_engine.get_engine_stats()

        assert 'total_rules' in stats
        assert 'total_executions' in stats
        assert 'query_cache_stats' in stats

    def test_callbacks(self, rule_engine):
        """Test callback functionality."""
        signal_callback_called = False
        execution_callback_called = False

        def signal_callback(signals):
            nonlocal signal_callback_called
            signal_callback_called = True

        def execution_callback(rule_id, success, signals_count, error):
            nonlocal execution_callback_called
            execution_callback_called = True

        rule_engine.add_signal_callback(signal_callback)
        rule_engine.add_execution_callback(execution_callback)

        # Load and execute a rule
        rules = [{
            "rule_id": "test-callbacks",
            "name": "Test Callbacks",
            "rule_type": "breakout",
            "conditions": {},
            "actions": {"signal_type": "BUY"},
            "metadata": {"author": "test", "created_at": datetime.now().isoformat(), "version": "1.0.0"}
        }]

        rule_engine.load_rules(rules)

        with patch.object(rule_engine, '_execute_query', return_value=[]):
            rule_engine.execute_rule('test-callbacks', date(2025, 9, 8))

        # Callbacks should have been executed
        assert execution_callback_called


class TestExecutionPipeline:
    """Test execution pipeline functionality."""

    @pytest.fixture
    def pipeline(self):
        """Create execution pipeline instance."""
        from src.rules.engine.execution_pipeline import ExecutionPipeline
        return ExecutionPipeline()

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline.config.max_workers == 4
        assert pipeline.config.enable_parallel
        assert len(pipeline.loaded_rules) == 0

    def test_load_rules_from_directory(self, pipeline, tmp_path):
        """Test loading rules from directory."""
        # Create test rule file
        rule_file = tmp_path / "test_rule.json"
        rule_data = [{
            "rule_id": "test-pipeline-rule",
            "name": "Test Pipeline Rule",
            "rule_type": "breakout",
            "conditions": {"breakout_conditions": {"min_volume_multiplier": 1.5}},
            "actions": {"signal_type": "BUY"},
            "metadata": {"author": "test", "created_at": datetime.now().isoformat(), "version": "1.0.0"}
        }]

        with open(rule_file, 'w') as f:
            json.dump(rule_data, f)

        # Load rules
        result = pipeline.load_rules_from_directory(str(tmp_path))

        assert result['total_files'] == 1
        assert result['loaded_rules'] == 1
        assert 'test-pipeline-rule' in pipeline.loaded_rules

    def test_pipeline_execution(self, pipeline):
        """Test pipeline execution."""
        # Load a test rule
        rules = [{
            "rule_id": "pipeline-test",
            "name": "Pipeline Test Rule",
            "rule_type": "breakout",
            "conditions": {},
            "actions": {"signal_type": "BUY"},
            "metadata": {"author": "test", "created_at": datetime.now().isoformat(), "version": "1.0.0"}
        }]

        pipeline.rule_engine.load_rules(rules)
        pipeline.loaded_rules = ['pipeline-test']

        # Execute pipeline
        with patch.object(pipeline.rule_engine, 'execute_rules_batch') as mock_batch:
            mock_batch.return_value = {
                'total_rules': 1,
                'successful_executions': 1,
                'failed_executions': 0,
                'total_signals': 2,
                'rule_results': {
                    'pipeline-test': {
                        'success': True,
                        'signals': [{'symbol': 'AAPL', 'signal_type': 'BUY'}]
                    }
                }
            }

            result = pipeline.execute_pipeline(date(2025, 9, 8))

            assert result.success
            assert result.total_rules == 1
            assert result.executed_rules == 1
            assert result.total_signals == 2

    def test_pipeline_stats(self, pipeline):
        """Test pipeline statistics."""
        stats = pipeline.get_pipeline_stats()

        assert 'executions' in stats
        assert 'engine_stats' in stats

    def test_export_results(self, pipeline):
        """Test result export functionality."""
        from src.rules.engine.execution_pipeline import PipelineResult

        result = PipelineResult(
            success=True,
            total_rules=2,
            executed_rules=2,
            failed_rules=0,
            total_signals=3,
            execution_time_ms=150.5,
            errors=[],
            signals=[{'symbol': 'AAPL', 'signal_type': 'BUY'}],
            performance_metrics={'avg_signals_per_rule': 1.5}
        )

        # Test JSON export
        json_export = pipeline.export_results(result, 'json')
        assert 'success' in json_export
        assert 'total_rules' in json_export

        # Test CSV export
        csv_export = pipeline.export_results(result, 'csv')
        assert 'symbol,rule_id' in csv_export
