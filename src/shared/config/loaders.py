"""
Configuration Loaders
Handle loading configuration from various file formats and sources
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

import yaml

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Configuration loader supporting multiple formats and sources
    """

    def __init__(self):
        """Initialize configuration loader"""
        self.supported_formats = {
            '.yaml': self._load_yaml,
            '.yml': self._load_yaml,
            '.json': self._load_json,
            '.env': self._load_env,
        }

    def load_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration from file

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If file format is not supported
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        file_extension = config_path.suffix.lower()

        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported configuration format: {file_extension}")

        loader_func = self.supported_formats[file_extension]

        try:
            config = loader_func(config_path)
            logger.debug(f"Loaded configuration from {config_path}")
            return config

        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            raise

    def _load_yaml(self, config_path: Path) -> Dict[str, Any]:
        """
        Load YAML configuration file

        Args:
            config_path: Path to YAML file

        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if config is None:
                logger.warning(f"Empty YAML file: {config_path}")
                return {}

            if not isinstance(config, dict):
                raise ValueError(f"YAML file must contain a dictionary at root level: {config_path}")

            return config

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}")

    def _load_json(self, config_path: Path) -> Dict[str, Any]:
        """
        Load JSON configuration file

        Args:
            config_path: Path to JSON file

        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if not isinstance(config, dict):
                raise ValueError(f"JSON file must contain an object at root level: {config_path}")

            return config

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {config_path}: {e}")

    def _load_env(self, config_path: Path) -> Dict[str, Any]:
        """
        Load environment variables from .env file

        Args:
            config_path: Path to .env file

        Returns:
            Configuration dictionary from environment variables
        """
        import os
        from dotenv import load_dotenv

        # Load environment variables from file
        load_dotenv(config_path)

        # Convert relevant environment variables to config dict
        config = {}

        # Database settings
        if os.getenv('DATABASE_PATH'):
            config.setdefault('database', {})['path'] = os.getenv('DATABASE_PATH')
        if os.getenv('DATABASE_MEMORY'):
            config.setdefault('database', {})['memory'] = os.getenv('DATABASE_MEMORY').lower() == 'true'

        # API settings
        if os.getenv('API_HOST'):
            config.setdefault('api', {})['host'] = os.getenv('API_HOST')
        if os.getenv('API_PORT'):
            config.setdefault('api', {})['port'] = int(os.getenv('API_PORT'))

        # Environment
        if os.getenv('TRADING_ENV'):
            config['environment'] = os.getenv('TRADING_ENV')

        return config

    def load_from_environment(self, prefix: str = "TRADING_") -> Dict[str, Any]:
        """
        Load configuration from environment variables

        Args:
            prefix: Environment variable prefix

        Returns:
            Configuration dictionary from environment
        """
        import os

        config = {}
        prefix_len = len(prefix)

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase with underscores
                config_key = key[prefix_len:].lower()

                # Handle nested keys (e.g., DATABASE_PATH -> database.path)
                if '_' in config_key:
                    parts = config_key.split('_', 1)
                    section = parts[0]
                    subsection = parts[1].replace('_', '.')
                    config.setdefault(section, {})[subsection] = self._parse_env_value(value)
                else:
                    config[config_key] = self._parse_env_value(value)

        return config

    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple configuration dictionaries

        Args:
            *configs: Configuration dictionaries to merge

        Returns:
            Merged configuration dictionary
        """
        merged = {}

        for config in configs:
            self._deep_merge(merged, config)

        return merged

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """
        Deep merge update dictionary into base dictionary

        Args:
            base: Base dictionary to update
            update: Dictionary with updates
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _parse_env_value(self, value: str) -> Union[str, int, float, bool, None]:
        """
        Parse environment variable value to appropriate type

        Args:
            value: String value from environment

        Returns:
            Parsed value with appropriate type
        """
        # Handle boolean values
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False

        # Handle None/null values
        if value.lower() in ('none', 'null', ''):
            return None

        # Handle numeric values
        try:
            # Try integer first
            if '.' not in value:
                return int(value)
            else:
                return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def save_config(self, config: Dict[str, Any], config_path: Union[str, Path], format: str = "yaml") -> None:
        """
        Save configuration to file

        Args:
            config: Configuration dictionary
            config_path: Path to save configuration
            format: File format (yaml or json)
        """
        config_path = Path(config_path)

        if format.lower() == "yaml":
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        elif format.lower() == "json":
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, sort_keys=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Saved configuration to {config_path}")

    def get_config_template(self, config_type: str) -> Dict[str, Any]:
        """
        Get configuration template for a specific type

        Args:
            config_type: Type of configuration (database, api, scanner, etc.)

        Returns:
            Configuration template
        """
        templates = {
            "database": {
                "path": "data/financial_data.duckdb",
                "memory": False,
                "extension_dir": "./extensions",
                "max_connections": 5,
                "connection_pool_size": 10,
                "connection_pool_timeout": 30.0,
                "query_cache_enabled": True,
                "query_cache_ttl": 300
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
                "rate_limit": "100/minute",
                "docs_url": "/docs",
                "redoc_url": "/redoc",
                "openapi_url": "/openapi.json"
            },
            "scanner": {
                "default": {
                    "breakout_period": 20,
                    "obv_threshold": 100.0,
                    "volume_multiplier": 1.5
                },
                "rules": {},
                "strategies": {},
                "backtest": {
                    "max_iterations": 1000,
                    "timeframe": "1d"
                }
            },
            "analytics": {
                "queries": {
                    "breakout_patterns": {
                        "timeout": 30,
                        "max_results": 1000
                    }
                },
                "rules": [],
                "dashboard": {
                    "port": 8080,
                    "host": "localhost"
                },
                "indicators": ["rsi", "macd", "obv"]
            }
        }

        return templates.get(config_type, {})
