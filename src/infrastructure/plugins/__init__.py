"""
Plugin System Infrastructure
============================

This module provides the infrastructure for a plugin-based architecture
that allows hot-swappable scanners, brokers, and other extensions.

The plugin system supports:
- Dynamic plugin discovery and loading
- Plugin lifecycle management
- Configuration management for plugins
- Plugin marketplace/registry
- Hot-reload capabilities
"""

from .plugin_manager import PluginManager
from .plugin_discovery import PluginDiscovery
from .plugin_registry import PluginRegistry
from .plugin_interfaces import (
    ScannerPluginInterface,
    BrokerPluginInterface,
    PluginInterface
)

__all__ = [
    'PluginManager',
    'PluginDiscovery',
    'PluginRegistry',
    'ScannerPluginInterface',
    'BrokerPluginInterface',
    'PluginInterface'
]
