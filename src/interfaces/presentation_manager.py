"""
Unified Presentation Layer Manager

Orchestrates and consolidates all presentation interfaces (API, CLI, Dashboard, WebSocket)
into a single cohesive system with unified configuration and lifecycle management.
"""

import asyncio
import logging
import signal
import threading
from typing import Dict, Any, List, Optional, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from ..infrastructure.infrastructure_initializer import (
    get_infrastructure_initializer, InfrastructureConfig, initialize_full_infrastructure
)
from ..application.cqrs_registry import get_cqrs_registry

logger = logging.getLogger(__name__)


@dataclass
class PresentationConfig:
    """Configuration for presentation layer components."""

    # API Server Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_enable_docs: bool = True
    api_reload: bool = False

    # CLI Configuration
    cli_enable_completion: bool = True
    cli_rich_output: bool = True

    # Dashboard Configuration
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8080
    dashboard_reload: bool = False
    dashboard_static_dir: Optional[str] = None
    dashboard_template_dir: Optional[str] = None

    # WebSocket Configuration
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8081
    websocket_reload: bool = False

    # Unified Configuration
    enable_all_interfaces: bool = False
    enable_health_monitoring: bool = True
    enable_metrics: bool = True
    shutdown_timeout: int = 30


class PresentationService:
    """Base class for presentation services."""

    def __init__(self, name: str, config: PresentationConfig):
        self.name = name
        self.config = config
        self._running = False
        self._server_thread: Optional[threading.Thread] = None
        self._shutdown_event = asyncio.Event()

    async def start(self) -> bool:
        """Start the presentation service."""
        raise NotImplementedError

    async def stop(self) -> bool:
        """Stop the presentation service."""
        raise NotImplementedError

    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service."""
        return {
            "service": self.name,
            "status": "running" if self._running else "stopped",
            "healthy": self._running
        }


class APIService(PresentationService):
    """API service wrapper."""

    def __init__(self, config: PresentationConfig):
        super().__init__("api", config)
        self.api_app = None
        self._server_task: Optional[asyncio.Task] = None

    async def start(self) -> bool:
        """Start the API service."""
        try:
            # Import here to avoid circular imports
            from .api.main import create_api_app, run_api_server

            logger.info(f"🚀 Starting API service on {self.config.api_host}:{self.config.api_port}")

            # Create API app
            self.api_app = create_api_app()

            # Run server in background thread to avoid blocking
            self._server_thread = threading.Thread(
                target=run_api_server,
                args=(self.config.api_host, self.config.api_port, self.config.api_reload),
                daemon=True
            )
            self._server_thread.start()

            self._running = True
            logger.info("✅ API service started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start API service: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the API service."""
        try:
            logger.info("🛑 Stopping API service")
            self._running = False

            if self._server_thread and self._server_thread.is_alive():
                # Note: In a real implementation, we'd need a way to gracefully shutdown uvicorn
                self._server_thread.join(timeout=5)

            logger.info("✅ API service stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop API service: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """API service health check."""
        base_health = await super().health_check()
        base_health.update({
            "host": self.config.api_host,
            "port": self.config.api_port,
            "docs_enabled": self.config.api_enable_docs,
            "endpoints": [
                "/health",
                "/docs",
                "/api/v1/market-data",
                "/api/v1/analytics",
                "/api/v1/scanner",
                "/api/v1/trading"
            ] if self._running else []
        })
        return base_health


class CLIService(PresentationService):
    """CLI service wrapper."""

    def __init__(self, config: PresentationConfig):
        super().__init__("cli", config)
        self.cli_app = None

    async def start(self) -> bool:
        """Start the CLI service."""
        try:
            logger.info("🚀 Starting CLI service")

            # Import here to avoid circular imports
            from .cli.main import cli_app

            self.cli_app = cli_app
            self._running = True

            logger.info("✅ CLI service started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start CLI service: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the CLI service."""
        try:
            logger.info("🛑 Stopping CLI service")
            self._running = False
            logger.info("✅ CLI service stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop CLI service: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """CLI service health check."""
        base_health = await super().health_check()
        base_health.update({
            "commands_available": [
                "status", "version", "market-data", "scanner", "analytics", "trading"
            ] if self._running else [],
            "completion_enabled": self.config.cli_enable_completion,
            "rich_output": self.config.cli_rich_output
        })
        return base_health


class DashboardService(PresentationService):
    """Dashboard service wrapper."""

    def __init__(self, config: PresentationConfig):
        super().__init__("dashboard", config)
        self.dashboard_app = None

    async def start(self) -> bool:
        """Start the dashboard service."""
        try:
            # Import here to avoid circular imports
            from .dashboard.main import create_dashboard_app, run_dashboard_server

            logger.info(f"🚀 Starting Dashboard service on {self.config.dashboard_host}:{self.config.dashboard_port}")

            # Create dashboard app
            self.dashboard_app = create_dashboard_app(
                self.config.dashboard_static_dir,
                self.config.dashboard_template_dir
            )

            # Run server in background thread
            self._server_thread = threading.Thread(
                target=run_dashboard_server,
                args=(
                    self.config.dashboard_host,
                    self.config.dashboard_port,
                    self.config.dashboard_reload,
                    self.config.dashboard_static_dir,
                    self.config.dashboard_template_dir
                ),
                daemon=True
            )
            self._server_thread.start()

            self._running = True
            logger.info("✅ Dashboard service started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start Dashboard service: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the dashboard service."""
        try:
            logger.info("🛑 Stopping Dashboard service")
            self._running = False

            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=5)

            logger.info("✅ Dashboard service stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop Dashboard service: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Dashboard service health check."""
        base_health = await super().health_check()
        base_health.update({
            "host": self.config.dashboard_host,
            "port": self.config.dashboard_port,
            "static_files": self.config.dashboard_static_dir is not None,
            "templates": self.config.dashboard_template_dir is not None,
            "routes": [
                "/", "/market-data", "/scanner", "/analytics", "/system"
            ] if self._running else []
        })
        return base_health


class WebSocketService(PresentationService):
    """WebSocket service wrapper."""

    def __init__(self, config: PresentationConfig):
        super().__init__("websocket", config)
        self.websocket_app = None
        self.connection_manager = None

    async def start(self) -> bool:
        """Start the WebSocket service."""
        try:
            # Import here to avoid circular imports
            from .websocket.main import create_websocket_app, run_websocket_server

            logger.info(f"🚀 Starting WebSocket service on {self.config.websocket_host}:{self.config.websocket_port}")

            # Create WebSocket app
            self.websocket_app = create_websocket_app()
            self.connection_manager = self.websocket_app.state.connection_manager

            # Run server in background thread
            self._server_thread = threading.Thread(
                target=run_websocket_server,
                args=(self.config.websocket_host, self.config.websocket_port, self.config.websocket_reload),
                daemon=True
            )
            self._server_thread.start()

            self._running = True
            logger.info("✅ WebSocket service started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start WebSocket service: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the WebSocket service."""
        try:
            logger.info("🛑 Stopping WebSocket service")
            self._running = False

            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=5)

            logger.info("✅ WebSocket service stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop WebSocket service: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """WebSocket service health check."""
        base_health = await super().health_check()

        connection_count = 0
        if self.connection_manager:
            try:
                connection_count = await self.connection_manager.get_active_connections_count()
            except Exception:
                connection_count = 0

        base_health.update({
            "host": self.config.websocket_host,
            "port": self.config.websocket_port,
            "active_connections": connection_count,
            "endpoints": [
                "/ws/market-data",
                "/ws/scanner",
                "/ws/trading"
            ] if self._running else []
        })
        return base_health


class PresentationManager:
    """
    Unified Presentation Layer Manager

    Orchestrates all presentation interfaces and provides unified management,
    monitoring, and configuration capabilities.
    """

    def __init__(self, config: PresentationConfig = None):
        self.config = config or PresentationConfig()
        self._services: Dict[str, PresentationService] = {}
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._health_monitor_task: Optional[asyncio.Task] = None

        # Initialize infrastructure
        self.infrastructure_config = InfrastructureConfig()
        self.infrastructure = get_infrastructure_initializer(self.infrastructure_config)

        # CQRS registry
        self.cqrs_registry = get_cqrs_registry()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def register_service(self, service: PresentationService):
        """Register a presentation service."""
        self._services[service.name] = service
        logger.info(f"Registered presentation service: {service.name}")

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the presentation manager and all services."""
        try:
            logger.info("🚀 Initializing Presentation Manager")

            # Initialize infrastructure
            infra_result = await initialize_full_infrastructure(self.infrastructure_config)
            if not infra_result["success"]:
                return infra_result

            # Create and register services
            if self.config.enable_all_interfaces or True:  # Enable all by default for demo
                self.register_service(APIService(self.config))
                self.register_service(CLIService(self.config))
                self.register_service(DashboardService(self.config))
                self.register_service(WebSocketService(self.config))

            logger.info(f"✅ Presentation Manager initialized with {len(self._services)} services")
            return {
                "success": True,
                "message": "Presentation Manager initialized successfully",
                "services_registered": list(self._services.keys())
            }

        except Exception as e:
            logger.error(f"Failed to initialize Presentation Manager: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Presentation Manager initialization failed"
            }

    async def start_services(self, services: List[str] = None) -> Dict[str, Any]:
        """Start presentation services."""
        if services is None:
            services = list(self._services.keys())

        results = {}
        started_services = []

        logger.info(f"🚀 Starting presentation services: {services}")

        for service_name in services:
            if service_name in self._services:
                service = self._services[service_name]
                success = await service.start()
                results[service_name] = success

                if success:
                    started_services.append(service_name)
                    logger.info(f"✅ {service_name} service started")
                else:
                    logger.error(f"❌ {service_name} service failed to start")
            else:
                results[service_name] = False
                logger.warning(f"Service {service_name} not found")

        # Start health monitoring
        if self.config.enable_health_monitoring:
            self._health_monitor_task = asyncio.create_task(self._health_monitor())

        self._running = True

        return {
            "success": len(started_services) > 0,
            "services_started": started_services,
            "services_failed": [s for s in services if not results.get(s, False)],
            "total_services": len(self._services)
        }

    async def stop_services(self, services: List[str] = None) -> Dict[str, Any]:
        """Stop presentation services."""
        if services is None:
            services = list(self._services.keys())

        # Stop health monitoring
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

        results = {}
        stopped_services = []

        logger.info(f"🛑 Stopping presentation services: {services}")

        for service_name in services:
            if service_name in self._services:
                service = self._services[service_name]
                success = await service.stop()
                results[service_name] = success

                if success:
                    stopped_services.append(service_name)
                    logger.info(f"✅ {service_name} service stopped")
                else:
                    logger.error(f"❌ {service_name} service failed to stop")

        self._running = False

        # Stop infrastructure
        await self.infrastructure.stop_services()

        return {
            "success": len(stopped_services) > 0,
            "services_stopped": stopped_services,
            "services_failed": [s for s in services if not results.get(s, False)]
        }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of all services."""
        health_status = {
            "timestamp": asyncio.get_event_loop().time(),
            "presentation_manager": {
                "status": "running" if self._running else "stopped",
                "services_registered": len(self._services),
                "health_monitoring": self.config.enable_health_monitoring
            },
            "services": {}
        }

        # Get infrastructure health
        try:
            infra_health = await self.infrastructure.get_health_status()
            health_status["infrastructure"] = infra_health
        except Exception as e:
            health_status["infrastructure"] = {"error": str(e)}

        # Get service health
        for service_name, service in self._services.items():
            try:
                service_health = await service.health_check()
                health_status["services"][service_name] = service_health
            except Exception as e:
                health_status["services"][service_name] = {
                    "service": service_name,
                    "status": "error",
                    "error": str(e)
                }

        # Overall health assessment
        service_statuses = [s.get("status", "unknown") for s in health_status["services"].values()]
        infra_status = health_status["infrastructure"].get("overall_health", "unknown")

        if all(s in ["running", "healthy"] for s in service_statuses) and infra_status in ["healthy"]:
            overall_health = "healthy"
        elif any(s in ["error", "unhealthy"] for s in service_statuses) or infra_status in ["unhealthy"]:
            overall_health = "unhealthy"
        else:
            overall_health = "degraded"

        health_status["overall_health"] = overall_health

        return health_status

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        try:
            system_metrics = await self.infrastructure.get_system_metrics()

            # Add presentation layer metrics
            system_metrics["presentation"] = {
                "services_running": len([s for s in self._services.values() if s.is_running()]),
                "total_services": len(self._services),
                "health_monitoring_enabled": self.config.enable_health_monitoring,
                "metrics_enabled": self.config.enable_metrics
            }

            # Add CQRS metrics
            cqrs_stats = self.cqrs_registry.get_registry_stats()
            system_metrics["cqrs"] = cqrs_stats

            return system_metrics

        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}

    async def _health_monitor(self):
        """Background health monitoring task."""
        logger.info("🏥 Starting presentation layer health monitoring")

        while self._running:
            try:
                # Perform health checks
                health_status = await self.get_health_status()

                # Log health issues
                if health_status["overall_health"] != "healthy":
                    logger.warning(f"Health check detected issues: {health_status['overall_health']}")

                # Could send alerts or take corrective action here

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(30)  # Wait before retry

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self._shutdown_event.set()

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()

    @asynccontextmanager
    async def manage_lifecycle(self):
        """Context manager for presentation lifecycle."""
        try:
            await self.initialize()
            await self.start_services()
            yield self
        finally:
            await self.stop_services()

    def get_service(self, name: str) -> Optional[PresentationService]:
        """Get a specific service by name."""
        return self._services.get(name)

    def list_services(self) -> List[str]:
        """List all registered services."""
        return list(self._services.keys())

    def is_running(self) -> bool:
        """Check if presentation manager is running."""
        return self._running


# Global presentation manager instance
_presentation_manager: Optional[PresentationManager] = None


def get_presentation_manager(config: PresentationConfig = None) -> PresentationManager:
    """Get global presentation manager instance."""
    global _presentation_manager
    if _presentation_manager is None:
        _presentation_manager = PresentationManager(config)
    return _presentation_manager


def reset_presentation_manager():
    """Reset global presentation manager (mainly for testing)."""
    global _presentation_manager
    _presentation_manager = None


async def run_unified_system(
    config: PresentationConfig = None,
    services: List[str] = None
) -> Dict[str, Any]:
    """
    Run the complete unified presentation system.

    Args:
        config: Presentation configuration
        services: List of services to start (default: all)

    Returns:
        Startup results
    """
    manager = get_presentation_manager(config)

    async with manager.manage_lifecycle():
        logger.info("🎯 Unified Trading System is running!")
        logger.info("Available services:")
        for service_name in manager.list_services():
            service = manager.get_service(service_name)
            if service:
                status = "✅ Running" if service.is_running() else "⏸️  Stopped"
                logger.info(f"  - {service_name}: {status}")

        logger.info("\n📋 Service Endpoints:")
        if manager.get_service("api") and manager.get_service("api").is_running():
            logger.info(f"  - API: http://{config.api_host}:{config.api_port}")
            logger.info(f"  - API Docs: http://{config.api_host}:{config.api_port}/docs")

        if manager.get_service("dashboard") and manager.get_service("dashboard").is_running():
            logger.info(f"  - Dashboard: http://{config.dashboard_host}:{config.dashboard_port}")

        if manager.get_service("websocket") and manager.get_service("websocket").is_running():
            logger.info(f"  - WebSocket: ws://{config.websocket_host}:{config.websocket_port}")

        if manager.get_service("cli"):
            logger.info("  - CLI: python -m src.interfaces.cli.main")

        logger.info("\nPress Ctrl+C to stop the system")

        # Wait for shutdown
        await manager.wait_for_shutdown()

    return {"success": True, "message": "System shutdown complete"}
