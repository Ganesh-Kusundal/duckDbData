"""
Query Builder

Main query builder that orchestrates specialized query builders using the Strategy pattern.
This module provides a unified interface for building SQL queries from rule conditions.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import date, time
import logging

from ..schema.rule_types import RuleType

# Import specialized query builders
from .breakout_query_builder import BreakoutQueryBuilder
from .crp_query_builder import CRPQueryBuilder
from .technical_query_builder import TechnicalQueryBuilder
from .volume_query_builder import VolumeQueryBuilder
from .custom_query_builder import CustomQueryBuilder

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Main query builder that orchestrates specialized builders using Strategy pattern.

    This class provides a unified interface while delegating to specialized
    builders for different rule types.
    """

    def __init__(self):
        # Initialize specialized builders
        self.builders = {
            'breakout': BreakoutQueryBuilder(),
            'crp': CRPQueryBuilder(),
            'technical': TechnicalQueryBuilder(),
            'volume': VolumeQueryBuilder(),
            'custom': CustomQueryBuilder(),
            'momentum': VolumeQueryBuilder()  # Reuse volume builder for momentum
        }

        # Global cache across all builders
        self.query_cache = {}
        self.max_cache_size = 2000

    def build_query(
        self,
        rule_type: RuleType,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for rule execution using appropriate specialized builder.

        Args:
            rule_type: Type of rule (breakout, crp, technical, etc.)
            conditions: Rule conditions dictionary
            scan_date: Date to scan
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter list

        Returns:
            Tuple of (SQL query string, parameters dictionary)
        """
        # Get the appropriate builder for this rule type
        rule_type_str = rule_type.value.lower()  # Use enum value, not string representation
        builder = self.builders.get(rule_type_str)

        if not builder:
            raise ValueError(f"No query builder available for rule type: {rule_type}")

        # Delegate to the specialized builder
        return builder.build_query(conditions, scan_date, start_time, end_time, symbols)

    # Legacy methods for backward compatibility
    def _build_breakout_query(self, conditions: Dict[str, Any], scan_date: date, start_time: Optional[time], end_time: Optional[time], symbols: Optional[List[str]]) -> Tuple[str, Dict[str, Any]]:
        """Legacy breakout query builder - delegates to specialized builder."""
        return self.builders['breakout'].build_query(conditions, scan_date, start_time, end_time, symbols)

    def _build_crp_query(self, conditions: Dict[str, Any], scan_date: date, start_time: Optional[time], end_time: Optional[time], symbols: Optional[List[str]]) -> Tuple[str, Dict[str, Any]]:
        """Legacy CRP query builder - delegates to specialized builder."""
        return self.builders['crp'].build_query(conditions, scan_date, start_time, end_time, symbols)

    def _build_technical_query(self, conditions: Dict[str, Any], scan_date: date, start_time: Optional[time], end_time: Optional[time], symbols: Optional[List[str]]) -> Tuple[str, Dict[str, Any]]:
        """Legacy technical query builder - delegates to specialized builder."""
        return self.builders['technical'].build_query(conditions, scan_date, start_time, end_time, symbols)

    def _build_volume_query(self, conditions: Dict[str, Any], scan_date: date, start_time: Optional[time], end_time: Optional[time], symbols: Optional[List[str]]) -> Tuple[str, Dict[str, Any]]:
        """Legacy volume query builder - delegates to specialized builder."""
        return self.builders['volume'].build_query(conditions, scan_date, start_time, end_time, symbols)

    def _build_momentum_query(self, conditions: Dict[str, Any], scan_date: date, start_time: Optional[time], end_time: Optional[time], symbols: Optional[List[str]]) -> Tuple[str, Dict[str, Any]]:
        """Legacy momentum query builder - delegates to specialized builder."""
        return self.builders['momentum'].build_query(conditions, scan_date, start_time, end_time, symbols)

    def _build_custom_query(self, conditions: Dict[str, Any], scan_date: date, start_time: Optional[time], end_time: Optional[time], symbols: Optional[List[str]]) -> Tuple[str, Dict[str, Any]]:
        """Legacy custom query builder - delegates to specialized builder."""
        return self.builders['custom'].build_query(conditions, scan_date, start_time, end_time, symbols)

    def _create_cache_key(
        self,
        rule_type: RuleType,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> str:
        """Create a cache key for query caching."""
        # Create a deterministic key from query parameters
        def format_time_param(time_param):
            if time_param is None:
                return "None"
            elif hasattr(time_param, 'isoformat'):
                return time_param.isoformat()
            else:
                return str(time_param)

        key_parts = [
            str(rule_type),
            str(scan_date),
            format_time_param(start_time),
            format_time_param(end_time),
            str(sorted(symbols)) if symbols else "None",
            str(sorted(conditions.items()))
        ]
        return "|".join(key_parts)

    def _cache_query(self, key: str, query_data: Tuple[str, Dict[str, Any]]):
        """Cache query result."""
        if len(self.query_cache) >= self.max_cache_size:
            # Remove oldest entry (simple LRU approximation)
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]
        self.query_cache[key] = query_data

    def _get_cached_query(self, key: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Get cached query if available."""
        return self.query_cache.get(key)

    def clear_cache(self):
        """Clear query cache."""
        self.query_cache.clear()
        # Also clear caches of all specialized builders
        for builder in self.builders.values():
            builder.clear_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_cached = len(self.query_cache)
        builder_stats = {}
        for name, builder in self.builders.items():
            builder_stats[name] = builder.get_cache_stats()

        return {
            'main_cache_size': total_cached,
            'main_cache_limit': self.max_cache_size,
            'builder_caches': builder_stats
        }
