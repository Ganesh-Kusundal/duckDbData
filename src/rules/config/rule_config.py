"""
Rule Configuration Manager

Centralized configuration management for rule-based backtesting system.
Loads configuration from YAML files and provides easy access to all settings.
"""

import os
import yaml
from typing import Dict, Any, Optional
from datetime import time
import logging

logger = logging.getLogger(__name__)


class RuleConfig:
    """Centralized configuration manager for rule-based backtesting."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to config file. If None, uses default scanners.yaml
        """
        if config_path is None:
            # Default to scanners.yaml in configs directory
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_path = os.path.join(base_path, "configs", "scanners.yaml")

        self.config_path = config_path
        self._config = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found: {self.config_path}")
                self._config = {}
                return

            with open(self.config_path, 'r') as f:
                full_config = yaml.safe_load(f)

            # Extract rules section
            self._config = full_config.get('rules', {})

            logger.info(f"Loaded rule configuration from {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self._config = {}

    def reload_config(self):
        """Reload configuration from file."""
        self._load_config()

    # ============================================================================
    # TIMING CONFIGURATION
    # ============================================================================

    def get_cutoff_time(self) -> str:
        """Get signal cutoff time (e.g., '09:45')."""
        return self._config.get('cutoff_time', '09:45')

    def get_cutoff_time_obj(self) -> time:
        """Get cutoff time as datetime.time object."""
        cutoff_str = self.get_cutoff_time()
        hour, minute = map(int, cutoff_str.split(':'))
        return time(hour, minute)

    def get_signal_time_window_start(self) -> str:
        """Get signal time window start time."""
        return self._config.get('signal_time_window_start', '09:15')

    def get_signal_time_window_end(self) -> str:
        """Get signal time window end time."""
        return self._config.get('signal_time_window_end', '09:45')

    def get_performance_start_time(self) -> str:
        """Get performance measurement start time."""
        return self._config.get('performance_start_time', '09:45')

    def get_performance_end_time(self) -> str:
        """Get performance measurement end time."""
        return self._config.get('performance_end_time', '15:15')

    # ============================================================================
    # BREAKOUT RULE CONFIGURATION
    # ============================================================================

    def get_breakout_config(self) -> Dict[str, Any]:
        """Get breakout rule configuration."""
        return self._config.get('breakout', {})

    def get_breakout_volume_multiplier_min(self) -> float:
        """Get minimum volume multiplier for breakout rules."""
        return self.get_breakout_config().get('volume_multiplier_min', 1.2)

    def get_breakout_volume_multiplier_max(self) -> float:
        """Get maximum volume multiplier for breakout rules."""
        return self.get_breakout_config().get('volume_multiplier_max', 3.0)

    def get_breakout_price_move_min(self) -> float:
        """Get minimum price move percentage for breakout rules."""
        return self.get_breakout_config().get('price_move_pct_min', 0.5)

    def get_breakout_price_move_max(self) -> float:
        """Get maximum price move percentage for breakout rules."""
        return self.get_breakout_config().get('price_move_pct_max', 5.0)

    def get_breakout_strength_threshold(self) -> float:
        """Get breakout strength threshold."""
        return self.get_breakout_config().get('breakout_strength_threshold', 2.0)

    def get_breakout_time_window_minutes(self) -> int:
        """Get breakout time window in minutes."""
        return self.get_breakout_config().get('time_window_minutes', 30)

    def get_breakout_volume_comparison_period(self) -> int:
        """Get volume comparison period for breakout rules."""
        return self.get_breakout_config().get('volume_comparison_period', 10)

    def get_breakout_min_price(self) -> float:
        """Get minimum price for breakout rules."""
        return self.get_breakout_config().get('min_price', 50)

    def get_breakout_max_price(self) -> float:
        """Get maximum price for breakout rules."""
        return self.get_breakout_config().get('max_price', 10000)

    def get_breakout_min_volume(self) -> int:
        """Get minimum volume for breakout rules."""
        return self.get_breakout_config().get('min_volume', 1000)

    # ============================================================================
    # CRP RULE CONFIGURATION
    # ============================================================================

    def get_crp_config(self) -> Dict[str, Any]:
        """Get CRP rule configuration."""
        return self._config.get('crp', {})

    def get_crp_close_threshold_pct(self) -> float:
        """Get close threshold percentage for CRP rules."""
        return self.get_crp_config().get('close_threshold_pct', 2.0)

    def get_crp_range_threshold_pct(self) -> float:
        """Get range threshold percentage for CRP rules."""
        return self.get_crp_config().get('range_threshold_pct', 3.0)

    def get_crp_consolidation_period(self) -> int:
        """Get consolidation period for CRP rules."""
        return self.get_crp_config().get('consolidation_period', 5)

    def get_crp_min_price(self) -> float:
        """Get minimum price for CRP rules."""
        return self.get_crp_config().get('min_price', 50)

    def get_crp_max_price(self) -> float:
        """Get maximum price for CRP rules."""
        return self.get_crp_config().get('max_price', 10000)

    def get_crp_min_volume(self) -> int:
        """Get minimum volume for CRP rules."""
        return self.get_crp_config().get('min_volume', 1000)

    # ============================================================================
    # TECHNICAL RULE CONFIGURATION
    # ============================================================================

    def get_technical_config(self) -> Dict[str, Any]:
        """Get technical rule configuration."""
        return self._config.get('technical', {})

    def get_rsi_oversold(self) -> int:
        """Get RSI oversold threshold."""
        return self.get_technical_config().get('rsi_oversold', 30)

    def get_rsi_overbought(self) -> int:
        """Get RSI overbought threshold."""
        return self.get_technical_config().get('rsi_overbought', 70)

    def get_macd_threshold(self) -> float:
        """Get MACD threshold."""
        return self.get_technical_config().get('macd_threshold', 0.1)

    def get_bb_deviation(self) -> float:
        """Get Bollinger Band deviation."""
        return self.get_technical_config().get('bb_deviation', 1.5)

    # ============================================================================
    # VOLUME RULE CONFIGURATION
    # ============================================================================

    def get_volume_config(self) -> Dict[str, Any]:
        """Get volume rule configuration."""
        return self._config.get('volume', {})

    def get_volume_multiplier_min(self) -> float:
        """Get minimum volume multiplier for volume rules."""
        return self.get_volume_config().get('volume_multiplier_min', 1.5)

    def get_volume_multiplier_max(self) -> float:
        """Get maximum volume multiplier for volume rules."""
        return self.get_volume_config().get('volume_multiplier_max', 5.0)

    # ============================================================================
    # BACKTESTING CONFIGURATION
    # ============================================================================

    def get_backtesting_config(self) -> Dict[str, Any]:
        """Get backtesting configuration."""
        return self._config.get('backtesting', {})

    def get_max_parallel_rules(self) -> int:
        """Get maximum number of parallel rules."""
        return self.get_backtesting_config().get('max_parallel_rules', 4)

    def get_database_connection_pool(self) -> bool:
        """Get database connection pool setting."""
        return self.get_backtesting_config().get('database_connection_pool', True)

    def get_query_cache_enabled(self) -> bool:
        """Get query cache enabled setting."""
        return self.get_backtesting_config().get('query_cache_enabled', True)

    def get_query_cache_ttl(self) -> int:
        """Get query cache TTL in seconds."""
        return self.get_backtesting_config().get('query_cache_ttl', 300)

    def get_performance_monitoring(self) -> bool:
        """Get performance monitoring setting."""
        return self.get_backtesting_config().get('performance_monitoring', True)

    def get_metrics_collection(self) -> bool:
        """Get metrics collection setting."""
        return self.get_backtesting_config().get('metrics_collection', True)

    # ============================================================================
    # OPTIMIZATION CONFIGURATION
    # ============================================================================

    def get_optimization_config(self) -> Dict[str, Any]:
        """Get optimization configuration."""
        return self._config.get('optimization', {})

    def get_default_optimization_algorithm(self) -> str:
        """Get default optimization algorithm."""
        return self.get_optimization_config().get('default_algorithm', 'grid_search')

    def get_max_optimization_evaluations(self) -> int:
        """Get maximum optimization evaluations."""
        return self.get_optimization_config().get('max_evaluations', 50)

    def get_parallel_workers(self) -> int:
        """Get number of parallel workers for optimization."""
        return self.get_optimization_config().get('parallel_workers', 2)

    def get_train_validation_split(self) -> float:
        """Get train/validation split ratio."""
        return self.get_optimization_config().get('train_validation_split', 0.7)

    def get_fitness_metric(self) -> str:
        """Get fitness metric for optimization."""
        return self.get_optimization_config().get('fitness_metric', 'intraday_win_rate')

    def get_early_stopping_threshold(self) -> float:
        """Get early stopping threshold."""
        return self.get_optimization_config().get('early_stopping_threshold', 0.001)

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set_config_value(self, key: str, value: Any):
        """Set a configuration value by key."""
        keys = key.split('.')
        config = self._config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value

    def save_config(self, file_path: Optional[str] = None):
        """Save current configuration to file."""
        if file_path is None:
            file_path = self.config_path

        try:
            # Load existing config to preserve other sections
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    full_config = yaml.safe_load(f) or {}
            else:
                full_config = {}

            # Update rules section
            full_config['rules'] = self._config

            # Save updated config
            with open(file_path, 'w') as f:
                yaml.dump(full_config, f, default_flow_style=False, indent=2)

            logger.info(f"Configuration saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def get_all_config(self) -> Dict[str, Any]:
        """Get entire configuration as dictionary."""
        return self._config.copy()

    def print_config_summary(self):
        """Print configuration summary."""
        print("=== RULE CONFIGURATION SUMMARY ===")
        print(f"Cutoff Time: {self.get_cutoff_time()}")
        print(f"Signal Window: {self.get_signal_time_window_start()} - {self.get_signal_time_window_end()}")
        print(f"Performance Window: {self.get_performance_start_time()} - {self.get_performance_end_time()}")
        print()
        print("Breakout Rules:")
        print(f"  Volume Multiplier: {self.get_breakout_volume_multiplier_min()} - {self.get_breakout_volume_multiplier_max()}")
        print(f"  Price Move: {self.get_breakout_price_move_min()}% - {self.get_breakout_price_move_max()}%")
        print(f"  Price Range: ₹{self.get_breakout_min_price()} - ₹{self.get_breakout_max_price()}")
        print()
        print("Backtesting:")
        print(f"  Max Parallel Rules: {self.get_max_parallel_rules()}")
        print(f"  Performance Monitoring: {self.get_performance_monitoring()}")
        print()
        print("Optimization:")
        print(f"  Default Algorithm: {self.get_default_optimization_algorithm()}")
        print(f"  Max Evaluations: {self.get_max_optimization_evaluations()}")


# Global configuration instance
_config_instance = None


def get_rule_config() -> RuleConfig:
    """Get global rule configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = RuleConfig()
    return _config_instance


def reload_rule_config():
    """Reload global rule configuration."""
    global _config_instance
    if _config_instance is not None:
        _config_instance.reload_config()
