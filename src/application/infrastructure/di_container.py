"""
Dependency Injection Container - Manages Application Dependencies

This container follows the Dependency Injection pattern to manage
all application dependencies, promoting loose coupling and testability.

SOLID Principles:
- Single Responsibility: Only manages dependencies
- Open/Closed: New dependencies can be added without modifying existing code
- Liskov Substitution: Different implementations can be swapped
- Interface Segregation: Clean container interface
- Dependency Inversion: Depends on abstractions
"""

from typing import Dict, Any, Optional

from .scanner_factory import ScannerFactory
from ..domain.services.scanner_service import ScannerService
from ..scanners.scanner_runner import ScannerRunner
# Database connection will be handled directly by scanners
from ...infrastructure.config.config_manager import ConfigManager


class DIContainer:
    """
    Dependency Injection Container for the scanner application.

    This container manages the creation and lifecycle of all dependencies,
    allowing for easy testing and configuration management.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}

    def register(self, interface: type, implementation: type, singleton: bool = False) -> None:
        """
        Register a service implementation.

        Args:
            interface: Interface or service type
            implementation: Implementation class
            singleton: Whether to create as singleton
        """
        self._services[interface.__name__] = {
            'implementation': implementation,
            'singleton': singleton,
            'instance': None if not singleton else None
        }

    def resolve(self, interface: type, *args, **kwargs) -> Any:
        """
        Resolve a service instance.

        Args:
            interface: Interface to resolve
            *args: Positional arguments for constructor
            **kwargs: Keyword arguments for constructor

        Returns:
            Service instance
        """
        service_name = interface.__name__

        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not registered")

        service_config = self._services[service_name]

        if service_config['singleton'] and service_config['instance'] is not None:
            return service_config['instance']

        # Create new instance
        implementation = service_config['implementation']
        instance = implementation(*args, **kwargs)

        if service_config['singleton']:
            service_config['instance'] = instance

        return instance

    def register_instance(self, interface: type, instance: Any) -> None:
        """
        Register a pre-created instance.

        Args:
            interface: Interface type
            instance: Instance to register
        """
        self._services[interface.__name__] = {
            'implementation': type(instance),
            'singleton': True,
            'instance': instance
        }


class ScannerDIContainer(DIContainer):
    """
    Specialized DI container for scanner application.

    This container provides convenient methods for setting up
    the scanner application dependencies.
    """

    def __init__(self, db_path: Optional[str] = None, config_path: Optional[str] = None):
        """
        Initialize scanner DI container.

        Args:
            db_path: Path to database file
            config_path: Path to configuration file
        """
        super().__init__()

        # Register core infrastructure
        self._register_infrastructure(db_path, config_path)

        # Register domain services
        self._register_domain_services()

        # Register application services
        self._register_application_services()

    def _register_infrastructure(self, db_path: Optional[str], config_path: Optional[str]) -> None:
        """Register infrastructure services."""
        # Database connection will be handled directly by scanners
        # No singleton database manager needed

        # Config manager
        if config_path:
            config_manager = ConfigManager(config_path)
            self.register_instance(ConfigManager, config_manager)

    def _register_domain_services(self) -> None:
        """Register domain services."""
        from ..domain.services.scanner_service import ScannerService
        self.register(ScannerService, ScannerService, singleton=True)

    def _register_application_services(self) -> None:
        """Register application services."""
        from .scanner_factory import ScannerFactory
        from ..scanners.scanner_runner import ScannerRunner

        # Scanner factory depends on infrastructure
        self.register(ScannerFactory, ScannerFactory, singleton=True)

        # Register the Nifty500FilterScanner explicitly
        ScannerFactory.register_scanner(
            "nifty500_filter",
            "src.application.scanners.strategies.nifty500_filter_scanner.Nifty500FilterScanner"
        )
        print(f"[DEBUG] After explicit registration in DI: {ScannerFactory.SCANNER_REGISTRY.keys()}")

        # Scanner runner depends on factory and domain service
        self.register(ScannerRunner, ScannerRunner, singleton=True)

    def get_scanner_runner(self) -> ScannerRunner:
        """Get the scanner runner instance."""
        # Resolve dependencies
        scanner_service = self.resolve(ScannerService)

        # Create scanner factory with dependencies
        # Database connection will be handled directly by scanners
        scanner_factory = ScannerFactory(
            db_path="data/financial_data.duckdb",
            config_manager=self._get_config_manager()
        )

        # Create scanner runner
        return ScannerRunner(
            scanner_factory=scanner_factory,
            scanner_service=scanner_service
        )

    def _get_config_manager(self) -> Optional[ConfigManager]:
        """Get config manager if available."""
        try:
            return self.resolve(ConfigManager)
        except ValueError:
            return None


def get_container(db_path: Optional[str] = None, config_path: Optional[str] = None) -> ScannerDIContainer:
    """
    Create a new DI container instance (no singleton).

    Args:
        db_path: Path to database file
        config_path: Path to configuration file

    Returns:
        DI container instance
    """
    return ScannerDIContainer(db_path, config_path)


def get_scanner_runner(db_path: Optional[str] = None, config_path: Optional[str] = None) -> ScannerRunner:
    """
    Get scanner runner instance with dependencies resolved.

    Args:
        db_path: Path to database file
        config_path: Path to configuration file

    Returns:
        Scanner runner instance
    """
    container = get_container(db_path, config_path)
    return container.get_scanner_runner()
