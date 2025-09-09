"""
Scanner Runner Interface - Clean Interface for Scanner Operations

This interface defines the contract for scanner runner implementations,
following Interface Segregation Principle (ISP) from SOLID.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import date, time


class IScannerRunner(ABC):
    """
    Interface for scanner runner operations.

    This interface follows ISP by providing focused methods for scanner operations
    without forcing implementations to depend on methods they don't need.
    """

    @abstractmethod
    def run_scanner(
        self,
        scanner_name: str,
        start_date: date,
        end_date: date,
        config: Optional[Dict[str, Any]] = None,
        cutoff_time: Optional[time] = None,
        end_of_day_time: Optional[time] = None
    ) -> List[Dict[str, Any]]:
        """
        Run a scanner for the specified parameters.

        Args:
            scanner_name: Name of the scanner to run
            start_date: Start date for scanning
            end_date: End date for scanning
            config: Optional scanner configuration
            cutoff_time: Optional cutoff time
            end_of_day_time: Optional end-of-day time

        Returns:
            List of scanner results
        """
        pass

    @abstractmethod
    def get_available_scanners(self) -> List[str]:
        """Get list of available scanner names."""
        pass

    @abstractmethod
    def get_scanner_config(self, scanner_name: str) -> Dict[str, Any]:
        """Get configuration for a specific scanner."""
        pass

    @abstractmethod
    def validate_scanner_config(self, scanner_name: str, config: Dict[str, Any]) -> bool:
        """Validate configuration for a scanner."""
        pass



