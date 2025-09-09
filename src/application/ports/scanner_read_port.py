"""
Scanner Read Port for strategy queries.

This port abstracts read-model queries needed by scanners (CRP, Breakout)
so strategies do not embed SQL or manage DB connections directly.
"""

from typing import Dict, List, Any, Protocol
from datetime import date, time


class ScannerReadPort(Protocol):
    def get_crp_candidates(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:  # pragma: no cover - protocol
        ...

    def get_end_of_day_prices(
        self,
        symbols: List[str],
        scan_date: date,
        end_time: time,
    ) -> Dict[str, Dict[str, Any]]:  # pragma: no cover - protocol
        ...

    def get_breakout_candidates(
        self,
        scan_date: date,
        cutoff_time: time,
        config: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:  # pragma: no cover - protocol
        ...
