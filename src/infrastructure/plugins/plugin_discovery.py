"""
Plugin Discovery
================

Component for discovering and analyzing available plugins in the system.
Provides functionality to scan plugin directories and extract plugin metadata.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import importlib.util
import inspect

from .plugin_interfaces import get_plugin_interface
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class PluginDiscovery:
    """
    Plugin discovery service.

    This class handles the discovery and analysis of plugins in configured
    directories, extracting metadata and capabilities information.
    """

    def __init__(self, plugin_directories: Optional[List[Path]] = None):
        """
        Initialize plugin discovery.

        Args:
            plugin_directories: List of directories to scan for plugins
        """
        self.plugin_directories = plugin_directories or []
        self.discovered_plugins: Dict[str, Dict[str, Any]] = {}

        logger.info("PluginDiscovery initialized")

    def scan_directories(self) -> Dict[str, Dict[str, Any]]:
        """
        Scan all configured directories for plugins.

        Returns:
            Dictionary of discovered plugins organized by type
        """
        self.discovered_plugins = {}

        for directory in self.plugin_directories:
            if not directory.exists():
                logger.warning(f"Plugin directory does not exist: {directory}")
                continue

            logger.info(f"Scanning plugin directory: {directory}")
            plugins_in_dir = self._scan_directory(directory)

            # Merge results
            for plugin_type, plugins in plugins_in_dir.items():
                if plugin_type not in self.discovered_plugins:
                    self.discovered_plugins[plugin_type] = {}

                self.discovered_plugins[plugin_type].update(plugins)

        logger.info(f"Plugin discovery completed: {self._count_discovered_plugins()} plugins found")
        return self.discovered_plugins.copy()

    def scan_single_directory(self, directory: Path) -> Dict[str, Dict[str, Any]]:
        """
        Scan a single directory for plugins.

        Args:
            directory: Directory to scan

        Returns:
            Dictionary of plugins found in the directory
        """
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return {}

        logger.info(f"Scanning directory: {directory}")
        return self._scan_directory(directory)

    def get_plugin_info(self, plugin_type: str, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            Plugin information or None if not found
        """
        if plugin_type not in self.discovered_plugins:
            return None

        return self.discovered_plugins[plugin_type].get(plugin_name)

    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, Any]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugins to retrieve

        Returns:
            Dictionary of plugins of the specified type
        """
        return self.discovered_plugins.get(plugin_type, {})

    def get_all_plugins(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all discovered plugins.

        Returns:
            Dictionary of all discovered plugins
        """
        return self.discovered_plugins.copy()

    def refresh_discovery(self) -> Dict[str, Dict[str, Any]]:
        """
        Refresh plugin discovery by rescanning directories.

        Returns:
            Updated dictionary of discovered plugins
        """
        logger.info("Refreshing plugin discovery")
        return self.scan_directories()

    def validate_plugin_file(self, plugin_file: Path) -> bool:
        """
        Validate that a file is a valid plugin.

        Args:
            plugin_file: Plugin file to validate

        Returns:
            True if file is a valid plugin
        """
        if not plugin_file.exists() or not plugin_file.is_file():
            return False

        if plugin_file.suffix != '.py':
            return False

        if plugin_file.name.startswith('_'):
            return False

        # Try to analyze the file
        try:
            analysis = self._analyze_plugin_file(plugin_file)
            return analysis is not None
        except Exception:
            return False

    def _scan_directory(self, directory: Path) -> Dict[str, Dict[str, Any]]:
        """
        Scan a directory for plugins.

        Args:
            directory: Directory to scan

        Returns:
            Dictionary of plugins found
        """
        plugins = {}

        # Scan for Python files
        for plugin_file in directory.rglob("*.py"):
            if plugin_file.name.startswith('_'):
                continue

            try:
                plugin_info = self._analyze_plugin_file(plugin_file)
                if plugin_info:
                    plugin_type = plugin_info['type']
                    plugin_name = plugin_info['name']

                    if plugin_type not in plugins:
                        plugins[plugin_type] = {}

                    plugins[plugin_type][plugin_name] = plugin_info
                    logger.debug(f"Discovered plugin: {plugin_type}.{plugin_name}")

            except Exception as e:
                logger.warning(f"Failed to analyze plugin file {plugin_file}: {e}")

        return plugins

    def _analyze_plugin_file(self, plugin_file: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a plugin file to extract metadata.

        Args:
            plugin_file: Plugin file to analyze

        Returns:
            Plugin information or None if analysis fails
        """
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                plugin_file.stem, plugin_file
            )

            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin classes
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    hasattr(obj, 'metadata') and
                    hasattr(obj, 'initialize')):
                    plugin_classes.append(obj)

            if not plugin_classes:
                return None

            # Use the first plugin class found
            plugin_class = plugin_classes[0]

            # Determine plugin type from inheritance
            plugin_type = self._determine_plugin_type(plugin_class)

            if not plugin_type:
                return None

            # Extract metadata
            try:
                metadata = plugin_class().metadata
            except Exception:
                # Create basic metadata if property fails
                metadata = type('Metadata', (), {
                    'name': plugin_file.stem,
                    'version': '1.0.0',
                    'description': f'Plugin {plugin_file.stem}',
                    'author': 'Unknown',
                    'license': 'Unknown'
                })()

            plugin_info = {
                'name': plugin_file.stem,
                'type': plugin_type,
                'module': module.__name__,
                'path': str(plugin_file),
                'class': plugin_class.__name__,
                'metadata': {
                    'name': getattr(metadata, 'name', plugin_file.stem),
                    'version': getattr(metadata, 'version', '1.0.0'),
                    'description': getattr(metadata, 'description', ''),
                    'author': getattr(metadata, 'author', 'Unknown'),
                    'license': getattr(metadata, 'license', 'Unknown')
                },
                'capabilities': self._extract_capabilities(plugin_class),
                'discovered_at': datetime.now().isoformat(),
                'file_size': plugin_file.stat().st_size
            }

            return plugin_info

        except Exception as e:
            logger.warning(f"Failed to analyze plugin file {plugin_file}: {e}")
            return None

    def _determine_plugin_type(self, plugin_class: type) -> Optional[str]:
        """
        Determine plugin type from class inheritance.

        Args:
            plugin_class: Plugin class to analyze

        Returns:
            Plugin type string or None
        """
        from .plugin_interfaces import (
            ScannerPluginInterface,
            BrokerPluginInterface,
            DataSourcePluginInterface,
            NotificationPluginInterface,
            AnalyticsPluginInterface
        )

        type_mappings = {
            ScannerPluginInterface: 'scanner',
            BrokerPluginInterface: 'broker',
            DataSourcePluginInterface: 'data_source',
            NotificationPluginInterface: 'notification',
            AnalyticsPluginInterface: 'analytics'
        }

        for interface, plugin_type in type_mappings.items():
            if (inspect.isclass(plugin_class) and
                issubclass(plugin_class, interface) and
                plugin_class != interface):
                return plugin_type

        return None

    def _extract_capabilities(self, plugin_class: type) -> Dict[str, Any]:
        """
        Extract plugin capabilities from class.

        Args:
            plugin_class: Plugin class to analyze

        Returns:
            Dictionary of plugin capabilities
        """
        capabilities = {}

        # Check for special methods
        special_methods = [
            'scan', 'connect', 'send_notification', 'analyze_data'
        ]

        for method in special_methods:
            if hasattr(plugin_class, method):
                capabilities[method] = True

        # Try to instantiate and get more info
        try:
            instance = plugin_class()
            if hasattr(instance, 'get_capabilities'):
                instance_capabilities = instance.get_capabilities()
                if isinstance(instance_capabilities, dict):
                    capabilities.update(instance_capabilities)
        except Exception:
            pass

        return capabilities

    def _count_discovered_plugins(self) -> int:
        """
        Count total number of discovered plugins.

        Returns:
            Total number of plugins
        """
        return sum(len(plugins) for plugins in self.discovered_plugins.values())

    def get_discovery_stats(self) -> Dict[str, Any]:
        """
        Get discovery statistics.

        Returns:
            Dictionary with discovery statistics
        """
        stats = {
            'total_plugins': self._count_discovered_plugins(),
            'plugin_types': list(self.discovered_plugins.keys()),
            'directories_scanned': len(self.plugin_directories),
            'last_scan': datetime.now().isoformat()
        }

        # Add per-type counts
        for plugin_type, plugins in self.discovered_plugins.items():
            stats[f'{plugin_type}_count'] = len(plugins)

        return stats
