"""Domain service for data synchronization operations."""

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, date, time
from decimal import Decimal
from abc import ABC, abstractmethod
import asyncio
import logging

from ...domain.entities.market_data import MarketData, OHLCV
from ...domain.entities.symbol import Symbol
from ...domain.repositories.market_data_repo import MarketDataRepository
from ...application.ports.event_bus_port import EventBusPort
from ...domain.events import DataIngestedEvent


logger = logging.getLogger(__name__)


class DataSyncService:
    """Domain service for data synchronization operations."""

    def __init__(self, market_data_repo: MarketDataRepository, event_bus: EventBusPort):
        """Initialize data sync service."""
        self.market_data_repo = market_data_repo
        self.event_bus = event_bus
        self._sync_callbacks: List[Callable] = []
        self._is_running = False

    def add_sync_callback(self, callback: Callable):
        """Add callback for sync events."""
        self._sync_callbacks.append(callback)

    def remove_sync_callback(self, callback: Callable):
        """Remove callback for sync events."""
        if callback in self._sync_callbacks:
            self._sync_callbacks.remove(callback)

    def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify all registered callbacks."""
        for callback in self._sync_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in sync callback: {e}")

    async def sync_historical_data(self,
                                 symbols: List[str],
                                 start_date: date,
                                 end_date: date,
                                 timeframe: str = '1D',
                                 batch_size: int = 50) -> Dict[str, Any]:
        """
        Sync historical market data for symbols.

        Args:
            symbols: List of symbols to sync
            start_date: Start date for data
            end_date: End date for data
            timeframe: Data timeframe
            batch_size: Number of symbols to process in each batch

        Returns:
            Sync statistics
        """
        stats = {
            'total_symbols': len(symbols),
            'processed_symbols': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'total_records': 0,
            'start_time': datetime.now(),
            'errors': []
        }

        logger.info(f"Starting historical data sync for {len(symbols)} symbols")

        # Process symbols in batches
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} symbols")

            for symbol in batch:
                try:
                    # Sync individual symbol
                    symbol_stats = await self._sync_symbol_historical(
                        symbol, start_date, end_date, timeframe
                    )

                    stats['processed_symbols'] += 1
                    stats['total_records'] += symbol_stats.get('records_synced', 0)

                    if symbol_stats.get('success', False):
                        stats['successful_syncs'] += 1
                    else:
                        stats['failed_syncs'] += 1
                        stats['errors'].append({
                            'symbol': symbol,
                            'error': symbol_stats.get('error', 'Unknown error')
                        })

                    # Notify callbacks
                    self._notify_callbacks('symbol_synced', {
                        'symbol': symbol,
                        'stats': symbol_stats
                    })

                except Exception as e:
                    logger.error(f"Error syncing {symbol}: {e}")
                    stats['failed_syncs'] += 1
                    stats['errors'].append({
                        'symbol': symbol,
                        'error': str(e)
                    })

            # Small delay between batches to avoid overwhelming the system
            await asyncio.sleep(0.1)

        stats['end_time'] = datetime.now()
        stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info(f"Historical sync completed: {stats['successful_syncs']}/{stats['total_symbols']} successful")

        # Publish completion event
        await self._publish_sync_completed_event(stats)

        return stats

    async def _sync_symbol_historical(self,
                                    symbol: str,
                                    start_date: date,
                                    end_date: date,
                                    timeframe: str) -> Dict[str, Any]:
        """Sync historical data for a single symbol."""
        try:
            # Get existing data range for this symbol
            existing_data = self.market_data_repo.find_by_symbol_and_date_range(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                timeframe=timeframe
            )

            # Determine what data is missing
            # This is a simplified implementation - in practice you'd compare
            # with what should exist vs what does exist

            stats = {
                'symbol': symbol,
                'existing_records': len(existing_data),
                'records_synced': 0,
                'success': True
            }

            # Here you would typically:
            # 1. Fetch missing data from broker/data source
            # 2. Convert to domain entities
            # 3. Save to repository
            # 4. Update statistics

            logger.debug(f"Synced {stats['records_synced']} records for {symbol}")

            return stats

        except Exception as e:
            logger.error(f"Error syncing historical data for {symbol}: {e}")
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e),
                'records_synced': 0
            }

    async def sync_intraday_data(self,
                               symbols: List[str],
                               target_date: date,
                               batch_size: int = 20) -> Dict[str, Any]:
        """
        Sync intraday data for a specific date.

        Args:
            symbols: List of symbols to sync
            target_date: Date to sync data for
            batch_size: Number of symbols per batch

        Returns:
            Sync statistics
        """
        stats = {
            'total_symbols': len(symbols),
            'processed_symbols': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'total_records': 0,
            'target_date': target_date,
            'start_time': datetime.now(),
            'errors': []
        }

        logger.info(f"Starting intraday data sync for {len(symbols)} symbols on {target_date}")

        # Process symbols in batches
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]

            for symbol in batch:
                try:
                    symbol_stats = await self._sync_symbol_intraday(symbol, target_date)

                    stats['processed_symbols'] += 1
                    stats['total_records'] += symbol_stats.get('records_synced', 0)

                    if symbol_stats.get('success', False):
                        stats['successful_syncs'] += 1
                    else:
                        stats['failed_syncs'] += 1
                        stats['errors'].append({
                            'symbol': symbol,
                            'error': symbol_stats.get('error', 'Unknown error')
                        })

                except Exception as e:
                    logger.error(f"Error syncing intraday data for {symbol}: {e}")
                    stats['failed_syncs'] += 1
                    stats['errors'].append({
                        'symbol': symbol,
                        'error': str(e)
                    })

            # Brief pause between batches
            await asyncio.sleep(0.05)

        stats['end_time'] = datetime.now()
        stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info(f"Intraday sync completed: {stats['successful_syncs']}/{stats['total_symbols']} successful")

        return stats

    async def _sync_symbol_intraday(self, symbol: str, target_date: date) -> Dict[str, Any]:
        """Sync intraday data for a single symbol."""
        try:
            # Get existing intraday data for the date
            existing_data = self.market_data_repo.find_by_symbol_and_date_range(
                symbol=symbol,
                start_date=target_date,
                end_date=target_date,
                timeframe='1m'  # Intraday data
            )

            stats = {
                'symbol': symbol,
                'existing_records': len(existing_data),
                'records_synced': 0,
                'success': True
            }

            # Here you would implement the actual intraday data fetching
            # and syncing logic similar to the existing sync_today_intraday_duckdb.py

            return stats

        except Exception as e:
            logger.error(f"Error syncing intraday data for {symbol}: {e}")
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e),
                'records_synced': 0
            }

    async def start_realtime_sync(self,
                                symbols: List[str],
                                callback: Optional[Callable] = None) -> bool:
        """
        Start real-time data synchronization.

        Args:
            symbols: List of symbols to monitor
            callback: Callback function for real-time updates

        Returns:
            True if started successfully
        """
        if self._is_running:
            logger.warning("Real-time sync already running")
            return False

        try:
            self._is_running = True
            logger.info(f"Starting real-time sync for {len(symbols)} symbols")

            # Add callback if provided
            if callback:
                self.add_sync_callback(callback)

            # Start the real-time sync loop
            asyncio.create_task(self._run_realtime_sync(symbols))

            return True

        except Exception as e:
            logger.error(f"Error starting real-time sync: {e}")
            self._is_running = False
            return False

    async def stop_realtime_sync(self) -> bool:
        """Stop real-time data synchronization."""
        if not self._is_running:
            return True

        try:
            self._is_running = False
            logger.info("Stopping real-time sync")

            # Clear callbacks
            self._sync_callbacks.clear()

            return True

        except Exception as e:
            logger.error(f"Error stopping real-time sync: {e}")
            return False

    async def _run_realtime_sync(self, symbols: List[str]):
        """Run the real-time synchronization loop."""
        logger.info("Real-time sync loop started")

        try:
            while self._is_running:
                try:
                    # Here you would implement real-time data fetching
                    # For now, just sleep and continue
                    await asyncio.sleep(1.0)

                except Exception as e:
                    logger.error(f"Error in real-time sync loop: {e}")
                    await asyncio.sleep(5.0)  # Wait before retrying

        except Exception as e:
            logger.error(f"Real-time sync loop failed: {e}")
        finally:
            self._is_running = False
            logger.info("Real-time sync loop stopped")

    async def _publish_sync_completed_event(self, stats: Dict[str, Any]):
        """Publish sync completion event."""
        try:
            event = DataIngestedEvent(
                symbol="SYNC_COMPLETED",
                timeframe="ALL",
                records_count=stats.get('total_records', 0),
                start_date=stats.get('start_date'),
                end_date=stats.get('end_date'),
                metadata=stats
            )

            # Use injected event bus port (sync publish acceptable in async context)
            self.event_bus.publish(event)

        except Exception as e:
            logger.error(f"Error publishing sync event: {e}")

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return {
            'is_running': self._is_running,
            'active_callbacks': len(self._sync_callbacks),
            'timestamp': datetime.now()
        }
