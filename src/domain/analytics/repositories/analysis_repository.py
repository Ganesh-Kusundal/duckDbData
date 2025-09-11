"""
Analysis Repository Interface

This module defines the repository interface for Analysis entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.analysis import Analysis, AnalysisId, AnalysisType, AnalysisStatus
from ..entities.indicator import Symbol


class AnalysisRepository(ABC):
    """
    Repository interface for Analysis entities.

    Defines the contract for analysis data persistence and retrieval.
    """

    @abstractmethod
    def save(self, analysis: Analysis) -> None:
        """Save an analysis to the repository."""
        pass

    @abstractmethod
    def find_by_id(self, analysis_id: AnalysisId) -> Optional[Analysis]:
        """Find an analysis by its ID."""
        pass

    @abstractmethod
    def find_by_symbol(self, symbol: Symbol) -> List[Analysis]:
        """Find all analyses for a specific symbol."""
        pass

    @abstractmethod
    def find_by_type(self, analysis_type: AnalysisType) -> List[Analysis]:
        """Find all analyses of a specific type."""
        pass

    @abstractmethod
    def find_by_status(self, status: AnalysisStatus) -> List[Analysis]:
        """Find all analyses with a specific status."""
        pass

    @abstractmethod
    def find_completed_analyses(self) -> List[Analysis]:
        """Find all completed analyses."""
        pass

    @abstractmethod
    def find_failed_analyses(self) -> List[Analysis]:
        """Find all failed analyses."""
        pass

    @abstractmethod
    def find_analyses_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Analysis]:
        """Find analyses within a date range."""
        pass

    @abstractmethod
    def find_analyses_by_symbol_and_date_range(
        self,
        symbol: Symbol,
        start_date: datetime,
        end_date: datetime
    ) -> List[Analysis]:
        """Find analyses for a symbol within a date range."""
        pass

    @abstractmethod
    def delete(self, analysis_id: AnalysisId) -> None:
        """Delete an analysis from the repository."""
        pass

    @abstractmethod
    def exists(self, analysis_id: AnalysisId) -> bool:
        """Check if an analysis exists in the repository."""
        pass

    @abstractmethod
    def count_analyses_by_symbol(self, symbol: Symbol) -> int:
        """Count analyses for a specific symbol."""
        pass

    @abstractmethod
    def count_analyses_by_status(self, status: AnalysisStatus) -> int:
        """Count analyses by status."""
        pass

    @abstractmethod
    def get_analysis_summary(self) -> dict:
        """
        Get analysis summary statistics.

        Returns:
            dict: Summary with counts by type, status, performance metrics, etc.
        """
        pass

    @abstractmethod
    def get_success_rate(self) -> float:
        """
        Get analysis success rate (completed / total).

        Returns:
            float: Success rate between 0 and 1
        """
        pass

    @abstractmethod
    def get_average_execution_time(self) -> Optional[float]:
        """
        Get average execution time for completed analyses.

        Returns:
            float: Average execution time in seconds, or None if no completed analyses
        """
        pass

    @abstractmethod
    def find_high_confidence_analyses(self, threshold: float = 0.8) -> List[Analysis]:
        """
        Find analyses with high confidence scores.

        Args:
            threshold: Confidence threshold (default 0.8)

        Returns:
            List[Analysis]: Analyses with confidence above threshold
        """
        pass

