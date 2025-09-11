"""
Scan Repository Interface

This module defines the repository interface for Scan entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.scan import Scan, ScanId, ScanStatus, ScanType


class ScanRepository(ABC):
    """
    Repository interface for Scan entities.

    Defines the contract for scan data persistence and retrieval.
    """

    @abstractmethod
    def save(self, scan: Scan) -> None:
        """Save a scan to the repository."""
        pass

    @abstractmethod
    def find_by_id(self, scan_id: ScanId) -> Optional[Scan]:
        """Find a scan by its ID."""
        pass

    @abstractmethod
    def find_by_status(self, status: ScanStatus) -> List[Scan]:
        """Find all scans with a specific status."""
        pass

    @abstractmethod
    def find_completed_scans(self) -> List[Scan]:
        """Find all completed scans."""
        pass

    @abstractmethod
    def find_failed_scans(self) -> List[Scan]:
        """Find all failed scans."""
        pass

    @abstractmethod
    def find_scans_by_type(self, scan_type: ScanType) -> List[Scan]:
        """Find all scans of a specific type."""
        pass

    @abstractmethod
    def find_scans_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Scan]:
        """Find scans within a date range."""
        pass

    @abstractmethod
    def find_recent_scans(self, limit: int = 10) -> List[Scan]:
        """Find most recent scans."""
        pass

    @abstractmethod
    def delete(self, scan_id: ScanId) -> None:
        """Delete a scan from the repository."""
        pass

    @abstractmethod
    def exists(self, scan_id: ScanId) -> bool:
        """Check if a scan exists in the repository."""
        pass

    @abstractmethod
    def count_scans_by_status(self, status: ScanStatus) -> int:
        """Count scans by status."""
        pass

    @abstractmethod
    def count_scans_by_type(self, scan_type: ScanType) -> int:
        """Count scans by type."""
        pass

    @abstractmethod
    def get_scan_execution_stats(self) -> dict:
        """
        Get scan execution statistics.

        Returns:
            dict: Statistics including success rate, average execution time, etc.
        """
        pass

    @abstractmethod
    def get_most_successful_scan_types(self, limit: int = 5) -> List[dict]:
        """
        Get most successful scan types by signal quality.

        Returns:
            List of dicts with scan type and success metrics
        """
        pass

    @abstractmethod
    def get_scan_performance_trends(self, days: int = 30) -> dict:
        """
        Get scan performance trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            dict: Performance trends and metrics
        """
        pass

