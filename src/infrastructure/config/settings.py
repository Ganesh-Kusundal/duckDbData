"""Configuration management using Pydantic settings."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = ConfigDict(env_prefix="DUCKDB_")

    path: str = Field(default="financial_data.duckdb")
    memory_limit: str = Field(default="8GB")
    threads: int = Field(default=8, ge=1)
    read_only: bool = Field(default=False)

    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        """Ensure database path is valid."""
        if v:
            path = Path(v)
            path.parent.mkdir(parents=True, exist_ok=True)
        return v


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    class FileSettings(BaseSettings):
        enabled: bool = Field(default=True)
        path: str = Field(default="logs/duckdb_financial.log")
        max_size: str = Field(default="100 MB")
        backup_count: int = Field(default=5, ge=0)

    class ConsoleSettings(BaseSettings):
        enabled: bool = Field(default=True)
        level: str = Field(default="INFO")

    file: FileSettings = FileSettings()
    console: ConsoleSettings = ConsoleSettings()


class ScannerSettings(BaseSettings):
    """Scanner configuration settings."""

    default_timeframe: str = Field(default="1D")
    max_execution_time: int = Field(default=300, ge=1)
    parallel_execution: bool = Field(default=True)
    max_workers: int = Field(default=4, ge=1)

    class RelativeVolumeSettings(BaseSettings):
        enabled: bool = Field(default=True)
        min_relative_volume: float = Field(default=1.5, ge=0)
        lookback_periods: int = Field(default=20, ge=1)

    class TechnicalSettings(BaseSettings):
        enabled: bool = Field(default=True)
        indicators: List[str] = Field(default_factory=lambda: ["sma_20", "rsi_14"])
        signal_threshold: float = Field(default=0.7, ge=0, le=1)

    class BreakoutSettings(BaseSettings):
        enabled: bool = Field(default=True)
        breakout_threshold: float = Field(default=2.0, ge=0)
        consolidation_period: int = Field(default=20, ge=1)
        volume_multiplier: float = Field(default=1.5, ge=0)

    relative_volume: RelativeVolumeSettings = RelativeVolumeSettings()
    technical: TechnicalSettings = TechnicalSettings()
    breakout: BreakoutSettings = BreakoutSettings()


class BrokerSettings(BaseSettings):
    """Broker configuration settings."""

    default_broker: str = Field(default="dhan")
    timeout: int = Field(default=30, ge=1)
    retry_attempts: int = Field(default=3, ge=0)

    class RateLimitingSettings(BaseSettings):
        requests_per_minute: int = Field(default=60, ge=1)
        burst_limit: int = Field(default=10, ge=1)

    rate_limiting: RateLimitingSettings = RateLimitingSettings()


class DataSyncSettings(BaseSettings):
    """Data synchronization configuration settings."""

    class HistoricalSettings(BaseSettings):
        enabled: bool = Field(default=True)
        batch_size: int = Field(default=1000, ge=1)
        retry_attempts: int = Field(default=3, ge=0)
        timeout: int = Field(default=60, ge=1)

    class LiveSettings(BaseSettings):
        enabled: bool = Field(default=False)
        update_interval: int = Field(default=60, ge=1)
        max_symbols: int = Field(default=50, ge=1)

    historical: HistoricalSettings = HistoricalSettings()
    live: LiveSettings = LiveSettings()


class ValidationSettings(BaseSettings):
    """Validation configuration settings."""

    strict_mode: bool = Field(default=True)
    data_quality_checks: List[str] = Field(
        default_factory=lambda: ["null_check", "range_check", "consistency_check"]
    )

    class GreatExpectationsSettings(BaseSettings):
        enabled: bool = Field(default=True)
        config_path: str = Field(default="config/great_expectations.yml")

    great_expectations: GreatExpectationsSettings = GreatExpectationsSettings()


class APISettings(BaseSettings):
    """API configuration settings."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False)
    workers: int = Field(default=1, ge=1)
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )


class MonitoringSettings(BaseSettings):
    """Monitoring configuration settings."""

    class PrometheusSettings(BaseSettings):
        enabled: bool = Field(default=True)
        port: int = Field(default=9090, ge=1, le=65535)

    prometheus: PrometheusSettings = PrometheusSettings()
    health_checks: Dict[str, Any] = Field(default_factory=dict)


class CacheSettings(BaseSettings):
    """Cache configuration settings."""

    enabled: bool = Field(default=True)
    ttl: int = Field(default=3600, ge=1)
    max_size: int = Field(default=1000, ge=1)


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    class APIKeySettings(BaseSettings):
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
    security: SecuritySettings = SecuritySettings()

    class Config:
        """Pydantic configuration."""

        # env_prefix = "DUCKDB_FINANCIAL_"
        # env_nested_delimiter = "__"
        # env_file = None
        # env_ignore_empty = True
        # case_sensitive = True


def yaml_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    """Load settings from YAML file."""
    import yaml

    config_paths = [
        Path("config/settings.yaml"),
        Path("config/settings.yml"),
        Path("settings.yaml"),
        Path("settings.yml"),
    ]

    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}

    return {}


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
