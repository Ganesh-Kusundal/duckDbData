"""
Plugin Interfaces
=================

Abstract base classes and interfaces for plugin implementations.
These interfaces define the contracts that all plugins must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ...domain.entities.market_data import MarketDataBatch
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for plugin information."""
    name: str
    version: str
    description: str
    author: str
    license: str
    homepage: Optional[str] = None
    repository: Optional[str] = None
    dependencies: Optional[List[str]] = None


class PluginInterface(ABC):
    """Base interface for all plugins."""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration."""
        pass

    @abstractmethod
    def shutdown(self) -> bool:
        """Shutdown the plugin gracefully."""
        pass

    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for the plugin."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get current plugin status."""
        return {
            'name': self.metadata.name,
            'version': self.metadata.version,
            'status': 'active',
            'last_updated': datetime.now().isoformat()
        }


class ScannerPluginInterface(PluginInterface):
    """Interface for scanner plugins."""

    @abstractmethod
    def scan(self, market_data: MarketDataBatch, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute scanning logic on market data.

        Args:
            market_data: Batch of market data to scan
            config: Scanner-specific configuration

        Returns:
            Dictionary containing scan results
        """
        pass

    @abstractmethod
    def get_scan_schema(self) -> Dict[str, Any]:
        """Get schema for scan results."""
        pass

    def pre_scan_validation(self, market_data: MarketDataBatch) -> bool:
        """
        Validate market data before scanning.

        Args:
            market_data: Market data to validate

        Returns:
            True if data is valid for scanning
        """
        if market_data.record_count == 0:
            logger.warning(f"No data to scan for symbol {market_data.symbol}")
            return False

        return True

    def post_scan_processing(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process scan results.

        Args:
            results: Raw scan results

        Returns:
            Processed scan results
        """
        # Add metadata
        results['metadata'] = {
            'plugin_name': self.metadata.name,
            'plugin_version': self.metadata.version,
            'scan_timestamp': datetime.now().isoformat()
        }

        return results


class BrokerPluginInterface(PluginInterface):
    """Interface for broker plugins."""

    @abstractmethod
    def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to broker API."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from broker API."""
        pass

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        pass

    @abstractmethod
    def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Place a trading order."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a trading order."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a trading order."""
        pass

    def is_connected(self) -> bool:
        """Check if broker connection is active."""
        return False

    def get_capabilities(self) -> Dict[str, Any]:
        """Get broker capabilities."""
        return {
            'supports_market_orders': True,
            'supports_limit_orders': True,
            'supports_stop_orders': False,
            'max_orders_per_minute': 60,
            'supported_symbols': []
        }


class DataSourcePluginInterface(PluginInterface):
    """Interface for data source plugins."""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to data source."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from data source."""
        pass

    @abstractmethod
    def fetch_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch historical market data."""
        pass

    @abstractmethod
    def fetch_realtime_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch real-time market data."""
        pass

    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols."""
        pass

    def is_connected(self) -> bool:
        """Check if data source connection is active."""
        return False

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Get data quality metrics."""
        return {
            'latency_ms': 0,
            'success_rate': 1.0,
            'last_update': datetime.now().isoformat()
        }


class NotificationPluginInterface(PluginInterface):
    """Interface for notification plugins."""

    @abstractmethod
    def send_notification(self, message: str, recipients: List[str], **kwargs) -> bool:
        """Send a notification."""
        pass

    @abstractmethod
    def send_alert(self, title: str, message: str, priority: str, recipients: List[str]) -> bool:
        """Send an alert notification."""
        pass

    def get_supported_channels(self) -> List[str]:
        """Get supported notification channels."""
        return ['default']

    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get notification delivery statistics."""
        return {
            'total_sent': 0,
            'successful': 0,
            'failed': 0,
            'success_rate': 0.0
        }


class AnalyticsPluginInterface(PluginInterface):
    """Interface for analytics plugins."""

    @abstractmethod
    def analyze_data(self, data: Any, analysis_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform data analysis."""
        pass

    @abstractmethod
    def get_supported_analyses(self) -> List[str]:
        """Get list of supported analysis types."""
        pass

    def validate_analysis_config(self, analysis_type: str, config: Dict[str, Any]) -> bool:
        """Validate analysis configuration."""
        return True

    def get_analysis_schema(self, analysis_type: str) -> Dict[str, Any]:
        """Get schema for analysis results."""
        return {}


# Plugin Type Registry
PLUGIN_TYPES = {
    'scanner': ScannerPluginInterface,
    'broker': BrokerPluginInterface,
    'data_source': DataSourcePluginInterface,
    'notification': NotificationPluginInterface,
    'analytics': AnalyticsPluginInterface
}


def get_plugin_interface(plugin_type: str) -> type:
    """
    Get the interface class for a plugin type.

    Args:
        plugin_type: Type of plugin

    Returns:
        Interface class for the plugin type

    Raises:
        ValueError: If plugin type is not supported
    """
    if plugin_type not in PLUGIN_TYPES:
        raise ValueError(f"Unsupported plugin type: {plugin_type}")

    return PLUGIN_TYPES[plugin_type]


def validate_plugin_implementation(plugin: Any, plugin_type: str) -> bool:
    """
    Validate that a plugin implements the required interface.

    Args:
        plugin: Plugin instance to validate
        plugin_type: Expected plugin type

    Returns:
        True if plugin implements the interface correctly
    """
    interface_class = get_plugin_interface(plugin_type)

    # Check if plugin inherits from the interface
    if not isinstance(plugin, interface_class):
        logger.error(f"Plugin does not inherit from {interface_class.__name__}")
        return False

    # Check required methods exist
    required_methods = [method for method in dir(interface_class) if not method.startswith('_') and callable(getattr(interface_class, method))]

    for method in required_methods:
        if not hasattr(plugin, method):
            logger.error(f"Plugin missing required method: {method}")
            return False

    return True
