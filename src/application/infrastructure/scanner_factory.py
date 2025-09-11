"""
Scanner Factory for creating and managing scanner instances.

This module provides a centralized factory for creating scanner objects
with proper dependency injection and configuration management.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class ScannerFactory:
    """
    Factory for creating and managing scanner instances.

    Provides centralized creation of scanner objects with proper
    dependency injection and configuration management.
    """

    def __init__(self, db_path: Optional[str] = None, config_manager=None):
        """
        Initialize the scanner factory.

        Args:
            db_path: Optional database path override
            config_manager: Optional configuration manager
        """
        self.db_path = db_path
        self.config_manager = config_manager
        self._scanner_cache = {}

    def create_scanner(self, scanner_type: str, **kwargs) -> Any:
        """
        Create a scanner instance.

        Args:
            scanner_type: Type of scanner to create
            **kwargs: Additional arguments for scanner creation

        Returns:
            Scanner instance

        Raises:
            ValueError: If scanner type is not supported
        """
        if scanner_type == 'breakout':
            return self._create_breakout_scanner(**kwargs)
        elif scanner_type == 'crp':
            return self._create_crp_scanner(**kwargs)
        else:
            raise ValueError(f"Unsupported scanner type: {scanner_type}")

    def _create_breakout_scanner(self, **kwargs):
        """Create a breakout scanner instance."""
        try:
            # Import here to avoid circular dependencies
            from app.startup import get_scanner
            return get_scanner('breakout', self.db_path)
        except ImportError as e:
            logger.error(f"Failed to create breakout scanner: {e}")
            raise

    def _create_crp_scanner(self, **kwargs):
        """Create a CRP scanner instance."""
        try:
            # Import here to avoid circular dependencies
            from app.startup import get_scanner
            return get_scanner('crp', self.db_path)
        except ImportError as e:
            logger.error(f"Failed to create CRP scanner: {e}")
            raise

    def get_scanner_config(self, scanner_type: str) -> Dict[str, Any]:
        """
        Get configuration for a scanner type.

        Args:
            scanner_type: Type of scanner

        Returns:
            Scanner configuration dictionary
        """
        # Default configurations
        configs = {
            'breakout': {
                'volume_multiplier': 1.5,
                'min_price': 50,
                'max_price': 2000,
                'min_volume': 10000,
                'time_window_minutes': 30,
                'breakout_cutoff_time': '09:45'
            },
            'crp': {
                'close_threshold_pct': 2.0,
                'range_threshold_pct': 3.0,
                'consolidation_period': 5,
                'min_price': 50,
                'max_price': 2000,
                'min_volume': 10000
            }
        }

        return configs.get(scanner_type, {})

    def list_available_scanners(self) -> List[str]:
        """
        List all available scanner types.

        Returns:
            List of available scanner type names
        """
        return ['breakout', 'crp']

    def validate_scanner_config(self, scanner_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate scanner configuration.

        Args:
            scanner_type: Type of scanner
            config: Configuration to validate

        Returns:
            Validation result with success status and any errors
        """
        errors = []

        # Get base config for validation
        base_config = self.get_scanner_config(scanner_type)

        # Validate required fields
        for key, value in base_config.items():
            if key not in config:
                config[key] = value  # Use default
            elif not isinstance(config[key], type(value)):
                errors.append(f"Invalid type for {key}: expected {type(value).__name__}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'config': config
        }
