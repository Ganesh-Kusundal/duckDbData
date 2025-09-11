"""
Metrics Collection and Monitoring Infrastructure

Provides comprehensive monitoring capabilities for system health,
performance tracking, and operational insights.
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Represents a single metric measurement."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = None
    metric_type: str = "gauge"  # gauge, counter, histogram, summary

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags,
            'metric_type': self.metric_type
        }


class MetricsCollector:
    """
    Main metrics collector for system monitoring.

    Collects various system and application metrics for monitoring and alerting.
    """

    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start metrics collection."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collector started")

    async def stop(self):
        """Stop metrics collection."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Metrics collector stopped")

    async def _collection_loop(self):
        """Main collection loop."""
        while self._running:
            try:
                await self._collect_system_metrics()
                await self._collect_application_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_gauge("system.cpu.percent", cpu_percent, {"type": "overall"})

            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
            for i, percent in enumerate(cpu_per_core):
                self.record_gauge("system.cpu.percent", percent, {"core": str(i)})

            # Memory metrics
            memory = psutil.virtual_memory()
            self.record_gauge("system.memory.percent", memory.percent)
            self.record_gauge("system.memory.used_bytes", memory.used)
            self.record_gauge("system.memory.available_bytes", memory.available)

            # Disk metrics
            disk = psutil.disk_usage('/')
            self.record_gauge("system.disk.percent", disk.percent)
            self.record_gauge("system.disk.used_bytes", disk.used)
            self.record_gauge("system.disk.free_bytes", disk.free)

            # Network metrics
            network = psutil.net_io_counters()
            self.record_counter("system.network.bytes_sent", network.bytes_sent)
            self.record_counter("system.network.bytes_recv", network.bytes_recv)

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    async def _collect_application_metrics(self):
        """Collect application-specific metrics."""
        try:
            # Process metrics
            process = psutil.Process()
            self.record_gauge("application.memory.rss_bytes", process.memory_info().rss)
            self.record_gauge("application.cpu.percent", process.cpu_percent())
            self.record_gauge("application.threads.count", process.num_threads())

            # Event loop metrics (if available)
            try:
                loop = asyncio.get_running_loop()
                # Note: asyncio loop metrics are limited in current Python
                self.record_gauge("application.asyncio.tasks.count", len(asyncio.all_tasks(loop)))
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")

    def record_counter(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a counter metric."""
        if tags is None:
            tags = {}

        # Counters are cumulative
        key = self._make_key(name, tags)
        self._counters[key] += value

        metric = Metric(name, self._counters[key], datetime.now(), tags, "counter")
        self._store_metric(metric)

    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a gauge metric."""
        if tags is None:
            tags = {}

        key = self._make_key(name, tags)
        self._gauges[key] = value

        metric = Metric(name, value, datetime.now(), tags, "gauge")
        self._store_metric(metric)

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram metric."""
        if tags is None:
            tags = {}

        key = self._make_key(name, tags)
        self._histograms[key].append(value)

        # Keep only last 1000 values per histogram
        if len(self._histograms[key]) > 1000:
            self._histograms[key].pop(0)

        metric = Metric(name, value, datetime.now(), tags, "histogram")
        self._store_metric(metric)

    def increment_counter(self, name: str, tags: Dict[str, str] = None):
        """Increment a counter by 1."""
        self.record_counter(name, 1.0, tags)

    def timing(self, name: str, duration_seconds: float, tags: Dict[str, str] = None):
        """Record timing information."""
        self.record_histogram(name, duration_seconds, tags)

    async def time_async(self, name: str, coro, tags: Dict[str, str] = None):
        """Time an async coroutine."""
        start_time = time.time()
        try:
            result = await coro
            duration = time.time() - start_time
            self.timing(name, duration, tags)
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.timing(f"{name}.error", duration, tags)
            raise e

    def _make_key(self, name: str, tags: Dict[str, str]) -> str:
        """Create a unique key for metric storage."""
        tag_parts = [f"{k}={v}" for k, v in sorted(tags.items())]
        return f"{name}|{'|'.join(tag_parts)}"

    def _store_metric(self, metric: Metric):
        """Store metric in internal storage."""
        key = self._make_key(metric.name, metric.tags)
        self._metrics[key].append(metric)

    def get_metric_history(self, name: str, tags: Dict[str, str] = None,
                          limit: int = 100) -> List[Metric]:
        """Get historical data for a metric."""
        if tags is None:
            tags = {}

        key = self._make_key(name, tags)
        metrics = list(self._metrics[key])

        # Return most recent metrics
        return metrics[-limit:] if limit > 0 else metrics

    def get_current_value(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """Get the current value of a metric."""
        if tags is None:
            tags = {}

        key = self._make_key(name, tags)

        # For gauges, return current value
        if key in self._gauges:
            return self._gauges[key]

        # For counters, return current count
        if key in self._counters:
            return self._counters[key]

        # For other metrics, return last recorded value
        if key in self._metrics and self._metrics[key]:
            return self._metrics[key][-1].value

        return None

    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """Get statistics for a histogram metric."""
        if tags is None:
            tags = {}

        key = self._make_key(name, tags)
        values = self._histograms[key]

        if not values:
            return {}

        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'p50': self._percentile(values, 50),
            'p95': self._percentile(values, 95),
            'p99': self._percentile(values, 99)
        }

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from a list of values."""
        if not values:
            return 0.0

        values_sorted = sorted(values)
        k = (len(values_sorted) - 1) * (percentile / 100)
        f = int(k)
        c = k - f

        if f + 1 < len(values_sorted):
            return values_sorted[f] * (1 - c) + values_sorted[f + 1] * c
        else:
            return values_sorted[f]

    def get_all_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all collected metrics."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_metrics_stored': sum(len(metrics) for metrics in self._metrics.values()),
            'unique_metric_keys': len(self._metrics),
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'histograms': {k: self.get_histogram_stats(k.split('|')[0],
                                                      self._parse_tags(k)) for k in self._histograms.keys()},
            'collection_interval_seconds': self.collection_interval,
            'is_running': self._running
        }

        return summary

    def _parse_tags(self, key: str) -> Dict[str, str]:
        """Parse tags from a metric key."""
        parts = key.split('|')
        if len(parts) < 2:
            return {}

        tags = {}
        for tag_part in parts[1:]:
            if '=' in tag_part:
                tag_key, tag_value = tag_part.split('=', 1)
                tags[tag_key] = tag_value

        return tags

    def export_metrics(self, format_type: str = "json") -> str:
        """Export all metrics in the specified format."""
        all_metrics = []
        for metrics_deque in self._metrics.values():
            all_metrics.extend(metrics_deque)

        if format_type == "json":
            return json.dumps([metric.to_dict() for metric in all_metrics], indent=2)
        elif format_type == "prometheus":
            return self._export_prometheus_format(all_metrics)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def _export_prometheus_format(self, metrics: List[Metric]) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Group metrics by name and type
        by_name_and_type = defaultdict(lambda: defaultdict(list))

        for metric in metrics:
            key = f"{metric.name}_{metric.metric_type}"
            tag_str = ",".join([f'{k}="{v}"' for k, v in metric.tags.items()])
            if tag_str:
                tag_str = "{" + tag_str + "}"
            by_name_and_type[key][tag_str].append(metric.value)

        for metric_key, tag_groups in by_name_and_type.items():
            lines.append(f"# HELP {metric_key} Auto-generated metric")
            lines.append(f"# TYPE {metric_key} gauge")

            for tag_str, values in tag_groups.items():
                # Use the most recent value
                if values:
                    latest_value = values[-1]
                    lines.append(f"{metric_key}{tag_str} {latest_value}")

        return "\n".join(lines)

    def clear_metrics(self, older_than_hours: int = 24):
        """Clear old metrics to free memory."""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        for key, metrics_deque in self._metrics.items():
            # Keep only recent metrics
            recent_metrics = deque(
                (m for m in metrics_deque if m.timestamp > cutoff_time),
                maxlen=metrics_deque.maxlen
            )
            self._metrics[key] = recent_metrics

        # Clear old histogram data
        for key, values in self._histograms.items():
            # Keep only recent values (approximate by keeping last 100)
            self._histograms[key] = values[-100:] if len(values) > 100 else values

        logger.info(f"Cleared metrics older than {older_than_hours} hours")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector():
    """Reset global metrics collector (mainly for testing)."""
    global _metrics_collector
    _metrics_collector = None


# Decorator for automatic timing
def timed(metric_name: str = None, tags: Dict[str, str] = None):
    """Decorator to automatically time function execution."""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__qualifier__}.{func.__name__}"
            collector = get_metrics_collector()
            return await collector.time_async(name, func(*args, **kwargs), tags)

        def sync_wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__qualifier__}.{func.__name__}"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                collector = get_metrics_collector()
                collector.timing(name, duration, tags)

                return result
            except Exception as e:
                duration = time.time() - start_time

                collector = get_metrics_collector()
                collector.timing(f"{name}.error", duration, tags)

                raise e

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Context manager for timing blocks of code
class Timer:
    """Context manager for timing code blocks."""

    def __init__(self, metric_name: str, tags: Dict[str, str] = None):
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = None
        self.collector = get_metrics_collector()

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time

            if exc_type is not None:
                # Exception occurred
                self.collector.timing(f"{self.metric_name}.error", duration, self.tags)
            else:
                # Normal execution
                self.collector.timing(self.metric_name, duration, self.tags)
