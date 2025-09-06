"""
OpenTelemetry metrics integration for DuckDB Financial Infrastructure.
"""

from typing import Optional
import time
from datetime import datetime

try:
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False
    metrics = None
    MeterProvider = None
    PeriodicExportingMetricReader = None
    PrometheusMetricReader = None

from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Enhanced OpenTelemetry metrics collector with alerting."""

    def __init__(self):
        """Initialize the metrics collector."""
        self._meter = None
        self._counters = {}
        self._histograms = {}
        self._gauges = {}
        self._alert_thresholds = {}
        self._last_alert_times = {}

        if HAS_OPENTELEMETRY:
            self._setup_metrics()
            self._setup_default_alerts()
        else:
            logger.warning("OpenTelemetry not available. Metrics collection disabled.")

    def _setup_metrics(self):
        """Set up OpenTelemetry metrics."""
        try:
            # Create metric readers
            prometheus_reader = PrometheusMetricReader()

            # Set up meter provider
            metrics.set_meter_provider(MeterProvider([prometheus_reader]))

            # Get meter
            self._meter = metrics.get_meter(
                "duckdb_financial",
                version="1.0.0",
                schema_url="https://opentelemetry.io/schemas/1.21.0"
            )

            # Initialize metrics
            self._setup_counters()
            self._setup_histograms()
            self._setup_gauges()
            self._setup_default_alerts()

            logger.info("OpenTelemetry metrics initialized")

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry metrics: {e}")
            self._meter = None

    def _setup_counters(self):
        """Set up counter metrics."""
        if not self._meter:
            return

        self._counters = {
            'data_ingested_records': self._meter.create_counter(
                name="data_ingested_records_total",
                description="Total number of market data records ingested",
                unit="1"
            ),
            'scanner_executions': self._meter.create_counter(
                name="scanner_executions_total",
                description="Total number of scanner executions",
                unit="1"
            ),
            'api_requests': self._meter.create_counter(
                name="api_requests_total",
                description="Total number of API requests",
                unit="1"
            ),
            'errors_total': self._meter.create_counter(
                name="errors_total",
                description="Total number of errors",
                unit="1"
            )
        }

    def _setup_histograms(self):
        """Set up histogram metrics."""
        if not self._meter:
            return

        self._histograms = {
            'data_ingestion_duration': self._meter.create_histogram(
                name="data_ingestion_duration_seconds",
                description="Time taken for data ingestion operations",
                unit="s"
            ),
            'scanner_execution_duration': self._meter.create_histogram(
                name="scanner_execution_duration_seconds",
                description="Time taken for scanner executions",
                unit="s"
            ),
            'api_request_duration': self._meter.create_histogram(
                name="api_request_duration_seconds",
                description="Time taken for API requests",
                unit="s"
            ),
            'query_execution_duration': self._meter.create_histogram(
                name="query_execution_duration_seconds",
                description="Time taken for database queries",
                unit="s"
            )
        }

    def _setup_gauges(self):
        """Set up gauge metrics."""
        if not self._meter:
            return

        # Note: OpenTelemetry doesn't have direct gauge support
        # We'll use observable gauges instead
        pass

    def _setup_default_alerts(self):
        """Set up default alert thresholds."""
        self._alert_thresholds = {
            "slow_query": {"threshold": 5.0, "cooldown": 300},  # 5 minutes cooldown
            "high_error_rate": {"threshold": 0.05, "cooldown": 600},  # 10 minutes cooldown
            "high_memory_usage": {"threshold": 90.0, "cooldown": 300},
            "high_cpu_usage": {"threshold": 90.0, "cooldown": 300}
        }

    def set_alert_threshold(self, alert_name: str, threshold: float, cooldown: int = 300):
        """Set alert threshold for a metric."""
        self._alert_thresholds[alert_name] = {
            "threshold": threshold,
            "cooldown": cooldown
        }

    def _trigger_alert(self, alert_name: str, data: dict):
        """Trigger alert for exceeded threshold."""
        import time

        current_time = time.time()
        last_alert = self._last_alert_times.get(alert_name, 0)
        cooldown = self._alert_thresholds.get(alert_name, {}).get("cooldown", 300)

        # Check cooldown period
        if current_time - last_alert < cooldown:
            return

        self._last_alert_times[alert_name] = current_time

        # Log alert
        logger.warning(f"ALERT: {alert_name}", **data)

        # Could integrate with external alerting systems here
        # (email, Slack, PagerDuty, etc.)

    # Counter methods
    def increment_data_ingested(self, count: int = 1, **attributes):
        """Increment data ingested counter."""
        if 'data_ingested_records' in self._counters:
            self._counters['data_ingested_records'].add(count, attributes)

    def increment_scanner_executions(self, count: int = 1, **attributes):
        """Increment scanner executions counter."""
        if 'scanner_executions' in self._counters:
            self._counters['scanner_executions'].add(count, attributes)

    def increment_api_requests(self, count: int = 1, **attributes):
        """Increment API requests counter."""
        if 'api_requests' in self._counters:
            self._counters['api_requests'].add(count, attributes)

    def increment_errors(self, count: int = 1, **attributes):
        """Increment errors counter."""
        if 'errors_total' in self._counters:
            self._counters['errors_total'].add(count, attributes)

    # Histogram methods
    def record_data_ingestion_duration(self, duration: float, **attributes):
        """Record data ingestion duration."""
        if 'data_ingestion_duration' in self._histograms:
            self._histograms['data_ingestion_duration'].record(duration, attributes)

    def record_scanner_execution_duration(self, duration: float, **attributes):
        """Record scanner execution duration."""
        if 'scanner_execution_duration' in self._histograms:
            self._histograms['scanner_execution_duration'].record(duration, attributes)

    def record_api_request_duration(self, duration: float, **attributes):
        """Record API request duration."""
        if 'api_request_duration' in self._histograms:
            self._histograms['api_request_duration'].record(duration, attributes)

    def record_query_execution_duration(self, duration: float, **attributes):
        """Record query execution duration."""
        if 'query_execution_duration' in self._histograms:
            self._histograms['query_execution_duration'].record(duration, attributes)

        # Check for slow query alert
        if duration > 5.0:  # 5 seconds threshold
            self._trigger_alert("slow_query", {
                "duration": duration,
                "query_type": attributes.get("query_type", "unknown"),
                "threshold": 5.0
            })

    # Context manager for timing operations
    def time_operation(self, operation_name: str):
        """Context manager for timing operations."""
        return MetricsTimer(self, operation_name)

    def get_metrics_endpoint(self):
        """Get Prometheus metrics endpoint."""
        if HAS_OPENTELEMETRY and PrometheusMetricReader:
            return "/metrics"
        return None


class MetricsTimer:
    """Context manager for timing operations."""

    def __init__(self, metrics_collector: MetricsCollector, operation_name: str):
        """Initialize timer."""
        self.metrics_collector = metrics_collector
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record duration."""
        if self.start_time is not None:
            duration = time.time() - self.start_time

            if self.operation_name == 'data_ingestion':
                self.metrics_collector.record_data_ingestion_duration(duration)
            elif self.operation_name == 'scanner_execution':
                self.metrics_collector.record_scanner_execution_duration(duration)
            elif self.operation_name == 'api_request':
                self.metrics_collector.record_api_request_duration(duration)
            elif self.operation_name == 'query_execution':
                self.metrics_collector.record_query_execution_duration(duration)


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record API request metrics."""
    collector = get_metrics_collector()
    collector.increment_api_requests(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    )
    collector.record_api_request_duration(
        duration,
        method=method,
        endpoint=endpoint,
        status_code=status_code
    )


def record_data_ingestion(records_count: int, source: str, duration: float):
    """Record data ingestion metrics."""
    collector = get_metrics_collector()
    collector.increment_data_ingested(records_count, source=source)
    collector.record_data_ingestion_duration(duration, source=source)


def record_scanner_execution(scanner_type: str, symbols_count: int, duration: float):
    """Record scanner execution metrics."""
    collector = get_metrics_collector()
    collector.increment_scanner_executions(
        scanner_type=scanner_type,
        symbols_count=symbols_count
    )
    collector.record_scanner_execution_duration(
        duration,
        scanner_type=scanner_type,
        symbols_count=symbols_count
    )


def record_error(error_type: str, component: str):
    """Record error metrics."""
    collector = get_metrics_collector()
    collector.increment_errors(error_type=error_type, component=component)
