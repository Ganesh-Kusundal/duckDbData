"""
Plugin Registry
===============

Central registry for managing plugin metadata, versions, and marketplace information.
Provides functionality for plugin versioning, dependency management, and marketplace features.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import json
from pathlib import Path

from .plugin_interfaces import PluginMetadata
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PluginRegistryEntry:
    """Entry in the plugin registry."""
    metadata: PluginMetadata
    registry_info: Dict[str, Any]
    registered_at: datetime
    last_updated: datetime
    download_count: int
    rating: Optional[float]
    tags: List[str]


class PluginRegistry:
    """
    Plugin registry for managing plugin metadata and marketplace information.

    This class provides functionality for:
    - Plugin registration and metadata management
    - Version tracking and compatibility
    - Dependency resolution
    - Marketplace features (ratings, downloads, etc.)
    - Plugin search and discovery
    """

    def __init__(self, registry_file: Optional[Path] = None):
        """
        Initialize plugin registry.

        Args:
            registry_file: Path to registry storage file
        """
        self.registry_file = registry_file or Path.home() / ".duckdb_financial" / "plugin_registry.json"
        self.entries: Dict[str, PluginRegistryEntry] = {}
        self._load_registry()

        logger.info("PluginRegistry initialized")

    def register_plugin(self, plugin_type: str, plugin_name: str,
                       metadata: PluginMetadata, **kwargs) -> bool:
        """
        Register a plugin in the registry.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin
            metadata: Plugin metadata
            **kwargs: Additional registry information

        Returns:
            True if registration successful
        """
        try:
            plugin_key = f"{plugin_type}.{plugin_name}"

            registry_info = {
                'plugin_type': plugin_type,
                'plugin_name': plugin_name,
                'version': metadata.version,
                'status': 'active',
                **kwargs
            }

            entry = PluginRegistryEntry(
                metadata=metadata,
                registry_info=registry_info,
                registered_at=datetime.now(),
                last_updated=datetime.now(),
                download_count=kwargs.get('download_count', 0),
                rating=kwargs.get('rating'),
                tags=kwargs.get('tags', [])
            )

            self.entries[plugin_key] = entry
            self._save_registry()

            logger.info(f"Plugin registered: {plugin_key} v{metadata.version}")
            return True

        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_type}.{plugin_name}: {e}")
            return False

    def unregister_plugin(self, plugin_type: str, plugin_name: str) -> bool:
        """
        Unregister a plugin from the registry.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            True if unregistration successful
        """
        plugin_key = f"{plugin_type}.{plugin_name}"

        if plugin_key in self.entries:
            del self.entries[plugin_key]
            self._save_registry()
            logger.info(f"Plugin unregistered: {plugin_key}")
            return True

        logger.warning(f"Plugin not found in registry: {plugin_key}")
        return False

    def get_plugin_info(self, plugin_type: str, plugin_name: str) -> Optional[PluginRegistryEntry]:
        """
        Get plugin information from registry.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            Plugin registry entry or None if not found
        """
        plugin_key = f"{plugin_type}.{plugin_name}"
        return self.entries.get(plugin_key)

    def list_plugins(self, plugin_type: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> Dict[str, PluginRegistryEntry]:
        """
        List plugins in the registry.

        Args:
            plugin_type: Filter by plugin type
            tags: Filter by tags

        Returns:
            Dictionary of matching plugins
        """
        plugins = self.entries.copy()

        # Filter by type
        if plugin_type:
            plugins = {
                key: entry for key, entry in plugins.items()
                if entry.registry_info['plugin_type'] == plugin_type
            }

        # Filter by tags
        if tags:
            filtered_plugins = {}
            for key, entry in plugins.items():
                if any(tag in entry.tags for tag in tags):
                    filtered_plugins[key] = entry
            plugins = filtered_plugins

        return plugins

    def search_plugins(self, query: str, plugin_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search plugins by name, description, or author.

        Args:
            query: Search query
            plugin_type: Filter by plugin type

        Returns:
            List of matching plugins with metadata
        """
        results = []
        query_lower = query.lower()

        for plugin_key, entry in self.entries.items():
            if plugin_type and entry.registry_info['plugin_type'] != plugin_type:
                continue

            # Search in name, description, and author
            searchable_text = (
                entry.metadata.name +
                entry.metadata.description +
                entry.metadata.author
            ).lower()

            if query_lower in searchable_text:
                results.append({
                    'plugin_key': plugin_key,
                    'metadata': {
                        'name': entry.metadata.name,
                        'version': entry.metadata.version,
                        'description': entry.metadata.description,
                        'author': entry.metadata.author
                    },
                    'registry_info': entry.registry_info,
                    'tags': entry.tags,
                    'rating': entry.rating,
                    'download_count': entry.download_count
                })

        return results

    def update_plugin_metadata(self, plugin_type: str, plugin_name: str,
                              metadata: PluginMetadata) -> bool:
        """
        Update plugin metadata.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin
            metadata: Updated metadata

        Returns:
            True if update successful
        """
        plugin_key = f"{plugin_type}.{plugin_name}"

        if plugin_key in self.entries:
            self.entries[plugin_key].metadata = metadata
            self.entries[plugin_key].last_updated = datetime.now()
            self._save_registry()
            logger.info(f"Plugin metadata updated: {plugin_key}")
            return True

        logger.warning(f"Plugin not found for metadata update: {plugin_key}")
        return False

    def increment_download_count(self, plugin_type: str, plugin_name: str) -> bool:
        """
        Increment download count for a plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            True if increment successful
        """
        plugin_key = f"{plugin_type}.{plugin_name}"

        if plugin_key in self.entries:
            self.entries[plugin_key].download_count += 1
            self._save_registry()
            return True

        return False

    def add_plugin_rating(self, plugin_type: str, plugin_name: str, rating: float) -> bool:
        """
        Add or update rating for a plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin
            rating: Rating value (0-5)

        Returns:
            True if rating update successful
        """
        plugin_key = f"{plugin_type}.{plugin_name}"

        if plugin_key in self.entries and 0 <= rating <= 5:
            self.entries[plugin_key].rating = rating
            self.entries[plugin_key].last_updated = datetime.now()
            self._save_registry()
            return True

        return False

    def add_plugin_tags(self, plugin_type: str, plugin_name: str, tags: List[str]) -> bool:
        """
        Add tags to a plugin.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin
            tags: List of tags to add

        Returns:
            True if tags added successfully
        """
        plugin_key = f"{plugin_type}.{plugin_name}"

        if plugin_key in self.entries:
            current_tags = set(self.entries[plugin_key].tags)
            current_tags.update(tags)
            self.entries[plugin_key].tags = list(current_tags)
            self.entries[plugin_key].last_updated = datetime.now()
            self._save_registry()
            return True

        return False

    def get_plugin_dependencies(self, plugin_type: str, plugin_name: str) -> List[str]:
        """
        Get plugin dependencies.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin

        Returns:
            List of plugin dependencies
        """
        plugin_key = f"{plugin_type}.{plugin_name}"
        entry = self.entries.get(plugin_key)

        if entry and entry.metadata.dependencies:
            return entry.metadata.dependencies

        return []

    def check_plugin_compatibility(self, plugin_type: str, plugin_name: str,
                                 target_version: str) -> Dict[str, Any]:
        """
        Check plugin compatibility with a target version.

        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin
            target_version: Target version to check compatibility with

        Returns:
            Compatibility information
        """
        plugin_key = f"{plugin_type}.{plugin_name}"
        entry = self.entries.get(plugin_key)

        if not entry:
            return {'compatible': False, 'reason': 'Plugin not found'}

        # Simple version compatibility check (can be enhanced)
        plugin_version = entry.metadata.version

        # For now, assume same major version is compatible
        plugin_major = plugin_version.split('.')[0]
        target_major = target_version.split('.')[0]

        compatible = plugin_major == target_major

        return {
            'compatible': compatible,
            'plugin_version': plugin_version,
            'target_version': target_version,
            'reason': 'Version mismatch' if not compatible else 'Compatible'
        }

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        total_plugins = len(self.entries)
        plugin_types = {}

        for entry in self.entries.values():
            ptype = entry.registry_info['plugin_type']
            plugin_types[ptype] = plugin_types.get(ptype, 0) + 1

        total_downloads = sum(entry.download_count for entry in self.entries.values())
        avg_rating = (
            sum(entry.rating for entry in self.entries.values() if entry.rating)
            / sum(1 for entry in self.entries.values() if entry.rating)
            if any(entry.rating for entry in self.entries.values())
            else 0
        )

        return {
            'total_plugins': total_plugins,
            'plugin_types': plugin_types,
            'total_downloads': total_downloads,
            'average_rating': round(avg_rating, 2) if avg_rating else 0,
            'last_updated': datetime.now().isoformat()
        }

    def export_registry(self, export_path: Path) -> bool:
        """
        Export registry to a file.

        Args:
            export_path: Path to export registry

        Returns:
            True if export successful
        """
        try:
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'stats': self.get_registry_stats(),
                'plugins': {}
            }

            for plugin_key, entry in self.entries.items():
                export_data['plugins'][plugin_key] = {
                    'metadata': {
                        'name': entry.metadata.name,
                        'version': entry.metadata.version,
                        'description': entry.metadata.description,
                        'author': entry.metadata.author,
                        'license': entry.metadata.license,
                        'homepage': entry.metadata.homepage,
                        'repository': entry.metadata.repository,
                        'dependencies': entry.metadata.dependencies
                    },
                    'registry_info': entry.registry_info,
                    'registered_at': entry.registered_at.isoformat(),
                    'last_updated': entry.last_updated.isoformat(),
                    'download_count': entry.download_count,
                    'rating': entry.rating,
                    'tags': entry.tags
                }

            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            logger.info(f"Registry exported to: {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export registry: {e}")
            return False

    def import_registry(self, import_path: Path) -> bool:
        """
        Import registry from a file.

        Args:
            import_path: Path to import registry from

        Returns:
            True if import successful
        """
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)

            # Clear current registry
            self.entries = {}

            # Import plugins
            for plugin_key, plugin_data in import_data.get('plugins', {}).items():
                metadata_dict = plugin_data['metadata']
                metadata = PluginMetadata(**metadata_dict)

                entry = PluginRegistryEntry(
                    metadata=metadata,
                    registry_info=plugin_data['registry_info'],
                    registered_at=datetime.fromisoformat(plugin_data['registered_at']),
                    last_updated=datetime.fromisoformat(plugin_data['last_updated']),
                    download_count=plugin_data['download_count'],
                    rating=plugin_data['rating'],
                    tags=plugin_data['tags']
                )

                self.entries[plugin_key] = entry

            self._save_registry()
            logger.info(f"Registry imported from: {import_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to import registry: {e}")
            return False

    def _load_registry(self):
        """Load registry from file."""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    registry_data = json.load(f)

                for plugin_key, plugin_data in registry_data.get('plugins', {}).items():
                    metadata_dict = plugin_data['metadata']
                    metadata = PluginMetadata(**metadata_dict)

                    entry = PluginRegistryEntry(
                        metadata=metadata,
                        registry_info=plugin_data['registry_info'],
                        registered_at=datetime.fromisoformat(plugin_data['registered_at']),
                        last_updated=datetime.fromisoformat(plugin_data['last_updated']),
                        download_count=plugin_data.get('download_count', 0),
                        rating=plugin_data.get('rating'),
                        tags=plugin_data.get('tags', [])
                    )

                    self.entries[plugin_key] = entry

                logger.info(f"Registry loaded from: {self.registry_file}")

        except Exception as e:
            logger.warning(f"Failed to load registry: {e}")

    def _save_registry(self):
        """Save registry to file."""
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)

            registry_data = {
                'last_saved': datetime.now().isoformat(),
                'plugins': {}
            }

            for plugin_key, entry in self.entries.items():
                registry_data['plugins'][plugin_key] = {
                    'metadata': {
                        'name': entry.metadata.name,
                        'version': entry.metadata.version,
                        'description': entry.metadata.description,
                        'author': entry.metadata.author,
                        'license': entry.metadata.license,
                        'homepage': entry.metadata.homepage,
                        'repository': entry.metadata.repository,
                        'dependencies': entry.metadata.dependencies
                    },
                    'registry_info': entry.registry_info,
                    'registered_at': entry.registered_at.isoformat(),
                    'last_updated': entry.last_updated.isoformat(),
                    'download_count': entry.download_count,
                    'rating': entry.rating,
                    'tags': entry.tags
                }

            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def __len__(self) -> int:
        """Get number of registered plugins."""
        return len(self.entries)

    def __contains__(self, plugin_key: str) -> bool:
        """Check if plugin is registered."""
        return plugin_key in self.entries

    def __iter__(self):
        """Iterate over registered plugin keys."""
        return iter(self.entries.keys())
