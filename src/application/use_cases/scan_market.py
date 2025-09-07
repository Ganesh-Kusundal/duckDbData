"""
Scan Market Use Case
====================

Orchestrates market scanning operations by coordinating between
domain services, repositories, and scanner strategies.

This use case handles:
- Scanner strategy selection and execution
- Result aggregation and processing
- Event publishing for scan completion
- Error handling and recovery
"""

from typing import Dict, List, Any, Optional
from datetime import date, time, datetime
import pandas as pd
from dataclasses import dataclass

from ...domain.repositories.market_data_repo import MarketDataRepository
from ...domain.services.data_sync_service import DataSyncService
from ...infrastructure.messaging.event_bus import EventBus
from ...infrastructure.logging import get_logger
from ...domain.exceptions import ScannerError
from ...infrastructure.utils.retry import retry_on_transient_errors
from ...infrastructure.config.config_manager import ConfigManager

from analytics.core.pattern_analyzer import PatternAnalyzer
from analytics.core.duckdb_connector import DuckDBAnalytics

logger = get_logger(__name__)


@dataclass
class ScanRequest:
    """Request data for market scanning."""
    scan_date: date
    cutoff_time: time
    scanner_types: List[str]
    config_overrides: Optional[Dict[str, Any]] = None


@dataclass
class ScanResult:
    """Result data from market scanning."""
    scanner_results: Dict[str, pd.DataFrame]
    total_stocks_found: int
    successful_scanners: int
    scan_timestamp: datetime
    execution_time_seconds: float
    pattern_stats: Dict[str, Any] = None
    failed_checks: int = 0


class ScanMarketUseCase:
    """
    Use case for orchestrating market scanning operations.
    
    This class coordinates the scanning workflow by:
    1. Validating scan parameters
    2. Executing scanner strategies
    3. Aggregating results
    4. Publishing completion events
    5. Handling errors gracefully
    """

    def __init__(
        self,
        market_data_repo: MarketDataRepository,
        data_sync_service: DataSyncService,
        event_bus: EventBus,
        config_manager: Optional[ConfigManager] = None
    ):
        """
        Initialize the scan market use case with centralized configuration.
        
        Args:
            market_data_repo: Repository for market data access
            data_sync_service: Service for data synchronization
            event_bus: Event bus for publishing scan events
            config_manager: ConfigManager instance for centralized configuration (optional for backward compatibility)
        """
        self.market_data_repo = market_data_repo
        self.data_sync_service = data_sync_service
        self.event_bus = event_bus
        self.config_manager = config_manager

        # Create PatternAnalyzer instance if ConfigManager available
        self.pattern_analyzer = None
        if self.config_manager:
            try:
                # Create DuckDBAnalytics with config
                db_analytics = DuckDBAnalytics(config_manager=self.config_manager)
                self.pattern_analyzer = PatternAnalyzer(db_connector=db_analytics)
                logger.info("PatternAnalyzer initialized with DuckDBAnalytics")
            except Exception as e:
                logger.warning(f"Failed to initialize PatternAnalyzer: {e}")
                self.pattern_analyzer = None

        # Scanner strategy registry
        self.scanner_strategies = {}

        logger.info("ScanMarketUseCase initialized")

    def register_scanner_strategy(self, name: str, scanner_class: Any):
        """
        Register a scanner strategy for use in scanning operations.

        Args:
            name: Name of the scanner strategy
            scanner_class: Scanner class to instantiate
        """
        self.scanner_strategies[name] = scanner_class
        logger.info(f"Registered scanner strategy: {name}")

    # @retry_on_transient_errors  # temporarily disabled for debugging
    def execute(self, request: ScanRequest) -> ScanResult:
        """
        Execute market scanning for the given request.
        
        Args:
            request: Scan request with parameters
            
        Returns:
            ScanResult containing aggregated results
            
        Raises:
            ValueError: If scan parameters are invalid
            ScannerError: If scanner execution fails
        """
        start_time = datetime.now()
        logger.info(f"Starting market scan for {request.scan_date} at {request.cutoff_time}")
        
        # Validate request
        self._validate_request(request)
        
        # Execute scanners
        scanner_results = {}
        errors = []
        
        for scanner_name in request.scanner_types:
            try:
                if scanner_name not in self.scanner_strategies:
                    logger.warning(f"Scanner strategy not found: {scanner_name}")
                    continue
                
                # Instantiate scanner with ConfigManager and PatternAnalyzer if available
                scanner_class = self.scanner_strategies[scanner_name]
                scanner_kwargs = {
                    'config_manager': self.config_manager if self.config_manager else None,
                    'pattern_analyzer': self.pattern_analyzer
                }
                
                # Create db_manager for scanner
                from src.infrastructure.core.database import DuckDBManager
                db_manager = DuckDBManager()
                scanner_kwargs['db_manager'] = db_manager
                
                scanner = scanner_class(**scanner_kwargs)
                
                # Apply enhanced config overrides using ConfigManager or fallback
                if self.config_manager and scanner_name in request.scanner_types:
                    try:
                        # Get scanner-specific overrides from ConfigManager
                        scanner_overrides = self.config_manager.get_value(f'scanners.strategies.{scanner_name}', {})
                        if scanner_overrides:
                            scanner.config.update(scanner_overrides)
                            logger.debug(f"Applied ConfigManager overrides for {scanner_name}")
                    except Exception as e:
                        logger.warning(f"Failed to apply ConfigManager overrides for {scanner_name}: {e}")
                
                # Apply request-specific overrides (backward compatibility)
                if request.config_overrides and scanner_name in request.config_overrides:
                    scanner.config.update(request.config_overrides[scanner_name])
                    logger.debug(f"Applied request overrides for {scanner_name}")
                
                # Execute scan
                logger.info(f"Executing scanner: {scanner_name}")
                results = scanner.scan(request.scan_date, request.cutoff_time)
                
                if not results.empty:
                    scanner_results[scanner_name] = results
                    logger.info(f"Scanner {scanner_name} found {len(results)} stocks")
                else:
                    scanner_results[scanner_name] = pd.DataFrame()
                    logger.info(f"Scanner {scanner_name} found no stocks")
                    
            except ScannerError as e:
                error_msg = f"Scanner {scanner_name} failed: {e.message}"
                logger.error(f"Scanner execution failed", extra=e.to_dict())
                errors.append(error_msg)
                scanner_results[scanner_name] = pd.DataFrame()
            except Exception as e:
                # Re-raise non-transient errors
                error_msg = f"Scanner {scanner_name} failed with unexpected error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                scanner_results[scanner_name] = pd.DataFrame()
                raise

        # Calculate summary statistics
        total_stocks = sum(len(df) for df in scanner_results.values() if not df.empty)
        successful_scanners = sum(1 for df in scanner_results.values() if not df.empty)
        execution_time = (datetime.now() - start_time).total_seconds()

        # Aggregate pattern statistics from scanner results
        pattern_stats = {}
        if self.pattern_analyzer:
            total_pattern_scores = 0
            total_symbols_with_patterns = 0
            avg_confidence = 0.0
            
            for scanner_name, df in scanner_results.items():
                if not df.empty and 'confidence_score' in df.columns:
                    # Count symbols with pattern signals (confidence > 0)
                    symbols_with_patterns = len(df[df['confidence_score'] > 0])
                    total_pattern_scores += df['confidence_score'].sum()
                    total_symbols_with_patterns += symbols_with_patterns
                    
                    if symbols_with_patterns > 0:
                        avg_confidence += df[df['confidence_score'] > 0]['confidence_score'].mean()
            
            if total_symbols_with_patterns > 0:
                avg_confidence = avg_confidence / len([df for df in scanner_results.values() if not df.empty and 'confidence_score' in df.columns])
            
            pattern_stats = {
                'total_pattern_signals': total_symbols_with_patterns,
                'total_confidence_score': round(total_pattern_scores, 3),
                'average_confidence': round(avg_confidence, 3),
                'pattern_coverage': round((total_symbols_with_patterns / total_stocks * 100), 1) if total_stocks > 0 else 0
            }

        result = ScanResult(
            scanner_results=scanner_results,
            total_stocks_found=total_stocks,
            successful_scanners=successful_scanners,
            scan_timestamp=start_time,
            execution_time_seconds=execution_time,
            pattern_stats=pattern_stats
        )

        # Publish completion event
        self._publish_scan_completed_event(result, errors)

        logger.info(f"Market scan completed: {total_stocks} stocks found, "
                   f"{successful_scanners} scanners successful in {execution_time:.2f}s")

        return result

    def _validate_request(self, request: ScanRequest):
        """
        Validate scan request parameters.

        Args:
            request: Scan request to validate

        Raises:
            ValueError: If validation fails
        """
        if not request.scanner_types:
            raise ValueError("At least one scanner type must be specified")

        if request.scan_date > date.today():
            raise ValueError("Scan date cannot be in the future")

        # Check if requested scanners are available
        unavailable_scanners = [
            name for name in request.scanner_types
            if name not in self.scanner_strategies
        ]

        if unavailable_scanners:
            logger.warning(f"Requested scanners not available: {unavailable_scanners}")

    def _publish_scan_completed_event(self, result: ScanResult, errors: List[str]):
        """
        Publish scan completion event to the event bus.

        Args:
            result: Scan results to publish
            errors: List of errors encountered during scanning
        """
        event_data = {
            'scan_timestamp': result.scan_timestamp.isoformat(),
            'total_stocks_found': result.total_stocks_found,
            'successful_scanners': result.successful_scanners,
            'execution_time_seconds': result.execution_time_seconds,
            'scanner_results': {
                name: len(df) for name, df in result.scanner_results.items()
            },
            'pattern_stats': result.pattern_stats,
            'errors': errors
        }

        try:
            self.event_bus.publish({
                'event_type': 'scan_completed',
                'data': event_data,
                'timestamp': datetime.now().isoformat()
            })
            logger.info("Published scan completion event")
        except Exception as e:
            logger.error(f"Failed to publish scan completion event: {e}")

    def get_available_scanners(self) -> List[str]:
        """
        Get list of available scanner strategies.

        Returns:
            List of scanner strategy names
        """
        return list(self.scanner_strategies.keys())

    def get_scanner_config_schema(self, scanner_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration schema for a scanner strategy.

        Args:
            scanner_name: Name of the scanner strategy

        Returns:
            Configuration schema or None if scanner not found
        """
        if scanner_name not in self.scanner_strategies:
            return None

        scanner_class = self.scanner_strategies[scanner_name]
        if hasattr(scanner_class, 'get_config_schema'):
            return scanner_class.get_config_schema()

        return None
