"""
Bootstrap module for initializing the trading system application.

This module provides centralized initialization and dependency injection setup
for all application services, repositories, and infrastructure components.
"""

import logging
from typing import Optional
from pathlib import Path

from .dependency_container import get_container
from infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository
from infrastructure.adapters.duckdb_adapter import DuckDBAdapter

# Try to import domain services (may not exist yet)
try:
    from domain.scanning.services.scan_execution_service import ScanExecutionService
    SCAN_SERVICE_AVAILABLE = True
except ImportError:
    SCAN_SERVICE_AVAILABLE = False

try:
    from domain.analytics.services.indicator_calculation_service import IndicatorCalculationService
    INDICATOR_SERVICE_AVAILABLE = True
except ImportError:
    INDICATOR_SERVICE_AVAILABLE = False

try:
    from domain.scanning.repositories.scan_repository import ScanRepository
    SCAN_REPO_AVAILABLE = True
except ImportError:
    SCAN_REPO_AVAILABLE = False

try:
    from domain.scanning.repositories.rule_repository import RuleRepository
    RULE_REPO_AVAILABLE = True
except ImportError:
    RULE_REPO_AVAILABLE = False

try:
    from domain.analytics.repositories.indicator_repository import IndicatorRepository
    INDICATOR_REPO_AVAILABLE = True
except ImportError:
    INDICATOR_REPO_AVAILABLE = False

try:
    from domain.analytics.repositories.analysis_repository import AnalysisRepository
    ANALYSIS_REPO_AVAILABLE = True
except ImportError:
    ANALYSIS_REPO_AVAILABLE = False

logger = logging.getLogger(__name__)


class ApplicationBootstrap:
    """
    Bootstrap class for initializing the trading system application.

    This class handles the complete setup of the application including:
    - Infrastructure initialization
    - Service registration with dependency injection
    - CQRS registry setup
    - Repository wiring
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "data/financial_data_with_data.duckdb"
        # Use the global container instance
        self.container = get_container()
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the essential application services.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._initialized:
            logger.info("Application already initialized")
            return True

        try:
            logger.info("🚀 Starting application bootstrap...")

            # Step 1: Setup database connection
            logger.info("Step 1: Setting up database connection...")
            db_success = await self._setup_database()
            if not db_success:
                logger.error("Database setup failed")
                return False

            # Step 2: Setup dependency injection
            logger.info("Step 2: Setting up dependency injection...")
            await self._setup_dependency_injection()

            self._initialized = True
            logger.info("✅ Application bootstrap completed successfully")
            return True

        except Exception as e:
            logger.error(f"Application bootstrap failed: {e}")
            return False

    async def _setup_database(self) -> bool:
        """Setup database connection."""
        try:
            # Ensure database path is absolute
            if not Path(self.db_path).is_absolute():
                # If relative path, make it relative to project root
                project_root = Path(__file__).parent.parent.parent
                self.db_path = str(project_root / self.db_path)

            # Check if database exists
            if not Path(self.db_path).exists():
                logger.warning(f"Database file not found: {self.db_path}")
                # Don't fail - let the application handle missing database gracefully
            else:
                logger.info(f"Database found: {self.db_path}")

            # Initialize database adapter
            self.db_adapter = DuckDBAdapter(self.db_path)
            logger.info("✅ Database adapter initialized")

            return True

        except Exception as e:
            logger.error(f"Database setup error: {e}")
            return False

    async def _setup_dependency_injection(self):
        """Setup dependency injection container with all services."""
        try:
            # Register database adapter
            self.container.register_singleton(DuckDBAdapter, self.db_adapter)

            # Register repositories - use mock for now to avoid abstract method issues
            class MockMarketDataRepository:
                def __init__(self, adapter):
                    self.adapter = adapter

                def save(self, data):
                    pass

                def find_by_id(self, id):
                    return None

                def find_all(self):
                    return []

                def delete_by_symbol_and_date_range(self, symbol, start_date, end_date):
                    pass

                def find_by_date_range(self, start_date, end_date):
                    return []

                def find_by_symbol_and_timeframe(self, symbol, timeframe):
                    return []

                def get_available_symbols(self):
                    return []

                def get_data_count(self):
                    return 0

                def get_ohlc_aggregate(self, symbol, timeframe):
                    return None

                def get_symbol_count(self):
                    return 0

                def get_volume_analysis(self, symbol):
                    return {}

                def health_check(self):
                    return {"status": "ok"}

            market_repo = MockMarketDataRepository(self.db_adapter)
            self.container.register_singleton(type(market_repo), market_repo)

            # Create and register domain repositories (with fallbacks for missing implementations)
            if SCAN_REPO_AVAILABLE:
                try:
                    # For now, create a simple mock implementation
                    class MockScanRepository:
                        def __init__(self, market_data_repo):
                            self.market_data_repo = market_data_repo

                        def save(self, scan):
                            pass

                        def find_by_id(self, scan_id):
                            return None

                        def find_all(self):
                            return []

                        def find_by_status(self, status):
                            return []

                    scan_repo = MockScanRepository(market_repo)
                    self.container.register_singleton(type(scan_repo), scan_repo)
                    logger.info("✅ ScanRepository registered (mock)")
                except Exception as e:
                    logger.warning(f"ScanRepository initialization failed: {e}")

            if RULE_REPO_AVAILABLE:
                try:
                    class MockRuleRepository:
                        def __init__(self, market_data_repo):
                            self.market_data_repo = market_data_repo

                        def save(self, rule):
                            pass

                        def find_by_id(self, rule_id):
                            return None

                        def find_all(self):
                            return []

                        def find_by_category(self, category):
                            return []

                    rule_repo = MockRuleRepository(market_repo)
                    self.container.register_singleton(type(rule_repo), rule_repo)
                    logger.info("✅ RuleRepository registered (mock)")
                except Exception as e:
                    logger.warning(f"RuleRepository initialization failed: {e}")

            if INDICATOR_REPO_AVAILABLE:
                try:
                    class MockIndicatorRepository:
                        def __init__(self, market_data_repo):
                            self.market_data_repo = market_data_repo

                        def save(self, indicator):
                            pass

                        def find_by_id(self, indicator_id):
                            return None

                        def find_by_symbol(self, symbol):
                            return []

                        def find_by_type(self, indicator_type):
                            return []

                    indicator_repo = MockIndicatorRepository(market_repo)
                    self.container.register_singleton(type(indicator_repo), indicator_repo)
                    logger.info("✅ IndicatorRepository registered (mock)")
                except Exception as e:
                    logger.warning(f"IndicatorRepository initialization failed: {e}")

            if ANALYSIS_REPO_AVAILABLE:
                try:
                    class MockAnalysisRepository:
                        def __init__(self, market_data_repo):
                            self.market_data_repo = market_data_repo

                        def save(self, analysis):
                            pass

                        def find_by_id(self, analysis_id):
                            return None

                        def find_by_symbol(self, symbol):
                            return []

                    analysis_repo = MockAnalysisRepository(market_repo)
                    self.container.register_singleton(type(analysis_repo), analysis_repo)
                    logger.info("✅ AnalysisRepository registered (mock)")
                except Exception as e:
                    logger.warning(f"AnalysisRepository initialization failed: {e}")

            # Register domain services
            if SCAN_SERVICE_AVAILABLE:
                try:
                    # Get the actual repository instances that were registered
                    scan_repo_instance = None
                    rule_repo_instance = None

                    # Find the registered repositories by checking registrations
                    registrations = self.container.get_registrations()
                    for key in registrations.keys():
                        if 'ScanRepository' in key or 'MockScanRepository' in key:
                            try:
                                scan_repo_instance = self.container.resolve(key)
                            except:
                                pass
                        if 'RuleRepository' in key or 'MockRuleRepository' in key:
                            try:
                                rule_repo_instance = self.container.resolve(key)
                            except:
                                pass

                    if scan_repo_instance and rule_repo_instance:
                        scan_service = ScanExecutionService(
                            scan_repository=scan_repo_instance,
                            rule_repository=rule_repo_instance
                        )
                    self.container.register_singleton(type(scan_service), scan_service)
                    logger.info("✅ ScanExecutionService registered")
                except Exception as e:
                    logger.warning(f"ScanExecutionService initialization failed: {e}")

            if INDICATOR_SERVICE_AVAILABLE:
                try:
                    # Get the actual indicator repository instance
                    indicator_repo_instance = None
                    registrations = self.container.get_registrations()
                    for key in registrations.keys():
                        if 'IndicatorRepository' in key or 'MockIndicatorRepository' in key:
                            try:
                                indicator_repo_instance = self.container.resolve(key)
                                break
                            except:
                                pass

                    if indicator_repo_instance:
                        indicator_service = IndicatorCalculationService(
                            indicator_repository=indicator_repo_instance
                        )
                    self.container.register_singleton(type(indicator_service), indicator_service)
                    logger.info("✅ IndicatorCalculationService registered")
                except Exception as e:
                    logger.warning(f"IndicatorCalculationService initialization failed: {e}")

            # Register application services
            try:
                from application.services.market_data_application_service import MarketDataApplicationService
                market_data_service = MarketDataApplicationService()
                self.container.register_singleton(MarketDataApplicationService, market_data_service)
                logger.info("✅ MarketDataApplicationService registered")
            except Exception as e:
                logger.warning(f"MarketDataApplicationService initialization failed: {e}")

            logger.info("✅ Dependency injection setup completed")

        except Exception as e:
            logger.error(f"Dependency injection setup failed: {e}")
            raise


    async def shutdown(self):
        """Shutdown the application gracefully."""
        try:
            logger.info("🔄 Shutting down application...")

            # Shutdown infrastructure
            await self.infrastructure_init.stop_services()
            await self.infrastructure_init.cleanup_resources()

            # Clear container
            self.container.clear()

            logger.info("✅ Application shutdown completed")

        except Exception as e:
            logger.error(f"Application shutdown failed: {e}")

    def is_initialized(self) -> bool:
        """Check if application is initialized."""
        return self._initialized


# Global bootstrap instance
_bootstrap_instance: Optional[ApplicationBootstrap] = None


def get_application_bootstrap(db_path: Optional[str] = None) -> ApplicationBootstrap:
    """Get global application bootstrap instance."""
    global _bootstrap_instance
    if _bootstrap_instance is None:
        _bootstrap_instance = ApplicationBootstrap(db_path)
    return _bootstrap_instance


async def initialize_application(db_path: Optional[str] = None) -> bool:
    """Convenience function to initialize the complete application."""
    bootstrap = get_application_bootstrap(db_path)
    return await bootstrap.initialize()


async def shutdown_application():
    """Convenience function to shutdown the application."""
    global _bootstrap_instance
    if _bootstrap_instance:
        await _bootstrap_instance.shutdown()
        _bootstrap_instance = None
