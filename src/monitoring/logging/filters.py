"""
Advanced Log Filtering and Querying
====================================

This module provides advanced filtering capabilities for log analysis,
including complex queries, pattern matching, and statistical filtering.
"""

from typing import List, Dict, Any, Optional, Set, Pattern, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import re
import json

from .structured_logger import get_logger

logger = get_logger(__name__)


class FilterOperator(Enum):
    """Filter operators for advanced queries."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"


@dataclass
class AdvancedFilter:
    """Advanced filter with operator support."""
    field: str
    operator: FilterOperator
    value: Union[str, int, float, List[Any], Tuple[Any, Any]]
    case_sensitive: bool = True

    def matches(self, log_entry: Dict[str, Any]) -> bool:
        """Check if log entry matches this filter."""
        try:
            field_value = self._get_nested_value(log_entry, self.field)
            if field_value is None:
                return False

            return self._apply_operator(field_value)

        except Exception:
            return False

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                current = current[int(key)] if int(key) < len(current) else None
            else:
                return None

        return current

    def _apply_operator(self, field_value: Any) -> bool:
        """Apply the filter operator to the field value."""
        if not self.case_sensitive and isinstance(field_value, str):
            field_value = field_value.lower()
            if isinstance(self.value, str):
                compare_value = self.value.lower()
            else:
                compare_value = self.value
        else:
            compare_value = self.value

        if self.operator == FilterOperator.EQUALS:
            return field_value == compare_value
        elif self.operator == FilterOperator.NOT_EQUALS:
            return field_value != compare_value
        elif self.operator == FilterOperator.CONTAINS:
            return str(compare_value) in str(field_value)
        elif self.operator == FilterOperator.NOT_CONTAINS:
            return str(compare_value) not in str(field_value)
        elif self.operator == FilterOperator.STARTS_WITH:
            return str(field_value).startswith(str(compare_value))
        elif self.operator == FilterOperator.ENDS_WITH:
            return str(field_value).endswith(str(compare_value))
        elif self.operator == FilterOperator.REGEX:
            try:
                pattern = re.compile(str(compare_value), re.IGNORECASE if not self.case_sensitive else 0)
                return bool(pattern.search(str(field_value)))
            except re.error:
                return False
        elif self.operator == FilterOperator.GREATER_THAN:
            try:
                return float(field_value) > float(compare_value)
            except (ValueError, TypeError):
                return False
        elif self.operator == FilterOperator.LESS_THAN:
            try:
                return float(field_value) < float(compare_value)
            except (ValueError, TypeError):
                return False
        elif self.operator == FilterOperator.GREATER_EQUAL:
            try:
                return float(field_value) >= float(compare_value)
            except (ValueError, TypeError):
                return False
        elif self.operator == FilterOperator.LESS_EQUAL:
            try:
                return float(field_value) <= float(compare_value)
            except (ValueError, TypeError):
                return False
        elif self.operator == FilterOperator.IN:
            if isinstance(compare_value, list):
                return field_value in compare_value
            return False
        elif self.operator == FilterOperator.NOT_IN:
            if isinstance(compare_value, list):
                return field_value not in compare_value
            return False
        elif self.operator == FilterOperator.BETWEEN:
            if isinstance(compare_value, (list, tuple)) and len(compare_value) == 2:
                try:
                    val = float(field_value)
                    return compare_value[0] <= val <= compare_value[1]
                except (ValueError, TypeError):
                    return False
            return False

        return False


@dataclass
class CompositeFilter:
    """Composite filter combining multiple filters with logical operators."""
    filters: List[Union[AdvancedFilter, 'CompositeFilter']] = field(default_factory=list)
    operator: str = "AND"  # "AND" or "OR"

    def matches(self, log_entry: Dict[str, Any]) -> bool:
        """Check if log entry matches this composite filter."""
        if not self.filters:
            return True

        results = []
        for filter_item in self.filters:
            results.append(filter_item.matches(log_entry))

        if self.operator == "AND":
            return all(results)
        elif self.operator == "OR":
            return any(results)

        return False


@dataclass
class LogQuery:
    """Advanced log query with multiple filter types."""
    time_range: Optional[tuple[datetime, datetime]] = None
    level_filter: Optional[List[str]] = None
    component_filter: Optional[List[str]] = None
    correlation_id: Optional[str] = None
    advanced_filters: Optional[List[AdvancedFilter]] = None
    composite_filter: Optional[CompositeFilter] = None
    sort_by: str = "timestamp"
    sort_order: str = "desc"
    limit: int = 1000
    offset: int = 0


class LogFilterEngine:
    """Advanced log filtering engine."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._compiled_patterns: Dict[str, Pattern] = {}

    def apply_filters(self, logs: List[Dict[str, Any]], query: LogQuery) -> List[Dict[str, Any]]:
        """Apply all filters to a list of log entries."""
        filtered_logs = logs

        # Apply time range filter
        if query.time_range:
            start_time, end_time = query.time_range
            filtered_logs = [
                log for log in filtered_logs
                if start_time <= log.get('timestamp') <= end_time
            ]

        # Apply level filter
        if query.level_filter:
            filtered_logs = [
                log for log in filtered_logs
                if log.get('level') in query.level_filter
            ]

        # Apply component filter
        if query.component_filter:
            filtered_logs = [
                log for log in filtered_logs
                if log.get('component') in query.component_filter
            ]

        # Apply correlation ID filter
        if query.correlation_id:
            filtered_logs = [
                log for log in filtered_logs
                if log.get('correlation_id') == query.correlation_id
            ]

        # Apply advanced filters
        if query.advanced_filters:
            for advanced_filter in query.advanced_filters:
                filtered_logs = [
                    log for log in filtered_logs
                    if advanced_filter.matches(log)
                ]

        # Apply composite filter
        if query.composite_filter:
            filtered_logs = [
                log for log in filtered_logs
                if query.composite_filter.matches(log)
            ]

        # Apply sorting
        reverse = query.sort_order.lower() == "desc"
        try:
            filtered_logs.sort(key=lambda x: x.get(query.sort_by), reverse=reverse)
        except (KeyError, TypeError):
            # Fallback to timestamp sorting
            filtered_logs.sort(key=lambda x: x.get('timestamp'), reverse=reverse)

        # Apply pagination
        start_idx = query.offset
        end_idx = start_idx + query.limit
        filtered_logs = filtered_logs[start_idx:end_idx]

        return filtered_logs

    def create_preset_filters(self) -> Dict[str, CompositeFilter]:
        """Create commonly used preset filters."""
        return {
            "errors_last_hour": CompositeFilter(
                filters=[
                    AdvancedFilter("level", FilterOperator.IN, ["ERROR", "CRITICAL"]),
                    AdvancedFilter("timestamp", FilterOperator.GREATER_THAN,
                                 datetime.now() - timedelta(hours=1))
                ],
                operator="AND"
            ),

            "database_operations": CompositeFilter(
                filters=[
                    AdvancedFilter("component", FilterOperator.CONTAINS, "database"),
                    AdvancedFilter("level", FilterOperator.NOT_EQUALS, "DEBUG")
                ],
                operator="AND"
            ),

            "user_actions": CompositeFilter(
                filters=[
                    AdvancedFilter("message", FilterOperator.REGEX, r"user.*action"),
                    AdvancedFilter("level", FilterOperator.IN, ["INFO", "WARNING"])
                ],
                operator="AND"
            ),

            "performance_issues": CompositeFilter(
                filters=[
                    AdvancedFilter("extra_data.duration", FilterOperator.GREATER_THAN, 5.0),
                    AdvancedFilter("level", FilterOperator.EQUALS, "WARNING")
                ],
                operator="AND"
            )
        }

    def parse_query_string(self, query_string: str) -> CompositeFilter:
        """Parse a simple query string into filters."""
        # Simple parser for basic queries like:
        # "level:ERROR component:database message:timeout"
        # "ERROR AND database AND timeout"

        filters = []

        # Split by AND/OR operators
        parts = re.split(r'\s+(AND|OR)\s+', query_string.upper())

        if len(parts) == 1:
            # Simple space-separated terms
            terms = query_string.split()
            for term in terms:
                if ':' in term:
                    field, value = term.split(':', 1)
                    filters.append(AdvancedFilter(field, FilterOperator.CONTAINS, value))
                else:
                    # Search in message field
                    filters.append(AdvancedFilter("message", FilterOperator.CONTAINS, term))
        else:
            # Complex query with operators
            # This is a simplified parser - could be enhanced
            operator = "AND"  # Default
            for part in parts:
                if part in ["AND", "OR"]:
                    operator = part
                else:
                    # Parse individual filter
                    if ':' in part:
                        field, value = part.split(':', 1)
                        filters.append(AdvancedFilter(field, FilterOperator.CONTAINS, value))
                    else:
                        filters.append(AdvancedFilter("message", FilterOperator.CONTAINS, part))

        return CompositeFilter(filters=filters, operator=operator)

    def get_filter_suggestions(self, partial_query: str) -> List[str]:
        """Get filter suggestions based on partial query."""
        suggestions = []

        # Field suggestions
        fields = ["level", "component", "message", "correlation_id", "source_file", "function_name"]
        for field in fields:
            if field.startswith(partial_query.lower()):
                suggestions.append(f"{field}:")

        # Operator suggestions
        if ":" in partial_query:
            operators = ["eq:", "ne:", "contains:", "regex:", "gt:", "lt:"]
            for op in operators:
                if op.startswith(partial_query.split(":")[-1]):
                    suggestions.append(partial_query.split(":")[0] + ":" + op)

        # Level suggestions
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in levels:
            if level.lower().startswith(partial_query.lower()):
                suggestions.append(f"level:{level}")

        return suggestions[:10]  # Limit suggestions

    def validate_filter(self, filter_obj: Union[AdvancedFilter, CompositeFilter]) -> List[str]:
        """Validate filter configuration and return any errors."""
        errors = []

        if isinstance(filter_obj, AdvancedFilter):
            # Validate field exists in typical log entry
            valid_fields = {
                "timestamp", "level", "component", "message", "correlation_id",
                "source_file", "source_line", "function_name", "extra_data"
            }

            # Allow nested fields in extra_data
            if not (filter_obj.field in valid_fields or filter_obj.field.startswith("extra_data.")):
                errors.append(f"Invalid field: {filter_obj.field}")

            # Validate operator and value compatibility
            if filter_obj.operator in [FilterOperator.IN, FilterOperator.NOT_IN]:
                if not isinstance(filter_obj.value, list):
                    errors.append(f"Operator {filter_obj.operator.value} requires a list value")

            if filter_obj.operator == FilterOperator.BETWEEN:
                if not isinstance(filter_obj.value, (list, tuple)) or len(filter_obj.value) != 2:
                    errors.append("BETWEEN operator requires a list/tuple of exactly 2 values")

        elif isinstance(filter_obj, CompositeFilter):
            if filter_obj.operator not in ["AND", "OR"]:
                errors.append(f"Invalid composite operator: {filter_obj.operator}")

            for sub_filter in filter_obj.filters:
                errors.extend(self.validate_filter(sub_filter))

        return errors


# Global instance
filter_engine = LogFilterEngine()
