"""
Monitoring Dashboard Configuration Settings
==========================================

This module contains all configuration settings for the monitoring dashboard.
Uses Pydantic for validation and follows the existing project patterns.
"""

from typing import Optional, List, Dict, Any, Tuple
from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path


class DashboardSettings(BaseSettings):
    """Dashboard UI and display settings."""

    # Basic settings
    title: str = "DuckDB Financial Infrastructure Monitor"
    port: int = Field(default=5006, description="Panel dashboard port")
    host: str = Field(default="localhost", description="Dashboard host")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Theme settings
    theme: str = Field(default="dark", description="Dashboard theme (dark/light)")
    refresh_interval: int = Field(default=30, description="Auto-refresh interval in seconds")
    max_display_rows: int = Field(default=1000, description="Maximum rows to display in tables")

    # Layout settings
    default_width: int = Field(default=1200, description="Default dashboard width")
    default_height: int = Field(default=800, description="Default dashboard height")
    sidebar_width: int = Field(default=300, description="Sidebar width in pixels")

    class Config:
        env_prefix = "DASHBOARD_"


class LoggingSettings(BaseSettings):
    """Logging framework configuration."""

    # Log levels
    console_level: str = Field(default="INFO", description="Console log level")
    file_level: str = Field(default="DEBUG", description="File log level")

    # Log paths
    log_directory: Path = Field(
        default=Path("logs"),
        description="Directory for log files"
    )
    max_log_size: str = Field(default="10 MB", description="Maximum log file size")
    backup_count: int = Field(default=5, description="Number of log file backups to keep")

    # Structured logging
    enable_structured_logging: bool = Field(default=True, description="Enable JSON structured logging")
    correlation_id_enabled: bool = Field(default=True, description="Enable correlation ID tracking")

    # Log retention
    retention_days: int = Field(default=30, description="Log retention period in days")

    class Config:
        env_prefix = "LOG_"


class DatabaseSettings(BaseSettings):
    """Database configuration for monitoring data."""

    # DuckDB settings
    database_path: Path = Field(
        default=Path("data/monitoring.duckdb"),
        description="Path to monitoring database"
    )

    # Connection settings
    connection_timeout: int = Field(default=30, description="Database connection timeout")
    max_connections: int = Field(default=10, description="Maximum database connections")

    # Performance settings
    enable_wal: bool = Field(default=True, description="Enable Write-Ahead Logging")
    cache_size: str = Field(default="1GB", description="DuckDB cache size")

    class Config:
        env_prefix = "DB_"


class TestMonitorSettings(BaseSettings):
    """Test monitoring configuration."""

    # Test execution settings
    default_timeout: int = Field(default=300, description="Default test timeout in seconds")
    max_parallel_tests: int = Field(default=4, description="Maximum parallel test executions")
    test_history_retention: int = Field(default=90, description="Test history retention in days")

    # pytest settings
    pytest_args: List[str] = Field(
        default_factory=lambda: ["--tb=short", "--strict-markers"],
        description="Default pytest arguments"
    )

    # Coverage settings
    enable_coverage: bool = Field(default=True, description="Enable test coverage tracking")
    coverage_threshold: float = Field(default=80.0, description="Coverage threshold percentage")

    class Config:
        env_prefix = "TEST_"


class MetricsSettings(BaseSettings):
    """Performance metrics collection settings."""

    # Collection intervals
    system_metrics_interval: int = Field(default=30, description="System metrics collection interval")
    database_metrics_interval: int = Field(default=60, description="Database metrics collection interval")

    # Thresholds
    cpu_threshold: float = Field(default=85.0, description="CPU usage alert threshold")
    memory_threshold: float = Field(default=90.0, description="Memory usage alert threshold")
    disk_threshold: float = Field(default=85.0, description="Disk usage alert threshold")

    # Retention
    metrics_retention_days: int = Field(default=30, description="Metrics retention period")

    class Config:
        env_prefix = "METRICS_"


class APISettings(BaseSettings):
    """REST API configuration."""

    # API settings
    api_host: str = Field(default="localhost", description="API server host")
    api_port: int = Field(default=8001, description="API server port")
    api_prefix: str = Field(default="/api/v1", description="API URL prefix")

    # Security
    enable_cors: bool = Field(default=True, description="Enable CORS")
    allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5006"],
        description="Allowed CORS origins"
    )

    # Rate limiting
    enable_rate_limiting: bool = Field(default=True, description="Enable API rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute limit")

    class Config:
        env_prefix = "API_"


class MonitoringConfig(BaseSettings):
    """Main monitoring configuration combining all settings."""

    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    test_monitor: TestMonitorSettings = Field(default_factory=TestMonitorSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    api: APISettings = Field(default_factory=APISettings)

    # Global settings
    environment: str = Field(default="development", description="Environment (development/production)")
    enable_monitoring: bool = Field(default=True, description="Enable monitoring system")

    class Config:
        env_prefix = "MONITORING_"
        # Disable env_file to prevent loading unrelated environment variables
        # env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global configuration instance
config = MonitoringConfig()
