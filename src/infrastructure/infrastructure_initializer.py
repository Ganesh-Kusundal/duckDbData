"""
Infrastructure Initialization Module

Provides centralized initialization and configuration of all infrastructure components.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .messaging.event_store import get_event_store
from .caching.cache_manager import get_cache_manager
from .monitoring.metrics_collector import get_metrics_collector
from .external.broker_integration_adapter import get_broker_integration_manager
from .database.duckdb_adapter import DuckDBAdapter

logger = logging.getLogger(__name__)


class InfrastructureConfig:
    """Configuration for infrastructure components."""

    def __init__(self,
                 event_store_db_path: str = "data/events.duckdb",
                 cache_max_size: int = 1000,
                 metrics_collection_interval: int = 60,
                 main_db_path: str = "data/financial_data.duckdb"):
        self.event_store_db_path = event_store_db_path
        self.cache_max_size = cache_max_size
        self.metrics_collection_interval = metrics_collection_interval
        self.main_db_path = main_db_path


class InfrastructureInitializer:
    """
    Initializes and manages all infrastructure components.

    Provides a centralized way to start, stop, and monitor infrastructure services.
    """

    def __init__(self, config: InfrastructureConfig = None):
        self.config = config or InfrastructureConfig()
        self._initialized = False
        self._started = False

        # Component instances
        self.event_store = None
        self.cache_manager = None
        self.metrics_collector = None
        self.broker_manager = None
        self.main_database = None

    async def initialize(self) -> Dict[str, Any]:
        """Initialize all infrastructure components."""
        if self._initialized:
            return {"success": True, "message": "Already initialized"}

        try:
            logger.info("Initializing infrastructure components...")

            # Ensure data directory exists
            Path("data").mkdir(exist_ok=True)

            # Initialize main database
            self.main_database = DuckDBAdapter(self.config.main_db_path)
            logger.info("Main database initialized")

            # Initialize event store
            self.event_store = get_event_store(
                store_type="duckdb",
                db_path=self.config.event_store_db_path
            )
            await self.event_store.initialize()
            logger.info("Event store initialized")

            # Initialize cache manager
            from .caching.cache_manager import InMemoryCacheBackend
            cache_backend = InMemoryCacheBackend(max_size=self.config.cache_max_size)
            self.cache_manager = get_cache_manager(backend=cache_backend)
            logger.info("Cache manager initialized")

            # Initialize metrics collector
            self.metrics_collector = get_metrics_collector()
            logger.info("Metrics collector initialized")

            # Initialize broker integration manager
            self.broker_manager = get_broker_integration_manager()
            logger.info("Broker integration manager initialized")

            self._initialized = True

            logger.info("All infrastructure components initialized successfully")

            return {
                "success": True,
                "message": "Infrastructure initialized successfully",
                "components": {
                    "main_database": "initialized",
                    "event_store": "initialized",
                    "cache_manager": "initialized",
                    "metrics_collector": "initialized",
                    "broker_manager": "initialized"
                }
            }

        except Exception as e:
            logger.error(f"Failed to initialize infrastructure: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Infrastructure initialization failed"
            }

    async def start_services(self) -> Dict[str, Any]:
        """Start all infrastructure services."""
        if not self._initialized:
            return {"success": False, "error": "Infrastructure not initialized"}

        if self._started:
            return {"success": True, "message": "Services already started"}

        try:
            logger.info("Starting infrastructure services...")

            # Start metrics collection
            await self.metrics_collector.start()
            logger.info("Metrics collector started")

            # Record startup metrics
            self.metrics_collector.increment_counter("infrastructure.startup")
            self.metrics_collector.record_gauge("infrastructure.status", 1.0)

            self._started = True

            logger.info("All infrastructure services started successfully")

            return {
                "success": True,
                "message": "Infrastructure services started successfully",
                "services": {
                    "metrics_collector": "running"
                }
            }

        except Exception as e:
            logger.error(f"Failed to start infrastructure services: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start infrastructure services"
            }

    async def stop_services(self) -> Dict[str, Any]:
        """Stop all infrastructure services."""
        if not self._started:
            return {"success": True, "message": "Services already stopped"}

        try:
            logger.info("Stopping infrastructure services...")

            # Stop metrics collection
            await self.metrics_collector.stop()
            logger.info("Metrics collector stopped")

            # Record shutdown metrics
            self.metrics_collector.record_gauge("infrastructure.status", 0.0)
            self.metrics_collector.increment_counter("infrastructure.shutdown")

            self._started = False

            logger.info("All infrastructure services stopped successfully")

            return {
                "success": True,
                "message": "Infrastructure services stopped successfully"
            }

        except Exception as e:
            logger.error(f"Failed to stop infrastructure services: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to stop infrastructure services"
            }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all infrastructure components."""
        status = {
            "overall_health": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "components": {}
        }

        # Check main database
        try:
            if self.main_database:
                # Simple health check - try to execute a basic query
                await self.main_database.execute_query("SELECT 1 as health_check")
                status["components"]["main_database"] = {"status": "healthy"}
            else:
                status["components"]["main_database"] = {"status": "not_initialized"}
                status["overall_health"] = "degraded"
        except Exception as e:
            status["components"]["main_database"] = {"status": "unhealthy", "error": str(e)}
            status["overall_health"] = "unhealthy"

        # Check event store
        try:
            if self.event_store:
                count = await self.event_store.get_event_count()
                status["components"]["event_store"] = {
                    "status": "healthy",
                    "event_count": count
                }
            else:
                status["components"]["event_store"] = {"status": "not_initialized"}
                status["overall_health"] = "degraded"
        except Exception as e:
            status["components"]["event_store"] = {"status": "unhealthy", "error": str(e)}
            status["overall_health"] = "unhealthy"

        # Check cache manager
        try:
            if self.cache_manager:
                cache_stats = await self.cache_manager.get_stats()
                status["components"]["cache_manager"] = {
                    "status": "healthy",
                    "stats": cache_stats
                }
            else:
                status["components"]["cache_manager"] = {"status": "not_initialized"}
        except Exception as e:
            status["components"]["cache_manager"] = {"status": "unhealthy", "error": str(e)}

        # Check metrics collector
        try:
            if self.metrics_collector:
                metrics_stats = await self.metrics_collector.get_all_metrics_summary()
                status["components"]["metrics_collector"] = {
                    "status": "healthy" if self._started else "stopped",
                    "stats": {
                        "total_metrics": metrics_stats.get("total_metrics_stored", 0),
                        "is_running": metrics_stats.get("is_running", False)
                    }
                }
            else:
                status["components"]["metrics_collector"] = {"status": "not_initialized"}
        except Exception as e:
            status["components"]["metrics_collector"] = {"status": "unhealthy", "error": str(e)}

        # Check broker manager
        try:
            if self.broker_manager:
                broker_stats = self.broker_manager.get_connection_stats()
                status["components"]["broker_manager"] = {
                    "status": "healthy",
                    "stats": broker_stats
                }
            else:
                status["components"]["broker_manager"] = {"status": "not_initialized"}
        except Exception as e:
            status["components"]["broker_manager"] = {"status": "unhealthy", "error": str(e)}

        return status

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        try:
            metrics_summary = await self.metrics_collector.get_all_metrics_summary()
            cache_stats = await self.cache_manager.get_stats()
            event_stats = await self.event_store.get_event_statistics()

            return {
                "timestamp": asyncio.get_event_loop().time(),
                "system_metrics": metrics_summary,
                "cache_stats": cache_stats,
                "event_stats": event_stats,
                "infrastructure_status": await self.get_health_status()
            }

        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }

    async def cleanup_resources(self) -> Dict[str, Any]:
        """Clean up infrastructure resources."""
        try:
            logger.info("Cleaning up infrastructure resources...")

            # Clear cache
            if self.cache_manager:
                await self.cache_manager.clear()

            # Clear old metrics
            if self.metrics_collector:
                self.metrics_collector.clear_metrics()

            # Close database connections
            if self.main_database:
                # Note: DuckDBAdapter may not have a close method
                pass

            logger.info("Infrastructure resources cleaned up successfully")

            return {
                "success": True,
                "message": "Infrastructure resources cleaned up successfully"
            }

        except Exception as e:
            logger.error(f"Failed to cleanup infrastructure resources: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to cleanup infrastructure resources"
            }

    def is_initialized(self) -> bool:
        """Check if infrastructure is initialized."""
        return self._initialized

    def is_started(self) -> bool:
        """Check if services are started."""
        return self._started

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        await self.start_services()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_services()
        await self.cleanup_resources()


# Global infrastructure initializer instance
_infrastructure_initializer: Optional[InfrastructureInitializer] = None


def get_infrastructure_initializer(config: InfrastructureConfig = None) -> InfrastructureInitializer:
    """Get global infrastructure initializer instance."""
    global _infrastructure_initializer
    if _infrastructure_initializer is None:
        _infrastructure_initializer = InfrastructureInitializer(config)
    return _infrastructure_initializer


def reset_infrastructure_initializer():
    """Reset global infrastructure initializer (mainly for testing)."""
    global _infrastructure_initializer
    _infrastructure_initializer = None


async def initialize_full_infrastructure(config: InfrastructureConfig = None) -> Dict[str, Any]:
    """Convenience function to initialize complete infrastructure."""
    initializer = get_infrastructure_initializer(config)

    init_result = await initializer.initialize()
    if not init_result["success"]:
        return init_result

    start_result = await initializer.start_services()
    if not start_result["success"]:
        return start_result

    return {
        "success": True,
        "message": "Full infrastructure initialized and started",
        "details": {
            "initialization": init_result,
            "startup": start_result
        }
    }


async def get_infrastructure_status() -> Dict[str, Any]:
    """Get current infrastructure status."""
    initializer = get_infrastructure_initializer()
    if not initializer.is_initialized():
        return {
            "status": "not_initialized",
            "message": "Infrastructure has not been initialized"
        }

    health_status = await initializer.get_health_status()
    return {
        "status": "initialized" if initializer.is_initialized() else "not_initialized",
        "services_running": initializer.is_started(),
        "health": health_status
    }
