"""Configuration management using Pydantic settings."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings

import logging


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = ConfigDict(env_prefix="DUCKDB_", extra='allow')

    path: str = Field(default="data/financial_data.duckdb")
    memory_limit: str = Field(default="8GB")
    threads: int = Field(default=8, ge=1)
    read_only: bool = Field(default=False)
    # Root directory containing partitioned Parquet data for direct querying
    parquet_root: Optional[str] = Field(default=None)
    # Optional custom glob; if not set, derived from parquet_root as YYYY/MM/DD/*.parquet
    parquet_glob: Optional[str] = Field(default=None)
    # Whether to auto-create a unified view that unions DB table with Parquet scan
    use_parquet_in_unified_view: bool = Field(default=True)
    # Performance/diagnostics switches
    enable_object_cache: bool = Field(default=True)
    enable_profiling: bool = Field(default=False)

    # Schema configuration loaded from database.yaml
    db_schema: Dict[str, Any] = Field(default_factory=dict, alias="schema")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        """Ensure database path is valid and log warnings if issues found."""
        logger = logging.getLogger(__name__)

        if v:
            path = Path(v)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Check if database file exists and is readable
            if path.exists():
                if not path.is_file():
                    logger.warning(f"Database path '{v}' exists but is not a file")
                elif not path.stat().st_size > 0:
                    logger.warning(f"Database file '{v}' exists but appears to be empty")
                elif not os.access(path, os.R_OK):
                    logger.warning(f"Database file '{v}' exists but is not readable")
            else:
                logger.info(f"Database file '{v}' does not exist yet - will be created on first use")

        return v

    @field_validator('parquet_root')
    @classmethod
    def validate_parquet_root(cls, v):
        if not v:
            return v
        p = Path(v)
        if not p.exists() or not p.is_dir():
            # Don't raise; just warn. Parquet root may be mounted later.
            logging.getLogger(__name__).warning(f"Parquet root '{v}' not found or not a directory")
        return v


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = ConfigDict(extra='allow')

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    class FileSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=True)
        path: str = Field(default="logs/duckdb_financial.log")
        max_size: str = Field(default="100 MB")
        backup_count: int = Field(default=5, ge=0)

    class ConsoleSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=True)
        level: str = Field(default="INFO")

    file: FileSettings = FileSettings()
    console: ConsoleSettings = ConsoleSettings()


class ScannerSettings(BaseSettings):
    """Scanner configuration settings."""

    model_config = ConfigDict(extra='allow')

    default_timeframe: str = Field(default="1D")
    max_execution_time: int = Field(default=300, ge=1)
    parallel_execution: bool = Field(default=True)
    max_workers: int = Field(default=4, ge=1)

    class RelativeVolumeSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=True)
        min_relative_volume: float = Field(default=1.5, ge=0)
        lookback_periods: int = Field(default=20, ge=1)

    class TechnicalSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=True)
        indicators: List[str] = Field(default_factory=lambda: ["sma_20", "rsi_14"])
        signal_threshold: float = Field(default=0.7, ge=0, le=1)

    class BreakoutSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=True)
        breakout_threshold: float = Field(default=2.0, ge=0)
        consolidation_period: int = Field(default=20, ge=1)
        volume_multiplier: float = Field(default=1.5, ge=0)

    relative_volume: RelativeVolumeSettings = RelativeVolumeSettings()
    technical: TechnicalSettings = TechnicalSettings()
    breakout: BreakoutSettings = BreakoutSettings()


class BrokerSettings(BaseSettings):
    """Broker configuration settings."""

    model_config = ConfigDict(extra='allow')

    default_broker: str = Field(default="dhan")
    timeout: int = Field(default=30, ge=1)
    retry_attempts: int = Field(default=3, ge=0)

    class RateLimitingSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        requests_per_minute: int = Field(default=60, ge=1)
        burst_limit: int = Field(default=10, ge=1)

    rate_limiting: RateLimitingSettings = RateLimitingSettings()


class DataSyncSettings(BaseSettings):
    """Data synchronization configuration settings."""

    model_config = ConfigDict(extra='allow')

    class HistoricalSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=True)
        batch_size: int = Field(default=1000, ge=1)
        retry_attempts: int = Field(default=3, ge=0)
        timeout: int = Field(default=60, ge=1)

    class LiveSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=False)
        update_interval: int = Field(default=60, ge=1)
        max_symbols: int = Field(default=50, ge=1)

    historical: HistoricalSettings = HistoricalSettings()
    live: LiveSettings = LiveSettings()


class ValidationSettings(BaseSettings):
    """Validation configuration settings."""

    model_config = ConfigDict(extra='allow')

    strict_mode: bool = Field(default=True)
    data_quality_checks: List[str] = Field(
        default_factory=lambda: ["null_check", "range_check", "consistency_check"]
    )

    class GreatExpectationsSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=True)
        config_path: str = Field(default="config/great_expectations.yml")

    great_expectations: GreatExpectationsSettings = GreatExpectationsSettings()


class APISettings(BaseSettings):
    """API configuration settings."""

    model_config = ConfigDict(extra='allow')

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False)
    workers: int = Field(default=1, ge=1)
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )


class MonitoringSettings(BaseSettings):
    """Monitoring configuration settings."""

    model_config = ConfigDict(extra='allow')

    class PrometheusSettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=True)
        port: int = Field(default=9090, ge=1, le=65535)

    prometheus: PrometheusSettings = PrometheusSettings()
    health_checks: Dict[str, Any] = Field(default_factory=dict)


class CacheSettings(BaseSettings):
    """Cache configuration settings."""

    model_config = ConfigDict(extra='allow')

    enabled: bool = Field(default=True)
    ttl: int = Field(default=3600, ge=1)
    max_size: int = Field(default=1000, ge=1)


class PerformanceSettings(BaseSettings):
    """Performance optimization settings."""

    model_config = ConfigDict(env_prefix="PERF_", extra='allow')

    # Fast mode toggle
    fast_mode: bool = Field(default=False, description="Enable fast mode for development")

    # Connection pooling settings
    connection_pool_enabled: bool = Field(default=True)
    connection_pool_size: int = Field(default=10, ge=1, le=100)
    connection_pool_timeout: float = Field(default=30.0, ge=0.1)

    # Verification settings
    skip_complex_verification: bool = Field(default=False)
    verification_timeout: float = Field(default=5.0, ge=0.1)
    essential_checks_only: bool = Field(default=False)

    # Query optimization settings
    query_cache_enabled: bool = Field(default=True)
    query_cache_ttl: int = Field(default=300, ge=1)
    prepared_statements_enabled: bool = Field(default=True)

    # Monitoring settings
    performance_monitoring: bool = Field(default=False)
    metrics_collection: bool = Field(default=False)

    @property
    def is_fast_mode(self) -> bool:
        """Check if fast mode is enabled."""
        return self.fast_mode

    @property
    def is_development_mode(self) -> bool:
        """Alias for is_fast_mode for clarity."""
        return self.is_fast_mode


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    model_config = ConfigDict(extra='allow')

    class APIKeySettings(BaseSettings):
        model_config = ConfigDict(extra='allow')

        enabled: bool = Field(default=False)
        required: bool = Field(default=False)

    api_keys: APIKeySettings = APIKeySettings()
    rate_limiting: Dict[str, Any] = Field(default_factory=dict)


class AppSettings(BaseSettings):
    """Main application settings."""

    database: DatabaseSettings = DatabaseSettings()
    logging: LoggingSettings = LoggingSettings()
    scanners: ScannerSettings = ScannerSettings()
    brokers: BrokerSettings = BrokerSettings()
    data_sync: DataSyncSettings = DataSyncSettings()
    validation: ValidationSettings = ValidationSettings()
    api: APISettings = APISettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    cache: CacheSettings = CacheSettings()
    performance: PerformanceSettings = PerformanceSettings()
    security: SecuritySettings = SecuritySettings()

    model_config = ConfigDict(
        # env_prefix = "DUCKDB_FINANCIAL_"
        # env_nested_delimiter = "__"
        # env_file = None
        # env_ignore_empty = True
        # case_sensitive = True
        extra='allow',  # Allow extra fields from YAML for flexibility
    )

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings,
    ):
        """Customize settings sources to include YAML files."""
        return (
            init_settings,
            yaml_settings_source,
            env_settings,
            file_secret_settings,
        )


def yaml_settings_source() -> Dict[str, Any]:
    """Load settings from YAML files."""
    import yaml

    # Load main settings
    config_paths = [
        Path("config/settings.yaml"),
        Path("config/settings.yml"),
        Path("configs/config.yaml"),
        Path("configs/config.yml"),
        Path("settings.yaml"),
        Path("settings.yml"),
    ]

    main_config = {}
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                main_config = yaml.safe_load(f) or {}
                break

    # Load database-specific configuration
    db_config_paths = [
        Path("config/database.yaml"),
        Path("config/database.yml"),
        Path("configs/database.yaml"),
        Path("configs/database.yml"),
    ]

    for db_config_path in db_config_paths:
        if db_config_path.exists():
            with open(db_config_path, 'r', encoding='utf-8') as f:
                db_config = yaml.safe_load(f) or {}
                # Merge database config into main config
                if 'database' not in main_config:
                    main_config['database'] = {}
                main_config['database'].update(db_config)
                break

    return main_config


# Global settings instance
settings = AppSettings()


def get_settings() -> AppSettings:
    """Get the global application settings."""
    return settings


def reload_settings() -> AppSettings:
    """Reload settings from sources."""
    global settings
    settings = AppSettings()
    return settings
