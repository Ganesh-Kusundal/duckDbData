#!/usr/bin/env python3
"""
Unified Trading System Interface

Single entry point for running the complete trading system with all presentation interfaces:
- REST API
- CLI
- Web Dashboard
- WebSocket Server
- Health Monitoring
- Metrics Collection
"""

import asyncio
import logging
import argparse
import sys
from typing import List, Optional
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .presentation_manager import (
    get_presentation_manager, PresentationConfig, run_unified_system
)
from .api.main import run_api_server
from .cli.main import run_cli
from .dashboard.main import run_dashboard_server
from .websocket.main import run_websocket_server

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/trading_system.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)


def create_default_config() -> PresentationConfig:
    """Create default presentation configuration."""
    return PresentationConfig(
        api_host="0.0.0.0",
        api_port=8000,
        api_enable_docs=True,
        api_reload=False,

        cli_enable_completion=True,
        cli_rich_output=True,

        dashboard_host="0.0.0.0",
        dashboard_port=8080,
        dashboard_reload=False,

        websocket_host="0.0.0.0",
        websocket_port=8081,
        websocket_reload=False,

        enable_all_interfaces=True,
        enable_health_monitoring=True,
        enable_metrics=True,
        shutdown_timeout=30
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Unified Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all services
  python unified_main.py

  # Run only API and CLI
  python unified_main.py --services api cli

  # Run with custom ports
  python unified_main.py --api-port 8080 --dashboard-port 8081 --websocket-port 8082

  # Run in development mode
  python unified_main.py --reload --debug

  # Run specific service
  python unified_main.py --service api
  python unified_main.py --service cli
  python unified_main.py --service dashboard
  python unified_main.py --service websocket
        """
    )

    # Service selection
    parser.add_argument(
        '--services', '-s',
        nargs='+',
        choices=['api', 'cli', 'dashboard', 'websocket'],
        help='Services to run (default: all)'
    )

    parser.add_argument(
        '--service',
        choices=['api', 'cli', 'dashboard', 'websocket'],
        help='Run single service (alternative to --services)'
    )

    # API configuration
    parser.add_argument('--api-host', default='0.0.0.0', help='API server host')
    parser.add_argument('--api-port', type=int, default=8000, help='API server port')
    parser.add_argument('--no-api-docs', action='store_true', help='Disable API documentation')

    # Dashboard configuration
    parser.add_argument('--dashboard-host', default='0.0.0.0', help='Dashboard server host')
    parser.add_argument('--dashboard-port', type=int, default=8080, help='Dashboard server port')

    # WebSocket configuration
    parser.add_argument('--websocket-host', default='0.0.0.0', help='WebSocket server host')
    parser.add_argument('--websocket-port', type=int, default=8081, help='WebSocket server port')

    # Development options
    parser.add_argument('--reload', '-r', action='store_true', help='Enable auto-reload for development')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    # Health and monitoring
    parser.add_argument('--no-health', action='store_true', help='Disable health monitoring')
    parser.add_argument('--no-metrics', action='store_true', help='Disable metrics collection')

    # Logging
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Set logging level')
    parser.add_argument('--log-file', help='Log file path')

    return parser.parse_args()


async def run_single_service(service_name: str, config: PresentationConfig):
    """Run a single service directly."""
    logger.info(f"🚀 Starting {service_name} service...")

    if service_name == "api":
        run_api_server(
            host=config.api_host,
            port=config.api_port,
            reload=config.api_reload
        )
    elif service_name == "cli":
        run_cli()
    elif service_name == "dashboard":
        run_dashboard_server(
            host=config.dashboard_host,
            port=config.dashboard_port,
            reload=config.dashboard_reload
        )
    elif service_name == "websocket":
        run_websocket_server(
            host=config.websocket_host,
            port=config.websocket_port,
            reload=config.websocket_reload
        )
    else:
        logger.error(f"Unknown service: {service_name}")
        return

    logger.info(f"✅ {service_name} service completed")


def print_banner():
    """Print the system banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    🔄 UNIFIED TRADING SYSTEM                    ║
    ║                                                                      ║
    ║  Clean Architecture + CQRS + Domain-Driven Design                   ║
    ║  Multi-Interface Presentation Layer                                ║
    ║                                                                      ║
    ║  Services:                                                          ║
    ║  • REST API (FastAPI)                                              ║
    ║  • CLI (Typer + Rich)                                              ║
    ║  • Web Dashboard (FastAPI + Jinja2)                                ║
    ║  • WebSocket Server (Real-time data)                               ║
    ║  • Health Monitoring & Metrics                                     ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_service_status(services: List[str], config: PresentationConfig):
    """Print service status and endpoints."""
    print("\n📋 SERVICE ENDPOINTS:")
    print("=" * 50)

    if "api" in services:
        docs_status = "enabled" if config.api_enable_docs else "disabled"
        print(f"🌐 REST API:     http://{config.api_host}:{config.api_port}")
        print(f"📖 API Docs:     http://{config.api_host}:{config.api_port}/docs ({docs_status})")
        print(f"📋 API ReDoc:    http://{config.api_host}:{config.api_port}/redoc")

    if "dashboard" in services:
        print(f"🖥️  Dashboard:    http://{config.dashboard_host}:{config.dashboard_port}")

    if "websocket" in services:
        print(f"🔌 WebSocket:    ws://{config.websocket_host}:{config.websocket_port}")
        print(f"📡 WS Status:     http://{config.websocket_host}:{config.websocket_port}/stats")

    if "cli" in services:
        print("💻 CLI:          python unified_main.py --service cli")
        print("                   or: python -m src.interfaces.cli.main")

    print("\n🎯 SYSTEM FEATURES:")
    print("✅ Clean Architecture with CQRS")
    print("✅ Domain-Driven Design")
    print("✅ Infrastructure Layer (Messaging, Persistence, Caching)")
    print("✅ Multi-Broker Integration")
    print("✅ Real-time Market Data")
    print("✅ Technical Analysis & Scanning")
    print("✅ Risk Management")
    print("✅ Health Monitoring & Metrics")


async def main():
    """Main entry point for the unified trading system."""
    args = parse_arguments()

    # Configure logging
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)

    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logging.getLogger().addHandler(file_handler)

    # Create configuration
    config = create_default_config()
    config.api_host = args.api_host
    config.api_port = args.api_port
    config.api_enable_docs = not args.no_api_docs
    config.api_reload = args.reload

    config.dashboard_host = args.dashboard_host
    config.dashboard_port = args.dashboard_port
    config.dashboard_reload = args.reload

    config.websocket_host = args.websocket_host
    config.websocket_port = args.websocket_port
    config.websocket_reload = args.reload

    config.enable_health_monitoring = not args.no_health
    config.enable_metrics = not args.no_metrics

    # Determine services to run
    services = args.services
    if args.service:
        services = [args.service]
    if not services:
        services = ['api', 'dashboard', 'websocket']  # CLI is interactive, so not included by default

    # Print banner
    print_banner()

    try:
        if len(services) == 1:
            # Run single service directly
            logger.info(f"🎯 Running single service: {services[0]}")
            await run_single_service(services[0], config)
        else:
            # Run unified system
            logger.info(f"🎯 Starting unified system with services: {services}")
            print_service_status(services, config)

            result = await run_unified_system(config, services)

            if result["success"]:
                logger.info("✅ System shutdown completed successfully")
            else:
                logger.error("❌ System shutdown encountered issues")

    except KeyboardInterrupt:
        logger.info("👋 System interrupted by user")
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)

    # Run the unified system
    asyncio.run(main())
