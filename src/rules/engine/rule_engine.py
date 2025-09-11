"""
Rule Engine

This module provides the main rule execution engine that:
- Loads and validates rules
- Executes rules against the database
- Generates trading signals
- Manages execution context and performance
"""

from typing import Dict, List, Any, Optional, Callable, Union
from datetime import date, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import json

from ..schema.rule_types import RuleType, SignalType
from ..schema.validation_engine import RuleValidator
from .context_manager import ContextManager, ExecutionContext
from .query_builder import QueryBuilder
from .signal_generator import SignalGenerator, TradingSignal, SignalBatch

logger = logging.getLogger(__name__)


class RuleEngine:
    """Main rule execution engine."""

    def __init__(self, db_connection=None, max_workers: int = 4):
        """
        Initialize the rule engine.

        Args:
            db_connection: Database connection object
            max_workers: Maximum number of worker threads for parallel execution
        """
        self.db_connection = db_connection
        self.max_workers = max_workers

        # Core components
        self.validator = RuleValidator()
        self.query_builder = QueryBuilder()
        self.signal_generator = SignalGenerator()
        self.context_manager = ContextManager()

        # Rule storage
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.rule_execution_stats: Dict[str, Dict[str, Any]] = {}

        # Callbacks
        self.signal_callbacks: List[Callable] = []
        self.execution_callbacks: List[Callable] = []

        logger.info("Rule engine initialized")

    def load_rules(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load and validate rules.

        Args:
            rules: List of rule definitions

        Returns:
            Loading results with validation status
        """
        results = {
            'total_rules': len(rules),
            'loaded_rules': 0,
            'failed_rules': 0,
            'validation_errors': [],
            'warnings': []
        }

        for rule in rules:
            rule_id = rule.get('rule_id')

            if not rule_id:
                results['validation_errors'].append({
                    'rule': 'unknown',
                    'error': 'Missing rule_id'
                })
                results['failed_rules'] += 1
                continue

            # Validate rule
            validation_result = self.validator.validate_rule(rule)

            if not validation_result.is_valid:
                results['validation_errors'].append({
                    'rule': rule_id,
                    'errors': [err.message for err in validation_result.errors]
                })
                results['failed_rules'] += 1
                continue

            # Load rule
            self.rules[rule_id] = rule
            self.rule_execution_stats[rule_id] = {
                'execution_count': 0,
                'success_count': 0,
                'failure_count': 0,
                'avg_execution_time': 0,
                'last_executed': None,
                'total_signals_generated': 0
            }

            results['loaded_rules'] += 1

            # Add warnings
            if validation_result.warnings:
                results['warnings'].append({
                    'rule': rule_id,
                    'warnings': validation_result.warnings
                })

        logger.info(f"Loaded {results['loaded_rules']} rules, {results['failed_rules']} failed")
        return results

    def load_rules_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load rules from JSON file.

        Args:
            file_path: Path to rules file

        Returns:
            Loading results
        """
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith('.json'):
                    rules = json.load(f)
                    # Handle both single rule and array of rules
                    if isinstance(rules, dict):
                        rules = [rules]
                else:
                    raise ValueError("Unsupported file format")

            return self.load_rules(rules)

        except Exception as e:
            logger.error(f"Failed to load rules from {file_path}: {e}")
            return {
                'total_rules': 0,
                'loaded_rules': 0,
                'failed_rules': 0,
                'validation_errors': [{'rule': 'file_load', 'error': str(e)}],
                'warnings': []
            }

    def execute_rule(
        self,
        rule_id: str,
        scan_date: Union[date, str],
        context: Optional[ExecutionContext] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a single rule.

        Args:
            rule_id: ID of rule to execute
            scan_date: Date to scan (date object or ISO string)
            context: Execution context
            **kwargs: Additional execution parameters

        Returns:
            Execution results
        """
        # Convert scan_date to date object if it's a string
        if isinstance(scan_date, str):
            try:
                from datetime import datetime
                scan_date = datetime.fromisoformat(scan_date).date()
            except ValueError:
                return {
                    'success': False,
                    'error': f'Invalid date format: {scan_date}',
                    'signals': []
                }

        if rule_id not in self.rules:
            return {
                'success': False,
                'error': f'Rule {rule_id} not found',
                'signals': []
            }

        rule = self.rules[rule_id]
        start_time = kwargs.get('start_time')
        end_time = kwargs.get('end_time')
        symbols = kwargs.get('symbols')

        # Create execution context if not provided
        if context is None:
            context = self.context_manager.create_context(
                scan_date=scan_date,
                start_time=start_time,
                end_time=end_time,
                symbols=symbols
            )

        context.performance_metrics['rules_executed'] += 1

        try:
            # Record execution start
            execution_start = context.performance_metrics['start_time']

            # Build query
            rule_type = RuleType(rule['rule_type'])
            query, params = self.query_builder.build_query(
                rule_type=rule_type,
                conditions=rule.get('conditions', {}),
                scan_date=scan_date,
                start_time=start_time,
                end_time=end_time,
                symbols=symbols
            )

            # Execute query
            if self.db_connection is None:
                raise ValueError("Database connection not provided")

            # Debug: Log the actual query being executed
            logger.info(f"DEBUG RULE {rule_id}: Generated query:\n{query}")
            logger.info(f"DEBUG RULE {rule_id}: Query params: {params}")

            context.record_query_execution(f"{rule_type.value}_query", 0)  # Query time would be measured

            # Execute the query (simplified - would use actual DB connection)
            logger.debug(f"Executing rule {rule_id} with query params: {params}")
            results = self._execute_query(query, params)
            logger.debug(f"Query returned {len(results)} results for rule {rule_id}")
            if results:
                logger.debug(f"First result sample: {results[0]}")

                # Generate signals
            signals = []
            logger.debug(f"Processing {len(results)} results for signal generation")
            for i, result in enumerate(results):
                logger.debug(f"Processing result {i}: {result} (type: {type(result)})")

                # Check if result is a dictionary
                if not isinstance(result, dict):
                    logger.error(f"Result {i} is not a dictionary: {result} (type: {type(result)})")
                    continue

                if 'symbol' not in result:
                    logger.error(f"Result {i} missing 'symbol' key: {result}")
                    continue

                # Extract confidence from available fields
                confidence = (result.get('probability_score', 0) or
                            result.get('confidence', 0) or
                            result.get('breakout_pct', 0) or 0.5)

                # Extract market data with proper field mapping
                market_data = {
                    'close': (result.get('price') or
                             result.get('breakout_price') or
                             result.get('close') or 0),
                    'volume': (result.get('volume') or
                              result.get('current_volume') or
                              result.get('vol') or 0),
                    'timestamp': result.get('timestamp'),
                    'price_change_pct': result.get('price_change_pct', 0),
                    'volume_multiplier': (result.get('volume_multiplier') or
                                         result.get('volume_ratio') or 1),
                    'breakout_strength': result.get('breakout_strength', 0),
                    'price_at_0950': result.get('price_at_0950'),
                    'price_at_1515': result.get('price_at_1515'),
                    'daily_performance_pct': result.get('daily_performance_pct')
                }

                # Debug logging for INTELLECT
                if result.get('symbol') == 'INTELLECT':
                    logger.info(f"DEBUG EXECUTE_RULE: result keys: {list(result.keys())}")
                    logger.info(f"DEBUG EXECUTE_RULE: price_at_1515 from result: {result.get('price_at_1515')}")
                    logger.info(f"DEBUG EXECUTE_RULE: daily_performance_pct from result: {result.get('daily_performance_pct')}")
                    logger.info(f"DEBUG EXECUTE_RULE: market_data: {market_data}")

                logger.debug(f"Creating signal for symbol: {result['symbol']}")
                signal = self.signal_generator.generate_signal(
                    rule_id=rule_id,
                    symbol=result['symbol'],
                    signal_type=SignalType(rule['actions']['signal_type']),
                    confidence=confidence,  # Use extracted confidence
                    market_data=market_data,
                    risk_management=rule['actions'].get('risk_management')
                )
                signals.append(signal)

            # Update statistics
            self._update_rule_stats(rule_id, True, len(signals))

            # Execute callbacks
            self._execute_signal_callbacks(signals)
            self._execute_execution_callbacks(rule_id, True, len(signals))

            return {
                'success': True,
                'rule_id': rule_id,
                'signals_generated': len(signals),
                'query_results': len(results),
                'signals': [s.to_dict() for s in signals]
            }

        except Exception as e:
            logger.error(f"Rule execution failed for {rule_id}: {e}")
            context.record_error(e, rule_id)
            self._update_rule_stats(rule_id, False, 0)

            self._execute_execution_callbacks(rule_id, False, 0, str(e))

            return {
                'success': False,
                'rule_id': rule_id,
                'error': str(e),
                'signals': []
            }

    def execute_rules_batch(
        self,
        rule_ids: List[str],
        scan_date: date,
        parallel: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute multiple rules in batch.

        Args:
            rule_ids: List of rule IDs to execute
            scan_date: Date to scan
            parallel: Whether to execute in parallel
            **kwargs: Additional execution parameters

        Returns:
            Batch execution results
        """
        if parallel and len(rule_ids) > 1:
            return self._execute_parallel(rule_ids, scan_date, **kwargs)
        else:
            return self._execute_sequential(rule_ids, scan_date, **kwargs)

    def _execute_parallel(
        self,
        rule_ids: List[str],
        scan_date: date,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute rules in parallel."""
        results = {
            'total_rules': len(rule_ids),
            'successful_executions': 0,
            'failed_executions': 0,
            'total_signals': 0,
            'signals': [],  # Collect all signals here
            'rule_results': {},
            'execution_errors': []
        }

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(rule_ids))) as executor:
            # Submit all tasks
            future_to_rule = {
                executor.submit(self.execute_rule, rule_id, scan_date, **kwargs): rule_id
                for rule_id in rule_ids
            }

            # Collect results
            for future in as_completed(future_to_rule):
                rule_id = future_to_rule[future]
                try:
                    result = future.result()
                    results['rule_results'][rule_id] = result

                    if result['success']:
                        results['successful_executions'] += 1
                        results['total_signals'] += result.get('signals_generated', 0)
                        # Collect all signals from this rule
                        results['signals'].extend(result.get('signals', []))
                    else:
                        results['failed_executions'] += 1
                        results['execution_errors'].append({
                            'rule_id': rule_id,
                            'error': result.get('error', 'Unknown error')
                        })

                except Exception as e:
                    logger.error(f"Parallel execution failed for {rule_id}: {e}")
                    results['failed_executions'] += 1
                    results['execution_errors'].append({
                        'rule_id': rule_id,
                        'error': str(e)
                    })

        return results

    def _execute_sequential(
        self,
        rule_ids: List[str],
        scan_date: date,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute rules sequentially."""
        results = {
            'total_rules': len(rule_ids),
            'successful_executions': 0,
            'failed_executions': 0,
            'total_signals': 0,
            'signals': [],  # Collect all signals here
            'rule_results': {},
            'execution_errors': []
        }

        for rule_id in rule_ids:
            result = self.execute_rule(rule_id, scan_date, **kwargs)
            results['rule_results'][rule_id] = result

            if result['success']:
                results['successful_executions'] += 1
                results['total_signals'] += result.get('signals_generated', 0)
                # Collect all signals from this rule
                results['signals'].extend(result.get('signals', []))
            else:
                results['failed_executions'] += 1
                results['execution_errors'].append({
                    'rule_id': rule_id,
                    'error': result.get('error', 'Unknown error')
                })

        return results

    def _execute_query(self, query: str, params: List[Any]) -> List[Dict[str, Any]]:
        """Execute SQL query against database."""
        try:
            if self.db_connection is None:
                logger.error("No database connection available")
                return []

            # Execute the query using the database connection
            logger.debug(f"Executing query: {query}")
            logger.debug(f"With params: {params}")

            # Use the database connection to execute query
            result = self.db_connection.execute(query, params)

            # Convert result to list of dictionaries
            if hasattr(result, 'fetchall'):
                rows = result.fetchall()
                logger.debug(f"Query returned {len(rows)} rows")

                if len(rows) > 0:
                    logger.debug(f"First row type: {type(rows[0])}")
                    logger.debug(f"First row length: {len(rows[0])}")
                    logger.debug(f"First row: {rows[0]}")
                    logger.debug(f"Processing {len(rows)} rows with {len(rows[0])} columns each")

                # DuckDB doesn't provide column names via .keys(), so we need to map by position
                # For breakout queries, we know the expected column order

                # Convert rows to dictionaries with proper column mapping
                results_list = []
                for row in rows:
                    row_dict = {}

                    # Map columns based on query type (determined by row length)
                    if len(row) == 11:  # breakout query with daily prices (updated)
                        column_names = ['symbol', 'timestamp', 'price', 'volume',
                                      'price_change_pct', 'volume_multiplier',
                                      'breakout_strength', 'price_at_0950',
                                      'price_at_1515', 'daily_performance_pct', 'pattern_type']
                    elif len(row) == 8:  # breakout query columns (original)
                        column_names = ['symbol', 'timestamp', 'price', 'volume',
                                      'price_change_pct', 'volume_multiplier',
                                      'breakout_strength', 'pattern_type']
                    elif len(row) == 7:  # crp query columns
                        column_names = ['symbol', 'timestamp', 'price', 'volume',
                                      'close_position', 'distance_from_mid', 'consolidation_range_pct']
                    else:
                        # Fallback to generic column names
                        column_names = [f'col_{i}' for i in range(len(row))]

                    # Map each column
                    for i, value in enumerate(row):
                        if i < len(column_names):
                            row_dict[column_names[i]] = value
                        else:
                            row_dict[f'col_{i}'] = value

                    results_list.append(row_dict)

                if results_list:
                    logger.debug(f"First mapped result dict: {results_list[0]}")
                    if len(results_list) > 0:
                        first_result = results_list[0]
                        logger.debug(f"price_at_1515 value: {first_result.get('price_at_1515', 'NOT_FOUND')}")
                        logger.debug(f"daily_performance_pct value: {first_result.get('daily_performance_pct', 'NOT_FOUND')}")
                return results_list
            else:
                logger.error("Query result does not support fetchall()")
                return []

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            return []

    def _calculate_confidence(self, result: Dict[str, Any], rule: Dict[str, Any]) -> float:
        """Calculate signal confidence based on rule and result data."""
        confidence = 0.5  # Base confidence

        # Adjust based on rule-specific metrics
        if 'volume_multiplier' in result:
            volume_mult = result['volume_multiplier']
            if volume_mult >= 2.0:
                confidence += 0.2
            elif volume_mult >= 1.5:
                confidence += 0.1

        if 'price_change_pct' in result:
            price_change = abs(result['price_change_pct'])
            if price_change >= 3.0:
                confidence += 0.2
            elif price_change >= 2.0:
                confidence += 0.1

        if 'distance_from_mid' in result:
            distance = result['distance_from_mid']
            if distance <= 0.05:
                confidence += 0.1

        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))

    def _update_rule_stats(self, rule_id: str, success: bool, signals_generated: int):
        """Update rule execution statistics."""
        stats = self.rule_execution_stats[rule_id]
        stats['execution_count'] += 1

        if success:
            stats['success_count'] += 1
        else:
            stats['failure_count'] += 1

        stats['total_signals_generated'] += signals_generated
        stats['last_executed'] = date.today()

    def add_signal_callback(self, callback: Callable):
        """Add callback for signal generation events."""
        self.signal_callbacks.append(callback)

    def add_execution_callback(self, callback: Callable):
        """Add callback for rule execution events."""
        self.execution_callbacks.append(callback)

    def _execute_signal_callbacks(self, signals: List[TradingSignal]):
        """Execute signal generation callbacks."""
        for callback in self.signal_callbacks:
            try:
                callback(signals)
            except Exception as e:
                logger.error(f"Signal callback failed: {e}")

    def _execute_execution_callbacks(self, rule_id: str, success: bool, signals_count: int, error: str = None):
        """Execute rule execution callbacks."""
        for callback in self.execution_callbacks:
            try:
                callback(rule_id, success, signals_count, error)
            except Exception as e:
                logger.error(f"Execution callback failed: {e}")

    def get_rule_stats(self, rule_id: Optional[str] = None) -> Dict[str, Any]:
        """Get rule execution statistics."""
        if rule_id:
            return self.rule_execution_stats.get(rule_id, {})
        else:
            return dict(self.rule_execution_stats)

    def get_engine_stats(self) -> Dict[str, Any]:
        """Get overall engine statistics."""
        total_rules = len(self.rules)
        total_executions = sum(stats['execution_count'] for stats in self.rule_execution_stats.values())
        total_signals = sum(stats['total_signals_generated'] for stats in self.rule_execution_stats.values())
        success_rate = 0

        if total_executions > 0:
            successful_executions = sum(stats['success_count'] for stats in self.rule_execution_stats.values())
            success_rate = successful_executions / total_executions

        return {
            'total_rules': total_rules,
            'total_executions': total_executions,
            'total_signals_generated': total_signals,
            'overall_success_rate': success_rate,
            'active_rules': len([r for r in self.rules.values() if r.get('enabled', True)]),
            'query_cache_stats': self.query_builder.get_cache_stats()
        }

    def clear_cache(self):
        """Clear all caches."""
        self.query_builder.clear_cache()
        logger.info("Rule engine caches cleared")

    def shutdown(self):
        """Shutdown the rule engine."""
        self.clear_cache()
        self.context_manager.cleanup_expired_contexts(max_age_seconds=0)  # Clean all
        logger.info("Rule engine shutdown complete")
