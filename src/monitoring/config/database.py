"""
Monitoring Database Schema and Setup
====================================

This module handles the DuckDB database schema setup for the monitoring dashboard.
Creates all necessary tables for storing test results, logs, and performance metrics.
"""

import duckdb
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager
from .settings import config


class MonitoringDatabase:
    """Handles monitoring database operations."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection."""
        self.db_path = db_path or config.database.database_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[duckdb.DuckDBPyConnection] = None

    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        if self._connection is None:
            self._connection = duckdb.connect(str(self.db_path))

        try:
            yield self._connection
        finally:
            # Keep connection open for reuse
            pass

    def setup_schema(self) -> None:
        """Create all monitoring database tables and indexes."""
        with self.get_connection() as conn:
            # Enable WAL mode for better concurrent access
            if config.database.enable_wal:
                try:
                    conn.execute("PRAGMA wal_autocheckpoint = 1000;")
                except Exception:
                    # WAL autocheckpoint may not be supported in all DuckDB versions
                    pass

            # Set cache size (may not be supported in all DuckDB versions)
            try:
                cache_size = config.database.cache_size
                if cache_size.endswith('GB'):
                    cache_mb = int(float(cache_size[:-2]) * 1024)
                elif cache_size.endswith('MB'):
                    cache_mb = int(float(cache_size[:-2]))
                else:
                    cache_mb = 1024  # Default 1GB
                conn.execute(f"PRAGMA cache_size = {cache_mb};")
            except Exception:
                # Cache size pragma may not be supported
                pass

            # Try to set memory limit (may not be supported in all DuckDB versions)
            try:
                conn.execute("PRAGMA memory_limit = '2GB';")
            except Exception:
                # Memory limit may not be supported or may cause parsing errors
                pass

            # Create test_results table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY,
                    suite_name VARCHAR NOT NULL,
                    test_name VARCHAR NOT NULL,
                    status VARCHAR NOT NULL, -- 'passed', 'failed', 'skipped', 'error'
                    duration FLOAT,
                    error_message TEXT,
                    traceback TEXT,
                    coverage_percentage FLOAT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    environment VARCHAR DEFAULT 'development',
                    python_version VARCHAR,
                    pytest_version VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create system_logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    level VARCHAR NOT NULL, -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
                    component VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    extra_data JSON,
                    correlation_id VARCHAR,
                    source_file VARCHAR,
                    source_line INTEGER,
                    function_name VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create performance_metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY,
                    metric_name VARCHAR NOT NULL,
                    metric_value FLOAT NOT NULL,
                    metric_type VARCHAR NOT NULL, -- 'cpu', 'memory', 'disk', 'network', 'db_query', 'db_connection'
                    component VARCHAR,
                    host_name VARCHAR,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tags JSON -- Additional metadata as JSON
                );
            """)

            # Create alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY,
                    alert_type VARCHAR NOT NULL, -- 'system', 'performance', 'test_failure', 'log_error'
                    severity VARCHAR NOT NULL, -- 'low', 'medium', 'high', 'critical'
                    title VARCHAR NOT NULL,
                    message TEXT,
                    component VARCHAR,
                    metric_name VARCHAR,
                    threshold_value FLOAT,
                    actual_value FLOAT,
                    status VARCHAR DEFAULT 'active', -- 'active', 'acknowledged', 'resolved'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    acknowledged_by VARCHAR,
                    resolved_by VARCHAR
                );
            """)

            # Create dashboard_sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_sessions (
                    id INTEGER PRIMARY KEY,
                    session_id VARCHAR UNIQUE NOT NULL,
                    user_agent VARCHAR,
                    ip_address VARCHAR,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
            """)

            # Create indexes for better query performance
            self._create_indexes(conn)

    def _create_indexes(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Create database indexes for optimal query performance."""

        # Test results indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_status ON test_results(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_suite ON test_results(suite_name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_executed_at ON test_results(executed_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_environment ON test_results(environment);")

        # System logs indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_correlation_id ON system_logs(correlation_id);")

        # Performance metrics indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_collected_at ON performance_metrics(collected_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_metrics_component ON performance_metrics(component);")

        # Alerts indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);")

        # Composite indexes for common queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_level_component ON system_logs(level, component);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type_collected ON performance_metrics(metric_type, collected_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_test_suite_status ON test_results(suite_name, status);")

    def cleanup_old_data(self) -> None:
        """Clean up old monitoring data based on retention policies."""
        with self.get_connection() as conn:
            # Clean up old test results
            test_retention = config.test_monitor.test_history_retention
            conn.execute(f"""
                DELETE FROM test_results
                WHERE executed_at < (CURRENT_TIMESTAMP - INTERVAL '{test_retention} days')
            """)

            # Clean up old logs
            log_retention = config.logging.retention_days
            conn.execute(f"""
                DELETE FROM system_logs
                WHERE timestamp < (CURRENT_TIMESTAMP - INTERVAL '{log_retention} days')
            """)

            # Clean up old metrics
            metrics_retention = config.metrics.metrics_retention_days
            conn.execute(f"""
                DELETE FROM performance_metrics
                WHERE collected_at < (CURRENT_TIMESTAMP - INTERVAL '{metrics_retention} days')
            """)

            # Clean up resolved alerts (keep for 30 days after resolution)
            conn.execute("""
                DELETE FROM alerts
                WHERE status = 'resolved'
                AND resolved_at < (CURRENT_TIMESTAMP - INTERVAL '30 days')
            """)

            # Optimize database after cleanup
            conn.execute("VACUUM;")

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            stats = {}

            # Table sizes
            tables = ['test_results', 'system_logs', 'performance_metrics', 'alerts']
            for table in tables:
                result = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                stats[f"{table}_count"] = result[0] if result else 0

            # Database file size
            if self.db_path.exists():
                stats["database_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)

            return stats

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Global database instance
monitoring_db = MonitoringDatabase()
