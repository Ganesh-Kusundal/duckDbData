"""
Sync Data Use Case
==================

Orchestrates data synchronization workflows by coordinating between
domain services, repositories, and external data sources.

This use case handles:
- Historical data synchronization
- Intraday data updates
- Real-time data streaming
- Data validation and quality checks
- Error handling and recovery
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime, time
from dataclasses import dataclass
from enum import Enum

from ...domain.repositories.market_data_repo import MarketDataRepository
from ...domain.services.data_sync_service import DataSyncService
from ...application.ports.event_bus_port import EventBusPort
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class SyncType(Enum):
    """Types of data synchronization."""
    HISTORICAL = "historical"
    INTRADAY = "intraday"
    REALTIME = "realtime"


@dataclass
class SyncRequest:
    """Request data for data synchronization."""
    sync_type: SyncType
    symbols: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    force_refresh: bool = False
    validate_data: bool = True


@dataclass
class SyncResult:
    """Result data from data synchronization."""
    sync_type: SyncType
    symbols_processed: int
    records_processed: int
    success_count: int
    error_count: int
    sync_timestamp: datetime
    execution_time_seconds: float
    errors: List[str]


class SyncDataUseCase:
    """
    Use case for orchestrating data synchronization operations.

    This class coordinates the data sync workflow by:
    1. Validating sync parameters
    2. Executing appropriate sync operations
    3. Handling data validation
    4. Publishing completion events
    5. Managing error recovery
    """

    def __init__(
        self,
        market_data_repo: MarketDataRepository,
        data_sync_service: DataSyncService,
        event_bus: EventBus
    ):
        """
        Initialize the sync data use case.

        Args:
            market_data_repo: Repository for market data access
            data_sync_service: Service for data synchronization
            event_bus: Event bus for publishing sync events
        """
        self.market_data_repo = market_data_repo
        self.data_sync_service = data_sync_service
        self.event_bus = event_bus

        logger.info("SyncDataUseCase initialized")

    def execute(self, request: SyncRequest) -> SyncResult:
        """
        Execute data synchronization for the given request.

        Args:
            request: Sync request with parameters

        Returns:
            SyncResult containing sync statistics

        Raises:
            ValueError: If sync parameters are invalid
            RuntimeError: If synchronization fails
        """
        start_time = datetime.now()
        logger.info(f"Starting {request.sync_type.value} data sync")

        # Validate request
        self._validate_request(request)

        # Execute sync based on type
        if request.sync_type == SyncType.HISTORICAL:
            result = self._execute_historical_sync(request)
        elif request.sync_type == SyncType.INTRADAY:
            result = self._execute_intraday_sync(request)
        elif request.sync_type == SyncType.REALTIME:
            result = self._execute_realtime_sync(request)
        else:
            raise ValueError(f"Unsupported sync type: {request.sync_type}")

        execution_time = (datetime.now() - start_time).total_seconds()

        final_result = SyncResult(
            sync_type=request.sync_type,
            symbols_processed=result['symbols_processed'],
            records_processed=result['records_processed'],
            success_count=result['success_count'],
            error_count=result['error_count'],
            sync_timestamp=start_time,
            execution_time_seconds=execution_time,
            errors=result['errors']
        )

        # Publish completion event
        self._publish_sync_completed_event(final_result)

        logger.info(f"Data sync completed: {final_result.records_processed} records, "
                   f"{final_result.success_count} successful, "
                   f"{final_result.error_count} errors in {execution_time:.2f}s")

        return final_result

    def _execute_historical_sync(self, request: SyncRequest) -> Dict[str, Any]:
        """
        Execute historical data synchronization.

        Args:
            request: Sync request parameters

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Executing historical data sync")

        # Determine symbols to sync
        symbols = request.symbols
        if not symbols:
            symbols = self.market_data_repo.get_all_symbols()
            logger.info(f"Syncing all {len(symbols)} symbols")

        # Sync parameters
        start_date = request.start_date or date(2015, 1, 1)
        end_date = request.end_date or date.today()

        total_records = 0
        success_count = 0
        errors = []

        for symbol in symbols:
            try:
                logger.debug(f"Syncing historical data for {symbol}")

                # Sync historical data for symbol
                records = self.data_sync_service.sync_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=request.force_refresh
                )

                total_records += records
                success_count += 1

                # Validate data if requested
                if request.validate_data:
                    self._validate_symbol_data(symbol, start_date, end_date)

            except Exception as e:
                error_msg = f"Failed to sync {symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        return {
            'symbols_processed': len(symbols),
            'records_processed': total_records,
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }

    def _execute_intraday_sync(self, request: SyncRequest) -> Dict[str, Any]:
        """
        Execute intraday data synchronization.

        Args:
            request: Sync request parameters

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Executing intraday data sync")

        # For intraday sync, we typically sync today's data
        sync_date = request.end_date or date.today()

        # Determine symbols to sync
        symbols = request.symbols
        if not symbols:
            symbols = self.market_data_repo.get_active_symbols()
            logger.info(f"Syncing intraday data for {len(symbols)} active symbols")

        total_records = 0
        success_count = 0
        errors = []

        for symbol in symbols:
            try:
                logger.debug(f"Syncing intraday data for {symbol}")

                # Sync intraday data for symbol
                records = self.data_sync_service.sync_intraday_data(
                    symbol=symbol,
                    sync_date=sync_date,
                    force_refresh=request.force_refresh
                )

                total_records += records
                success_count += 1

            except Exception as e:
                error_msg = f"Failed to sync intraday data for {symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        return {
            'symbols_processed': len(symbols),
            'records_processed': total_records,
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }

    def _execute_realtime_sync(self, request: SyncRequest) -> Dict[str, Any]:
        """
        Execute real-time data synchronization.

        Args:
            request: Sync request parameters

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Executing real-time data sync")

        # Determine symbols to sync
        symbols = request.symbols
        if not symbols:
            symbols = self.market_data_repo.get_active_symbols()
            logger.info(f"Starting real-time sync for {len(symbols)} active symbols")

        # Start real-time streaming
        try:
            self.data_sync_service.start_realtime_sync(symbols)
            success_count = len(symbols)
            errors = []
        except Exception as e:
            error_msg = f"Failed to start real-time sync: {str(e)}"
            logger.error(error_msg)
            success_count = 0
            errors = [error_msg]

        return {
            'symbols_processed': len(symbols),
            'records_processed': 0,  # Real-time sync doesn't return immediate records
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors
        }

    def _validate_request(self, request: SyncRequest):
        """
        Validate sync request parameters.

        Args:
            request: Sync request to validate

        Raises:
            ValueError: If validation fails
        """
        if request.start_date and request.end_date and request.start_date > request.end_date:
            raise ValueError("Start date cannot be after end date")

        if request.sync_type == SyncType.REALTIME and not request.symbols:
            raise ValueError("Real-time sync requires specific symbols")

    def _validate_symbol_data(self, symbol: str, start_date: date, end_date: date):
        """
        Validate data quality for a symbol.

        Args:
            symbol: Symbol to validate
            start_date: Start date for validation
            end_date: End date for validation
        """
        try:
            # Check data completeness
            data_count = self.market_data_repo.get_data_count(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

            expected_days = (end_date - start_date).days + 1
            expected_records = expected_days * 375  # Rough estimate for trading hours

            if data_count < expected_records * 0.8:  # Allow 20% missing data
                logger.warning(f"Low data quality for {symbol}: {data_count} records "
                             f"(expected ~{expected_records})")

        except Exception as e:
            logger.error(f"Data validation failed for {symbol}: {e}")

    def _publish_sync_completed_event(self, result: SyncResult):
        """
        Publish sync completion event to the event bus.

        Args:
            result: Sync results to publish
        """
        event_data = {
            'sync_type': result.sync_type.value,
            'sync_timestamp': result.sync_timestamp.isoformat(),
            'symbols_processed': result.symbols_processed,
            'records_processed': result.records_processed,
            'success_count': result.success_count,
            'error_count': result.error_count,
            'execution_time_seconds': result.execution_time_seconds,
            'errors': result.errors
        }

        try:
            self.event_bus.publish({
                'event_type': 'data_sync_completed',
                'data': event_data,
                'timestamp': datetime.now().isoformat()
            })
            logger.info("Published data sync completion event")
        except Exception as e:
            logger.error(f"Failed to publish sync completion event: {e}")

    def stop_realtime_sync(self):
        """
        Stop real-time data synchronization.
        """
        try:
            self.data_sync_service.stop_realtime_sync()
            logger.info("Real-time sync stopped")
        except Exception as e:
            logger.error(f"Failed to stop real-time sync: {e}")

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current synchronization status.

        Returns:
            Dictionary with sync status information
        """
        try:
            return self.data_sync_service.get_sync_status()
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {'status': 'error', 'message': str(e)}
