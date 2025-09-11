"""
Dashboard Routes
Web routes for the unified dashboard interface
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse

from src.infrastructure.dependency_container import get_container as get_dependency_container
from src.application.services.market_data_application_service import MarketDataApplicationService

logger = logging.getLogger(__name__)
router = APIRouter()


def setup_dashboard_routes(app):
    """
    Setup and include dashboard routes

    Args:
        app: FastAPI application instance
    """
    # Include dashboard router
    app.include_router(router, prefix="", tags=["Dashboard"])

    # Main dashboard route
    @app.get("/", response_class=HTMLResponse)
    async def dashboard_home(request: Request):
        """Main dashboard page"""
        return await render_template(request, "dashboard.html", {
            "title": "Trading System Dashboard",
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    logger.info("✅ Dashboard routes configured")


async def render_template(request: Request, template_name: str, context: Optional[dict] = None):
    """
    Render HTML template with context

    Args:
        request: FastAPI request
        template_name: Name of template file
        context: Template context variables

    Returns:
        HTML response
    """
    if context is None:
        context = {}

    templates = getattr(request.app.state, 'templates', None)
    if templates is None:
        # Fallback HTML if templates not available
        return HTMLResponse(f"""
        <html>
        <head><title>{context.get('title', 'Dashboard')}</title></head>
        <body>
        <h1>{context.get('title', 'Dashboard')}</h1>
        <p>Dashboard templates not configured.</p>
        <p>Current time: {context.get('current_time', 'Unknown')}</p>
        </body>
        </html>
        """)

    # Render template with Jinja2
    return templates.TemplateResponse(template_name, {"request": request, **context})


@router.get("/market-data", response_class=HTMLResponse)
async def market_data_dashboard(request: Request):
    """
    Market data dashboard page
    """
    try:
        logger.info("Dashboard: Market data page requested")

        # Get recent market data for display
        container = await get_dependency_container().initialize()
        service = container.get(MarketDataApplicationService)

        # Mock data for now - in real implementation, get from service
        market_data = [
            {"symbol": "AAPL", "price": 152.34, "change": "+2.1%", "volume": "45.2M"},
            {"symbol": "MSFT", "price": 305.67, "change": "-0.8%", "volume": "32.1M"},
            {"symbol": "GOOGL", "price": 2845.50, "change": "+1.5%", "volume": "18.9M"}
        ]

        return await render_template(request, "market_data.html", {
            "title": "Market Data Dashboard",
            "market_data": market_data,
            "last_update": datetime.now().strftime("%H:%M:%S")
        })

    except Exception as e:
        logger.error(f"Error loading market data dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request):
    """
    Analytics dashboard page
    """
    try:
        logger.info("Dashboard: Analytics page requested")

        # Mock analytics data
        analytics_data = {
            "indicators": ["SMA", "EMA", "RSI", "MACD"],
            "anomaly_count": 12,
            "signal_accuracy": 73.5,
            "popular_symbols": ["AAPL", "MSFT", "GOOGL", "AMZN"]
        }

        return await render_template(request, "analytics.html", {
            "title": "Analytics Dashboard",
            "analytics_data": analytics_data
        })

    except Exception as e:
        logger.error(f"Error loading analytics dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scanner", response_class=HTMLResponse)
async def scanner_dashboard(request: Request):
    """
    Scanner dashboard page
    """
    try:
        logger.info("Dashboard: Scanner page requested")

        # Mock scanner data
        scanner_data = {
            "active_rules": 8,
            "signals_today": 156,
            "win_rate": 68.2,
            "top_rules": [
                {"name": "Momentum Breakout", "signals": 45, "accuracy": 72.3},
                {"name": "Volume Surge", "signals": 38, "accuracy": 65.8},
                {"name": "RSI Divergence", "signals": 32, "accuracy": 69.1}
            ]
        }

        return await render_template(request, "scanner.html", {
            "title": "Scanner Dashboard",
            "scanner_data": scanner_data
        })

    except Exception as e:
        logger.error(f"Error loading scanner dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system", response_class=HTMLResponse)
async def system_dashboard(request: Request):
    """
    System dashboard page
    """
    try:
        logger.info("Dashboard: System page requested")

        # Get system health data
        container = await get_dependency_container().initialize()
        service = container.get(MarketDataApplicationService)
        health_data = await service.get_market_health_status()

        # Add system metrics
        import psutil
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }

        return await render_template(request, "system.html", {
            "title": "System Dashboard",
            "health_data": health_data,
            "system_metrics": system_metrics
        })

    except Exception as e:
        logger.error(f"Error loading system dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/dashboard-data")
async def dashboard_api_data(
    data_type: str = Query("market_data", description="Type of data to retrieve"),
    limit: int = Query(10, description="Number of records to return")
):
    """
    API endpoint for dashboard data
    Provides JSON data for dashboard components
    """
    try:
        logger.info(f"Dashboard API: Getting {data_type} data")

        container = await get_dependency_container().initialize()
        service = container.get(MarketDataApplicationService)

        if data_type == "market_data":
            # Mock market data
            data = {
                "labels": ["09:00", "10:00", "11:00", "12:00", "13:00"],
                "datasets": [
                    {
                        "label": "AAPL",
                        "data": [150.2, 151.8, 152.4, 153.1, 152.8],
                        "borderColor": "rgb(75, 192, 192)"
                    },
                    {
                        "label": "MSFT",
                        "data": [302.1, 303.5, 305.2, 304.8, 305.6],
                        "borderColor": "rgb(255, 99, 132)"
                    }
                ]
            }

        elif data_type == "analytics":
            data = {
                "indicators": ["SMA", "EMA", "RSI"],
                "values": [152.34, 151.89, 68.5],
                "signals": ["BUY", "HOLD", "SELL"]
            }

        elif data_type == "scanner":
            data = {
                "signals": [
                    {"symbol": "AAPL", "rule": "momentum", "signal": "BUY", "confidence": 0.85},
                    {"symbol": "MSFT", "rule": "volume", "signal": "SELL", "confidence": 0.72}
                ]
            }

        else:
            data = {"error": f"Unknown data type: {data_type}"}

        return {
            "data_type": data_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting dashboard API data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
