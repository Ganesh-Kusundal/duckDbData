"""
Log Aggregation and Analysis Service
====================================

This module provides services for aggregating, filtering, and analyzing log data.
Supports advanced search, filtering, and statistical analysis of logs.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import re

from ..config.database import monitoring_db
from ..config.settings import config
from .structured_logger import get_logger

logger = get_logger(__name__)


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogFilter:
    """Log filtering criteria."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    levels: Optional[List[str]] = None
    components: Optional[List[str]] = None
    correlation_id: Optional[str] = None
    message_contains: Optional[str] = None
    source_file: Optional[str] = None
    limit: int = 1000
    offset: int = 0


@dataclass
class LogStats:
    """Log statistics summary."""
    total_entries: int
    entries_by_level: Dict[str, int]
    entries_by_component: Dict[str, int]
    time_range: Tuple[datetime, datetime]
    error_rate: float
    unique_correlation_ids: int
    most_common_errors: List[Tuple[str, int]]


class LogAggregator:
    """Service for aggregating and analyzing log data."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def get_logs(self, filter_criteria: LogFilter) -> List[Dict[str, Any]]:
        """Retrieve logs based on filter criteria."""
        query = """
            SELECT
                id,
                timestamp,
                level,
                component,
                message,
                extra_data,
                correlation_id,
                source_file,
                source_line,
                function_name,
                created_at
            FROM system_logs
            WHERE 1=1
        """
        params = []

        # Apply filters
        if filter_criteria.start_time:
            query += " AND timestamp >= ?"
            params.append(filter_criteria.start_time)

        if filter_criteria.end_time:
            query += " AND timestamp <= ?"
            params.append(filter_criteria.end_time)

        if filter_criteria.levels:
            placeholders = ','.join('?' * len(filter_criteria.levels))
            query += f" AND level IN ({placeholders})"
            params.extend(filter_criteria.levels)

        if filter_criteria.components:
            placeholders = ','.join('?' * len(filter_criteria.components))
            query += f" AND component IN ({placeholders})"
            params.extend(filter_criteria.components)

        if filter_criteria.correlation_id:
            query += " AND correlation_id = ?"
            params.append(filter_criteria.correlation_id)

        if filter_criteria.message_contains:
            query += " AND message LIKE ?"
            params.append(f"%{filter_criteria.message_contains}%")

        if filter_criteria.source_file:
            query += " AND source_file LIKE ?"
            params.append(f"%{filter_criteria.source_file}%")

        # Order by timestamp descending (most recent first)
        query += " ORDER BY timestamp DESC"

        # Apply pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([filter_criteria.limit, filter_criteria.offset])

        try:
            with monitoring_db.get_connection() as conn:
                results = conn.execute(query, params).fetchall()

            # Convert to dictionaries
            logs = []
            for row in results:
                log_entry = {
                    'id': row[0],
                    'timestamp': row[1],
                    'level': row[2],
                    'component': row[3],
                    'message': row[4],
                    'extra_data': json.loads(row[5]) if row[5] else {},
                    'correlation_id': row[6],
                    'source_file': row[7],
                    'source_line': row[8],
                    'function_name': row[9],
                    'created_at': row[10]
                }
                logs.append(log_entry)

            return logs

        except Exception as e:
            self.logger.error("Failed to retrieve logs", extra={'error': str(e), 'filter': asdict(filter_criteria)})
            return []

    def search_logs(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search logs using full-text search."""
        try:
            with monitoring_db.get_connection() as conn:
                # Use DuckDB's full-text search capabilities
                search_query = """
                    SELECT
                        id,
                        timestamp,
                        level,
                        component,
                        message,
                        extra_data,
                        correlation_id,
                        source_file,
                        source_line,
                        function_name
                    FROM system_logs
                    WHERE message LIKE ? OR extra_data LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """

                search_pattern = f"%{query}%"
                results = conn.execute(search_query, [search_pattern, search_pattern, limit]).fetchall()

            # Convert to dictionaries
            logs = []
            for row in results:
                log_entry = {
                    'id': row[0],
                    'timestamp': row[1],
                    'level': row[2],
                    'component': row[3],
                    'message': row[4],
                    'extra_data': json.loads(row[5]) if row[5] else {},
                    'correlation_id': row[6],
                    'source_file': row[7],
                    'source_line': row[8],
                    'function_name': row[9]
                }
                logs.append(log_entry)

            return logs

        except Exception as e:
            self.logger.error("Failed to search logs", extra={'error': str(e), 'query': query})
            return []

    def get_log_stats(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> LogStats:
        """Get comprehensive log statistics."""
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()

        try:
            with monitoring_db.get_connection() as conn:
                # Get total entries
                total_query = "SELECT COUNT(*) FROM system_logs WHERE timestamp BETWEEN ? AND ?"
                total_result = conn.execute(total_query, [start_time, end_time]).fetchone()
                total_entries = total_result[0] if total_result else 0

                # Get entries by level
                level_query = """
                    SELECT level, COUNT(*) as count
                    FROM system_logs
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY level
                    ORDER BY count DESC
                """
                level_results = conn.execute(level_query, [start_time, end_time]).fetchall()
                entries_by_level = {row[0]: row[1] for row in level_results}

                # Get entries by component
                component_query = """
                    SELECT component, COUNT(*) as count
                    FROM system_logs
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY component
                    ORDER BY count DESC
                    LIMIT 20
                """
                component_results = conn.execute(component_query, [start_time, end_time]).fetchall()
                entries_by_component = {row[0]: row[1] for row in component_results}

                # Get unique correlation IDs
                correlation_query = """
                    SELECT COUNT(DISTINCT correlation_id)
                    FROM system_logs
                    WHERE timestamp BETWEEN ? AND ?
                    AND correlation_id IS NOT NULL
                """
                correlation_result = conn.execute(correlation_query, [start_time, end_time]).fetchone()
                unique_correlation_ids = correlation_result[0] if correlation_result else 0

                # Calculate error rate
                error_levels = ['ERROR', 'CRITICAL']
                error_count = sum(entries_by_level.get(level, 0) for level in error_levels)
                error_rate = (error_count / total_entries * 100) if total_entries > 0 else 0.0

                # Get most common errors
                error_query = """
                    SELECT message, COUNT(*) as count
                    FROM system_logs
                    WHERE timestamp BETWEEN ? AND ?
                    AND level IN ('ERROR', 'CRITICAL')
                    GROUP BY message
                    ORDER BY count DESC
                    LIMIT 10
                """
                error_results = conn.execute(error_query, [start_time, end_time]).fetchall()
                most_common_errors = [(row[0], row[1]) for row in error_results]

            return LogStats(
                total_entries=total_entries,
                entries_by_level=entries_by_level,
                entries_by_component=entries_by_component,
                time_range=(start_time, end_time),
                error_rate=error_rate,
                unique_correlation_ids=unique_correlation_ids,
                most_common_errors=most_common_errors
            )

        except Exception as e:
            self.logger.error("Failed to get log statistics", extra={'error': str(e)})
            return LogStats(
                total_entries=0,
                entries_by_level={},
                entries_by_component={},
                time_range=(start_time, end_time),
                error_rate=0.0,
                unique_correlation_ids=0,
                most_common_errors=[]
            )

    def get_components(self) -> List[str]:
        """Get list of all unique components."""
        try:
            with monitoring_db.get_connection() as conn:
                results = conn.execute("SELECT DISTINCT component FROM system_logs ORDER BY component").fetchall()
            return [row[0] for row in results]
        except Exception as e:
            self.logger.error("Failed to get components", extra={'error': str(e)})
            return []

    def get_correlation_trace(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get all logs for a specific correlation ID."""
        filter_criteria = LogFilter(
            correlation_id=correlation_id,
            limit=1000  # Get all logs for this correlation ID
        )
        return self.get_logs(filter_criteria)

    def cleanup_old_logs(self) -> int:
        """Clean up old logs based on retention policy. Returns number of deleted entries."""
        try:
            retention_days = config.logging.retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            with monitoring_db.get_connection() as conn:
                result = conn.execute(
                    "DELETE FROM system_logs WHERE timestamp < ?",
                    [cutoff_date]
                )
                deleted_count = result.fetchone()[0]

            self.logger.info("Cleaned up old logs", extra={
                'deleted_count': deleted_count,
                'retention_days': retention_days
            })

            return deleted_count

        except Exception as e:
            self.logger.error("Failed to cleanup old logs", extra={'error': str(e)})
            return 0

    def export_logs(self, filter_criteria: LogFilter, format: str = 'json') -> str:
        """Export logs in specified format."""
        logs = self.get_logs(filter_criteria)

        if format.lower() == 'json':
            return json.dumps(logs, indent=2, default=str)
        elif format.lower() == 'csv':
            if not logs:
                return "No logs found"

            # Get all unique keys for CSV headers
            all_keys = set()
            for log in logs:
                all_keys.update(log.keys())

            headers = sorted(all_keys)

            # Create CSV content
            lines = [','.join(f'"{h}"' for h in headers)]

            for log in logs:
                row = []
                for header in headers:
                    value = log.get(header, '')
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    row.append(f'"{str(value).replace(chr(34), chr(34) + chr(34))}"')
                lines.append(','.join(row))

            return '\n'.join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global instance
log_aggregator = LogAggregator()
