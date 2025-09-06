"""
FastAPI Application
===================

Main FastAPI application for the DuckDB Financial Infrastructure.
Provides REST API endpoints for all platform functionality.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import structlog

from ...infrastructure.logging import get_logger
from ...infrastructure.config.settings import get_settings
from .routes import (
    health_router,
    market_data_router,
    scanner_router,
    plugin_router,
    system_router,
    metrics_router
)

logger = get_logger(__name__)
settings = get_settings()

# Configure templates
templates = Jinja2Templates(directory="src/interfaces/templates")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting DuckDB Financial Infrastructure API")
    yield
    # Shutdown
    logger.info("Shutting down DuckDB Financial Infrastructure API")


# Create FastAPI application
app = FastAPI(
    title="DuckDB Financial Infrastructure API",
    description="REST API for comprehensive financial data platform with plugin-based extensibility",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/interfaces/static"), name="static")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.

    Args:
        request: FastAPI request object
        exc: Exception that occurred

    Returns:
        JSON response with error details
    """
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Include routers
app.include_router(
    health_router,
    prefix="/health",
    tags=["Health"]
)

app.include_router(
    market_data_router,
    prefix="/api/v1/market-data",
    tags=["Market Data"]
)

app.include_router(
    scanner_router,
    prefix="/api/v1/scanners",
    tags=["Scanners"]
)

app.include_router(
    plugin_router,
    prefix="/api/v1/plugins",
    tags=["Plugins"]
)

app.include_router(
    system_router,
    prefix="/api/v1/system",
    tags=["System"]
)

app.include_router(
    metrics_router,
    prefix="/metrics",
    tags=["Metrics"]
)


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint providing API information.

    Returns:
        API information and available endpoints
    """
    return {
        "name": "DuckDB Financial Infrastructure API",
        "version": "1.0.0",
        "description": "REST API for comprehensive financial data platform",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "market_data": "/api/v1/market-data",
            "scanners": "/api/v1/scanners",
            "plugins": "/api/v1/plugins",
            "system": "/api/v1/system"
        }
    }


# API info endpoint
@app.get("/api/v1/info")
async def api_info():
    """
    API information endpoint.

    Returns:
        Detailed API information
    """
    return {
        "name": "DuckDB Financial Infrastructure API",
        "version": "1.0.0",
        "description": "REST API for comprehensive financial data platform",
        "features": [
            "Market Data Management",
            "Plugin-based Scanning",
            "Real-time Data Streaming",
            "Data Validation & Quality",
            "Event-driven Architecture",
            "Comprehensive Monitoring"
        ],
        "technologies": [
            "FastAPI",
            "DuckDB",
            "Pydantic v2",
            "RxPy",
            "OpenTelemetry"
        ]
    }


# Dashboard routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/market-data", response_class=HTMLResponse)
async def market_data_dashboard(request: Request):
    """Market data visualization dashboard."""
    return templates.TemplateResponse("market_data.html", {"request": request})


@app.get("/scanners", response_class=HTMLResponse)
async def scanner_dashboard(request: Request):
    """Scanner results dashboard."""
    return templates.TemplateResponse("scanners.html", {"request": request})


@app.get("/system", response_class=HTMLResponse)
async def system_dashboard(request: Request):
    """System monitoring dashboard."""
    return templates.TemplateResponse("system.html", {"request": request})


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Start the FastAPI server with uvicorn.

    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
    """
    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "src.interfaces.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
