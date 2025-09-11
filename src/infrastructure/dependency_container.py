"""
Dependency Injection Container
Manages dependencies and implements dependency inversion principle
"""

import logging
from typing import Dict, Type, Any, Optional, Callable
from contextlib import asynccontextmanager
import asyncio

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Simple dependency injection container
    Manages object lifecycle and dependencies
    """

    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._transient_factories: Dict[str, Callable] = {}
        self._scopes: Dict[str, Dict[str, Any]] = {}

    def register_singleton(self, interface: Type, implementation: Any, name: Optional[str] = None):
        """
        Register a singleton instance

        Args:
            interface: Interface/abstract class
            implementation: Concrete implementation instance
            name: Optional name for multiple implementations
        """
        key = self._get_key(interface, name)
        self._singletons[key] = implementation
        logger.debug(f"Registered singleton: {key}")

    def register_factory(self, interface: Type, factory: Callable, name: Optional[str] = None):
        """
        Register a factory function for creating instances

        Args:
            interface: Interface/abstract class
            factory: Factory function that returns implementation
            name: Optional name for multiple implementations
        """
        key = self._get_key(interface, name)
        self._factories[key] = factory
        logger.debug(f"Registered factory: {key}")

    def register_transient(self, interface: Type, factory: Callable, name: Optional[str] = None):
        """
        Register a transient factory (new instance each time)

        Args:
            interface: Interface/abstract class
            factory: Factory function that returns implementation
            name: Optional name for multiple implementations
        """
        key = self._get_key(interface, name)
        self._transient_factories[key] = factory
        logger.debug(f"Registered transient: {key}")

    def resolve(self, interface: Type, name: Optional[str] = None) -> Any:
        """
        Resolve dependency

        Args:
            interface: Interface/abstract class to resolve
            name: Optional name for multiple implementations

        Returns:
            Resolved implementation

        Raises:
            ValueError: If dependency cannot be resolved
        """
        key = self._get_key(interface, name)

        # Try singletons first
        if key in self._singletons:
            return self._singletons[key]

        # Try factories
        if key in self._factories:
            instance = self._factories[key]()
            self._singletons[key] = instance  # Cache as singleton
            return instance

        # Try transient factories
        if key in self._transient_factories:
            return self._transient_factories[key]()

        raise ValueError(f"No registration found for {key}")

    @asynccontextmanager
    async def scope(self, scope_name: str):
        """
        Create a scoped container for request-specific dependencies

        Args:
            scope_name: Name of the scope
        """
        scope_data = {}
        self._scopes[scope_name] = scope_data

        try:
            yield ScopedContainer(self, scope_name)
        finally:
            # Cleanup scope
            del self._scopes[scope_name]

    def resolve_scoped(self, interface: Type, scope_name: str, name: Optional[str] = None) -> Any:
        """
        Resolve scoped dependency

        Args:
            interface: Interface/abstract class to resolve
            scope_name: Scope name
            name: Optional name for multiple implementations
        """
        if scope_name not in self._scopes:
            raise ValueError(f"Scope {scope_name} does not exist")

        key = self._get_key(interface, name)
        scope_data = self._scopes[scope_name]

        if key not in scope_data:
            # Create new instance for scope
            instance = self.resolve(interface, name)
            scope_data[key] = instance

        return scope_data[key]

    def _get_key(self, interface: Type, name: Optional[str] = None) -> str:
        """Generate key for dependency registration"""
        if name:
            return f"{interface.__name__}:{name}"
        return interface.__name__

    def clear(self):
        """Clear all registrations and instances"""
        self._singletons.clear()
        self._factories.clear()
        self._transient_factories.clear()
        self._scopes.clear()
        logger.info("Dependency container cleared")

    def get_registrations(self) -> Dict[str, str]:
        """Get all current registrations for debugging"""
        registrations = {}

        for key in self._singletons:
            registrations[key] = "singleton"

        for key in self._factories:
            registrations[key] = "factory"

        for key in self._transient_factories:
            registrations[key] = "transient"

        return registrations


class ScopedContainer:
    """
    Scoped container for request-specific dependencies
    """

    def __init__(self, container: DependencyContainer, scope_name: str):
        self.container = container
        self.scope_name = scope_name

    def resolve(self, interface: Type, name: Optional[str] = None) -> Any:
        """Resolve dependency within scope"""
        return self.container.resolve_scoped(interface, self.scope_name, name)


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get global dependency container"""
    global _container
    if _container is None:
        _container = DependencyContainer()
        logger.info("Created global dependency container")
    return _container


def reset_container():
    """Reset global container (mainly for testing)"""
    global _container
    if _container:
        _container.clear()
    _container = None
    logger.info("Reset global dependency container")


# Decorator for dependency injection
def inject(*dependencies):
    """
    Decorator to inject dependencies into functions/classes

    Usage:
        @inject(DatabaseAdapter, EventPublisher)
        def my_function(db_adapter, event_publisher):
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            container = get_container()

            # Inject dependencies
            injected_args = []
            for dep in dependencies:
                try:
                    injected_args.append(container.resolve(dep))
                except ValueError as e:
                    raise ValueError(f"Cannot inject dependency {dep.__name__}: {e}")

            # Call function with injected dependencies
            return func(*injected_args, *args, **kwargs)

        return wrapper
    return decorator


# Service locator pattern for simpler access
class ServiceLocator:
    """
    Service locator for accessing common services
    """

    @staticmethod
    def get_database_adapter():
        """Get database adapter"""
        return get_container().resolve('DuckDBAdapter')

    @staticmethod
    def get_broker_adapter():
        """Get broker adapter"""
        return get_container().resolve('BrokerAdapter')

    @staticmethod
    def get_event_publisher():
        """Get event publisher"""
        return get_container().resolve('EventPublisher')

    @staticmethod
    def get_market_data_repository():
        """Get market data repository"""
        return get_container().resolve('MarketDataRepository')
