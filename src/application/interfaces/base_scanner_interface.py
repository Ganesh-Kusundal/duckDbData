"""
Base Scanner Interface - Contract for All Scanner Implementations

This interface defines the contract that all scanner implementations must follow,
following Interface Segregation Principle (ISP) from SOLID.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date, time
import pandas as pd


class IBaseScanner(ABC):
    """
    Interface that all scanner implementations must follow.

    This interface ensures that all scanners have a consistent API
    while allowing for different implementations.
    """

    @property
    @abstractmethod
    def scanner_name(self) -> str:
        """Get the name of this scanner."""
        pass

    @abstractmethod
    def scan(self, scan_date: date, cutoff_time: time = time(9, 50)) -> pd.DataFrame:
        """
        Execute scanner logic for given date and time.

        Args:
            scan_date: Date to scan
            cutoff_time: Time cutoff for scanning

        Returns:
            DataFrame with scan results
        """
        pass

    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols."""
        pass



