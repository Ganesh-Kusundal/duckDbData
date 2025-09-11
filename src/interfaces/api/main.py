"""
Unified API Application
Consolidates all API endpoints into a single FastAPI application
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Try to import FastAPI dependencies, fallback to mock if not available
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Mock classes for when FastAPI is not available
    class FastAPI:
        def __init__(self, **kwargs):
            self.routes = []
            self.state = type('State', (), {})()

        def add_middleware(self, *args, **kwargs):
            pass

        def include_router(self, *args, **kwargs):
            pass

        def get(self, path):
            def decorator(func):
                self.routes.append(f"GET {path}")
                return func
            return decorator

        def exception_handler(self, exc_class):
            def decorator(func):
                return func
            return decorator

    class JSONResponse:
        def __init__(self, **kwargs):
            pass

from .middleware import setup_middleware
from .routes import setup_routes
try:
    from src.infrastructure.dependency_container import get_container as get_dependency_container
except ImportError:
    def get_dependency_container():
        return type('MockContainer', (), {
            'initialize': lambda: None,
            'shutdown': lambda: None
        })()

try:
    from src.infrastructure.messaging.event_types import DomainEvent
except ImportError:
    DomainEvent = type

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    logger.info("🚀 Starting Unified API Application")

    # Initialize dependency container
    container = get_dependency_container()

    # Store container in app state for dependency injection
    app.state.container = container

    # Initialize infrastructure components
    await container.initialize()

    logger.info("✅ API Application startup complete")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Unified API Application")
    await container.shutdown()
    logger.info("✅ API Application shutdown complete")


def create_api_app() -> FastAPI:
    """
    Create and configure the unified FastAPI application

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Trading System API",
        description="Unified API for Market Data, Analytics, Scanner, and Trading Operations",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Setup middleware
    setup_middleware(app)

    # Setup routes
    setup_routes(app)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors"""
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "path": str(request.url)
            }
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """API health check endpoint"""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "services": ["market_data", "analytics", "scanner", "trading"]
        }

    logger.info("✅ Unified API Application created")
    return app


def run_api_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Run the API server with uvicorn

    Args:
        host: Server host
        port: Server port
        reload: Enable auto-reload for development
    """
    app = create_api_app()

    logger.info(f"🚀 Starting API server on {host}:{port}")

    uvicorn.run(
        "src.interfaces.api.main:create_api_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
        log_level="info"
    )


if __name__ == "__main__":
    run_api_server()
