"""
Market Read Port for simple read-model queries used by runners.
"""

from typing import List
from datetime import date, datetime, time
from typing import Protocol
import pandas as pd


class MarketReadPort(Protocol):
    def get_symbols_for_date(self, trading_date: date) -> List[str]:  # pragma: no cover - protocol
        ...

    def get_minute_data(
        self,
        symbol: str,
        trading_date: date,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:  # pragma: no cover - protocol
        ...

