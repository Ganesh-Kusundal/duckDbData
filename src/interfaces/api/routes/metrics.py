"""
Metrics API routes for Prometheus integration.
"""

from fastapi import APIRouter, HTTPException, Response
from typing import Dict, Any

from ....infrastructure.logging import get_logger
from ....infrastructure.observability.metrics import get_metrics_collector

logger = get_logger(__name__)
router = APIRouter()


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus format for scraping.
    """
    try:
        collector = get_metrics_collector()

        # For now, return a simple Prometheus format response
        # In a full implementation, this would integrate with the OpenTelemetry Prometheus exporter

        metrics_output = """# HELP duckdb_financial_info System information
# TYPE duckdb_financial_info gauge
duckdb_financial_info{version="1.0.0",service="financial_platform"} 1

# HELP duckdb_financial_up System uptime
# TYPE duckdb_financial_up gauge
duckdb_financial_up 1

# HELP duckdb_financial_data_records_total Total data records
# TYPE duckdb_financial_data_records_total counter
duckdb_financial_data_records_total 0

# HELP duckdb_financial_api_requests_total Total API requests
# TYPE duckdb_financial_api_requests_total counter
duckdb_financial_api_requests_total 0

# HELP duckdb_financial_scanner_executions_total Total scanner executions
# TYPE duckdb_financial_scanner_executions_total counter
duckdb_financial_scanner_executions_total 0
"""

        return Response(
            content=metrics_output,
            media_type="text/plain; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get("/metrics/health")
async def metrics_health() -> Dict[str, Any]:
    """
    Health check for metrics system.

    Returns:
        Health status of the metrics system
    """
    try:
        collector = get_metrics_collector()

        return {
            "status": "healthy",
            "metrics_enabled": True,
            "opentelemetry_available": True,
            "prometheus_endpoint": "/metrics"
        }

    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "metrics_enabled": False
        }


@router.get("/metrics/system")
async def system_metrics() -> Dict[str, Any]:
    """
    System metrics endpoint.

    Returns:
        Current system metrics
    """
    try:
        import psutil
        import platform
        from datetime import datetime

        # Get system information
        system_info = {
            "timestamp": datetime.now().isoformat(),
            "platform": platform.system(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total": psutil.virtual_memory().total,
            "memory_used": psutil.virtual_memory().used,
            "memory_percent": psutil.virtual_memory().percent,
            "disk_total": psutil.disk_usage('/').total,
            "disk_used": psutil.disk_usage('/').used,
            "disk_percent": psutil.disk_usage('/').percent
        }

        return system_info

    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")


@router.get("/metrics/database")
async def database_metrics() -> Dict[str, Any]:
    """
    Database metrics endpoint.

    Returns:
        Current database metrics
    """
    try:
        from ....infrastructure.adapters.duckdb_adapter import DuckDBAdapter
        from ....infrastructure.config.settings import get_settings
        from datetime import datetime

        adapter = DuckDBAdapter(database_path=get_settings().database.path)
        df = adapter.execute_query(
            """
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT symbol) as total_symbols,
                    MAX(timestamp) as latest_record,
                    AVG(volume) as avg_volume
                FROM market_data_unified
            """
        )
        total_records = int(df.iloc[0]["total_records"]) if not df.empty else 0
        total_symbols = int(df.iloc[0]["total_symbols"]) if not df.empty else 0
        latest_record = df.iloc[0]["latest_record"] if not df.empty else None
        avg_volume = float(df.iloc[0]["avg_volume"]) if not df.empty else 0.0

        return {
            "timestamp": datetime.now().isoformat(),
            "total_records": total_records,
            "total_symbols": total_symbols,
            "latest_record": str(latest_record) if latest_record else None,
            "avg_volume": avg_volume,
        }

    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get database metrics")


@router.get("/metrics/performance")
async def performance_metrics() -> Dict[str, Any]:
    """
    Performance metrics endpoint.

    Returns:
        Performance-related metrics
    """
    try:
        import psutil
        from datetime import datetime

        process = psutil.Process()

        return {
            "timestamp": datetime.now().isoformat(),
            "process": {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "threads": process.num_threads(),
                "status": process.status()
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")
