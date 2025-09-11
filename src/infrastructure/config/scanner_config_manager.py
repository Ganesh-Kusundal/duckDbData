"""
Scanner Configuration Manager
============================

Unified configuration management for scanner framework across all interfaces.
Provides centralized configuration loading, validation, and management.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class ScannerType(str, Enum):
    """Available scanner types."""
    BREAKOUT = "breakout"
    CRP = "crp"
    TECHNICAL = "technical"
    RELATIVE_VOLUME = "relative_volume"


@dataclass
class ScannerConfig:
    """Scanner configuration data class."""
    consolidation_period: int = 5
    breakout_volume_ratio: float = 1.5
    resistance_break_pct: float = 0.5
    min_price: float = 50
    max_price: float = 2000
    max_results_per_day: int = 3
    min_volume: int = 10000
    min_probability_score: float = 10.0
    timeout: int = 300
    retry_attempts: int = 3
    enable_caching: bool = True
    cache_ttl: int = 300


@dataclass
class StreamingConfig:
    """Streaming configuration data class."""
    enabled: bool = True
    interval_seconds: int = 30
    max_concurrent_scans: int = 3
    websocket_enabled: bool = True
    auto_refresh_ui: bool = True
    real_time_alerts: bool = True


@dataclass
class APIConfig:
    """API configuration data class."""
    host: str = "localhost"
    port: int = 8000
    timeout: int = 300
    max_batch_size: int = 10
    enable_cors: bool = True
    rate_limiting: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CLIConfig:
    """CLI configuration data class."""
    verbose_logging: bool = False
    progress_bars: bool = True
    color_output: bool = True
    default_format: str = "table"
    auto_save_results: bool = True
    results_directory: str = "scanner_results"


@dataclass
class StreamlitConfig:
    """Streamlit configuration data class."""
    theme: str = "light"
    auto_refresh_interval: int = 30
    max_chart_points: int = 1000
    enable_export: bool = True
    default_scanner: str = "breakout"
    dashboard_layout: str = "wide"


class ScannerConfigManager:
    """Unified configuration manager for scanner framework."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file or self._find_config_file()
        self._config = {}
        self._load_config()

    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        search_paths = [
            Path.cwd() / "configs" / "scanner_config.json",
            Path.cwd() / "config" / "scanner_config.json",
            Path.cwd() / "scanner_config.json",
            Path.home() / ".scanner" / "config.json"
        ]

        for path in search_paths:
            if path.exists():
                logger.info(f"Found configuration file: {path}")
                return str(path)

        # Return default path
        default_path = Path.cwd() / "configs" / "scanner_config.json"
        logger.info(f"Using default configuration path: {default_path}")
        return str(default_path)

    def _load_config(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
            else:
                logger.warning(f"Configuration file not found: {self.config_file}")
                self._create_default_config()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration."""
        self._config = {
            "default": {
                "consolidation_period": 5,
                "breakout_volume_ratio": 1.5,
                "resistance_break_pct": 0.5,
                "min_price": 50,
                "max_price": 2000,
                "max_results_per_day": 3,
                "min_volume": 10000,
                "min_probability_score": 10.0,
                "timeout": 300,
                "retry_attempts": 3,
                "enable_caching": True,
                "cache_ttl": 300
            }
        }
        logger.info("Created default configuration")

    def save_config(self):
        """Save current configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def get_scanner_config(self, scanner_type: Optional[str] = None) -> ScannerConfig:
        """Get scanner configuration."""
        scanner_key = scanner_type or "default"
        config_data = self._config.get(scanner_key, self._config.get("default", {}))

        return ScannerConfig(**config_data)

    def get_streaming_config(self) -> StreamingConfig:
        """Get streaming configuration."""
        config_data = self._config.get("streaming", {})
        return StreamingConfig(**config_data)

    def get_api_config(self) -> APIConfig:
        """Get API configuration."""
        config_data = self._config.get("api", {})
        return APIConfig(**config_data)

    def get_cli_config(self) -> CLIConfig:
        """Get CLI configuration."""
        config_data = self._config.get("cli", {})
        return CLIConfig(**config_data)

    def get_streamlit_config(self) -> StreamlitConfig:
        """Get Streamlit configuration."""
        config_data = self._config.get("streamlit", {})
        return StreamlitConfig(**config_data)

    def update_scanner_config(self, scanner_type: str, key: str, value: Any):
        """Update scanner configuration."""
        if scanner_type not in self._config:
            self._config[scanner_type] = {}

        self._config[scanner_type][key] = value
        logger.info(f"Updated {scanner_type}.{key} = {value}")

    def update_config(self, section: str, key: str, value: Any):
        """Update configuration in any section."""
        if section not in self._config:
            self._config[section] = {}

        self._config[section][key] = value
        logger.info(f"Updated {section}.{key} = {value}")

    def get_config(self, section: str) -> Dict[str, Any]:
        """Get configuration section."""
        return self._config.get(section, {})

    def validate_config(self) -> bool:
        """Validate current configuration."""
        try:
            # Validate scanner configurations for all types including default
            scanner_types_to_check = [scanner_type.value for scanner_type in ScannerType] + ["default"]

            for scanner_type in scanner_types_to_check:
                config = self.get_scanner_config(scanner_type)
                assert config.consolidation_period > 0
                assert config.breakout_volume_ratio > 0
                assert 0 < config.resistance_break_pct < 1
                assert config.min_price > 0
                assert config.max_price > config.min_price
                assert config.min_probability_score >= 0

            # Validate other configurations
            streaming_config = self.get_streaming_config()
            assert streaming_config.interval_seconds > 0

            api_config = self.get_api_config()
            assert 1024 <= api_config.port <= 65535

            logger.info("Configuration validation passed")
            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self._create_default_config()
        logger.info("Reset configuration to defaults")

    def get_available_scanners(self) -> list[str]:
        """Get list of configured scanners."""
        scanners = []
        for key in self._config.keys():
            if key in [s.value for s in ScannerType]:
                scanners.append(key)
        return scanners or ["breakout", "crp", "technical", "relative_volume"]

    def export_config(self, output_file: str):
        """Export configuration to file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Exported configuration to {output_file}")
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            raise

    def import_config(self, input_file: str):
        """Import configuration from file."""
        try:
            with open(input_file, 'r') as f:
                new_config = json.load(f)

            self._config.update(new_config)
            logger.info(f"Imported configuration from {input_file}")
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            raise


# Global configuration manager instance
_config_manager = None


def get_config_manager() -> ScannerConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ScannerConfigManager()
    return _config_manager


def create_default_config_file(config_file: str):
    """Create default configuration file."""
    manager = ScannerConfigManager()
    manager.config_file = config_file
    manager.save_config()
    logger.info(f"Created default configuration file: {config_file}")
