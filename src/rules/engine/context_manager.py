"""
Execution Context Manager

This module manages execution context for rule processing including:
- Date ranges and time windows
- Symbol filtering
- Performance tracking
- Resource management
"""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime, date, time as dt_time
from dataclasses import dataclass, field
from contextlib import contextmanager
import logging
import time as time_module

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Execution context for rule processing."""
    scan_date: date
    start_time: Optional[dt_time] = None
    end_time: Optional[dt_time] = None
    symbols: Optional[List[str]] = None
    market_data_cache: Dict[str, Any] = field(default_factory=dict)
    execution_params: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize execution context."""
        if self.start_time is None:
            self.start_time = dt_time(9, 15)  # Default market open
        if self.end_time is None:
            self.end_time = dt_time(15, 30)  # Default market close

        # Initialize performance tracking
        self.performance_metrics = {
            'start_time': datetime.now(),
            'rules_executed': 0,
            'queries_executed': 0,
            'signals_generated': 0,
            'execution_time_ms': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': []
        }

    def is_time_in_window(self, check_time: dt_time) -> bool:
        """Check if a time falls within the execution window."""
        return self.start_time <= check_time <= self.end_time

    def should_process_symbol(self, symbol: str) -> bool:
        """Check if a symbol should be processed based on filters."""
        if self.symbols is None:
            return True
        return symbol in self.symbols

    def record_query_execution(self, query_type: str, execution_time_ms: float):
        """Record query execution metrics."""
        self.performance_metrics['queries_executed'] += 1
        if 'query_times' not in self.performance_metrics:
            self.performance_metrics['query_times'] = []
        self.performance_metrics['query_times'].append({
            'type': query_type,
            'time_ms': execution_time_ms
        })

    def record_signal_generation(self, rule_id: str, confidence: float):
        """Record signal generation metrics."""
        self.performance_metrics['signals_generated'] += 1
        if 'signals' not in self.performance_metrics:
            self.performance_metrics['signals'] = []
        self.performance_metrics['signals'].append({
            'rule_id': rule_id,
            'confidence': confidence,
            'timestamp': datetime.now()
        })

    def record_error(self, error: Exception, rule_id: Optional[str] = None):
        """Record execution errors."""
        self.performance_metrics['errors'].append({
            'rule_id': rule_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now()
        })

    def finalize_metrics(self):
        """Finalize performance metrics."""
        end_time = datetime.now()
        start_time = self.performance_metrics['start_time']
        self.performance_metrics['execution_time_ms'] = (end_time - start_time).total_seconds() * 1000
        self.performance_metrics['end_time'] = end_time

        # Calculate averages
        if self.performance_metrics['query_times']:
            query_times = [q['time_ms'] for q in self.performance_metrics['query_times']]
            self.performance_metrics['avg_query_time_ms'] = sum(query_times) / len(query_times)
            self.performance_metrics['max_query_time_ms'] = max(query_times)
            self.performance_metrics['min_query_time_ms'] = min(query_times)

        # Calculate cache hit rate
        total_cache_accesses = self.performance_metrics['cache_hits'] + self.performance_metrics['cache_misses']
        if total_cache_accesses > 0:
            self.performance_metrics['cache_hit_rate'] = (
                self.performance_metrics['cache_hits'] / total_cache_accesses
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            'scan_date': self.scan_date.isoformat(),
            'time_window': f"{self.start_time} - {self.end_time}",
            'symbols_count': len(self.symbols) if self.symbols else 'all',
            'execution_time_ms': self.performance_metrics.get('execution_time_ms', 0),
            'rules_executed': self.performance_metrics.get('rules_executed', 0),
            'signals_generated': self.performance_metrics.get('signals_generated', 0),
            'queries_executed': self.performance_metrics.get('queries_executed', 0),
            'cache_hit_rate': self.performance_metrics.get('cache_hit_rate', 0),
            'errors_count': len(self.performance_metrics.get('errors', []))
        }


class ContextManager:
    """Manages execution contexts and resource lifecycle."""

    def __init__(self):
        self.active_contexts: Dict[str, ExecutionContext] = {}
        self.context_history: List[ExecutionContext] = []
        self.max_history_size = 100

    def create_context(
        self,
        scan_date: date,
        start_time: Optional[dt_time] = None,
        end_time: Optional[dt_time] = None,
        symbols: Optional[List[str]] = None,
        context_id: Optional[str] = None
    ) -> ExecutionContext:
        """Create a new execution context."""
        context = ExecutionContext(
            scan_date=scan_date,
            start_time=start_time,
            end_time=end_time,
            symbols=symbols
        )

        if context_id is None:
            context_id = f"ctx_{int(time_module.time())}_{id(context)}"

        self.active_contexts[context_id] = context
        logger.info(f"Created execution context: {context_id}")

        return context

    def get_context(self, context_id: str) -> Optional[ExecutionContext]:
        """Get an active execution context."""
        return self.active_contexts.get(context_id)

    def finalize_context(self, context_id: str) -> Optional[ExecutionContext]:
        """Finalize and remove an execution context."""
        context = self.active_contexts.pop(context_id, None)
        if context:
            context.finalize_metrics()
            self._add_to_history(context)
            logger.info(f"Finalized execution context: {context_id}")
        return context

    def cleanup_expired_contexts(self, max_age_seconds: int = 3600):
        """Clean up old execution contexts."""
        current_time = datetime.now()
        expired_ids = []

        for context_id, context in self.active_contexts.items():
            age = (current_time - context.performance_metrics['start_time']).total_seconds()
            if age > max_age_seconds:
                expired_ids.append(context_id)

        for context_id in expired_ids:
            self.finalize_context(context_id)
            logger.info(f"Cleaned up expired context: {context_id}")

    def _add_to_history(self, context: ExecutionContext):
        """Add context to history with size limit."""
        self.context_history.append(context)
        if len(self.context_history) > self.max_history_size:
            self.context_history.pop(0)

    def get_context_history(self, limit: int = 10) -> List[ExecutionContext]:
        """Get recent execution context history."""
        return self.context_history[-limit:]

    def get_performance_summary(self, context_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get performance summary for contexts."""
        contexts = []
        if context_ids:
            contexts = [self.active_contexts.get(cid) for cid in context_ids if cid in self.active_contexts]
        else:
            contexts = list(self.active_contexts.values())

        if not contexts:
            return {}

        total_execution_time = sum(c.performance_metrics.get('execution_time_ms', 0) for c in contexts)
        total_signals = sum(c.performance_metrics.get('signals_generated', 0) for c in contexts)
        total_queries = sum(c.performance_metrics.get('queries_executed', 0) for c in contexts)
        total_errors = sum(len(c.performance_metrics.get('errors', [])) for c in contexts)

        return {
            'active_contexts': len(contexts),
            'total_execution_time_ms': total_execution_time,
            'total_signals_generated': total_signals,
            'total_queries_executed': total_queries,
            'total_errors': total_errors,
            'avg_execution_time_ms': total_execution_time / len(contexts) if contexts else 0,
            'avg_signals_per_context': total_signals / len(contexts) if contexts else 0
        }


@contextmanager
def execution_context_manager(
    scan_date: date,
    start_time: Optional[dt_time] = None,
    end_time: Optional[dt_time] = None,
    symbols: Optional[List[str]] = None
):
    """
    Context manager for rule execution.

    Usage:
        with execution_context_manager(date.today()) as context:
            # Execute rules within context
            pass
    """
    manager = ContextManager()
    context = manager.create_context(scan_date, start_time, end_time, symbols)

    try:
        yield context
    finally:
        manager.finalize_context(f"ctx_{int(time.time())}_{id(context)}")
