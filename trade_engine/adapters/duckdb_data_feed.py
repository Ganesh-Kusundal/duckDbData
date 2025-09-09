"""
DuckDB Data Feed Adapter
======================

Implements DataFeedPort using DuckDB for historical data.
Supports both backtest (deterministic replay) and live extensions.
"""

import duckdb
from typing import AsyncIterable, List
from datetime import date, time
from decimal import Decimal
import asyncio
import os

from ..domain.models import Bar
from ..ports.data_feed import DataFeedPort


class DuckDBDataFeed(DataFeedPort):
    """DuckDB-based data feed implementation"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        self._ensure_connection()

    def _ensure_connection(self):
        """Ensure database connection exists"""
        if self._conn is None:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"Database not found: {self.db_path}")
            self._conn = duckdb.connect(self.db_path, read_only=True)
            self._conn.execute("SET memory_limit='2GB'")
            self._conn.execute("SET threads=2")

    async def subscribe(self, symbols: List[str], timeframe: str) -> AsyncIterable[Bar]:
        """
        Subscribe to historical bars (for backtesting).
        In live mode, this would connect to real-time feeds.
        """
        # For backtesting, we return historical data as async stream
        for symbol in symbols:
            bars = self.get_historical_bars(symbol, date.min, date.max, timeframe)
            for bar in bars:
                yield bar
                await asyncio.sleep(0)  # Allow other coroutines

    def get_historical_bars(self, symbol: str, start_date: date,
                           end_date: date, timeframe: str,
                           start_time: time = None, end_time: time = None) -> List[Bar]:
        """
        Get historical bars from DuckDB

        Note: This assumes your existing market_data table structure
        """
        self._ensure_connection()

        query = """
        SELECT
            timestamp,
            symbol,
            open,
            high,
            low,
            close,
            volume,
            date_partition
        FROM market_data
        WHERE symbol = ?
          AND date_partition BETWEEN ? AND ?
        ORDER BY timestamp
        """

        params = [symbol, start_date.isoformat(), end_date.isoformat()]

        # Add time filters if specified
        if start_time and end_time:
            query += " AND CAST(timestamp AS TIME) BETWEEN ? AND ?"
            params.extend([start_time.isoformat(), end_time.isoformat()])

        try:
            result = self._conn.execute(query, params).fetchall()

            bars = []
            for row in result:
                bar = Bar(
                    timestamp=row[0],  # Assuming timestamp is datetime
                    symbol=row[1],
                    open=Decimal(str(row[2])),
                    high=Decimal(str(row[3])),
                    low=Decimal(str(row[4])),
                    close=Decimal(str(row[5])),
                    volume=int(row[6]),
                    timeframe=timeframe
                )
                bars.append(bar)

            return bars

        except Exception as e:
            print(f"Error fetching bars for {symbol}: {e}")
            return []

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        self._ensure_connection()

        try:
            result = self._conn.execute("""
                SELECT DISTINCT symbol
                FROM market_data
                ORDER BY symbol
            """).fetchall()

            return [row[0] for row in result]

        except Exception as e:
            print(f"Error fetching symbols: {e}")
            return []

    def __del__(self):
        """Cleanup connection"""
        if self._conn:
            self._conn.close()
