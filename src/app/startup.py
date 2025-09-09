"""
Composition root for wiring ports and adapters.

Provides helpers to construct scanners and services with injected
dependencies (settings, repositories, event bus port, etc.).
"""

from typing import Optional

from src.infrastructure.config.settings import get_settings
from src.application.infrastructure.scanner_factory import ScannerFactory
from src.infrastructure.adapters.event_bus_adapter import EventBusAdapter
from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from src.infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository
from src.application.services.scanner_service import ScannerService
from src.application.services.data_service import DataService
from src.application.services.notification_service import NotificationService
from src.rules.mappers.breakout_mapper import RuleBasedBreakoutScanner
from src.rules.mappers.crp_mapper import RuleBasedCRPScanner
from src.rules.engine.rule_engine import RuleEngine
from src.rules.templates.breakout_rules import BreakoutRuleTemplates
from src.rules.templates.crp_rules import CRPRuleTemplates
from src.infrastructure.adapters.scanner_read_adapter import DuckDBScannerReadAdapter
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


def get_scanner_factory(db_path: Optional[str] = None) -> ScannerFactory:
    """Create a ScannerFactory with configured database path and config manager.

    Args:
        db_path: Optional override for database path.

    Returns:
        ScannerFactory instance.
    """
    settings = get_settings()
    return ScannerFactory(db_path=db_path or settings.database.path, config_manager=None)


def get_event_bus_port() -> EventBusAdapter:
    """Return an EventBusPort implementation bound to infra bus."""
    return EventBusAdapter()


def get_market_data_repo(db_path: str | None = None) -> DuckDBMarketDataRepository:
    settings = get_settings()
    adapter = DuckDBAdapter(database_path=db_path or settings.database.path)
    return DuckDBMarketDataRepository(adapter=adapter)


# Remove duplicate function - keep the improved one at the bottom


def build_application_services(db_path: str | None = None):
    """Wire core application services with ports/adapters.

    Returns a dict for convenience with constructed services.
    """
    repo = get_market_data_repo(db_path)
    bus = get_event_bus_port()
    # DataSyncService not present here; assume simple placeholder None
    data_service = DataService(market_data_repo=repo, event_bus=bus)
    # ScannerService expects a DataSyncService; construct with repo + bus if available
    try:
        from src.domain.services.data_sync_service import DataSyncService
        data_sync = DataSyncService(market_data_repo=repo, event_bus=bus)
    except Exception:
        data_sync = None  # Fallback if not available
    scanner_service = ScannerService(market_data_repo=repo, data_sync_service=data_sync, event_bus=bus)
    notifier = NotificationService(event_bus=bus)
    return {
        'market_data_repo': repo,
        'event_bus': bus,
        'data_service': data_service,
        'scanner_service': scanner_service,
        'notification_service': notifier,
    }


def get_scanner(name: str, db_path: str | None = None):
    """Convenience helper to construct rule-based scanners with injected dependencies.

    Supported names: 'enhanced_breakout', 'enhanced_crp', 'breakout', 'crp'

    Uses the new rule-based system with unified DuckDB integration for improved performance.
    """
    # Create unified adapter (default behavior)
    if db_path is None:
        settings = get_settings()
        db_path = settings.database.path  # Use unified database path

    # Initialize scanner adapter first to get unified manager
    scanner_adapter = DuckDBScannerReadAdapter(db_path=db_path)

    # Get database connection from unified manager
    db_connection = None
    if hasattr(scanner_adapter, 'unified_manager') and scanner_adapter.unified_manager:
        try:
            db_connection = scanner_adapter.unified_manager.connection_pool.get_connection()
        except Exception as e:
            logger.warning(f"Could not get database connection from unified manager: {e}")

    # Initialize rule engine with database connection
    rule_engine = RuleEngine(db_connection=db_connection)

    lname = name.lower()
    if lname in {"enhanced_breakout", "breakout"}:
        # Create rule-based breakout scanner
        scanner = RuleBasedBreakoutScanner(rule_engine)

        # Set scanner read adapter for the mapper
        if hasattr(scanner.rule_mapper, 'scanner_read'):
            scanner.rule_mapper.scanner_read = scanner_adapter

        return scanner

    elif lname in {"enhanced_crp", "crp"}:
        # Create rule-based CRP scanner
        scanner = RuleBasedCRPScanner(rule_engine)

        # Set scanner read adapter for the mapper
        if hasattr(scanner.rule_mapper, 'scanner_read'):
            scanner.rule_mapper.scanner_read = scanner_adapter

        return scanner

    raise ValueError(f"Unsupported scanner name: {name}. Supported: 'breakout', 'crp', 'enhanced_breakout', 'enhanced_crp'")
