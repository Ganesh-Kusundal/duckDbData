"""
API Routes Setup
Configure and include all API route modules
"""

import logging
from fastapi import APIRouter

from .routes import (
    market_data_router,
    analytics_router,
    scanner_router,
    health_router
)

logger = logging.getLogger(__name__)


def setup_routes(app):
    """
    Setup and include all API routes

    Args:
        app: FastAPI application instance
    """
    # Create main API router with prefix
    api_router = APIRouter(prefix="/api/v1")

    # Include route modules
    api_router.include_router(
        market_data_router,
        prefix="/market-data",
        tags=["Market Data"]
    )

    api_router.include_router(
        analytics_router,
        prefix="/analytics",
        tags=["Analytics"]
    )

    api_router.include_router(
        scanner_router,
        prefix="/scanner",
        tags=["Scanner"]
    )

    api_router.include_router(
        health_router,
        prefix="/health",
        tags=["Health"]
    )

    # Include the main API router in the app
    app.include_router(api_router)

    logger.info("✅ API routes configured")

    # Log available endpoints
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append(f"{list(route.methods)[0]} {route.path}")

    logger.info(f"📋 Available endpoints: {len(routes)}")
    for route in sorted(routes):
        logger.debug(f"  {route}")


def create_market_data_routes():
    """
    Create market data specific routes
    Consolidates routes from analytics and trade_engine modules
    """
    from .market_data_routes import router
    return router


def create_analytics_routes():
    """
    Create analytics specific routes
    Consolidates routes from analytics module
    """
    from .analytics_routes import router
    return router


def create_scanner_routes():
    """
    Create scanner specific routes
    Consolidates routes from scanner module
    """
    from .scanner_routes import router
    return router


def create_health_routes():
    """
    Create health check routes
    System monitoring and diagnostics
    """
    from .health_routes import router
    return router
