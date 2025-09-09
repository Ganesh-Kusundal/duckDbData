"""
Scanner Factory - Factory Pattern for Scanner Creation

This factory creates scanner instances following the Factory pattern,
which allows for dynamic scanner instantiation based on configuration.

SOLID Principles:
- Single Responsibility: Only responsible for scanner creation
- Open/Closed: New scanners can be added without modifying existing code
- Liskov Substitution: All created scanners implement the same interface
- Interface Segregation: Clean factory interface
- Dependency Inversion: Depends on abstractions
"""

from typing import Dict, Any, Optional, Type
import importlib

from ..interfaces.base_scanner_interface import IBaseScanner
from .config.scanner_config import ScannerConfig
from src.infrastructure.config.settings import get_settings


class ScannerFactory:
    """
    Factory for creating scanner instances.

    This factory uses reflection to dynamically create scanner instances
    based on scanner names, following the Factory pattern.
    """

    # Registry of available scanners
    SCANNER_REGISTRY = {
        'breakout': 'src.application.scanners.strategies.breakout_scanner.BreakoutScanner',
        'enhanced_breakout': 'src.application.scanners.strategies.breakout_scanner.BreakoutScanner',
        'crp': 'src.application.scanners.strategies.crp_scanner.CRPScanner',
        'enhanced_crp': 'src.application.scanners.strategies.crp_scanner.CRPScanner',
        'technical': 'src.application.scanners.strategies.technical_scanner.TechnicalScanner',
        'nifty500_filter': 'src.application.scanners.strategies.nifty500_filter_scanner.Nifty500FilterScanner',
        'relative_volume': 'src.application.scanners.strategies.relative_volume_scanner.RelativeVolumeScanner',
        'simple_breakout': 'src.application.scanners.strategies.simple_breakout_scanner.SimpleBreakoutScanner',
    }
    print(f"[DEBUG] ScannerFactory.SCANNER_REGISTRY initialized: {SCANNER_REGISTRY.keys()}")

    def __init__(self, db_path: str = None, config_manager=None):
        """
        Initialize factory with dependencies.

        Args:
            db_path: Database file path
            config_manager: Configuration manager instance
        """
        settings = get_settings()
        self._db_path = db_path or settings.database.path
        self._config_manager = config_manager

    def create_scanner(self, scanner_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[IBaseScanner]:
        print(f"[DEBUG] create_scanner called for: {scanner_name}")
        """
        Create a scanner instance by name with proper port injection.

        Args:
            scanner_name: Name of the scanner to create
            config: Optional configuration overrides

        Returns:
            Scanner instance with ports injected or None if scanner not found
        """
        if scanner_name not in self.SCANNER_REGISTRY:
            print(f"[DEBUG] Scanner '{scanner_name}' not found in registry: {self.SCANNER_REGISTRY.keys()}")
            return None

        try:
            # Import scanner class dynamically
            module_path, class_name = self.SCANNER_REGISTRY[scanner_name].rsplit('.', 1)
            module = importlib.import_module(module_path)
            scanner_class = getattr(module, class_name)

            # Prepare scanner configuration
            scanner_config = self._prepare_config(scanner_name, config)

            # Create scanner with proper port injection based on scanner type
            if scanner_name.lower() in ['crp', 'enhanced_crp']:
                # CRP scanner requires ScannerReadPort injection
                from src.infrastructure.adapters.scanner_read_adapter import DuckDBScannerReadAdapter
                scanner_read_port = DuckDBScannerReadAdapter(database_path=self._db_path)
                return scanner_class(scanner_read_port=scanner_read_port, config=scanner_config)
            elif scanner_name.lower() in ['breakout', 'enhanced_breakout']:
                # Breakout scanner requires ScannerReadPort injection
                from src.infrastructure.adapters.scanner_read_adapter import DuckDBScannerReadAdapter
                scanner_read_port = DuckDBScannerReadAdapter(database_path=self._db_path)
                return scanner_class(scanner_read_port=scanner_read_port, config=scanner_config)
            else:
                # Legacy scanners that still use direct db_path
                return scanner_class(
                    db_path=self._db_path,
                    config_manager=self._config_manager,
                    config=scanner_config
                )

        except (ImportError, AttributeError) as e:
            print(f"[DEBUG] Error creating scanner {scanner_name}: {e}")
            return None
        except Exception as e:
            print(f"[DEBUG] Unexpected error creating scanner {scanner_name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_available_scanners(self) -> list[str]:
        """Get list of available scanner names."""
        return list(self.SCANNER_REGISTRY.keys())

    def get_scanner_config(self, scanner_name: str) -> Dict[str, Any]:
        """Get default configuration for a scanner."""
        return ScannerConfig.get_default_config(scanner_name)

    def validate_config(self, scanner_name: str, config: Dict[str, Any]) -> bool:
        """Validate configuration for a scanner."""
        return ScannerConfig.validate_config(scanner_name, config)

    def _prepare_config(self, scanner_name: str, custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare configuration by merging defaults with custom config."""
        default_config = self.get_scanner_config(scanner_name)

        if custom_config:
            # Merge custom config with defaults
            merged_config = default_config.copy()
            merged_config.update(custom_config)
            return merged_config

        return default_config

    @classmethod
    def register_scanner(cls, name: str, class_path: str) -> None:
        """
        Register a new scanner in the factory.

        Args:
            name: Scanner name
            class_path: Full module path to scanner class
        """
        cls.SCANNER_REGISTRY[name] = class_path

    @classmethod
    def unregister_scanner(cls, name: str) -> None:
        """
        Unregister a scanner from the factory.

        Args:
            name: Scanner name to remove
        """
        if name in cls.SCANNER_REGISTRY:
            del cls.SCANNER_REGISTRY[name]


