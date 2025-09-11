"""
Base Query Builder

Abstract base class for rule-specific query builders following the Strategy pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import date, time
import logging

logger = logging.getLogger(__name__)


class BaseQueryBuilder(ABC):
    """Abstract base class for rule-specific query builders."""

    def __init__(self):
        self.query_cache = {}
        self.max_cache_size = 500

    @abstractmethod
    def build_query(
        self,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build SQL query for specific rule type.

        Args:
            conditions: Rule conditions dictionary
            scan_date: Date to scan
            start_time: Start time filter
            end_time: End time filter
            symbols: Symbol filter list

        Returns:
            Tuple of (SQL query string, parameters dict)
        """
        pass

    def _create_cache_key(
        self,
        rule_type: str,
        conditions: Dict[str, Any],
        scan_date: date,
        start_time: Optional[time],
        end_time: Optional[time],
        symbols: Optional[List[str]]
    ) -> str:
        """Create cache key for query caching."""
        key_parts = [
            rule_type,
            str(scan_date),
            str(start_time) if start_time else "None",
            str(end_time) if end_time else "None",
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

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cache_size': len(self.query_cache),
            'max_cache_size': self.max_cache_size,
            'cache_hit_ratio': 0.0  # Could be implemented with hit/miss counters
        }

    @staticmethod
    def convert_time_to_seconds(time_param: Union[str, time]) -> int:
        """Convert time parameter to seconds since midnight."""
        if isinstance(time_param, str):
            # Parse time string like "09:30:00"
            if ":" in time_param:
                parts = time_param.split(":")
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                seconds = int(parts[2]) if len(parts) > 2 else 0
                return hours * 3600 + minutes * 60 + seconds
            else:
                return int(time_param)
        elif isinstance(time_param, time):
            return time_param.hour * 3600 + time_param.minute * 60 + time_param.second
        else:
            raise ValueError(f"Unsupported time parameter type: {type(time_param)}")

    @staticmethod
    def format_time_param(time_param: Union[str, time]) -> str:
        """Format time parameter for SQL queries."""
        if isinstance(time_param, str):
            return time_param
        elif isinstance(time_param, time):
            return time_param.strftime("%H:%M:%S")
        else:
            return str(time_param)
