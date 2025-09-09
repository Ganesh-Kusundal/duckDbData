"""
Execution Pipeline

This module provides the execution pipeline that orchestrates:
- Rule loading and validation
- Parallel/sequential execution
- Signal generation and aggregation
- Performance monitoring and reporting
"""

from typing import Dict, List, Any, Optional
from datetime import date, time
from dataclasses import dataclass
import logging

from .rule_engine import RuleEngine
from .context_manager import ExecutionContext
from .signal_generator import SignalBatch

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for execution pipeline."""
    max_workers: int = 4
    enable_parallel: bool = True
    enable_caching: bool = True
    batch_size: int = 10
    timeout_seconds: int = 300
    retry_failed_rules: bool = True
    max_retries: int = 3


@dataclass
class PipelineResult:
    """Results from pipeline execution."""
    success: bool
    total_rules: int
    executed_rules: int
    failed_rules: int
    total_signals: int
    execution_time_ms: float
    errors: List[Dict[str, Any]]
    signals: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


class ExecutionPipeline:
    """Orchestrates rule execution pipeline."""

    def __init__(self, db_connection=None, config: Optional[PipelineConfig] = None):
        """
        Initialize execution pipeline.

        Args:
            db_connection: Database connection
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        self.rule_engine = RuleEngine(db_connection, self.config.max_workers)

        # Pipeline state
        self.loaded_rules: List[str] = []
        self.execution_history: List[PipelineResult] = []

        logger.info("Execution pipeline initialized")

    def load_rules_from_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        Load all rules from a directory.

        Args:
            directory_path: Path to directory containing rule files

        Returns:
            Loading results
        """
        import os
        import glob

        all_results = {
            'total_files': 0,
            'loaded_rules': 0,
            'failed_rules': 0,
            'validation_errors': [],
            'warnings': []
        }

        # Find all JSON files in directory
        pattern = os.path.join(directory_path, "*.json")
        rule_files = glob.glob(pattern)

        for file_path in rule_files:
            all_results['total_files'] += 1

            try:
                result = self.rule_engine.load_rules_from_file(file_path)

                all_results['loaded_rules'] += result['loaded_rules']
                all_results['failed_rules'] += result['failed_rules']
                all_results['validation_errors'].extend(result['validation_errors'])
                all_results['warnings'].extend(result['warnings'])

                # Track loaded rule IDs
                if result['loaded_rules'] > 0:
                    # Extract rule IDs from file (simplified)
                    with open(file_path, 'r') as f:
                        rules_data = __import__('json').load(f)
                        if isinstance(rules_data, list):
                            for rule in rules_data:
                                if 'rule_id' in rule:
                                    self.loaded_rules.append(rule['rule_id'])
                        elif isinstance(rules_data, dict) and 'rule_id' in rules_data:
                            self.loaded_rules.append(rules_data['rule_id'])

            except Exception as e:
                logger.error(f"Failed to load rules from {file_path}: {e}")
                all_results['failed_rules'] += 1
                all_results['validation_errors'].append({
                    'file': file_path,
                    'error': str(e)
                })

        logger.info(f"Loaded {all_results['loaded_rules']} rules from {all_results['total_files']} files")
        return all_results

    def execute_pipeline(
        self,
        scan_date: date,
        rule_ids: Optional[List[str]] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None,
        **kwargs
    ) -> PipelineResult:
        """
        Execute the complete pipeline.

        Args:
            scan_date: Date to scan
            rule_ids: Specific rules to execute (None = all loaded rules)
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter
            **kwargs: Additional execution parameters

        Returns:
            Pipeline execution results
        """
        import time
        start_time_ms = time.time() * 1000

        # Determine which rules to execute
        if rule_ids is None:
            rule_ids = self.loaded_rules

        if not rule_ids:
            return PipelineResult(
                success=False,
                total_rules=0,
                executed_rules=0,
                failed_rules=0,
                total_signals=0,
                execution_time_ms=0,
                errors=[{'type': 'configuration', 'message': 'No rules loaded'}],
                signals=[],
                performance_metrics={}
            )

        # Execute rules
        batch_result = self.rule_engine.execute_rules_batch(
            rule_ids=rule_ids,
            scan_date=scan_date,
            parallel=self.config.enable_parallel,
            start_time=start_time,
            end_time=end_time,
            symbols=symbols,
            **kwargs
        )

        # Calculate execution time
        execution_time_ms = (time.time() * 1000) - start_time_ms

        # Create pipeline result
        result = PipelineResult(
            success=batch_result['failed_executions'] == 0,
            total_rules=batch_result['total_rules'],
            executed_rules=batch_result['successful_executions'],
            failed_rules=batch_result['failed_executions'],
            total_signals=batch_result['total_signals'],
            execution_time_ms=execution_time_ms,
            errors=batch_result.get('execution_errors', []),
            signals=self._extract_signals_from_results(batch_result['rule_results']),
            performance_metrics=self._calculate_performance_metrics(batch_result, execution_time_ms)
        )

        # Store in history
        self.execution_history.append(result)

        logger.info(f"Pipeline execution completed: {result.executed_rules}/{result.total_rules} rules successful, "
                   f"{result.total_signals} signals generated in {execution_time_ms:.2f}ms")

        return result

    def execute_with_retry(
        self,
        scan_date: date,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> PipelineResult:
        """
        Execute pipeline with retry logic for failed rules.

        Args:
            scan_date: Date to scan
            max_retries: Maximum retry attempts
            **kwargs: Additional execution parameters

        Returns:
            Final pipeline execution results
        """
        if max_retries is None:
            max_retries = self.config.max_retries

        final_result = self.execute_pipeline(scan_date, **kwargs)

        if not self.config.retry_failed_rules or final_result.failed_rules == 0:
            return final_result

        # Extract failed rule IDs
        failed_rules = []
        for error in final_result.errors:
            if 'rule_id' in error:
                failed_rules.append(error['rule_id'])

        # Retry failed rules
        retry_count = 0
        while retry_count < max_retries and failed_rules:
            retry_count += 1
            logger.info(f"Retrying {len(failed_rules)} failed rules (attempt {retry_count})")

            retry_result = self.execute_pipeline(
                scan_date=scan_date,
                rule_ids=failed_rules,
                **kwargs
            )

            # Update final result with retry results
            final_result.executed_rules += retry_result.executed_rules
            final_result.failed_rules = retry_result.failed_rules
            final_result.total_signals += retry_result.total_signals
            final_result.execution_time_ms += retry_result.execution_time_ms
            final_result.signals.extend(retry_result.signals)

            # Update success status
            final_result.success = final_result.failed_rules == 0

            # Update errors (keep only final failures)
            final_result.errors = retry_result.errors

            if retry_result.failed_rules == 0:
                break

            # Update failed rules for next retry
            failed_rules = [error['rule_id'] for error in retry_result.errors if 'rule_id' in error]

        return final_result

    def _extract_signals_from_results(self, rule_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all signals from rule execution results."""
        all_signals = []

        for rule_result in rule_results.values():
            if rule_result.get('success', False):
                all_signals.extend(rule_result.get('signals', []))

        return all_signals

    def _calculate_performance_metrics(
        self,
        batch_result: Dict[str, Any],
        execution_time_ms: float
    ) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        metrics = {
            'execution_time_ms': execution_time_ms,
            'rules_per_second': 0,
            'signals_per_second': 0,
            'success_rate': 0,
            'avg_signals_per_rule': 0
        }

        total_rules = batch_result.get('total_rules', 0)
        successful_rules = batch_result.get('successful_executions', 0)
        total_signals = batch_result.get('total_signals', 0)

        if execution_time_ms > 0:
            metrics['rules_per_second'] = (total_rules / execution_time_ms) * 1000
            metrics['signals_per_second'] = (total_signals / execution_time_ms) * 1000

        if total_rules > 0:
            metrics['success_rate'] = successful_rules / total_rules
            if successful_rules > 0:
                metrics['avg_signals_per_rule'] = total_signals / successful_rules

        return metrics

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get overall pipeline statistics."""
        if not self.execution_history:
            return {
                'executions': 0,
                'engine_stats': self.rule_engine.get_engine_stats()
            }

        total_executions = len(self.execution_history)
        successful_executions = sum(1 for r in self.execution_history if r.success)
        total_signals = sum(r.total_signals for r in self.execution_history)
        avg_execution_time = sum(r.execution_time_ms for r in self.execution_history) / total_executions

        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': successful_executions / total_executions if total_executions > 0 else 0,
            'total_signals_generated': total_signals,
            'avg_execution_time_ms': avg_execution_time,
            'avg_signals_per_execution': total_signals / total_executions if total_executions > 0 else 0,
            'loaded_rules': len(self.loaded_rules),
            'engine_stats': self.rule_engine.get_engine_stats()
        }

    def clear_history(self):
        """Clear execution history."""
        self.execution_history.clear()
        logger.info("Pipeline execution history cleared")

    def get_recent_executions(self, limit: int = 5) -> List[PipelineResult]:
        """Get recent pipeline executions."""
        return self.execution_history[-limit:] if self.execution_history else []

    def export_results(self, result: PipelineResult, format: str = 'json') -> str:
        """
        Export pipeline results in specified format.

        Args:
            result: Pipeline result to export
            format: Export format ('json', 'csv')

        Returns:
            Formatted result string
        """
        if format == 'json':
            import json
            return json.dumps({
                'success': result.success,
                'total_rules': result.total_rules,
                'executed_rules': result.executed_rules,
                'failed_rules': result.failed_rules,
                'total_signals': result.total_signals,
                'execution_time_ms': result.execution_time_ms,
                'errors': result.errors,
                'performance_metrics': result.performance_metrics,
                'signal_count': len(result.signals)
            }, indent=2, default=str)

        elif format == 'csv':
            # Simple CSV format for signals
            lines = ['symbol,rule_id,signal_type,confidence,price,volume,timestamp']
            for signal in result.signals:
                lines.append(','.join([
                    signal.get('symbol', ''),
                    signal.get('rule_id', ''),
                    signal.get('signal_type', ''),
                    str(signal.get('confidence', 0)),
                    str(signal.get('price', '')),
                    str(signal.get('volume', '')),
                    signal.get('timestamp', '')
                ]))
            return '\n'.join(lines)

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def shutdown(self):
        """Shutdown the pipeline."""
        self.rule_engine.shutdown()
        self.clear_history()
        logger.info("Execution pipeline shutdown complete")
