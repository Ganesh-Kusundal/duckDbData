"""
Unified Dashboard Application
Consolidates dashboard components from all modules into a single web interface
"""

import logging
from pathlib import Path
from typing import Optional

# Try to import FastAPI dependencies, fallback to mock if not available
try:
    import uvicorn
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Mock classes for when FastAPI is not available
    class FastAPI:
        def __init__(self, **kwargs):
            self.state = type('State', (), {})()
            self.routes = []

        def add_middleware(self, *args, **kwargs):
            pass

        def get(self, path):
            def decorator(func):
                self.routes.append(f"GET {path}")
                return func
            return decorator

        def mount(self, *args, **kwargs):
            pass

    class HTTPException:
        def __init__(self, **kwargs):
            pass

    uvicorn = None

from .components import register_components
from .routes import setup_dashboard_routes

try:
    from src.infrastructure.dependency_container import get_container as get_dependency_container
except ImportError:
    def get_dependency_container():
        return type('MockContainer', (), {
            'initialize': lambda: None,
            'shutdown': lambda: None
        })()

logger = logging.getLogger(__name__)


def create_dashboard_app(
    static_dir: Optional[str] = None,
    template_dir: Optional[str] = None
) -> FastAPI:
    """
    Create and configure the unified dashboard application

    Args:
        static_dir: Directory for static files (CSS, JS, images)
        template_dir: Directory for HTML templates

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Trading System Dashboard",
        description="Unified Web Dashboard for Market Data, Analytics, and Trading",
        version="2.0.0"
    )

    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup static files
    if static_dir is None:
        static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Setup templates
    if template_dir is None:
        template_dir = Path(__file__).parent / "templates"
    if template_dir.exists():
        templates = Jinja2Templates(directory=str(template_dir))
    else:
        templates = None

    # Store templates in app state
    app.state.templates = templates

    # Setup dashboard routes
    setup_dashboard_routes(app)

    # Register components
    register_components(app)

    logger.info("✅ Unified Dashboard Application created")
    return app


def run_dashboard_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = False,
    static_dir: Optional[str] = None,
    template_dir: Optional[str] = None
):
    """
    Run the dashboard server with uvicorn

    Args:
        host: Server host
        port: Server port
        reload: Enable auto-reload for development
        static_dir: Directory for static files
        template_dir: Directory for HTML templates
    """
    app = create_dashboard_app(static_dir, template_dir)

    logger.info(f"🚀 Starting Dashboard server on {host}:{port}")

    uvicorn.run(
        "src.interfaces.dashboard.main:create_dashboard_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
        log_level="info"
    )


if __name__ == "__main__":
    run_dashboard_server()
