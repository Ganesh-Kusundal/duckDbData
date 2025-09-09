"""
Scanner Configuration - Centralized Configuration Management

This module provides centralized configuration management for all scanners,
following the Configuration pattern and SOLID principles.
"""

from typing import Dict, Any
from datetime import time


class ScannerConfig:
    """
    Centralized configuration management for scanners.

    This class provides default configurations and validation
    for all supported scanners.
    """

    # Default configurations for each scanner
    DEFAULT_CONFIGS = {
        'breakout': {
            'consolidation_period': 5,
            'breakout_volume_ratio': 1.5,
            'resistance_break_pct': 0.5,
            'min_price': 50,
            'max_price': 2000,
            'max_results_per_day': 3,
            'breakout_cutoff_time': time(9, 50),
            'end_of_day_time': time(15, 15)
        },
        'enhanced_breakout': {
            'consolidation_period': 5,
            'breakout_volume_ratio': 1.5,
            'resistance_break_pct': 0.5,
            'min_price': 50,
            'max_price': 2000,
            'max_results_per_day': 3,
            'breakout_cutoff_time': time(9, 50),
            'end_of_day_time': time(15, 15)
        },
        'crp': {
            'consolidation_period': 5,
            'close_threshold_pct': 2.0,
            'range_threshold_pct': 3.0,
            'min_volume': 50000,
            'max_volume': 5000000,
            'min_price': 50,
            'max_price': 2000,
            'max_results_per_day': 3,
            'crp_cutoff_time': time(9, 50),
            'end_of_day_time': time(15, 15)
        },
        'enhanced_crp': {
            'consolidation_period': 5,
            'close_threshold_pct': 2.0,
            'range_threshold_pct': 3.0,
            'min_volume': 50000,
            'max_volume': 5000000,
            'min_price': 50,
            'max_price': 2000,
            'max_results_per_day': 3,
            'crp_cutoff_time': time(9, 50),
            'end_of_day_time': time(15, 15)
        },
        'technical': {
            'min_price': 50,
            'max_price': 2000,
            'max_results': 50,
            'indicators': ['RSI', 'MACD', 'BB'],
            'cutoff_time': time(9, 50)
        },
        'nifty500_filter': {
            "high_period": 120,
            "high_multiplier": 1.05,
            "volume_avg_period": 5,
            "min_price": 10,
            "max_price": 10000,
            "max_results": 50
        },
        'relative_volume': {
            'volume_multiplier': 1.5,
            'lookback_period': 20,
            'min_price': 50,
            'max_price': 2000,
            'max_results': 50
        },
        'simple_breakout': {
            'breakout_pct': 1.0,
            'volume_ratio': 1.2,
            'min_price': 50,
            'max_price': 2000,
            'max_results': 20
        }
    }

    @classmethod
    def get_default_config(cls, scanner_name: str) -> Dict[str, Any]:
        """
        Get default configuration for a scanner.

        Args:
            scanner_name: Name of the scanner

        Returns:
            Default configuration dictionary

        Raises:
            ValueError: If scanner is not supported
        """
        if scanner_name not in cls.DEFAULT_CONFIGS:
            raise ValueError(f"Scanner '{scanner_name}' is not supported")

        return cls.DEFAULT_CONFIGS[scanner_name].copy()

    @classmethod
    def validate_config(cls, scanner_name: str, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for a scanner.

        Args:
            scanner_name: Name of the scanner
            config: Configuration to validate

        Returns:
            True if configuration is valid
        """
        if scanner_name not in cls.DEFAULT_CONFIGS:
            return False

        default_config = cls.DEFAULT_CONFIGS[scanner_name]

        # Check that all required keys are present
        required_keys = set(default_config.keys())
        provided_keys = set(config.keys())

        if not required_keys.issubset(provided_keys):
            return False

        # Validate value types and ranges
        return cls._validate_config_values(config)

    @classmethod
    def _validate_config_values(cls, config: Dict[str, Any]) -> bool:
        """Validate configuration values."""
        try:
            # Price validation
            if 'min_price' in config and 'max_price' in config:
                if config['min_price'] >= config['max_price']:
                    return False
                if config['min_price'] < 0 or config['max_price'] < 0:
                    return False

            # Volume validation
            if 'min_volume' in config and config['min_volume'] < 0:
                return False
            if 'max_volume' in config and config['max_volume'] < 0:
                return False

            # Percentage validation
            percentage_fields = ['breakout_volume_ratio', 'resistance_break_pct',
                               'close_threshold_pct', 'range_threshold_pct']
            for field in percentage_fields:
                if field in config and (config[field] < 0 or config[field] > 100):
                    return False

            # Results limit validation
            results_fields = ['max_results_per_day', 'max_results']
            for field in results_fields:
                if field in config and config[field] < 1:
                    return False

            return True

        except (TypeError, ValueError):
            return False

    @classmethod
    def get_config_template(cls, scanner_name: str) -> Dict[str, Any]:
        """
        Get configuration template with descriptions.

        Args:
            scanner_name: Name of the scanner

        Returns:
            Configuration template with field descriptions
        """
        if scanner_name not in cls.DEFAULT_CONFIGS:
            raise ValueError(f"Scanner '{scanner_name}' is not supported")

        config = cls.DEFAULT_CONFIGS[scanner_name].copy()

        # Add descriptions
        descriptions = cls._get_config_descriptions(scanner_name)
        config['_descriptions'] = descriptions

        return config

    @classmethod
    def _get_config_descriptions(cls, scanner_name: str) -> Dict[str, str]:
        """Get field descriptions for a scanner."""
        base_descriptions = {
            'min_price': 'Minimum stock price to consider',
            'max_price': 'Maximum stock price to consider',
            'max_results_per_day': 'Maximum results to return per day',
            'max_results': 'Maximum results to return',
            'consolidation_period': 'Number of days for consolidation analysis',
            'breakout_cutoff_time': 'Time for breakout detection',
            'end_of_day_time': 'Time for end-of-day analysis',
            'crp_cutoff_time': 'Time for CRP detection',
            'cutoff_time': 'Time cutoff for scanning'
        }

        scanner_specific = {
            'breakout': {
                'breakout_volume_ratio': 'Volume ratio required for breakout confirmation',
                'resistance_break_pct': 'Percentage above resistance for breakout'
            },
            'crp': {
                'close_threshold_pct': 'Max % difference for close near high/low',
                'range_threshold_pct': 'Max % for narrow range',
                'min_volume': 'Minimum volume for consideration',
                'max_volume': 'Maximum volume for consideration'
            },
            'technical': {
                'indicators': 'List of technical indicators to use'
            },
            'relative_volume': {
                'volume_multiplier': 'Volume multiplier threshold',
                'lookback_period': 'Lookback period for volume analysis'
            },
            'simple_breakout': {
                'breakout_pct': 'Breakout percentage threshold',
                'volume_ratio': 'Volume ratio threshold'
            }
        }

        descriptions = base_descriptions.copy()
        if scanner_name in scanner_specific:
            descriptions.update(scanner_specific[scanner_name])

        return descriptions



