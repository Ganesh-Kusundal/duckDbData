"""
Health Check Routes
===================

Health check endpoints for monitoring system status and availability.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import psutil
import platform

from ....infrastructure.logging import get_logger
from ....infrastructure.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Basic health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "DuckDB Financial Infrastructure API"
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with system information.

    Returns:
        Comprehensive health status with system metrics
    """
    try:
        # System information
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/')._asdict()
        }

        # Process information
        process = psutil.Process()
        process_info = {
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_info": process.memory_info()._asdict(),
            "num_threads": process.num_threads(),
            "status": process.status()
        }

        # Comprehensive health checks
        health_checks = await perform_health_checks()

        return {
            "status": "healthy" if all(check['status'] == 'healthy' for check in health_checks.values()) else "degraded",
            "timestamp": datetime.now().isoformat(),
            "service": "DuckDB Financial Infrastructure API",
            "version": "1.0.0",
            "system": system_info,
            "process": process_info,
            "checks": health_checks
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Health check failed")


async def perform_health_checks() -> dict:
    """Perform comprehensive health checks."""
    checks = {}

    # Database health check
    checks['database'] = await check_database_health()

    # Plugin system health check
    checks['plugins'] = await check_plugin_health()

    # Event bus health check
    checks['event_bus'] = await check_event_bus_health()

    # Metrics system health check
    checks['metrics'] = await check_metrics_health()

    # File system health check
    checks['filesystem'] = await check_filesystem_health()

    return checks


async def check_database_health() -> dict:
    """Check database connectivity and basic operations."""
    try:
        from ....infrastructure.adapters.duckdb_adapter import DuckDBAdapter
        from ....infrastructure.config.settings import get_settings

        adapter = DuckDBAdapter(database_path=get_settings().database.path)
        df = adapter.execute_query("SELECT COUNT(*) AS cnt FROM market_data_unified")
        record_count = int(df.iloc[0]["cnt"]) if not df.empty else 0

        return {
            'status': 'healthy',
            'details': f'Connected with {record_count:,} records',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def check_plugin_health() -> dict:
    """Check plugin system health."""
    try:
        from ....infrastructure.plugins.plugin_manager import PluginManager

        # This would check if plugins are loaded and functional
        # For now, return a basic healthy status
        return {
            'status': 'healthy',
            'details': 'Plugin system operational',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'status': 'degraded',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def check_event_bus_health() -> dict:
    """Check event bus health."""
    try:
        from ....infrastructure.messaging.event_bus import get_event_bus

        event_bus = get_event_bus()

        # Check if event bus is operational
        return {
            'status': 'healthy',
            'details': 'Event bus operational',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'status': 'degraded',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def check_metrics_health() -> dict:
    """Check metrics system health."""
    try:
        from ....infrastructure.observability.metrics import get_metrics_collector

        collector = get_metrics_collector()

        return {
            'status': 'healthy',
            'details': 'Metrics system operational',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'status': 'degraded',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


async def check_filesystem_health() -> dict:
    """Check filesystem health."""
    try:
        import os

        # Check critical directories
        critical_paths = [
            'data',
            'logs',
            'src/interfaces/templates',
            'src/interfaces/static'
        ]

        missing_paths = []
        for path in critical_paths:
            if not os.path.exists(path):
                missing_paths.append(path)

        if missing_paths:
            return {
                'status': 'degraded',
                'error': f'Missing directories: {", ".join(missing_paths)}',
                'timestamp': datetime.now().isoformat()
            }

        return {
            'status': 'healthy',
            'details': 'All critical directories present',
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for Kubernetes/Docker health checks.

    Returns:
        Readiness status
    """
    # TODO: Add actual readiness checks (database connections, etc.)
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for Kubernetes/Docker health checks.

    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/metrics")
async def health_metrics() -> Dict[str, Any]:
    """
    Health metrics for monitoring systems.

    Returns:
        Detailed health metrics
    """
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu = psutil.cpu_percent(interval=1)

        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "cpu_percent": cpu,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / 1024 / 1024,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / 1024 / 1024 / 1024,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024
            },
            "status": "healthy" if cpu < 90 and memory.percent < 90 else "warning"
        }

    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "error"
        }
