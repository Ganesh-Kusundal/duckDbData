"""
Dashboard Components
Reusable dashboard components and utilities
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def register_components(app):
    """
    Register dashboard components with the FastAPI app

    Args:
        app: FastAPI application instance
    """
    # Store components in app state for use in templates
    app.state.dashboard_components = {
        "navigation": get_navigation_component(),
        "market_data_table": get_market_data_table_component(),
        "analytics_chart": get_analytics_chart_component(),
        "scanner_signals": get_scanner_signals_component(),
        "system_health": get_system_health_component()
    }

    logger.info("✅ Dashboard components registered")


def get_navigation_component() -> Dict[str, Any]:
    """
    Get navigation component configuration

    Returns:
        Navigation component data
    """
    return {
        "brand": "Trading System",
        "version": "2.0.0",
        "menu_items": [
            {"name": "Dashboard", "url": "/", "icon": "dashboard"},
            {"name": "Market Data", "url": "/market-data", "icon": "trending_up"},
            {"name": "Analytics", "url": "/analytics", "icon": "analytics"},
            {"name": "Scanner", "url": "/scanner", "icon": "search"},
            {"name": "System", "url": "/system", "icon": "settings"}
        ]
    }


def get_market_data_table_component() -> Dict[str, Any]:
    """
    Get market data table component configuration

    Returns:
        Market data table component data
    """
    return {
        "title": "Market Data",
        "columns": [
            {"field": "symbol", "header": "Symbol", "sortable": True},
            {"field": "price", "header": "Price", "sortable": True, "format": "currency"},
            {"field": "change", "header": "Change", "sortable": True, "format": "percentage"},
            {"field": "volume", "header": "Volume", "sortable": True, "format": "number"},
            {"field": "timestamp", "header": "Last Update", "sortable": True, "format": "datetime"}
        ],
        "actions": [
            {"name": "View Details", "action": "view_details"},
            {"name": "Add to Watchlist", "action": "add_watchlist"}
        ]
    }


def get_analytics_chart_component() -> Dict[str, Any]:
    """
    Get analytics chart component configuration

    Returns:
        Analytics chart component data
    """
    return {
        "title": "Technical Analysis",
        "chart_types": ["line", "candlestick", "bar"],
        "indicators": [
            {"name": "SMA", "type": "moving_average", "periods": [20, 50, 200]},
            {"name": "EMA", "type": "exponential_ma", "periods": [12, 26]},
            {"name": "RSI", "type": "oscillator", "levels": [30, 70]},
            {"name": "MACD", "type": "momentum", "fast": 12, "slow": 26, "signal": 9}
        ],
        "timeframes": ["1D", "1H", "30m", "15m", "5m"],
        "features": ["zoom", "pan", "crosshair", "volume"]
    }


def get_scanner_signals_component() -> Dict[str, Any]:
    """
    Get scanner signals component configuration

    Returns:
        Scanner signals component data
    """
    return {
        "title": "Scanner Signals",
        "signal_types": [
            {"type": "BUY", "color": "green", "icon": "trending_up"},
            {"type": "SELL", "color": "red", "icon": "trending_down"},
            {"type": "HOLD", "color": "yellow", "icon": "horizontal_rule"},
            {"type": "WATCH", "color": "blue", "icon": "visibility"}
        ],
        "rules": [
            {"name": "Momentum Breakout", "category": "momentum"},
            {"name": "Volume Surge", "category": "volume"},
            {"name": "Price Gap", "category": "price_action"},
            {"name": "RSI Divergence", "category": "oscillator"}
        ],
        "filters": ["symbol", "rule", "signal_type", "confidence", "time_range"]
    }


def get_system_health_component() -> Dict[str, Any]:
    """
    Get system health component configuration

    Returns:
        System health component data
    """
    return {
        "title": "System Health",
        "metrics": [
            {"name": "CPU Usage", "type": "percentage", "threshold": {"warning": 70, "critical": 90}},
            {"name": "Memory Usage", "type": "percentage", "threshold": {"warning": 80, "critical": 95}},
            {"name": "Disk Usage", "type": "percentage", "threshold": {"warning": 85, "critical": 95}},
            {"name": "Response Time", "type": "milliseconds", "threshold": {"warning": 1000, "critical": 5000}}
        ],
        "services": [
            {"name": "API Server", "endpoint": "/health"},
            {"name": "Database", "endpoint": "/health/database"},
            {"name": "Cache", "endpoint": "/health/cache"},
            {"name": "Message Queue", "endpoint": "/health/queue"}
        ],
        "alerts": [
            {"level": "info", "message": "System running normally"},
            {"level": "warning", "message": "High memory usage detected"},
            {"level": "error", "message": "Database connection failed"}
        ]
    }


def create_market_data_widget(
    symbol: str,
    price: float,
    change: float,
    volume: int,
    timestamp: datetime
) -> Dict[str, Any]:
    """
    Create a market data widget for dashboard display

    Args:
        symbol: Trading symbol
        price: Current price
        change: Price change percentage
        volume: Trading volume
        timestamp: Last update timestamp

    Returns:
        Market data widget configuration
    """
    return {
        "type": "market_data_card",
        "symbol": symbol,
        "price": price,
        "change": change,
        "change_color": "green" if change >= 0 else "red",
        "volume": volume,
        "timestamp": timestamp.isoformat(),
        "formatted_price": ".2f",
        "formatted_change": "+.2f" if change >= 0 else ".2f",
        "formatted_volume": ","
    }


def create_analytics_widget(
    title: str,
    chart_type: str,
    data: List[Dict[str, Any]],
    indicators: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create an analytics widget for dashboard display

    Args:
        title: Widget title
        chart_type: Type of chart (line, bar, candlestick)
        data: Chart data points
        indicators: Technical indicators to display

    Returns:
        Analytics widget configuration
    """
    return {
        "type": "analytics_chart",
        "title": title,
        "chart_type": chart_type,
        "data": data,
        "indicators": indicators or [],
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": True},
                "tooltip": {"enabled": True}
            }
        }
    }


def create_scanner_widget(
    signals: List[Dict[str, Any]],
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a scanner widget for dashboard display

    Args:
        signals: List of scanner signals
        filters: Active filters

    Returns:
        Scanner widget configuration
    """
    return {
        "type": "scanner_signals",
        "signals": signals,
        "filters": filters or {},
        "total_signals": len(signals),
        "signal_counts": {
            "BUY": len([s for s in signals if s.get("signal") == "BUY"]),
            "SELL": len([s for s in signals if s.get("signal") == "SELL"]),
            "HOLD": len([s for s in signals if s.get("signal") == "HOLD"]),
            "WATCH": len([s for s in signals if s.get("signal") == "WATCH"])
        }
    }


def create_system_widget(
    health_status: str,
    metrics: Dict[str, Any],
    alerts: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create a system health widget for dashboard display

    Args:
        health_status: Overall system health status
        metrics: System metrics
        alerts: Active system alerts

    Returns:
        System widget configuration
    """
    return {
        "type": "system_health",
        "status": health_status,
        "status_color": {
            "healthy": "green",
            "warning": "yellow",
            "critical": "red",
            "unknown": "gray"
        }.get(health_status, "gray"),
        "metrics": metrics,
        "alerts": alerts or [],
        "last_update": datetime.now().isoformat()
    }


def get_dashboard_layout() -> Dict[str, Any]:
    """
    Get the default dashboard layout configuration

    Returns:
        Dashboard layout configuration
    """
    return {
        "layout": "grid",
        "columns": 12,
        "rows": 6,
        "widgets": [
            {
                "id": "market_data_table",
                "component": "market_data_table",
                "position": {"x": 0, "y": 0, "width": 8, "height": 3}
            },
            {
                "id": "analytics_chart",
                "component": "analytics_chart",
                "position": {"x": 8, "y": 0, "width": 4, "height": 3}
            },
            {
                "id": "scanner_signals",
                "component": "scanner_signals",
                "position": {"x": 0, "y": 3, "width": 6, "height": 2}
            },
            {
                "id": "system_health",
                "component": "system_health",
                "position": {"x": 6, "y": 3, "width": 6, "height": 2}
            }
        ],
        "responsive_breakpoints": {
            "lg": 1200,
            "md": 996,
            "sm": 768,
            "xs": 480
        }
    }
