"""
Scanner Service
===============

Application service for orchestrating scanner operations and workflows.
This service coordinates between domain services, repositories, and
scanner strategies to provide high-level scanning functionality.

Features:
- Scanner orchestration and scheduling
- Result aggregation and processing
- Performance monitoring and optimization
- Scanner configuration management
- Workflow automation
"""

from typing import Dict, List, Any, Optional
from datetime import date, time, datetime
from dataclasses import dataclass
import asyncio

from ...domain.repositories.market_data_repo import MarketDataRepository
from ...domain.services.data_sync_service import DataSyncService
from ...application.ports.event_bus_port import EventBusPort
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ScannerConfig:
    """Configuration for scanner operations."""
    scanner_types: List[str]
    symbols: Optional[List[str]] = None
    scan_date: Optional[date] = None
    cutoff_time: Optional[time] = None
    config_overrides: Optional[Dict[str, Any]] = None
    parallel_execution: bool = False
    max_concurrent_scanners: int = 3


@dataclass
class ScannerResult:
    """Result from scanner service operations."""
    scanner_results: Dict[str, Any]
    execution_stats: Dict[str, Any]
    timestamp: datetime
    duration_seconds: float


class ScannerService:
    """
    Application service for scanner orchestration.

    This service provides high-level scanner operations by coordinating
    between domain services, repositories, and scanner strategies.
    """

    def __init__(
        self,
        market_data_repo: MarketDataRepository,
        data_sync_service: DataSyncService,
        event_bus: EventBusPort
    ):
        """
        Initialize the scanner service.

        Args:
            market_data_repo: Repository for market data access
            data_sync_service: Service for data synchronization
            event_bus: Event bus for publishing scanner events
        """
        self.market_data_repo = market_data_repo
        self.data_sync_service = data_sync_service
        self.event_bus = event_bus

        # Scanner registry
        self.scanner_strategies = {}

        logger.info("ScannerService initialized")

    def register_scanner_strategy(self, name: str, scanner_class: Any):
        """
        Register a scanner strategy.

        Args:
            name: Name of the scanner strategy
            scanner_class: Scanner class to register
        """
        self.scanner_strategies[name] = scanner_class
        logger.info(f"Registered scanner strategy: {name}")

    async def execute_scanner_workflow(self, config: ScannerConfig) -> ScannerResult:
        """
        Execute a complete scanner workflow.

        Args:
            config: Scanner configuration

        Returns:
            ScannerResult with aggregated results
        """
        start_time = datetime.now()
        logger.info(f"Starting scanner workflow with {len(config.scanner_types)} scanners")

        # Validate configuration
        self._validate_config(config)

        # Prepare scanner instances
        scanners = self._prepare_scanners(config)

        # Execute scanners
        if config.parallel_execution:
            results = await self._execute_parallel(scanners, config)
        else:
            results = await self._execute_sequential(scanners, config)

        # Aggregate results
        aggregated_results = self._aggregate_results(results)

        # Calculate execution stats
        execution_stats = self._calculate_execution_stats(results, start_time)

        # Publish workflow completion event
        await self._publish_workflow_event(aggregated_results, execution_stats)

        duration = (datetime.now() - start_time).total_seconds()

        result = ScannerResult(
            scanner_results=aggregated_results,
            execution_stats=execution_stats,
            timestamp=start_time,
            duration_seconds=duration
        )

        logger.info(f"Scanner workflow completed in {duration:.2f}s")
        return result

    def execute_daily_scan(self, scanner_types: Optional[List[str]] = None) -> ScannerResult:
        """
        Execute daily scanner workflow.

        Args:
            scanner_types: List of scanner types to execute

        Returns:
            ScannerResult with daily scan results
        """
        logger.info("Executing daily scanner workflow")

        # Default scanner types
        if not scanner_types:
            scanner_types = ['relative_volume', 'technical']

        # Create daily scan configuration
        config = ScannerConfig(
            scanner_types=scanner_types,
            scan_date=date.today(),
            cutoff_time=time(9, 50),  # 9:50 AM cutoff
            parallel_execution=True
        )

        # Run workflow synchronously for daily scan
        async_result = asyncio.run(self.execute_scanner_workflow(config))
        return async_result

    def execute_custom_scan(
        self,
        scanner_types: List[str],
        symbols: Optional[List[str]] = None,
        scan_date: Optional[date] = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> ScannerResult:
        """
        Execute custom scanner configuration.

        Args:
            scanner_types: List of scanner types to execute
            symbols: Specific symbols to scan
            scan_date: Date to scan
            config_overrides: Configuration overrides

        Returns:
            ScannerResult with custom scan results
        """
        logger.info("Executing custom scanner workflow")

        config = ScannerConfig(
            scanner_types=scanner_types,
            symbols=symbols,
            scan_date=scan_date or date.today(),
            config_overrides=config_overrides,
            parallel_execution=len(scanner_types) > 1
        )

        # Run workflow synchronously
        async_result = asyncio.run(self.execute_scanner_workflow(config))
        return async_result

    def get_scanner_status(self) -> Dict[str, Any]:
        """
        Get current scanner service status.

        Returns:
            Dictionary with scanner service status
        """
        return {
            'registered_scanners': list(self.scanner_strategies.keys()),
            'total_scanners': len(self.scanner_strategies),
            'service_status': 'active',
            'timestamp': datetime.now().isoformat()
        }

    def get_scanner_performance_metrics(self) -> Dict[str, Any]:
        """
        Get scanner performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        # This would integrate with a metrics collection system
        return {
            'avg_execution_time': 0.0,
            'total_scans_executed': 0,
            'success_rate': 0.0,
            'last_scan_timestamp': None
        }

    async def _execute_parallel(self, scanners: Dict[str, Any], config: ScannerConfig) -> Dict[str, Any]:
        """
        Execute scanners in parallel.

        Args:
            scanners: Dictionary of scanner instances
            config: Scanner configuration

        Returns:
            Dictionary of scanner results
        """
        logger.info(f"Executing {len(scanners)} scanners in parallel")

        # Create tasks for parallel execution
        tasks = []
        semaphore = asyncio.Semaphore(config.max_concurrent_scanners)

        async def execute_with_semaphore(name: str, scanner: Any):
            async with semaphore:
                return await self._execute_single_scanner(name, scanner, config)

        for name, scanner in scanners.items():
            task = asyncio.create_task(execute_with_semaphore(name, scanner))
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = {}
        for i, result in enumerate(results):
            scanner_name = list(scanners.keys())[i]
            if isinstance(result, Exception):
                logger.error(f"Scanner {scanner_name} failed: {result}")
                processed_results[scanner_name] = {'error': str(result)}
            else:
                processed_results[scanner_name] = result

        return processed_results

    async def _execute_sequential(self, scanners: Dict[str, Any], config: ScannerConfig) -> Dict[str, Any]:
        """
        Execute scanners sequentially.

        Args:
            scanners: Dictionary of scanner instances
            config: Scanner configuration

        Returns:
            Dictionary of scanner results
        """
        logger.info(f"Executing {len(scanners)} scanners sequentially")

        results = {}
        for name, scanner in scanners.items():
            try:
                result = await self._execute_single_scanner(name, scanner, config)
                results[name] = result
            except Exception as e:
                logger.error(f"Scanner {name} failed: {e}")
                results[name] = {'error': str(e)}

        return results

    async def _execute_single_scanner(self, name: str, scanner: Any, config: ScannerConfig) -> Dict[str, Any]:
        """
        Execute a single scanner.

        Args:
            name: Scanner name
            scanner: Scanner instance
            config: Scanner configuration

        Returns:
            Scanner execution result
        """
        start_time = datetime.now()
        logger.debug(f"Executing scanner: {name}")

        try:
            # Execute scanner
            results = scanner.scan(config.scan_date, config.cutoff_time)

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                'success': True,
                'results': results.to_dict('records') if hasattr(results, 'to_dict') else results,
                'execution_time': execution_time,
                'records_found': len(results) if hasattr(results, '__len__') else 0
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Scanner {name} execution failed: {e}")

            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'records_found': 0
            }

    def _prepare_scanners(self, config: ScannerConfig) -> Dict[str, Any]:
        """
        Prepare scanner instances for execution.

        Args:
            config: Scanner configuration

        Returns:
            Dictionary of scanner instances
        """
        scanners = {}

        for scanner_name in config.scanner_types:
            if scanner_name not in self.scanner_strategies:
                logger.warning(f"Scanner strategy not found: {scanner_name}")
                continue

            scanner_class = self.scanner_strategies[scanner_name]
            scanner = scanner_class(
                market_data_repo=self.market_data_repo,
                data_sync_service=self.data_sync_service
            )

            # Apply configuration overrides
            if config.config_overrides and scanner_name in config.config_overrides:
                scanner.config.update(config.config_overrides[scanner_name])

            scanners[scanner_name] = scanner

        return scanners

    def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate scanner results.

        Args:
            results: Raw scanner results

        Returns:
            Aggregated results
        """
        aggregated = {
            'summary': {
                'total_scanners': len(results),
                'successful_scanners': sum(1 for r in results.values() if r.get('success', False)),
                'failed_scanners': sum(1 for r in results.values() if not r.get('success', False)),
                'total_records': sum(r.get('records_found', 0) for r in results.values())
            },
            'scanner_details': results
        }

        return aggregated

    def _calculate_execution_stats(self, results: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
        """
        Calculate execution statistics.

        Args:
            results: Scanner results
            start_time: Workflow start time

        Returns:
            Execution statistics
        """
        execution_times = [r.get('execution_time', 0) for r in results.values()]

        return {
            'total_execution_time': (datetime.now() - start_time).total_seconds(),
            'avg_scanner_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'min_scanner_time': min(execution_times) if execution_times else 0,
            'max_scanner_time': max(execution_times) if execution_times else 0,
            'scanners_executed': len(results)
        }

    async def _publish_workflow_event(self, results: Dict[str, Any], stats: Dict[str, Any]):
        """
        Publish scanner workflow completion event.

        Args:
            results: Aggregated scanner results
            stats: Execution statistics
        """
        event_data = {
            'workflow_type': 'scanner_execution',
            'summary': results['summary'],
            'execution_stats': stats,
            'timestamp': datetime.now().isoformat()
        }

        try:
            self.event_bus.publish({
                'event_type': 'scanner_workflow_completed',
                'data': event_data,
                'timestamp': datetime.now().isoformat()
            })
            logger.info("Published scanner workflow completion event")
        except Exception as e:
            logger.error(f"Failed to publish workflow event: {e}")

    def _validate_config(self, config: ScannerConfig):
        """
        Validate scanner configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if not config.scanner_types:
            raise ValueError("At least one scanner type must be specified")

        # Check if requested scanners are available
        unavailable_scanners = [
            name for name in config.scanner_types
            if name not in self.scanner_strategies
        ]

        if unavailable_scanners:
            raise ValueError(f"Requested scanners not available: {unavailable_scanners}")

        if config.scan_date and config.scan_date > date.today():
            raise ValueError("Scan date cannot be in the future")

    def optimize_scanner_config(self, scanner_name: str) -> Dict[str, Any]:
        """
        Optimize configuration for a scanner.

        Args:
            scanner_name: Name of the scanner to optimize

        Returns:
            Optimized configuration
        """
        # This would implement configuration optimization logic
        # For now, return default optimization suggestions
        return {
            'batch_size': 100,
            'parallel_processing': True,
            'memory_limit': '512MB'
        }
