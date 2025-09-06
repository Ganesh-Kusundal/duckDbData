"""Adapter to integrate existing data sync components with the new DDD architecture."""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
import asyncio
import logging

from ...domain.entities.market_data import MarketData, OHLCV
from ...domain.services.data_sync_service import DataSyncService
from ...domain.repositories.market_data_repo import MarketDataRepository
from ...infrastructure.repositories.duckdb_market_repo import DuckDBMarketDataRepository


logger = logging.getLogger(__name__)


class LegacyDataSyncAdapter:
    """Adapter for existing data synchronization components."""

    def __init__(self,
                 market_data_repo: Optional[MarketDataRepository] = None,
                 broker_adapter=None):
        """Initialize the data sync adapter."""
        self.market_data_repo = market_data_repo or DuckDBMarketDataRepository()
        self.broker_adapter = broker_adapter
        self.sync_service = DataSyncService(self.market_data_repo)

    def convert_pandas_to_domain_entities(self,
                                        df: pd.DataFrame,
                                        symbol: str,
                                        timeframe: str = '1D') -> List[MarketData]:
        """Convert pandas DataFrame to domain MarketData entities."""
        entities = []

        for _, row in df.iterrows():
            try:
                # Create OHLCV entity
                ohlcv = OHLCV(
                    open=Decimal(str(row.get('open', 0))),
                    high=Decimal(str(row.get('high', 0))),
                    low=Decimal(str(row.get('low', 0))),
                    close=Decimal(str(row.get('close', 0))),
                    volume=int(row.get('volume', 0))
                )

                # Create MarketData entity
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=pd.to_datetime(row.get('timestamp')).to_pydatetime(),
                    timeframe=timeframe,
                    ohlcv=ohlcv,
                    date_partition=pd.to_datetime(row.get('timestamp')).date()
                )

                entities.append(market_data)

            except Exception as e:
                logger.error(f"Error converting row to MarketData entity: {e}")
                continue

        return entities

    async def sync_today_intraday_data(self,
                                     symbols: Optional[List[str]] = None,
                                     max_symbols: Optional[int] = None) -> Dict[str, Any]:
        """
        Sync today's intraday data using the legacy sync component.

        Args:
            symbols: List of symbols to sync (optional)
            max_symbols: Maximum number of symbols to process

        Returns:
            Sync statistics
        """
        try:
            # Import the legacy sync module
            from src.infrastructure.external.data_sync.historical.sync_today_intraday_duckdb import TodayIntradaySync

            # Create legacy sync instance
            legacy_sync = TodayIntradaySync()

            # Get symbols if not provided
            if symbols is None:
                symbols = legacy_sync.get_available_symbols()

            if max_symbols:
                symbols = symbols[:max_symbols]

            # Run legacy sync
            success = legacy_sync.run_sync(symbols=symbols, max_symbols=max_symbols)

            # Get basic stats (legacy sync doesn't return detailed stats)
            stats = {
                'total_symbols': len(symbols) if symbols else 0,
                'processed_symbols': len(symbols) if symbols else 0,
                'successful_syncs': len(symbols) if success else 0,
                'failed_syncs': 0 if success else len(symbols) if symbols else 0,
                'total_records': 0,  # Legacy sync doesn't track this
                'start_time': datetime.now(),
                'end_time': datetime.now(),
                'duration_seconds': 0.0,
                'errors': [] if success else [{'error': 'Sync failed'}],
                'method': 'legacy_intraday'
            }

            logger.info(f"Legacy intraday sync completed: {stats['successful_syncs']}/{stats['total_symbols']} successful")

            return stats

        except Exception as e:
            logger.error(f"Error in legacy intraday sync: {e}")
            return {
                'total_symbols': len(symbols) if symbols else 0,
                'processed_symbols': 0,
                'successful_syncs': 0,
                'failed_syncs': len(symbols) if symbols else 0,
                'total_records': 0,
                'start_time': datetime.now(),
                'end_time': datetime.now(),
                'duration_seconds': 0.0,
                'errors': [{'error': str(e)}],
                'method': 'legacy_intraday'
            }

    async def sync_historical_data_with_broker(self,
                                             symbols: List[str],
                                             start_date: date,
                                             end_date: date,
                                             timeframe: str = '1D') -> Dict[str, Any]:
        """
        Sync historical data using broker adapter.

        Args:
            symbols: List of symbols to sync
            start_date: Start date for data
            end_date: End date for data
            timeframe: Data timeframe

        Returns:
            Sync statistics
        """
        if not self.broker_adapter:
            raise ValueError("Broker adapter not configured")

        stats = {
            'total_symbols': len(symbols),
            'processed_symbols': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'total_records': 0,
            'start_time': datetime.now(),
            'errors': [],
            'method': 'broker_historical'
        }

        logger.info(f"Starting broker historical sync for {len(symbols)} symbols")

        for symbol in symbols:
            try:
                # Get historical data from broker
                if hasattr(self.broker_adapter, 'get_historical_data'):
                    data = self.broker_adapter.get_historical_data(
                        symbol=symbol,
                        exchange="NSE",
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date
                    )

                    if data is not None and not data.empty:
                        # Convert to domain entities
                        entities = self.convert_pandas_to_domain_entities(data, symbol, timeframe)

                        # Save to repository
                        saved_count = 0
                        for entity in entities:
                            try:
                                self.market_data_repo.save(entity)
                                saved_count += 1
                            except Exception as e:
                                logger.error(f"Error saving {symbol} data: {e}")

                        stats['total_records'] += saved_count
                        stats['successful_syncs'] += 1
                        logger.info(f"Synced {saved_count} records for {symbol}")
                    else:
                        stats['failed_syncs'] += 1
                        stats['errors'].append({
                            'symbol': symbol,
                            'error': 'No data returned from broker'
                        })
                else:
                    stats['failed_syncs'] += 1
                    stats['errors'].append({
                        'symbol': symbol,
                        'error': 'Broker adapter does not support historical data'
                    })

            except Exception as e:
                logger.error(f"Error syncing {symbol}: {e}")
                stats['failed_syncs'] += 1
                stats['errors'].append({
                    'symbol': symbol,
                    'error': str(e)
                })

            stats['processed_symbols'] += 1

        stats['end_time'] = datetime.now()
        stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info(f"Broker historical sync completed: {stats['successful_syncs']}/{stats['total_symbols']} successful")

        return stats

    async def start_realtime_data_stream(self,
                                       symbols: List[str],
                                       callback: Optional[callable] = None) -> bool:
        """
        Start real-time data streaming.

        Args:
            symbols: List of symbols to stream
            callback: Callback function for real-time updates

        Returns:
            True if streaming started successfully
        """
        if not self.broker_adapter:
            raise ValueError("Broker adapter not configured for real-time streaming")

        try:
            # Start real-time sync using the domain service
            success = await self.sync_service.start_realtime_sync(symbols, callback)

            if success:
                logger.info(f"Started real-time data stream for {len(symbols)} symbols")
            else:
                logger.error("Failed to start real-time data stream")

            return success

        except Exception as e:
            logger.error(f"Error starting real-time stream: {e}")
            return False

    async def stop_realtime_data_stream(self) -> bool:
        """Stop real-time data streaming."""
        try:
            success = await self.sync_service.stop_realtime_sync()

            if success:
                logger.info("Stopped real-time data stream")
            else:
                logger.error("Failed to stop real-time data stream")

            return success

        except Exception as e:
            logger.error(f"Error stopping real-time stream: {e}")
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return self.sync_service.get_sync_status()

    async def sync_missing_data(self,
                              symbols: List[str],
                              start_date: date,
                              end_date: date,
                              timeframe: str = '1D') -> Dict[str, Any]:
        """
        Sync missing data by comparing what exists vs what should exist.

        Args:
            symbols: List of symbols to check
            start_date: Start date for data range
            end_date: End date for data range
            timeframe: Data timeframe

        Returns:
            Sync statistics for missing data
        """
        stats = {
            'total_symbols': len(symbols),
            'symbols_with_missing_data': 0,
            'total_missing_records': 0,
            'records_synced': 0,
            'start_time': datetime.now(),
            'errors': []
        }

        logger.info(f"Checking for missing data in {len(symbols)} symbols")

        for symbol in symbols:
            try:
                # Get existing data for this symbol and date range
                existing_data = self.market_data_repo.find_by_symbol_and_date_range(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=timeframe
                )

                # Calculate expected number of records
                # This is a simplified calculation - in practice you'd need
                # to know trading days, market hours, etc.
                date_diff = (end_date - start_date).days
                expected_records = max(1, date_diff)  # At least 1 record per day

                existing_count = len(existing_data)
                missing_count = max(0, expected_records - existing_count)

                if missing_count > 0:
                    stats['symbols_with_missing_data'] += 1
                    stats['total_missing_records'] += missing_count

                    logger.info(f"{symbol}: {existing_count}/{expected_records} records ({missing_count} missing)")

                    # Here you could implement logic to fetch the missing data
                    # For now, just log the missing data
                else:
                    logger.debug(f"{symbol}: Complete ({existing_count} records)")

            except Exception as e:
                logger.error(f"Error checking missing data for {symbol}: {e}")
                stats['errors'].append({
                    'symbol': symbol,
                    'error': str(e)
                })

        stats['end_time'] = datetime.now()
        stats['duration_seconds'] = (stats['end_time'] - stats['start_time']).total_seconds()

        logger.info(f"Missing data check completed: {stats['symbols_with_missing_data']}/{stats['total_symbols']} symbols have missing data")

        return stats
