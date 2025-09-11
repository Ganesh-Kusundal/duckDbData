"""
Configuration Manager
Centralized configuration management with hierarchical loading and validation
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum

from .loaders import ConfigLoader
from .validators import ConfigValidator
from .settings import AppSettings

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class ConfigManager:
    """
    Centralized configuration manager

    Features:
    - Hierarchical configuration loading
    - Environment-specific overrides
    - Configuration validation
    - Hot-reload capability
    - Type-safe settings access
    """

    # Configuration paths
    base_config_path: Path = field(default_factory=lambda: Path("src/shared/config"))
    config_dir: Path = field(default_factory=lambda: Path("configs"))
    env_config_dir: Path = field(default_factory=lambda: Path("configs/environments"))

    # Current environment
    environment: Environment = Environment.DEVELOPMENT

    # Configuration cache
    _config_cache: Dict[str, Any] = field(default_factory=dict)
    _settings_cache: Dict[str, Any] = field(default_factory=dict)
    _last_modified: Dict[str, float] = field(default_factory=dict)

    # Components
    loader: ConfigLoader = field(default_factory=ConfigLoader)
    validator: ConfigValidator = field(default_factory=ConfigValidator)

    def __post_init__(self):
        """Initialize configuration manager"""
        # Set environment from environment variable
        env_var = os.getenv("TRADING_ENV", "development").upper()
        try:
            self.environment = Environment[env_var]
        except KeyError:
            logger.warning(f"Unknown environment '{env_var}', defaulting to DEVELOPMENT")
            self.environment = Environment.DEVELOPMENT

        logger.info(f"Configuration Manager initialized for environment: {self.environment.value}")

    def get_config(self, config_name: str, reload: bool = False) -> Dict[str, Any]:
        """
        Get configuration by name

        Args:
            config_name: Name of the configuration file (without extension)
            reload: Force reload from disk

        Returns:
            Configuration dictionary
        """
        cache_key = f"{config_name}_{self.environment.value}"

        # Check if we need to reload
        if not reload and cache_key in self._config_cache:
            config_file = self._find_config_file(config_name)
            if config_file and self._is_config_modified(config_file, cache_key):
                logger.debug(f"Configuration {config_name} modified, reloading")
                reload = True

        if reload or cache_key not in self._config_cache:
            config = self._load_config(config_name)
            if config:
                self._config_cache[cache_key] = config

        return self._config_cache.get(cache_key, {})

    def get_settings(self, settings_class: type, reload: bool = False) -> Any:
        """
        Get typed settings object

        Args:
            settings_class: Settings class to instantiate
            reload: Force reload from disk

        Returns:
            Instantiated settings object
        """
        class_name = settings_class.__name__

        if not reload and class_name in self._settings_cache:
            return self._settings_cache[class_name]

        # Load configuration data
        config_data = {}
        for config_name in self._get_required_configs(settings_class):
            config_data.update(self.get_config(config_name, reload))

        # Create settings instance
        try:
            settings = settings_class(**config_data)
            self._settings_cache[class_name] = settings
            logger.debug(f"Created settings instance: {class_name}")
            return settings
        except Exception as e:
            logger.error(f"Failed to create settings for {class_name}: {e}")
            raise

    def reload_all(self) -> None:
        """
        Reload all configurations from disk
        """
        logger.info("Reloading all configurations")
        self._config_cache.clear()
        self._settings_cache.clear()
        self._last_modified.clear()

    def list_configs(self) -> List[str]:
        """
        List all available configuration files

        Returns:
            List of configuration names
        """
        configs = set()

        # Base configurations
        if self.config_dir.exists():
            for config_file in self.config_dir.glob("*.yaml"):
                configs.add(config_file.stem)
            for config_file in self.config_dir.glob("*.yml"):
                configs.add(config_file.stem)
            for config_file in self.config_dir.glob("*.json"):
                configs.add(config_file.stem)

        # Environment-specific configurations
        env_dir = self.env_config_dir / self.environment.value
        if env_dir.exists():
            for config_file in env_dir.glob("*.yaml"):
                configs.add(config_file.stem)
            for config_file in env_dir.glob("*.yml"):
                configs.add(config_file.stem)
            for config_file in env_dir.glob("*.json"):
                configs.add(config_file.stem)

        return sorted(list(configs))

    def validate_config(self, config_name: str) -> bool:
        """
        Validate a configuration file

        Args:
            config_name: Name of the configuration file

        Returns:
            True if valid, False otherwise
        """
        config = self.get_config(config_name)
        if not config:
            return False

        return self.validator.validate_config(config_name, config)

    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get information about the current environment

        Returns:
            Environment information
        """
        return {
            "environment": self.environment.value,
            "config_dir": str(self.config_dir),
            "env_config_dir": str(self.env_config_dir / self.environment.value),
            "available_configs": self.list_configs(),
            "cache_size": len(self._config_cache),
            "settings_cache_size": len(self._settings_cache)
        }

    def _load_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Load configuration from file

        Args:
            config_name: Name of the configuration file

        Returns:
            Configuration dictionary or None if not found
        """
        config_file = self._find_config_file(config_name)
        if not config_file:
            logger.warning(f"Configuration file not found: {config_name}")
            return None

        try:
            config = self.loader.load_config(config_file)

            # Validate configuration
            if not self.validator.validate_config(config_name, config):
                logger.error(f"Configuration validation failed: {config_name}")
                return None

            # Update last modified time
            cache_key = f"{config_name}_{self.environment.value}"
            self._last_modified[cache_key] = config_file.stat().st_mtime

            logger.debug(f"Loaded configuration: {config_name}")
            return config

        except Exception as e:
            logger.error(f"Failed to load configuration {config_name}: {e}")
            return None

    def _find_config_file(self, config_name: str) -> Optional[Path]:
        """
        Find configuration file in the search paths

        Args:
            config_name: Name of the configuration file

        Returns:
            Path to configuration file or None if not found
        """
        # Search paths in order of precedence
        search_paths = [
            # Environment-specific config
            self.env_config_dir / self.environment.value / f"{config_name}.yaml",
            self.env_config_dir / self.environment.value / f"{config_name}.yml",
            self.env_config_dir / self.environment.value / f"{config_name}.json",
            # Base config
            self.config_dir / f"{config_name}.yaml",
            self.config_dir / f"{config_name}.yml",
            self.config_dir / f"{config_name}.json",
            # Legacy locations (for backward compatibility)
            Path("trade_engine/config") / f"{config_name}.yaml",
            Path("trade_engine/config") / f"{config_name}.yml",
            Path("trade_engine/config") / f"{config_name}.json",
        ]

        for config_file in search_paths:
            if config_file.exists():
                return config_file

        return None

    def _is_config_modified(self, config_file: Path, cache_key: str) -> bool:
        """
        Check if configuration file has been modified

        Args:
            config_file: Path to configuration file
            cache_key: Cache key for the configuration

        Returns:
            True if modified, False otherwise
        """
        if cache_key not in self._last_modified:
            return True

        current_mtime = config_file.stat().st_mtime
        last_mtime = self._last_modified[cache_key]

        return current_mtime > last_mtime

    def _get_required_configs(self, settings_class: type) -> List[str]:
        """
        Get list of required configuration files for a settings class

        Args:
            settings_class: Settings class

        Returns:
            List of required configuration names
        """
        # This could be enhanced with class annotations or metadata
        # For now, use a simple mapping
        config_mapping = {
            "AppSettings": ["config", "database", "analytics"],
            "DatabaseSettings": ["database"],
            "APISettings": ["config"],
            "CLISettings": ["config"],
            "DashboardSettings": ["config", "analytics"],
            "WebSocketSettings": ["config"],
        }

        class_name = settings_class.__name__
        return config_mapping.get(class_name, ["config"])


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get global configuration manager instance

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reset_config_manager():
    """
    Reset global configuration manager (mainly for testing)

    Returns:
        New ConfigManager instance
    """
    global _config_manager
    old_manager = _config_manager
    _config_manager = ConfigManager()
    return old_manager
