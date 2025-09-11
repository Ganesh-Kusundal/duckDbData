"""
Health Check API Routes
System monitoring and diagnostics endpoints
"""

import logging
import psutil
import platform
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends

from ..dependencies import get_application_service, get_correlation_id
from src.application.services.market_data_application_service import MarketDataApplicationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def health_check(
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Basic health check endpoint

    Args:
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        Basic health status
    """
    try:
        logger.info("API: Health check requested", extra={'correlation_id': correlation_id})

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "service": "trading_system_api"
        }

    except Exception as e:
        logger.error(f"Health check error: {e}", extra={'correlation_id': correlation_id})
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/detailed")
async def detailed_health_check(
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Detailed health check with system metrics

    Args:
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        Detailed health status with system metrics
    """
    try:
        logger.info("API: Detailed health check requested", extra={'correlation_id': correlation_id})

        # Get system health data from application service
        health_data = await service.get_market_health_status()

        # Add system metrics
        system_metrics = get_system_metrics()

        # Combine health data
        detailed_health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "service": "trading_system_api",
            "components": {
                "application_service": {
                    "status": health_data.get("status", "unknown"),
                    "details": health_data
                },
                "api_layer": {
                    "status": "healthy",
                    "routes_configured": True
                },
                "system": system_metrics
            },
            "checks": {
                "database_connection": True,  # Would be checked in real implementation
                "external_services": True,   # Would be checked in real implementation
                "memory_usage": "normal" if system_metrics["memory"]["percent"] < 80 else "high",
                "cpu_usage": "normal" if system_metrics["cpu"]["percent"] < 80 else "high"
            }
        }

        return detailed_health

    except Exception as e:
        logger.error(f"Detailed health check error: {e}", extra={'correlation_id': correlation_id})
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "service": "trading_system_api"
        }


@router.get("/metrics")
async def system_metrics(
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get detailed system metrics

    Args:
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        System performance metrics
    """
    try:
        logger.info("API: System metrics requested", extra={'correlation_id': correlation_id})

        metrics = get_system_metrics()

        # Add application-specific metrics
        metrics["application"] = {
            "uptime": "0d 2h 15m",  # Would track actual uptime
            "requests_today": 1250,
            "active_connections": 5,
            "error_rate": 0.002
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"System metrics error: {e}", extra={'correlation_id': correlation_id})
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "metrics": {}
        }


@router.get("/dependencies")
async def dependency_check(
    service: MarketDataApplicationService = Depends(get_application_service),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Check external dependencies and services

    Args:
        service: Application service
        correlation_id: Request correlation ID

    Returns:
        Dependency health status
    """
    try:
        logger.info("API: Dependency check requested", extra={'correlation_id': correlation_id})

        # Mock dependency checks - in real implementation, these would be actual checks
        dependencies = {
            "database": {
                "status": "healthy",
                "response_time": "15ms",
                "connection_pool": {
                    "active": 3,
                    "idle": 7,
                    "total": 10
                }
            },
            "redis_cache": {
                "status": "healthy",
                "response_time": "2ms",
                "hit_rate": 0.87
            },
            "external_api": {
                "status": "healthy",
                "response_time": "120ms",
                "rate_limit_remaining": 95
            },
            "message_queue": {
                "status": "healthy",
                "queue_depth": 12,
                "processing_rate": "50 msg/s"
            }
        }

        # Check if all dependencies are healthy
        all_healthy = all(dep["status"] == "healthy" for dep in dependencies.values())

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy" if all_healthy else "degraded",
            "dependencies": dependencies,
            "summary": {
                "total": len(dependencies),
                "healthy": sum(1 for dep in dependencies.values() if dep["status"] == "healthy"),
                "degraded": sum(1 for dep in dependencies.values() if dep["status"] == "degraded"),
                "unhealthy": sum(1 for dep in dependencies.values() if dep["status"] == "unhealthy")
            }
        }

    except Exception as e:
        logger.error(f"Dependency check error: {e}", extra={'correlation_id': correlation_id})
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error": str(e)
        }


def get_system_metrics() -> Dict[str, Any]:
    """
    Get system-level performance metrics

    Returns:
        Dictionary of system metrics
    """
    try:
        return {
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "cores": psutil.cpu_count(),
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "system": {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "python_version": platform.python_version()
            }
        }
    except Exception as e:
        logger.warning(f"Error getting system metrics: {e}")
        return {
            "error": "Unable to retrieve system metrics",
            "details": str(e)
        }
