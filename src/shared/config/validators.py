"""
Configuration Validators
Validate configuration data against schemas and business rules
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Configuration validator with schema validation and business rule checks
    """

    def __init__(self):
        """Initialize configuration validator"""
        self.validation_rules = {
            "database": self._validate_database_config,
            "api": self._validate_api_config,
            "scanner": self._validate_scanner_config,
            "analytics": self._validate_analytics_config,
            "brokers": self._validate_brokers_config,
        }

    def validate_config(self, config_name: str, config: Dict[str, Any]) -> bool:
        """
        Validate a configuration dictionary

        Args:
            config_name: Name of the configuration
            config: Configuration dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(config, dict):
            logger.error(f"Configuration {config_name} must be a dictionary")
            return False

        # Get validation function
        validator_func = self.validation_rules.get(config_name)
        if validator_func:
            return validator_func(config)
        else:
            # Generic validation for unknown configs
            logger.warning(f"No specific validator for {config_name}, using generic validation")
            return self._validate_generic_config(config)

    def _validate_database_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate database configuration

        Args:
            config: Database configuration

        Returns:
            True if valid
        """
        # Required fields
        required_fields = ["path"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Database config missing required field: {field}")
                return False

        # Path validation
        path = config.get("path", "")
        if not path:
            logger.error("Database path cannot be empty")
            return False

        # Check if path is valid
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Invalid database path: {e}")
            return False

        # Numeric validations
        if "max_connections" in config:
            max_conn = config["max_connections"]
            if not isinstance(max_conn, int) or max_conn < 1:
                logger.error("max_connections must be a positive integer")
                return False

        if "connection_pool_size" in config:
            pool_size = config["connection_pool_size"]
            if not isinstance(pool_size, int) or pool_size < 1:
                logger.error("connection_pool_size must be a positive integer")
                return False

        logger.debug("Database configuration validation passed")
        return True

    def _validate_api_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate API configuration

        Args:
            config: API configuration

        Returns:
            True if valid
        """
        # Port validation
        if "port" in config:
            port = config["port"]
            if not isinstance(port, int) or not (1 <= port <= 65535):
                logger.error(f"Invalid API port: {port}. Must be between 1 and 65535")
                return False

        # Host validation
        if "host" in config:
            host = config["host"]
            if not isinstance(host, str) or not host.strip():
                logger.error("API host must be a non-empty string")
                return False

        # CORS origins validation
        if "cors_origins" in config:
            origins = config["cors_origins"]
            if not isinstance(origins, list):
                logger.error("CORS origins must be a list")
                return False

            for origin in origins:
                if not isinstance(origin, str) or not self._is_valid_url(origin):
                    logger.error(f"Invalid CORS origin: {origin}")
                    return False

        # URL validation
        url_fields = ["docs_url", "redoc_url", "openapi_url"]
        for field in url_fields:
            if field in config:
                url = config[field]
                if not isinstance(url, str) or not url.startswith("/"):
                    logger.error(f"{field} must start with '/'")
                    return False

        logger.debug("API configuration validation passed")
        return True

    def _validate_scanner_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate scanner configuration

        Args:
            config: Scanner configuration

        Returns:
            True if valid
        """
        # Time format validation
        time_fields = ["cutoff_time", "performance_start_time", "performance_end_time",
                      "signal_time_window_start", "signal_time_window_end"]

        for field in time_fields:
            if field in config:
                time_str = config[field]
                if not self._is_valid_time_format(time_str):
                    logger.error(f"Invalid time format for {field}: {time_str}. Use HH:MM format")
                    return False

        # Numeric validations
        if "backtest" in config and "max_iterations" in config["backtest"]:
            max_iter = config["backtest"]["max_iterations"]
            if not isinstance(max_iter, int) or max_iter < 1:
                logger.error("backtest.max_iterations must be a positive integer")
                return False

        # Rules validation
        if "rules" in config:
            rules = config["rules"]
            if not isinstance(rules, dict):
                logger.error("Scanner rules must be a dictionary")
                return False

        logger.debug("Scanner configuration validation passed")
        return True

    def _validate_analytics_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate analytics configuration

        Args:
            config: Analytics configuration

        Returns:
            True if valid
        """
        # Indicators validation
        if "indicators" in config:
            indicators = config["indicators"]
            if not isinstance(indicators, list):
                logger.error("Analytics indicators must be a list")
                return False

            valid_indicators = ["rsi", "macd", "obv", "sma", "ema", "bollinger_bands",
                              "stochastic", "williams_r", "cci", "adx"]

            for indicator in indicators:
                if not isinstance(indicator, str):
                    logger.error(f"Indicator must be a string: {indicator}")
                    return False
                if indicator.lower() not in valid_indicators:
                    logger.warning(f"Unknown indicator: {indicator}")

        # Dashboard validation
        if "dashboard" in config:
            dashboard = config["dashboard"]
            if not isinstance(dashboard, dict):
                logger.error("Analytics dashboard must be a dictionary")
                return False

            if "port" in dashboard:
                port = dashboard["port"]
                if not isinstance(port, int) or not (1 <= port <= 65535):
                    logger.error(f"Invalid dashboard port: {port}")
                    return False

        logger.debug("Analytics configuration validation passed")
        return True

    def _validate_brokers_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate brokers configuration

        Args:
            config: Brokers configuration

        Returns:
            True if valid
        """
        # Default broker validation
        if "default" in config:
            default_broker = config["default"]
            if not isinstance(default_broker, str) or not default_broker.strip():
                logger.error("Default broker must be a non-empty string")
                return False

        # Brokers validation
        if "brokers" in config:
            brokers = config["brokers"]
            if not isinstance(brokers, dict):
                logger.error("Brokers must be a dictionary")
                return False

            required_keys = ["api_key", "api_secret", "access_token"]
            for broker_name, broker_config in brokers.items():
                if not isinstance(broker_config, dict):
                    logger.error(f"Broker {broker_name} configuration must be a dictionary")
                    return False

                for key in required_keys:
                    if key not in broker_config:
                        logger.error(f"Broker {broker_name} missing required key: {key}")
                        return False

                    if not isinstance(broker_config[key], str) or not broker_config[key].strip():
                        logger.error(f"Broker {broker_name} {key} must be a non-empty string")
                        return False

        # Endpoints validation
        if "endpoints" in config:
            endpoints = config["endpoints"]
            if not isinstance(endpoints, dict):
                logger.error("Broker endpoints must be a dictionary")
                return False

            for broker_name, endpoint in endpoints.items():
                if not isinstance(endpoint, str) or not self._is_valid_url(endpoint):
                    logger.error(f"Invalid endpoint for broker {broker_name}: {endpoint}")
                    return False

        logger.debug("Brokers configuration validation passed")
        return True

    def _validate_generic_config(self, config: Dict[str, Any]) -> bool:
        """
        Generic validation for configurations without specific validators

        Args:
            config: Configuration dictionary

        Returns:
            True if valid
        """
        # Basic structure validation
        if not config:
            logger.warning("Empty configuration")
            return True  # Empty configs are technically valid

        # Check for nested structure issues
        def validate_nested(obj, path="root"):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}"
                    if not isinstance(key, str):
                        logger.error(f"Non-string key at {new_path}: {type(key)}")
                        return False
                    if not validate_nested(value, new_path):
                        return False
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"
                    if not validate_nested(item, new_path):
                        return False
            # Basic type validation for values
            elif not isinstance(obj, (str, int, float, bool, type(None))):
                logger.error(f"Unsupported type at {path}: {type(obj)}")
                return False

            return True

        return validate_nested(config)

    def _is_valid_url(self, url: str) -> bool:
        """
        Check if string is a valid URL

        Args:
            url: URL string to validate

        Returns:
            True if valid URL
        """
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return url_pattern.match(url) is not None

    def _is_valid_time_format(self, time_str: str) -> bool:
        """
        Check if string is a valid time format (HH:MM)

        Args:
            time_str: Time string to validate

        Returns:
            True if valid time format
        """
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
        return time_pattern.match(time_str) is not None

    def get_validation_errors(self, config_name: str, config: Dict[str, Any]) -> List[str]:
        """
        Get detailed validation errors for a configuration

        Args:
            config_name: Name of the configuration
            config: Configuration dictionary

        Returns:
            List of validation error messages
        """
        # This would implement detailed error collection
        # For now, return empty list (validation happens in validate_config)
        return []

    def validate_environment_config(self, environment: str, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for a specific environment

        Args:
            environment: Environment name
            config: Configuration dictionary

        Returns:
            True if valid for environment
        """
        # Environment-specific validations could be added here
        # For example, production configs might require certain security settings

        if environment == "production":
            # Production-specific validations
            if "api" in config:
                api_config = config["api"]
                # Ensure production has proper security settings
                if "secret_key" not in api_config:
                    logger.error("Production environment requires API secret_key")
                    return False

        return True
