#!/usr/bin/env python3
"""
Sync Today's Intraday Data to DuckDB
Fetches today's 1-minute intraday data and inserts missing records into DuckDB.

Features:
- Gets today's intraday data only (no fallback to yesterday)
- Checks for existing data in DuckDB to avoid duplicates
- Inserts only missing 1-minute records
- Handles broker API limitations gracefully
- Comprehensive logging and error handling
"""

import os
import sys
import datetime
import pandas as pd
from pathlib import Path
from typing import List, Optional, Tuple
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from broker import get_broker
from core.duckdb_infra.database import DuckDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TodayIntradaySync:
    """Handles syncing today's intraday data to DuckDB."""

    def __init__(self, db_path: str = "data/financial_data.duckdb"):
        """
        Initialize the intraday sync handler.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_manager = DuckDBManager(db_path=db_path)
        self.broker = None
        self.today = datetime.date.today()

        logger.info(f"Initialized TodayIntradaySync for {self.today}")

    def connect_broker(self):
        """Connect to the broker."""
        try:
            logger.info("🔗 Connecting to broker...")
            self.broker = get_broker()
            logger.info("✅ Broker connected successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to broker: {e}")
            return False

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols from DuckDB."""
        try:
            logger.info("🔍 Getting available symbols from DuckDB...")
            symbols = self.db_manager.get_available_symbols()
            logger.info(f"📊 Found {len(symbols)} symbols in database")
            return symbols
        except Exception as e:
            logger.error(f"❌ Failed to get symbols from database: {e}")
            return []

    def get_today_intraday_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get today's intraday data from broker.

        Args:
            symbol: Trading symbol

        Returns:
            DataFrame with today's intraday data or None if failed
        """
        try:
            logger.debug(f"📈 Fetching today's intraday data for {symbol}")

            # Get intraday data (1-minute intervals) - this is the key difference
            # We want today's 1-minute data, not historical daily data
            data = self.broker.get_intraday_data(symbol, "NSE", 1)  # 1-minute timeframe

            if data is not None and not data.empty:
                logger.debug(f"✅ Retrieved {len(data)} intraday records for {symbol}")

                # Ensure we have the required columns
                required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                if not all(col in data.columns for col in required_cols):
                    logger.error(f"❌ Missing required columns in intraday data for {symbol}")
                    return None

                # Filter to today's data only
                data_copy = data.copy()
                data_copy['date'] = pd.to_datetime(data_copy['timestamp']).dt.date
                today_data = data_copy[data_copy['date'] == self.today]

                if not today_data.empty:
                    # Remove temporary date column and return
                    today_data = today_data.drop('date', axis=1)
                    logger.info(f"✅ Found {len(today_data)} today's intraday records for {symbol}")
                    return today_data
                else:
                    logger.info(f"ℹ️ No today's intraday data found for {symbol}")
                    return None
            else:
                logger.warning(f"⚠️ No intraday data returned for {symbol}")
                return None

        except Exception as e:
            error_msg = str(e).lower()
            if 'dh-905' in error_msg or 'no data present' in error_msg:
                logger.info(f"ℹ️ No intraday data available for {symbol} today (market may still be open)")
                return None
            elif 'input_exception' in error_msg:
                logger.warning(f"⚠️ Invalid parameters for {symbol}: {e}")
                return None
            else:
                logger.error(f"❌ Error getting intraday data for {symbol}: {e}")
                return None

    def get_existing_today_data(self, symbol: str) -> pd.DataFrame:
        """
        Get existing today's data for a symbol from DuckDB.

        Args:
            symbol: Trading symbol

        Returns:
            DataFrame with existing today's data
        """
        try:
            # Query existing data for today
            existing_data = self.db_manager.query_market_data(
                symbol=symbol,
                start_date=self.today,
                end_date=self.today
            )

            logger.debug(f"📊 Found {len(existing_data)} existing records for {symbol} today")
            return existing_data

        except Exception as e:
            logger.error(f"❌ Error querying existing data for {symbol}: {e}")
            return pd.DataFrame()

    def get_missing_timestamps(self, symbol: str, new_data: pd.DataFrame) -> pd.DataFrame:
        """
        Identify which timestamps are missing from DuckDB.

        Args:
            symbol: Trading symbol
            new_data: New intraday data from broker

        Returns:
            DataFrame with only missing timestamps
        """
        if new_data.empty:
            return pd.DataFrame()

        try:
            # Get existing data
            existing_data = self.get_existing_today_data(symbol)

            if existing_data.empty:
                # No existing data, all new data is missing
                logger.info(f"ℹ️ No existing data for {symbol} today, all {len(new_data)} records are new")
                return new_data

            # Find missing timestamps
            existing_timestamps = set(existing_data['timestamp'])
            new_timestamps = set(new_data['timestamp'])

            missing_timestamps = new_timestamps - existing_timestamps
            missing_data = new_data[new_data['timestamp'].isin(missing_timestamps)]

            if not missing_data.empty:
                logger.info(f"📊 Found {len(missing_data)} missing records for {symbol} today")
            else:
                logger.info(f"✅ All {len(new_data)} records already exist for {symbol} today")

            return missing_data

        except Exception as e:
            logger.error(f"❌ Error identifying missing timestamps for {symbol}: {e}")
            return pd.DataFrame()

    def insert_intraday_data(self, symbol: str, data: pd.DataFrame) -> int:
        """
        Insert intraday data into DuckDB.

        Args:
            symbol: Trading symbol
            data: DataFrame with intraday data

        Returns:
            Number of records inserted
        """
        if data.empty:
            return 0

        try:
            # Prepare data for insertion
            df_insert = data.copy()

            # Add symbol column if not present
            if 'symbol' not in df_insert.columns:
                df_insert['symbol'] = symbol

            # Ensure timestamp is in proper format
            df_insert['timestamp'] = pd.to_datetime(df_insert['timestamp'])

            # Insert into database
            records_inserted = self.db_manager.insert_market_data(df_insert)

            if records_inserted > 0:
                logger.info(f"💾 Successfully inserted {records_inserted} records for {symbol}")
            else:
                logger.info(f"ℹ️ No new records inserted for {symbol} (all duplicates)")

            return records_inserted

        except Exception as e:
            logger.error(f"❌ Error inserting data for {symbol}: {e}")
            return 0

    def sync_symbol_intraday(self, symbol: str) -> dict:
        """
        Sync today's intraday data for a single symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with sync statistics for this symbol
        """
        stats = {
            'symbol': symbol,
            'broker_records': 0,
            'existing_records': 0,
            'missing_records': 0,
            'inserted_records': 0,
            'status': 'failed'
        }

        try:
            logger.info(f"🔄 Processing {symbol}")

            # Get today's intraday data from broker
            broker_data = self.get_today_intraday_data(symbol)
            if broker_data is None or broker_data.empty:
                stats['status'] = 'no_data'
                return stats

            stats['broker_records'] = len(broker_data)

            # Get existing data count
            existing_data = self.get_existing_today_data(symbol)
            stats['existing_records'] = len(existing_data)

            # Find missing data
            missing_data = self.get_missing_timestamps(symbol, broker_data)
            stats['missing_records'] = len(missing_data)

            if missing_data.empty:
                stats['status'] = 'up_to_date'
                logger.info(f"✅ {symbol} is already up to date")
                return stats

            # Insert missing data
            inserted = self.insert_intraday_data(symbol, missing_data)
            stats['inserted_records'] = inserted

            if inserted > 0:
                stats['status'] = 'success'
                logger.info(f"✅ Successfully synced {symbol}")
            else:
                stats['status'] = 'no_insert'

            return stats

        except Exception as e:
            logger.error(f"❌ Error syncing {symbol}: {e}")
            stats['status'] = 'error'
            return stats

    def sync_today_intraday(self, symbols: Optional[List[str]] = None, max_symbols: Optional[int] = None) -> dict:
        """
        Sync today's intraday data for all symbols.

        Args:
            symbols: List of symbols to sync (optional, uses all if None)
            max_symbols: Maximum number of symbols to process (optional)

        Returns:
            Dictionary with overall sync statistics
        """
        overall_stats = {
            'total_symbols': 0,
            'processed_symbols': 0,
            'successful_syncs': 0,
            'up_to_date': 0,
            'no_data': 0,
            'errors': 0,
            'total_broker_records': 0,
            'total_inserted_records': 0,
            'symbol_stats': []
        }

        # Get symbols to process
        if symbols is None:
            symbols = self.get_available_symbols()

        if not symbols:
            logger.error("❌ No symbols available for sync")
            return overall_stats

        # Limit symbols if specified
        if max_symbols:
            symbols = symbols[:max_symbols]
            logger.info(f"🔢 Limited to first {max_symbols} symbols")

        overall_stats['total_symbols'] = len(symbols)

        logger.info(f"🚀 Starting intraday sync for {len(symbols)} symbols on {self.today}")

        # Process each symbol
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"🔄 [{i}/{len(symbols)}] Processing {symbol}")

            symbol_stats = self.sync_symbol_intraday(symbol)
            overall_stats['symbol_stats'].append(symbol_stats)
            overall_stats['processed_symbols'] += 1

            # Update overall stats
            overall_stats['total_broker_records'] += symbol_stats['broker_records']
            overall_stats['total_inserted_records'] += symbol_stats['inserted_records']

            if symbol_stats['status'] == 'success':
                overall_stats['successful_syncs'] += 1
            elif symbol_stats['status'] == 'up_to_date':
                overall_stats['up_to_date'] += 1
            elif symbol_stats['status'] == 'no_data':
                overall_stats['no_data'] += 1
            elif symbol_stats['status'] == 'error':
                overall_stats['errors'] += 1

            # Progress update
            if i % 10 == 0:
                logger.info(f"📊 Progress: {i}/{len(symbols)} symbols processed")

        logger.info("📊 INTRADAY SYNC COMPLETED!")
        logger.info(f"   ✅ Total symbols: {overall_stats['total_symbols']}")
        logger.info(f"   ✅ Processed: {overall_stats['processed_symbols']}")
        logger.info(f"   ✅ Successful syncs: {overall_stats['successful_syncs']}")
        logger.info(f"   ✅ Up to date: {overall_stats['up_to_date']}")
        logger.info(f"   ⚠️  No data: {overall_stats['no_data']}")
        logger.info(f"   ❌ Errors: {overall_stats['errors']}")
        logger.info(f"   📊 Total broker records: {overall_stats['total_broker_records']}")
        logger.info(f"   💾 Total inserted records: {overall_stats['total_inserted_records']}")

        return overall_stats

    def run_sync(self, symbols: Optional[List[str]] = None, max_symbols: Optional[int] = None) -> bool:
        """
        Run the complete intraday sync process.

        Args:
            symbols: List of symbols to sync (optional)
            max_symbols: Maximum number of symbols to process (optional)

        Returns:
            True if sync completed successfully, False otherwise
        """
        try:
            logger.info("🎯 STARTING TODAY'S INTRADAY DATA SYNC")
            logger.info("=" * 60)

            # Connect to broker
            if not self.connect_broker():
                return False

            # Run sync
            stats = self.sync_today_intraday(symbols, max_symbols)

            logger.info("🎯 INTRADAY SYNC SUMMARY")
            logger.info("=" * 60)
            logger.info(f"📅 Date: {self.today}")
            logger.info(f"📊 Symbols processed: {stats['processed_symbols']}/{stats['total_symbols']}")
            logger.info(f"✅ Successful syncs: {stats['successful_syncs']}")
            logger.info(f"✅ Up to date: {stats['up_to_date']}")
            logger.info(f"⚠️  No data available: {stats['no_data']}")
            logger.info(f"❌ Errors: {stats['errors']}")
            logger.info(f"📊 Total broker records fetched: {stats['total_broker_records']}")
            logger.info(f"💾 Total records inserted: {stats['total_inserted_records']}")

            success_rate = (stats['successful_syncs'] / stats['processed_symbols'] * 100) if stats['processed_symbols'] > 0 else 0
            logger.info(f"🎯 Success rate: {success_rate:.1f}%")

            return stats['successful_syncs'] > 0

        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync today's intraday data to DuckDB")
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to sync')
    parser.add_argument('--max-symbols', type=int, help='Maximum number of symbols to process')
    parser.add_argument('--db-path', default='data/financial_data.duckdb', help='Path to DuckDB database')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Create sync handler
    sync_handler = TodayIntradaySync(db_path=args.db_path)

    # Run sync
    success = sync_handler.run_sync(symbols=args.symbols, max_symbols=args.max_symbols)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
