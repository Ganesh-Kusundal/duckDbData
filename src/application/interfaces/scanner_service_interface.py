"""
Scanner Service Interface - Domain Service Contract

This interface defines the contract for scanner service implementations,
following Interface Segregation Principle (ISP) from SOLID.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date, time

from .base_scanner_interface import IBaseScanner


class IScannerService(ABC):
    """
    Interface for scanner service operations.

    This interface defines the contract for domain services that handle
    scanner business logic.
    """

    @abstractmethod
    def run_scanner_date_range(
        self,
        scanner: IBaseScanner,
        start_date: date,
        end_date: date,
        cutoff_time: Optional[time] = None,
        end_of_day_time: Optional[time] = None
    ) -> List[Dict[str, Any]]:
        """
        Run scanner for date range with business logic applied.

        Args:
            scanner: Scanner instance to run
            start_date: Start date for scanning
            end_date: End date for scanning
            cutoff_time: Optional cutoff time
            end_of_day_time: Optional end-of-day time

        Returns:
            List of scanner results with business rules applied
        """
        pass



