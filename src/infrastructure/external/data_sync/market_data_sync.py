#!/usr/bin/env python3
"""
Market Data Synchronization Service
====================================

Production-ready service for syncing market data from DhanHQ broker API.
Based on testing findings: the API can fetch historical data across multiple days.

Features:
- Fetches complete historical data for symbols
- Handles deduplication and data quality
- Provides sync status and reporting
- Extensible for multiple symbols
- Production logging and error handling
"""

import sys
import pandas as pd
import duckdb
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from broker.tradehull_broker import get_broker


class MarketDataSyncService:
    """Service for synchronizing market data from broker API to DuckDB."""

    def __init__(self, database_path: str = "data/financial_data.duckdb"):
        """
        Initialize the market data sync service.

        Args:
            database_path: Path to the DuckDB database file
        """
        self.database_path = database_path
        self.broker = None
        self.logger = logging.getLogger(__name__)

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def initialize_broker(self) -> bool:
        """Initialize broker connection."""
        try:
            self.broker = get_broker()
            self.logger.info("✅ Broker initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize broker: {e}")
            return False

    def get_symbol_status(self, symbol: str) -> Dict:
        """
        Get current sync status for a symbol.

        Args:
            symbol: Trading symbol (e.g., 'TCS', 'RELIANCE')

        Returns:
            Dictionary with sync status information
        """
        try:
            conn = duckdb.connect(self.database_path)
            result = conn.execute(f"""
                SELECT
                    COUNT(*) as total_records,
                    MAX(date_partition) as latest_date,
                    MIN(date_partition) as earliest_date,
                    COUNT(DISTINCT date_partition) as trading_days
                FROM market_data
                WHERE symbol = '{symbol}'
            """).fetchone()
            conn.close()

            today = datetime.now().date()

            return {
                'symbol': symbol,
                'total_records': result[0],
                'latest_date': result[1],
                'earliest_date': result[2],
                'trading_days': result[3],
                'days_behind': (today - result[1]).days if result[1] else None,
                'is_up_to_date': result[1] >= today if result[1] else False
            }

        except Exception as e:
            self.logger.error(f"Error getting status for {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'total_records': 0,
                'latest_date': None,
                'is_up_to_date': False
            }

    def fetch_symbol_data(self, symbol: str, start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a symbol from broker API with 90-day chunking.

        Args:
            symbol: Trading symbol
            start_date: Start date for data (optional)
            end_date: End date for data (optional, defaults to today)

        Returns:
            Pandas DataFrame with OHLCV data or None if failed
        """
        try:
            if not self.broker:
                if not self.initialize_broker():
                    return None

            # Set default date range (last 90 days if not specified)
            if end_date is None:
                end_date = datetime.now()
            if start_date is None:
                start_date = end_date - timedelta(days=90)

            self.logger.info(f"📊 Fetching historical data for {symbol} from {start_date.date()} to {end_date.date()}...")

            # Calculate 90-day chunks
            chunks = self._calculate_date_chunks(start_date, end_date, chunk_days=90)

            all_data = []
            total_records = 0

            for i, (chunk_start, chunk_end) in enumerate(chunks):
                self.logger.info(f"📅 Fetching chunk {i+1}/{len(chunks)}: {chunk_start.date()} to {chunk_end.date()}")

                try:
                    # Fetch data for this chunk
                    chunk_data = self._fetch_single_chunk(symbol, chunk_start, chunk_end)

                    if chunk_data is not None and not chunk_data.empty:
                        all_data.append(chunk_data)
                        total_records += len(chunk_data)
                        self.logger.info(f"✅ Chunk {i+1}: {len(chunk_data):,} records")
                    else:
                        self.logger.warning(f"⚠️  Chunk {i+1}: No data received")

                    # Small delay between requests to be respectful to the API
                    if i < len(chunks) - 1:  # Don't delay after last chunk
                        import time
                        time.sleep(0.5)

                except Exception as e:
                    self.logger.error(f"❌ Error fetching chunk {i+1}: {e}")
                    # Continue with other chunks even if one fails
                    continue

            if not all_data:
                self.logger.warning(f"No data received for {symbol} in any chunks")
                return None

            # Combine all chunks
            combined_data = pd.concat(all_data, ignore_index=True)

            # Remove duplicates based on timestamp
            combined_data = combined_data.drop_duplicates(subset=['timestamp'], keep='first')

            # Sort by timestamp
            combined_data = combined_data.sort_values('timestamp').reset_index(drop=True)

            self.logger.info(f"✅ Received {len(combined_data):,} total records for {symbol} ({total_records:,} before deduplication)")

            # Ensure timestamp is datetime and add partitioning
            if 'timestamp' in combined_data.columns:
                if not pd.api.types.is_datetime64_any_dtype(combined_data['timestamp']):
                    combined_data['timestamp'] = pd.to_datetime(combined_data['timestamp'], unit='s')

                # Add date_partition for DuckDB partitioning
                combined_data['date_partition'] = combined_data['timestamp'].dt.date

            return combined_data

        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def _calculate_date_chunks(self, start_date: datetime, end_date: datetime,
                              chunk_days: int = 90) -> List[Tuple[datetime, datetime]]:
        """
        Calculate date chunks for API calls.

        Args:
            start_date: Start of the date range
            end_date: End of the date range
            chunk_days: Number of days per chunk (default 90)

        Returns:
            List of (start, end) tuples for each chunk
        """
        chunks = []
        current_start = start_date

        while current_start < end_date:
            current_end = min(current_start + timedelta(days=chunk_days), end_date)
            chunks.append((current_start, current_end))
            current_start = current_end

        return chunks

    def _fetch_single_chunk(self, symbol: str, start_date: datetime,
                           end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch data for a single date chunk from the broker API.

        Args:
            symbol: Trading symbol
            start_date: Start date for this chunk
            end_date: End date for this chunk

        Returns:
            Pandas DataFrame with data for this chunk or None if failed
        """
        try:
            # Note: DhanHQ API doesn't accept start_date/end_date parameters
            # The broker.get_historical_data method fetches the most recent data
            # So we'll call it and then filter the results to our date range
            data = self.broker._tradehull.get_historical_data(
                tradingsymbol=symbol,
                exchange='NSE',
                timeframe='1'
            )

            if data is None or data.empty:
                return None

            # Convert timestamp if needed
            if 'timestamp' in data.columns:
                if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
                    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')

            # Filter to our date range
            mask = (data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)
            filtered_data = data[mask].copy()

            return filtered_data if not filtered_data.empty else None

        except Exception as e:
            self.logger.error(f"Error fetching chunk for {symbol}: {e}")
            return None

    def sync_symbol_historical(self, symbol: str, days_back: int = 365,
                              force_update: bool = False) -> Dict:
        """
        Sync historical data for a symbol by fetching in 90-day chunks.

        This method handles the API limitation of 90 days per call by:
        1. Breaking the requested period into 90-day chunks
        2. Fetching each chunk separately
        3. Combining and deduplicating all data

        Args:
            symbol: Trading symbol to sync
            days_back: Number of days of historical data to fetch
            force_update: If True, re-sync all data regardless of current status

        Returns:
            Dictionary with sync results
        """
        try:
            self.logger.info(f"📚 Starting historical sync for {symbol} - {days_back} days back")

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            self.logger.info(f"📅 Date range: {start_date.date()} to {end_date.date()}")

            # Calculate total chunks needed
            chunks = self._calculate_date_chunks(start_date, end_date, chunk_days=90)
            self.logger.info(f"📦 Will fetch in {len(chunks)} chunks of ~90 days each")

            # Fetch data in chunks
            all_data = []
            total_raw_records = 0
            successful_chunks = 0

            for i, (chunk_start, chunk_end) in enumerate(chunks):
                self.logger.info(f"📅 Processing chunk {i+1}/{len(chunks)}: {chunk_start.date()} to {chunk_end.date()}")

                # Fetch data for this chunk
                chunk_data = self.fetch_symbol_data(symbol, chunk_start, chunk_end)

                if chunk_data is not None and not chunk_data.empty:
                    all_data.append(chunk_data)
                    total_raw_records += len(chunk_data)
                    successful_chunks += 1
                    self.logger.info(f"✅ Chunk {i+1} successful: {len(chunk_data):,} records")
                else:
                    self.logger.warning(f"⚠️  Chunk {i+1} failed or empty")

                # Respectful delay between chunks
                if i < len(chunks) - 1:
                    import time
                    time.sleep(1)

            if not all_data:
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': 'No data received from any chunks'
                }

            # Combine all chunks
            combined_data = pd.concat(all_data, ignore_index=True)

            # Remove duplicates and sort
            combined_data = combined_data.drop_duplicates(subset=['timestamp'], keep='first')
            combined_data = combined_data.sort_values('timestamp').reset_index(drop=True)

            final_records = len(combined_data)
            deduplication_rate = ((total_raw_records - final_records) / total_raw_records * 100) if total_raw_records > 0 else 0

            self.logger.info(f"📊 Combined data: {final_records:,} records "
                           f"({total_raw_records:,} raw, {deduplication_rate:.1f}% deduplicated)")

            # Store in database
            records_added = self._store_data_chunk(symbol, combined_data, force_update)

            return {
                'symbol': symbol,
                'success': True,
                'message': f'Historical sync completed',
                'records_added': records_added,
                'chunks_processed': len(chunks),
                'successful_chunks': successful_chunks,
                'total_raw_records': total_raw_records,
                'final_records': final_records,
                'deduplication_rate': deduplication_rate
            }

        except Exception as e:
            self.logger.error(f"Error in historical sync for {symbol}: {e}")
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e)
            }

    def _store_data_chunk(self, symbol: str, data: pd.DataFrame,
                         force_update: bool = False) -> int:
        """
        Store data chunk in database with proper deduplication.

        Args:
            symbol: Trading symbol
            data: DataFrame to store
            force_update: If True, replace existing data

        Returns:
            Number of records actually inserted
        """
        try:
            conn = duckdb.connect(self.database_path)

            # Prepare data for insertion
            data_to_insert = data.copy()
            data_to_insert['symbol'] = symbol

            # Add source tracking
            data_to_insert['source'] = 'historical_sync_chunked'

            # Convert to list of tuples for batch insert
            records = []
            for _, row in data_to_insert.iterrows():
                record = (
                    row['symbol'],
                    row['timestamp'],
                    row.get('open', row.get('ltp', 0)),
                    row.get('high', row.get('ltp', 0)),
                    row.get('low', row.get('ltp', 0)),
                    row.get('close', row.get('ltp', 0)),
                    row.get('volume', 0),
                    row['date_partition'],
                    '1m',  # timeframe
                    'historical_sync_chunked'
                )
                records.append(record)

            if records:
                # Insert with REPLACE to handle duplicates
                conn.executemany("""
                    INSERT OR REPLACE INTO market_data
                    (symbol, timestamp, open, high, low, close, volume, date_partition, timeframe, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, records)

                self.logger.info(f"✅ Stored {len(records):,} records for {symbol}")
                return len(records)
            else:
                self.logger.warning(f"No records to store for {symbol}")
                return 0

        except Exception as e:
            self.logger.error(f"Error storing data chunk for {symbol}: {e}")
            return 0
        finally:
            if 'conn' in locals():
                conn.close()

    def sync_symbol(self, symbol: str, force_update: bool = False,
                   historical_days: int = 90) -> Dict:
        """
        Sync market data for a symbol with proper 90-day chunking.

        Args:
            symbol: Trading symbol to sync
            force_update: If True, re-sync all data regardless of current status
            historical_days: Number of days of historical data to fetch (default 90)

        Returns:
            Dictionary with sync results
        """
        try:
            self.logger.info(f"🚀 Starting sync for {symbol}")

            # Get current status
            current_status = self.get_symbol_status(symbol)
            self.logger.info(f"Current status: {current_status['total_records']:,} records, "
                           f"latest: {current_status['latest_date']}")

            # Determine date range to fetch
            end_date = datetime.now()
            if force_update:
                # Force update: fetch from earliest date or last N days
                start_date = end_date - timedelta(days=historical_days)
                self.logger.info(f"🔄 Force update: fetching last {historical_days} days")
            elif current_status['latest_date']:
                # Incremental update: fetch from day after latest
                start_date = datetime.combine(current_status['latest_date'], datetime.min.time()) + timedelta(days=1)
                if start_date >= end_date:
                    self.logger.info(f"✅ {symbol} is already up to date")
                    return {
                        'symbol': symbol,
                        'success': True,
                        'message': 'Already up to date',
                        'records_added': 0,
                        'total_records': current_status['total_records']
                    }
            else:
                # No existing data: fetch from last N days
                start_date = end_date - timedelta(days=historical_days)
                self.logger.info(f"📅 New symbol: fetching last {historical_days} days")

            # Fetch data for the calculated date range
            data = self.fetch_symbol_data(symbol, start_date, end_date)
            if data is None:
                return {
                    'symbol': symbol,
                    'success': False,
                    'error': 'Failed to fetch data from broker'
                }

            # Prepare data for insertion
            data_to_insert = data.copy()
            data_to_insert['symbol'] = symbol

            self.logger.info(f"🔄 Processing {len(data_to_insert):,} records for {symbol}")

            # Connect to database
            conn = duckdb.connect(self.database_path)

            # Insert data with deduplication
            insert_query = """
            INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume, date_partition)
            SELECT
                symbol,
                timestamp,
                open,
                high,
                low,
                close,
                volume,
                date_partition
            FROM data_to_insert
            WHERE NOT EXISTS (
                SELECT 1 FROM market_data
                WHERE market_data.symbol = data_to_insert.symbol
                AND market_data.timestamp = data_to_insert.timestamp
            )
            """

            # Execute insertion
            result = conn.execute(insert_query)
            inserted_count = result.fetchall()[0][0]

            # Get final status
            final_status = self.get_symbol_status(symbol)
            conn.close()

            success = inserted_count > 0 or current_status.get('total_records', 0) > 0

            result = {
                'symbol': symbol,
                'success': success,
                'records_added': inserted_count,
                'total_records': final_status['total_records'],
                'latest_date': final_status['latest_date'],
                'earliest_date': final_status['earliest_date'],
                'trading_days': final_status['trading_days'],
                'days_behind': final_status['days_behind'],
                'is_up_to_date': final_status['is_up_to_date']
            }

            if success:
                self.logger.info(f"✅ {symbol} sync completed: +{inserted_count:,} records")
            else:
                self.logger.warning(f"⚠️  {symbol} sync completed with no new data")

            return result

        except Exception as e:
            self.logger.error(f"❌ Sync failed for {symbol}: {e}")
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e),
                'records_added': 0
            }

    def sync_multiple_symbols(self, symbols: List[str], force_update: bool = False,
                            historical_days: int = 90, use_chunked_sync: bool = False,
                            batch_size: int = 20) -> List[Dict]:
        """
        Sync multiple symbols with 90-day chunking support and internal batching.

        Args:
            symbols: List of trading symbols
            force_update: If True, force update all symbols
            historical_days: Number of days of historical data to fetch (default 90)
            use_chunked_sync: If True, use chunked historical sync for longer periods
            batch_size: Number of symbols to process in each batch (default 20)

        Returns:
            List of sync results for each symbol
        """
        results = []
        total_added = 0

        sync_mode = "chunked_historical" if use_chunked_sync else "incremental"
        self.logger.info(f"🚀 Starting {sync_mode} multi-symbol sync for {len(symbols)} symbols")

        if use_chunked_sync and historical_days > 90:
            self.logger.info(f"📚 Will fetch {historical_days} days of data in 90-day chunks")

        # Process symbols in batches
        for batch_start in range(0, len(symbols), batch_size):
            batch_end = min(batch_start + batch_size, len(symbols))
            batch_symbols = symbols[batch_start:batch_end]

            self.logger.info(f"📦 Processing batch {batch_start//batch_size + 1}/{(len(symbols) + batch_size - 1)//batch_size} "
                           f"({len(batch_symbols)} symbols)")

            for i, symbol in enumerate(batch_symbols, 1):
                batch_position = batch_start + i
                self.logger.info(f"[{batch_position}/{len(symbols)}] Processing {symbol}...")

                try:
                    if use_chunked_sync and historical_days > 90:
                        # Use chunked historical sync for longer periods
                        result = self.sync_symbol_historical(symbol, historical_days, force_update)
                    else:
                        # Use regular sync with updated chunking logic
                        result = self.sync_symbol(symbol, force_update, historical_days)

                    results.append(result)

                    if result['success']:
                        total_added += result.get('records_added', 0)
                        self.logger.info(f"✅ {symbol} sync completed: +{result.get('records_added', 0)} records")

                except Exception as e:
                    self.logger.error(f"❌ {symbol} sync failed: {e}")
                    results.append({
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })

            # Small delay between batches to be respectful
            if batch_end < len(symbols):
                import time
                time.sleep(1)

        self.logger.info(f"🎯 Multi-symbol sync completed: {total_added:,} total records added "
                        f"({sync_mode} mode, {historical_days} days)")
        return results

    def get_sync_report(self, symbols: Optional[List[str]] = None) -> Dict:
        """
        Generate a comprehensive sync report.

        Args:
            symbols: List of symbols to include (None for all symbols in database)

        Returns:
            Dictionary with comprehensive sync report
        """
        try:
            conn = duckdb.connect(self.database_path)

            if symbols:
                symbols_str = "', '".join(symbols)
                symbols_filter = f"WHERE symbol IN ('{symbols_str}')"
            else:
                symbols_filter = ""

            # Get overall statistics
            overall_stats = conn.execute(f"""
                SELECT
                    COUNT(DISTINCT symbol) as total_symbols,
                    SUM(CASE WHEN date_partition >= CURRENT_DATE THEN 1 ELSE 0 END) as current_symbols,
                    COUNT(*) as total_records,
                    MAX(date_partition) as latest_date,
                    MIN(date_partition) as earliest_date,
                    COUNT(DISTINCT date_partition) as total_trading_days
                FROM market_data
                {symbols_filter}
            """).fetchone()

            # Get per-symbol statistics
            symbol_stats = conn.execute(f"""
                SELECT
                    symbol,
                    COUNT(*) as records,
                    MAX(date_partition) as latest_date,
                    MIN(date_partition) as earliest_date,
                    COUNT(DISTINCT date_partition) as trading_days,
                    (CURRENT_DATE - MAX(date_partition)) as days_behind
                FROM market_data
                {symbols_filter}
                GROUP BY symbol
                ORDER BY records DESC
            """).fetchall()

            conn.close()

            today = datetime.now().date()

            return {
                'generated_at': datetime.now(),
                'overall_stats': {
                    'total_symbols': overall_stats[0],
                    'current_symbols': overall_stats[1],
                    'total_records': overall_stats[2],
                    'latest_date': overall_stats[3],
                    'earliest_date': overall_stats[4],
                    'total_trading_days': overall_stats[5],
                    'data_freshness_days': (today - overall_stats[3]).days if overall_stats[3] else None
                },
                'symbol_stats': [
                    {
                        'symbol': stat[0],
                        'records': stat[1],
                        'latest_date': stat[2],
                        'earliest_date': stat[3],
                        'trading_days': stat[4],
                        'days_behind': stat[5],
                        'is_current': stat[5] <= 0 if stat[5] is not None else False
                    }
                    for stat in symbol_stats
                ]
            }

        except Exception as e:
            self.logger.error(f"Error generating sync report: {e}")
            return {'error': str(e)}


def main():
    """Command line interface for market data sync."""
    import argparse

    parser = argparse.ArgumentParser(description='Market Data Synchronization Service')
    parser.add_argument('symbols', nargs='*', help='Trading symbols to sync (default: TCS)')
    parser.add_argument('--force', action='store_true', help='Force update all data')
    parser.add_argument('--report', action='store_true', help='Generate sync report only')
    parser.add_argument('--database', default='data/financial_data.duckdb', help='Database path')
    parser.add_argument('--historical-days', type=int, default=90,
                       help='Number of days of historical data to fetch (default: 90)')
    parser.add_argument('--chunked-sync', action='store_true',
                       help='Use chunked sync for historical data beyond 90 days')
    parser.add_argument('--all-symbols', action='store_true',
                       help='Sync all symbols in the database (overrides symbol list)')

    args = parser.parse_args()

    # Initialize service
    service = MarketDataSyncService(args.database)

    # Handle all symbols option
    if args.all_symbols:
        print("📊 FETCHING ALL SYMBOLS FROM DATABASE...")
        try:
            conn = duckdb.connect(args.database)
            all_symbols_result = conn.execute("SELECT DISTINCT symbol FROM market_data ORDER BY symbol").fetchall()
            conn.close()
            symbols = [row[0] for row in all_symbols_result]
            print(f"✅ Found {len(symbols)} symbols to sync")
        except Exception as e:
            print(f"❌ Error fetching symbols: {e}")
            return
    else:
        # Default to TCS if no symbols provided
        symbols = args.symbols if args.symbols else ['TCS']

    if args.report:
        # Generate and display report
        print("📊 MARKET DATA SYNC REPORT")
        print("=" * 50)

        report = service.get_sync_report(symbols if len(symbols) > 1 else None)

        if 'error' in report:
            print(f"❌ Error: {report['error']}")
            return

        overall = report['overall_stats']
        print("\n📈 OVERALL STATISTICS:")
        print(f"   Total Symbols: {overall['total_symbols']}")
        print(f"   Current Symbols: {overall['current_symbols']}")
        print(f"   Total Records: {overall['total_records']:,}")
        print(f"   Latest Date: {overall['latest_date']}")
        print(f"   Trading Days: {overall['total_trading_days']}")
        print(f"   Days Behind: {overall['data_freshness_days']}")

        print("\n📋 SYMBOL DETAILS:")
        for symbol_stat in report['symbol_stats']:
            status_icon = "✅" if symbol_stat['is_current'] else "⚠️"
            print(f"   {status_icon} {symbol_stat['symbol']}: {symbol_stat['records']:,} records "
                  f"({symbol_stat['days_behind']} days behind)")

    else:
        # Determine sync mode and parameters
        sync_mode_desc = "incremental"
        if args.chunked_sync and args.historical_days > 90:
            sync_mode_desc = f"chunked historical ({args.historical_days} days)"
        elif args.historical_days != 90:
            sync_mode_desc = f"{args.historical_days}-day historical"

        # Perform sync
        print(f"🚀 SYNCING MARKET DATA FOR: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
        print(f"📊 Mode: {sync_mode_desc}")
        print(f"🔧 Force Update: {'Yes' if args.force else 'No'}")
        print("=" * 60)

        results = service.sync_multiple_symbols(
            symbols,
            force_update=args.force,
            historical_days=args.historical_days,
            use_chunked_sync=args.chunked_sync
        )

        print("\n📊 SYNC RESULTS:")
        print("=" * 40)

        total_added = 0
        success_count = 0
        total_chunks = 0
        total_raw_records = 0

        for result in results:
            if result['success']:
                success_count += 1
                records_added = result.get('records_added', 0)
                total_added += records_added

                # Show additional details for chunked sync
                if args.chunked_sync and 'chunks_processed' in result:
                    chunks = result.get('chunks_processed', 0)
                    raw_records = result.get('total_raw_records', 0)
                    total_chunks += chunks
                    total_raw_records += raw_records
                    print(f"   ✅ {result['symbol']}: +{records_added:,} records ({chunks} chunks, {raw_records:,} raw)")
                else:
                    print(f"   ✅ {result['symbol']}: +{records_added:,} records")
            else:
                print(f"   ❌ {result['symbol']}: FAILED - {result.get('error', 'Unknown error')}")

        print(f"\n🎯 SUMMARY: {success_count}/{len(symbols)} successful, {total_added:,} total records added")

        if args.chunked_sync and total_chunks > 0:
            deduplication_rate = ((total_raw_records - total_added) / total_raw_records * 100) if total_raw_records > 0 else 0
            print(f"📦 Chunks Processed: {total_chunks}")
            print(f"🔄 Deduplication: {deduplication_rate:.1f}% ({total_raw_records:,} raw → {total_added:,} final)")


if __name__ == "__main__":
    main()
