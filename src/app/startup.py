"""
Composition root for wiring ports and adapters.

Provides helpers to construct scanners and services with injected
dependencies (settings, repositories, event bus port, etc.).
"""

from typing import Optional, Union

try:
    from infrastructure.config.settings import get_settings
    from application.infrastructure.scanner_factory import ScannerFactory
    from infrastructure.adapters.event_bus_adapter import EventBusAdapter
    from infrastructure.adapters.duckdb_adapter import DuckDBAdapter
    from infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository
    from application.services.scanner_service import ScannerService
    from application.services.data_service import DataService
    from application.services.notification_service import NotificationService
    from rules.mappers.breakout_mapper import RuleBasedBreakoutScanner
    from rules.mappers.crp_mapper import RuleBasedCRPScanner
    from rules.engine.rule_engine import RuleEngine
    from rules.templates.breakout_rules import BreakoutRuleTemplates
    from rules.templates.crp_rules import CRPRuleTemplates
    from infrastructure.adapters.scanner_read_adapter import DuckDBScannerReadAdapter
    from infrastructure.logging import get_logger
except ImportError as e:
    # Fallback for when infrastructure dependencies are not available
    print(f"Warning: Some imports failed: {e}")
    get_settings = None
    ScannerFactory = None
    EventBusAdapter = None
    DuckDBAdapter = None
    DuckDBMarketDataRepository = None
    ScannerService = None
    DataService = None
    NotificationService = None
    RuleBasedBreakoutScanner = None
    RuleBasedCRPScanner = None
    RuleEngine = None
    BreakoutRuleTemplates = None
    CRPRuleTemplates = None
    DuckDBScannerReadAdapter = None
    get_logger = None

logger = get_logger(__name__) if get_logger else None


def get_scanner_factory(db_path: Optional[str] = None) -> ScannerFactory:
    """Create a ScannerFactory with configured database path and config manager.

    Args:
        db_path: Optional override for database path.

    Returns:
        ScannerFactory instance.
    """
    if ScannerFactory is None:
        raise ImportError("ScannerFactory not available - missing dependencies")

    if get_settings is None:
        # Fallback when settings not available
        return ScannerFactory(db_path=db_path, config_manager=None)
    else:
        settings = get_settings()
        return ScannerFactory(db_path=db_path or settings.database.path, config_manager=None)


def get_event_bus_port() -> EventBusAdapter:
    """Return an EventBusPort implementation bound to infra bus."""
    return EventBusAdapter()


def get_market_data_repo(db_path: Optional[str] = None) -> DuckDBMarketDataRepository:
    if DuckDBMarketDataRepository is None or DuckDBAdapter is None:
        raise ImportError("Database components not available - missing dependencies")

    if get_settings is None:
        # Fallback when settings not available
        if db_path is None:
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "..", "..", "data", "financial_data_with_data.duckdb")
            db_path = os.path.abspath(db_path)
        adapter = DuckDBAdapter(database_path=db_path)
    else:
        settings = get_settings()
        adapter = DuckDBAdapter(database_path=db_path or settings.database.path)

    return DuckDBMarketDataRepository(adapter=adapter)


# Remove duplicate function - keep the improved one at the bottom


def build_application_services(db_path: Optional[str] = None):
    """Wire core application services with ports/adapters.

    Returns a dict for convenience with constructed services.
    """
    services = {}

    try:
        repo = get_market_data_repo(db_path)
        services['market_data_repo'] = repo
    except ImportError:
        services['market_data_repo'] = None

    try:
        if EventBusAdapter is not None:
            bus = get_event_bus_port()
            services['event_bus'] = bus
        else:
            services['event_bus'] = None
    except Exception:
        services['event_bus'] = None

    # Data service
    try:
        if DataService is not None and services['market_data_repo'] is not None:
            data_service = DataService(market_data_repo=services['market_data_repo'], event_bus=services['event_bus'])
            services['data_service'] = data_service
        else:
            services['data_service'] = None
    except Exception:
        services['data_service'] = None

    # Scanner service
    try:
        if ScannerService is not None and services['market_data_repo'] is not None:
            # DataSyncService placeholder
            data_sync = None
            scanner_service = ScannerService(market_data_repo=services['market_data_repo'], data_sync_service=data_sync, event_bus=services['event_bus'])
            services['scanner_service'] = scanner_service
        else:
            services['scanner_service'] = None
    except Exception:
        services['scanner_service'] = None

    # Notification service
    try:
        if NotificationService is not None:
            notifier = NotificationService(event_bus=services['event_bus'])
            services['notification_service'] = notifier
        else:
            services['notification_service'] = None
    except Exception:
        services['notification_service'] = None

    return services


def get_scanner(name: str, db_path: Optional[str] = None):
    """Convenience helper to construct rule-based scanners with injected dependencies.

    Supported names: 'enhanced_breakout', 'enhanced_crp', 'breakout', 'crp'

    Uses the new rule-based system with unified DuckDB integration for improved performance.
    """
    # Create unified adapter (default behavior)
    if db_path is None:
        if get_settings is None:
            # Fallback to default path if settings not available
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "..", "..", "project", "data", "financial_data_with_data.duckdb")
            db_path = os.path.abspath(db_path)  # Ensure absolute path
        else:
            settings = get_settings()
            db_path = settings.database.path  # Use unified database path
            # Ensure the path from settings is also absolute
            import os
            if not os.path.isabs(db_path):
                # Use the project data directory - check if we're already in project directory
                current_dir = os.getcwd()
                if os.path.basename(current_dir) == "project":
                    # We're already in project directory, just use data subdirectory
                    db_path = os.path.join(current_dir, "data", "financial_data_with_data.duckdb")
                else:
                    # We're in parent directory, need to add project
                    db_path = os.path.join(current_dir, "project", "data", "financial_data_with_data.duckdb")
                db_path = os.path.abspath(db_path)

    # Database path configured successfully

    # Initialize scanner adapter first to get unified manager
    if DuckDBScannerReadAdapter is None:
        raise ImportError("DuckDBScannerReadAdapter not available - missing aiohttp dependency")

    scanner_adapter = DuckDBScannerReadAdapter(db_path=db_path)

    # Get database connection from scanner adapter
    db_connection = None
    try:
        db_connection = scanner_adapter.get_connection()
    except Exception as e:
        if logger:
            logger.warning(f"Could not get database connection from scanner adapter: {e}")
        db_connection = None

    # Initialize rule engine with database connection
    if RuleEngine is None:
        raise ImportError("RuleEngine not available - missing aiohttp dependency")

    rule_engine = RuleEngine(db_connection=db_connection)

    lname = name.lower()
    if lname in {"enhanced_breakout", "breakout"}:
        # Create rule-based breakout scanner
        if RuleBasedBreakoutScanner is None:
            raise ImportError("RuleBasedBreakoutScanner not available - missing aiohttp dependency")
        scanner = RuleBasedBreakoutScanner(rule_engine)

        # Set scanner read adapter for the mapper
        if hasattr(scanner.rule_mapper, 'scanner_read'):
            scanner.rule_mapper.scanner_read = scanner_adapter

        return scanner

    elif lname in {"enhanced_crp", "crp"}:
        # Create rule-based CRP scanner
        if RuleBasedCRPScanner is None:
            raise ImportError("RuleBasedCRPScanner not available - missing aiohttp dependency")
        scanner = RuleBasedCRPScanner(rule_engine)

        # Set scanner read adapter for the mapper
        if hasattr(scanner.rule_mapper, 'scanner_read'):
            scanner.rule_mapper.scanner_read = scanner_adapter

        return scanner

    raise ValueError(f"Unsupported scanner name: {name}. Supported: 'breakout', 'crp', 'enhanced_breakout', 'enhanced_crp'")
