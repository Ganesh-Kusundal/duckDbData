"""
Risk Assessment Repository Interface

This module defines the repository interface for RiskAssessment entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..entities.risk_assessment import RiskAssessment, RiskAssessmentId, AssessmentType, AssessmentStatus, RiskLevel
from ..entities.risk_profile import RiskProfileId


class RiskAssessmentRepository(ABC):
    """
    Repository interface for RiskAssessment entities.

    Defines the contract for risk assessment data persistence and retrieval.
    """

    @abstractmethod
    def save(self, risk_assessment: RiskAssessment) -> None:
        """Save a risk assessment to the repository."""
        pass

    @abstractmethod
    def find_by_id(self, assessment_id: RiskAssessmentId) -> Optional[RiskAssessment]:
        """Find a risk assessment by its ID."""
        pass

    @abstractmethod
    def find_by_entity_id(self, entity_id: str) -> List[RiskAssessment]:
        """Find all risk assessments for a specific entity."""
        pass

    @abstractmethod
    def find_by_risk_profile(self, risk_profile_id: RiskProfileId) -> List[RiskAssessment]:
        """Find all risk assessments for a specific risk profile."""
        pass

    @abstractmethod
    def find_by_type(self, assessment_type: AssessmentType) -> List[RiskAssessment]:
        """Find all risk assessments of a specific type."""
        pass

    @abstractmethod
    def find_by_status(self, status: AssessmentStatus) -> List[RiskAssessment]:
        """Find all risk assessments with a specific status."""
        pass

    @abstractmethod
    def find_by_risk_level(self, risk_level: RiskLevel) -> List[RiskAssessment]:
        """Find all risk assessments with a specific risk level."""
        pass

    @abstractmethod
    def find_pending_approvals(self) -> List[RiskAssessment]:
        """Find all risk assessments pending approval."""
        pass

    @abstractmethod
    def find_expired_assessments(self) -> List[RiskAssessment]:
        """Find all expired risk assessments."""
        pass

    @abstractmethod
    def find_assessments_in_date_range(self, start_date: datetime, end_date: datetime) -> List[RiskAssessment]:
        """Find risk assessments within a date range."""
        pass

    @abstractmethod
    def find_high_risk_assessments(self) -> List[RiskAssessment]:
        """Find all high or critical risk assessments."""
        pass

    @abstractmethod
    def delete(self, assessment_id: RiskAssessmentId) -> None:
        """Delete a risk assessment from the repository."""
        pass

    @abstractmethod
    def exists(self, assessment_id: RiskAssessmentId) -> bool:
        """Check if a risk assessment exists in the repository."""
        pass

    @abstractmethod
    def count_assessments_by_status(self, status: AssessmentStatus) -> int:
        """Count risk assessments by status."""
        pass

    @abstractmethod
    def count_assessments_by_risk_level(self, risk_level: RiskLevel) -> int:
        """Count risk assessments by risk level."""
        pass

    @abstractmethod
    def count_assessments_by_type(self, assessment_type: AssessmentType) -> int:
        """Count risk assessments by type."""
        pass

    @abstractmethod
    def get_assessment_summary(self) -> dict:
        """
        Get risk assessment summary statistics.

        Returns:
            dict: Summary with counts by type, status, risk level, etc.
        """
        pass

    @abstractmethod
    def get_approval_rate(self) -> float:
        """
        Get risk assessment approval rate.

        Returns:
            float: Approval rate between 0 and 1
        """
        pass

    @abstractmethod
    def get_average_assessment_time(self) -> Optional[float]:
        """
        Get average time for assessment completion.

        Returns:
            float: Average assessment time in seconds, or None if no completed assessments
        """
        pass

    @abstractmethod
    def get_risk_trends(self, days: int = 30) -> dict:
        """
        Get risk assessment trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            dict: Risk trends and patterns
        """
        pass

    @abstractmethod
    def approve_assessment(self, assessment_id: RiskAssessmentId, approved_by: str) -> None:
        """Approve a risk assessment."""
        pass

    @abstractmethod
    def reject_assessment(self, assessment_id: RiskAssessmentId, reason: str) -> None:
        """Reject a risk assessment."""
        pass

    @abstractmethod
    def expire_assessments(self, before_date: datetime) -> int:
        """
        Mark assessments as expired before a specific date.

        Args:
            before_date: Date before which to expire assessments

        Returns:
            int: Number of assessments expired
        """
        pass

