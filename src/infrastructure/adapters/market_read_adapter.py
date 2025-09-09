from __future__ import annotations

from datetime import date, datetime
from typing import List
import pandas as pd

from src.application.ports.market_read_port import MarketReadPort
from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from src.infrastructure.config.settings import get_settings


class DuckDBMarketReadAdapter(MarketReadPort):
    def __init__(self, database_path: str | None = None):
        self._adapter = DuckDBAdapter(database_path=database_path or get_settings().database.path)

    def get_symbols_for_date(self, trading_date: date) -> List[str]:
        df = self._adapter.execute_query(
            """
                SELECT DISTINCT symbol
                FROM market_data_unified
                WHERE date_partition = ?
                ORDER BY symbol
            """,
            [trading_date],
        )
        return df['symbol'].tolist() if not df.empty else []

    def get_minute_data(
        self,
        symbol: str,
        trading_date: date,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        return self._adapter.execute_query(
            """
                SELECT timestamp, open, high, low, close, volume
                FROM market_data_unified
                WHERE symbol = ?
                  AND date_partition = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                ORDER BY timestamp
            """,
            [symbol, trading_date, start, end],
        )
