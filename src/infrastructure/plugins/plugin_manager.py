"""
Plugin Manager
==============

Core component for managing plugin lifecycle, loading, and execution.
Provides centralized plugin management with hot-reload capabilities.
"""

from typing import Dict, List, Any, Optional, Type
import importlib
import inspect
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from .plugin_interfaces import (
    PluginInterface,
    PluginMetadata,
    get_plugin_interface,
    validate_plugin_implementation
)
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PluginInfo:
    """Information about a loaded plugin."""
    name: str
    plugin_type: str
    instance: PluginInterface
    metadata: PluginMetadata
    loaded_at: datetime
    status: str
    config: Dict[str, Any]


class PluginManager:
    """
    Central manager for plugin lifecycle and operations.

    This class handles:
    - Plugin discovery and loading
    - Plugin initialization and configuration
    - Plugin lifecycle management
    - Hot-reload capabilities
    - Plugin dependency resolution
    """

    def __init__(self):
        """Initialize the plugin manager."""
        self.loaded_plugins: Dict[str, PluginInfo] = {}
        self.plugin_types: Dict[str, Type[PluginInterface]] = {}
        self.plugin_directories: List[Path] = []

        # Default plugin directories
        self._setup_default_directories()

        logger.info("PluginManager initialized")

    def _setup_default_directories(self):
        """Set up default plugin directories."""
        base_dir = Path(__file__).parent.parent.parent.parent
        self.plugin_directories = [
            base_dir / "plugins",
            base_dir / "src" / "plugins",
            Path.home() / ".duckdb_financial" / "plugins"
        ]

        # Create directories if they don't exist
        for directory in self.plugin_directories:
            directory.mkdir(parents=True, exist_ok=True)

    def register_plugin_type(self, plugin_type: str, interface_class: Type[PluginInterface]):
        """
        Register a plugin type with its interface.

        Args:
            plugin_type: Type identifier for the plugin
            interface_class: Interface class for the plugin type
        """
        self.plugin_types[plugin_type] = interface_class
        logger.info(f"Registered plugin type: {plugin_type}")

    def add_plugin_directory(self, directory: Path):
        """
        Add a directory to search for plugins.

        Args:
            directory: Directory path to add
        """
        if directory not in self.plugin_directories:
            self.plugin_directories.append(directory)
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Added plugin directory: {directory}")

    def discover_plugins(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover available plugins in configured directories.

        Returns:
            Dictionary of discovered plugins by type
        """
        discovered_plugins = {}

        for directory in self.plugin_directories:
            if not directory.exists():
                continue

            # Look for plugin files
            for plugin_file in directory.glob("**/*.py"):
                if plugin_file.name.startswith('_'):
                    continue

                try:
                    plugin_info = self._analyze_plugin_file(plugin_file)
                    if plugin_info:
                        plugin_type = plugin_info['type']
                        if plugin_type not in discovered_plugins:
                            discovered_plugins[plugin_type] = {}

                        plugin_name = plugin_info['name']
                        discovered_plugins[plugin_type][plugin_name] = plugin_info

                except Exception as e:
                    logger.warning(f"Failed to analyze plugin file {plugin_file}: {e}")

        logger.info(f"Discovered {sum(len(plugins) for plugins in discovered_plugins.values())} plugins")
        return discovered_plugins

    def load_plugin(self, plugin_type: str, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load and initialize a plugin.

        Args:
            plugin_type: Type of plugin to load
            plugin_name: Name of the plugin to load
            config: Configuration for the plugin

        Returns:
            True if plugin loaded successfully
        """
        try:
            # Find plugin module
            plugin_module = self._find_plugin_module(plugin_type, plugin_name)
            if not plugin_module:
                logger.error(f"Plugin module not found: {plugin_type}.{plugin_name}")
                return False

            # Import plugin class
            plugin_class = self._import_plugin_class(plugin_module, plugin_name)
            if not plugin_class:
                logger.error(f"Plugin class not found: {plugin_name}")
                return False

            # Validate plugin implementation
            if not validate_plugin_implementation(plugin_class, plugin_type):
                logger.error(f"Plugin validation failed: {plugin_name}")
                return False

            # Create plugin instance
            plugin_instance = plugin_class()

            # Initialize plugin
            plugin_config = config or {}
            if not plugin_instance.initialize(plugin_config):
                logger.error(f"Plugin initialization failed: {plugin_name}")
                return False

            # Store plugin info
            plugin_info = PluginInfo(
                name=plugin_name,
                plugin_type=plugin_type,
                instance=plugin_instance,
                metadata=plugin_instance.metadata,
                loaded_at=datetime.now(),
                status='active',
                config=plugin_config
            )

            self.loaded_plugins[f"{plugin_type}.{plugin_name}"] = plugin_info

            logger.info(f"Plugin loaded successfully: {plugin_type}.{plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_type}.{plugin_name}: {e}")
            return False

    def unload_plugin(self, plugin_type: str, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            True if plugin unloaded successfully
        """
        plugin_key = f"{plugin_type}.{plugin_name}"

        if plugin_key not in self.loaded_plugins:
            logger.warning(f"Plugin not loaded: {plugin_key}")
            return False

        try:
            plugin_info = self.loaded_plugins[plugin_key]

            # Shutdown plugin
            if plugin_info.instance.shutdown():
                del self.loaded_plugins[plugin_key]
                logger.info(f"Plugin unloaded successfully: {plugin_key}")
                return True
            else:
                logger.error(f"Plugin shutdown failed: {plugin_key}")
                return False

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_key}: {e}")
            return False

    def reload_plugin(self, plugin_type: str, plugin_name: str) -> bool:
        """
        Reload a plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            True if plugin reloaded successfully
        """
        plugin_key = f"{plugin_type}.{plugin_name}"

        if plugin_key not in self.loaded_plugins:
            logger.warning(f"Plugin not loaded: {plugin_key}")
            return False

        # Get current config
        current_config = self.loaded_plugins[plugin_key].config

        # Unload and reload
        if self.unload_plugin(plugin_type, plugin_name):
            return self.load_plugin(plugin_type, plugin_name, current_config)

        return False

    def get_plugin(self, plugin_type: str, plugin_name: str) -> Optional[PluginInterface]:
        """
        Get a loaded plugin instance.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            Plugin instance or None if not found
        """
        plugin_key = f"{plugin_type}.{plugin_name}"
        plugin_info = self.loaded_plugins.get(plugin_key)

        return plugin_info.instance if plugin_info else None

    def get_loaded_plugins(self, plugin_type: Optional[str] = None) -> Dict[str, PluginInfo]:
        """
        Get information about loaded plugins.

        Args:
            plugin_type: Filter by plugin type (optional)

        Returns:
            Dictionary of loaded plugins
        """
        if plugin_type:
            return {
                name: info for name, info in self.loaded_plugins.items()
                if info.plugin_type == plugin_type
            }

        return self.loaded_plugins.copy()

    def get_plugin_status(self, plugin_type: str, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            Plugin status information or None if not found
        """
        plugin_key = f"{plugin_type}.{plugin_name}"
        plugin_info = self.loaded_plugins.get(plugin_key)

        if not plugin_info:
            return None

        return {
            'name': plugin_info.name,
            'type': plugin_info.plugin_type,
            'status': plugin_info.status,
            'loaded_at': plugin_info.loaded_at.isoformat(),
            'metadata': {
                'version': plugin_info.metadata.version,
                'description': plugin_info.metadata.description,
                'author': plugin_info.metadata.author
            }
        }

    def execute_plugin_method(self, plugin_type: str, plugin_name: str, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a method on a loaded plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin
            method_name: Name of method to execute
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method

        Returns:
            Result of method execution

        Raises:
            ValueError: If plugin not found or method doesn't exist
        """
        plugin = self.get_plugin(plugin_type, plugin_name)
        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_type}.{plugin_name}")

        if not hasattr(plugin, method_name):
            raise ValueError(f"Plugin method not found: {method_name}")

        method = getattr(plugin, method_name)
        if not callable(method):
            raise ValueError(f"Plugin attribute is not callable: {method_name}")

        try:
            return method(*args, **kwargs)
        except Exception as e:
            logger.error(f"Plugin method execution failed: {plugin_type}.{plugin_name}.{method_name}: {e}")
            raise

    def validate_all_plugins(self) -> Dict[str, bool]:
        """
        Validate all loaded plugins.

        Returns:
            Dictionary mapping plugin names to validation status
        """
        validation_results = {}

        for plugin_key, plugin_info in self.loaded_plugins.items():
            try:
                is_valid = validate_plugin_implementation(
                    plugin_info.instance,
                    plugin_info.plugin_type
                )
                validation_results[plugin_key] = is_valid

                if not is_valid:
                    logger.warning(f"Plugin validation failed: {plugin_key}")

            except Exception as e:
                logger.error(f"Plugin validation error for {plugin_key}: {e}")
                validation_results[plugin_key] = False

        return validation_results

    def _find_plugin_module(self, plugin_type: str, plugin_name: str) -> Optional[str]:
        """
        Find the module path for a plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            Module path or None if not found
        """
        # Try different naming conventions
        possible_names = [
            f"plugins.{plugin_type}.{plugin_name}",
            f"plugins.{plugin_name}",
            f"{plugin_type}.{plugin_name}",
            plugin_name
        ]

        for module_name in possible_names:
            try:
                importlib.import_module(module_name)
                return module_name
            except ImportError:
                continue

        return None

    def _import_plugin_class(self, module_name: str, plugin_name: str) -> Optional[Type[PluginInterface]]:
        """
        Import plugin class from module.

        Args:
            module_name: Name of the module
            plugin_name: Name of the plugin

        Returns:
            Plugin class or None if not found
        """
        try:
            module = importlib.import_module(module_name)

            # Look for plugin class
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, PluginInterface) and
                    not inspect.isabstract(obj)):
                    return obj

            # Try class name based on plugin name
            class_name = self._camel_case(plugin_name) + "Plugin"
            if hasattr(module, class_name):
                plugin_class = getattr(module, class_name)
                if (inspect.isclass(plugin_class) and
                    issubclass(plugin_class, PluginInterface)):
                    return plugin_class

        except Exception as e:
            logger.error(f"Failed to import plugin class: {e}")

        return None

    def _analyze_plugin_file(self, plugin_file: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a plugin file to extract metadata.

        Args:
            plugin_file: Path to plugin file

        Returns:
            Plugin information or None if analysis fails
        """
        try:
            # This is a simplified analysis - in practice, you might
            # want to actually import and inspect the module
            module_name = self._get_module_name_from_path(plugin_file)

            # Extract plugin type from directory structure
            plugin_type = self._extract_plugin_type_from_path(plugin_file)

            if not plugin_type:
                return None

            return {
                'name': plugin_file.stem,
                'type': plugin_type,
                'module': module_name,
                'path': str(plugin_file),
                'discovered_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.warning(f"Failed to analyze plugin file {plugin_file}: {e}")
            return None

    def _get_module_name_from_path(self, plugin_file: Path) -> str:
        """
        Get module name from file path.

        Args:
            plugin_file: Plugin file path

        Returns:
            Module name
        """
        # Simplified module name generation
        return plugin_file.stem

    def _extract_plugin_type_from_path(self, plugin_file: Path) -> Optional[str]:
        """
        Extract plugin type from file path.

        Args:
            plugin_file: Plugin file path

        Returns:
            Plugin type or None
        """
        # Check parent directory name
        parent_name = plugin_file.parent.name
        if parent_name in self.plugin_types:
            return parent_name

        # Check if filename contains type
        for plugin_type in self.plugin_types:
            if plugin_type in plugin_file.name:
                return plugin_type

        return None

    def _camel_case(self, snake_str: str) -> str:
        """
        Convert snake_case to CamelCase.

        Args:
            snake_str: String in snake_case

        Returns:
            String in CamelCase
        """
        return ''.join(word.capitalize() for word in snake_str.split('_'))

    def __len__(self) -> int:
        """Get number of loaded plugins."""
        return len(self.loaded_plugins)

    def __contains__(self, plugin_key: str) -> bool:
        """Check if plugin is loaded."""
        return plugin_key in self.loaded_plugins

    def __iter__(self):
        """Iterate over loaded plugin names."""
        return iter(self.loaded_plugins.keys())
