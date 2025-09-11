"""
Metrics Storage and Retrieval
=============================

This module handles storage and retrieval of performance metrics
with efficient querying and data retention management.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from ..config.database import monitoring_db
from ..config.settings import config
from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricData:
    """Metric data point."""
    metric_name: str
    metric_value: float
    metric_type: str
    component: str
    host_name: str
    collected_at: datetime
    tags: Dict[str, Any]


class MetricsStorage:
    """Handles metrics storage and retrieval operations."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def store_metric(self, metric: MetricData) -> None:
        """Store a single metric data point."""
        try:
            with monitoring_db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric.metric_name,
                    metric.metric_value,
                    metric.metric_type,
                    metric.component,
                    metric.host_name,
                    metric.collected_at,
                    json.dumps(metric.tags) if metric.tags else None
                ))
        except Exception as e:
            self.logger.error("Failed to store metric", extra={
                'metric_name': metric.metric_name,
                'error': str(e)
            })

    def store_metrics_batch(self, metrics: List[MetricData]) -> None:
        """Store multiple metric data points in batch."""
        if not metrics:
            return

        try:
            with monitoring_db.get_connection() as conn:
                values = []
                for metric in metrics:
                    values.append((
                        metric.metric_name,
                        metric.metric_value,
                        metric.metric_type,
                        metric.component,
                        metric.host_name,
                        metric.collected_at,
                        json.dumps(metric.tags) if metric.tags else None
                    ))

                conn.executemany("""
                    INSERT INTO performance_metrics (
                        metric_name, metric_value, metric_type, component,
                        host_name, collected_at, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, values)

        except Exception as e:
            self.logger.error("Failed to store metrics batch", extra={
                'batch_size': len(metrics),
                'error': str(e)
            })

    def get_metrics(self,
                   metric_names: Optional[List[str]] = None,
                   metric_type: Optional[str] = None,
                   component: Optional[str] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   limit: int = 1000) -> List[MetricData]:
        """Retrieve metrics with filtering options."""
        query = """
            SELECT
                metric_name, metric_value, metric_type, component,
                collected_at, tags
            FROM performance_metrics
            WHERE 1=1
        """
        params = []

        if metric_names:
            placeholders = ','.join('?' * len(metric_names))
            query += f" AND metric_name IN ({placeholders})"
            params.extend(metric_names)

        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type)

        if component:
            query += " AND component = ?"
            params.append(component)

        if start_time:
            query += " AND collected_at >= ?"
            params.append(start_time)

        if end_time:
            query += " AND collected_at <= ?"
            params.append(end_time)

        query += " ORDER BY collected_at DESC LIMIT ?"
        params.append(limit)

        try:
            with monitoring_db.get_connection() as conn:
                results = conn.execute(query, params).fetchall()

            metrics = []
            for row in results:
                metrics.append(MetricData(
                    metric_name=row[0],
                    metric_value=row[1],
                    metric_type=row[2],
                    component=row[3],
                    collected_at=row[4],
                    tags=json.loads(row[5]) if row[5] else {}
                ))

            return metrics

        except Exception as e:
            self.logger.error("Failed to retrieve metrics", extra={
                'error': str(e),
                'filters': {
                    'metric_names': metric_names,
                    'metric_type': metric_type,
                    'component': component
                }
            })
            return []

    def get_metric_aggregates(self,
                             metric_name: str,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             group_by: str = 'hour') -> List[Dict[str, Any]]:
        """Get aggregated metrics with time grouping."""
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.now()

        # Determine time grouping
        if group_by == 'hour':
            time_format = "%Y-%m-%d %H:00:00"
            group_sql = "strftime('%Y-%m-%d %H:00:00', collected_at)"
        elif group_by == 'day':
            time_format = "%Y-%m-%d"
            group_sql = "date(collected_at)"
        elif group_by == 'minute':
            time_format = "%Y-%m-%d %H:%M:00"
            group_sql = "strftime('%Y-%m-%d %H:%M:00', collected_at)"
        else:
            raise ValueError(f"Unsupported group_by: {group_by}")

        query = f"""
            SELECT
                {group_sql} as time_group,
                AVG(metric_value) as avg_value,
                MAX(metric_value) as max_value,
                MIN(metric_value) as min_value,
                COUNT(*) as sample_count
            FROM performance_metrics
            WHERE metric_name = ?
            AND collected_at BETWEEN ? AND ?
            GROUP BY time_group
            ORDER BY time_group
        """

        try:
            with monitoring_db.get_connection() as conn:
                results = conn.execute(query, [metric_name, start_time, end_time]).fetchall()

            aggregates = []
            for row in results:
                aggregates.append({
                    'time_group': row[0],
                    'avg_value': row[1] or 0.0,
                    'max_value': row[2] or 0.0,
                    'min_value': row[3] or 0.0,
                    'sample_count': row[4] or 0
                })

            return aggregates

        except Exception as e:
            self.logger.error("Failed to get metric aggregates", extra={
                'error': str(e),
                'metric_name': metric_name,
                'group_by': group_by
            })
            return []

    def get_latest_metrics(self, metric_names: Optional[List[str]] = None) -> Dict[str, MetricData]:
        """Get the latest value for specified metrics."""
        if metric_names:
            placeholders = ','.join('?' * len(metric_names))
            query = f"""
                SELECT DISTINCT metric_name,
                       FIRST(metric_value) as latest_value,
                       FIRST(metric_type) as metric_type,
                       FIRST(component) as component,
                       FIRST(collected_at) as collected_at,
                       FIRST(tags) as tags
                FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (PARTITION BY metric_name ORDER BY collected_at DESC) as rn
                    FROM performance_metrics
                    WHERE metric_name IN ({placeholders})
                ) t
                WHERE rn = 1
            """
            params = metric_names
        else:
            query = """
                SELECT DISTINCT metric_name,
                       FIRST(metric_value) as latest_value,
                       FIRST(metric_type) as metric_type,
                       FIRST(component) as component,
                       FIRST(collected_at) as collected_at,
                       FIRST(tags) as tags
                FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (PARTITION BY metric_name ORDER BY collected_at DESC) as rn
                    FROM performance_metrics
                ) t
                WHERE rn = 1
            """
            params = []

        try:
            with monitoring_db.get_connection() as conn:
                results = conn.execute(query, params).fetchall()

            latest_metrics = {}
            for row in results:
                latest_metrics[row[0]] = MetricData(
                    metric_name=row[0],
                    metric_value=row[1],
                    metric_type=row[2],
                    component=row[3],
                    collected_at=row[4],
                    tags=json.loads(row[5]) if row[5] else {}
                )

            return latest_metrics

        except Exception as e:
            self.logger.error("Failed to get latest metrics", extra={
                'error': str(e),
                'metric_names': metric_names
            })
            return {}

    def cleanup_old_metrics(self) -> int:
        """Clean up old metrics based on retention policy."""
        try:
            retention_days = config.metrics.metrics_retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            with monitoring_db.get_connection() as conn:
                result = conn.execute(
                    "DELETE FROM performance_metrics WHERE collected_at < ?",
                    [cutoff_date]
                )
                deleted_count = result.fetchone()[0]

            self.logger.info("Cleaned up old metrics", extra={
                'deleted_count': deleted_count,
                'retention_days': retention_days
            })

            return deleted_count

        except Exception as e:
            self.logger.error("Failed to cleanup old metrics", extra={'error': str(e)})
            return 0

    def get_metric_stats(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get statistical information for a metric."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with monitoring_db.get_connection() as conn:
                stats_result = conn.execute("""
                    SELECT
                        COUNT(*) as sample_count,
                        AVG(metric_value) as avg_value,
                        MAX(metric_value) as max_value,
                        MIN(metric_value) as min_value,
                        STDDEV(metric_value) as std_dev,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY metric_value) as median,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY metric_value) as p95,
                        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY metric_value) as p99
                    FROM performance_metrics
                    WHERE metric_name = ? AND collected_at >= ?
                """, [metric_name, cutoff_time]).fetchone()

                # Get trend (compare last 12 hours with previous 12 hours)
                midpoint = datetime.now() - timedelta(hours=hours//2)
                recent_avg = conn.execute("""
                    SELECT AVG(metric_value)
                    FROM performance_metrics
                    WHERE metric_name = ? AND collected_at >= ?
                """, [metric_name, midpoint]).fetchone()

                older_avg = conn.execute("""
                    SELECT AVG(metric_value)
                    FROM performance_metrics
                    WHERE metric_name = ? AND collected_at BETWEEN ? AND ?
                """, [metric_name, cutoff_time, midpoint]).fetchone()

            if stats_result and stats_result[0] > 0:
                trend = "stable"
                if recent_avg and older_avg and recent_avg[0] and older_avg[0]:
                    change_percent = ((recent_avg[0] - older_avg[0]) / older_avg[0]) * 100
                    if change_percent > 5:
                        trend = "increasing"
                    elif change_percent < -5:
                        trend = "decreasing"

                return {
                    'sample_count': stats_result[0],
                    'avg_value': stats_result[1] or 0.0,
                    'max_value': stats_result[2] or 0.0,
                    'min_value': stats_result[3] or 0.0,
                    'std_dev': stats_result[4] or 0.0,
                    'median': stats_result[5] or 0.0,
                    'p95': stats_result[6] or 0.0,
                    'p99': stats_result[7] or 0.0,
                    'trend': trend,
                    'time_range': f'last {hours} hours'
                }
            else:
                return {
                    'sample_count': 0,
                    'avg_value': 0.0,
                    'max_value': 0.0,
                    'min_value': 0.0,
                    'std_dev': 0.0,
                    'median': 0.0,
                    'p95': 0.0,
                    'p99': 0.0,
                    'trend': 'no_data',
                    'time_range': f'last {hours} hours'
                }

        except Exception as e:
            self.logger.error("Failed to get metric stats", extra={
                'error': str(e),
                'metric_name': metric_name
            })
            return {
                'sample_count': 0,
                'avg_value': 0.0,
                'trend': 'error'
            }

    def export_metrics(self,
                      metric_names: Optional[List[str]] = None,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      format: str = 'json') -> str:
        """Export metrics in specified format."""
        metrics = self.get_metrics(
            metric_names=metric_names,
            start_time=start_time,
            end_time=end_time,
            limit=10000  # Reasonable limit for export
        )

        data = [metric.__dict__ for metric in metrics]

        if format.lower() == 'json':
            return json.dumps(data, indent=2, default=str)
        elif format.lower() == 'csv':
            if not data:
                return "No metrics found"

            import csv
            from io import StringIO

            output = StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global instance
metrics_storage = MetricsStorage()
