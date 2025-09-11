"""
Risk Profile Repository Interface

This module defines the repository interface for RiskProfile entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.risk_profile import RiskProfile, RiskProfileId, RiskTolerance, RiskProfileStatus


class RiskProfileRepository(ABC):
    """
    Repository interface for RiskProfile entities.

    Defines the contract for risk profile data persistence and retrieval.
    """

    @abstractmethod
    def save(self, risk_profile: RiskProfile) -> None:
        """Save a risk profile to the repository."""
        pass

    @abstractmethod
    def find_by_id(self, risk_profile_id: RiskProfileId) -> Optional[RiskProfile]:
        """Find a risk profile by its ID."""
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[RiskProfile]:
        """Find a risk profile by name."""
        pass

    @abstractmethod
    def find_by_risk_tolerance(self, risk_tolerance: RiskTolerance) -> List[RiskProfile]:
        """Find all risk profiles with a specific risk tolerance."""
        pass

    @abstractmethod
    def find_by_status(self, status: RiskProfileStatus) -> List[RiskProfile]:
        """Find all risk profiles with a specific status."""
        pass

    @abstractmethod
    def find_active_profiles(self) -> List[RiskProfile]:
        """Find all active risk profiles."""
        pass

    @abstractmethod
    def find_profiles_for_strategy(self, strategy_id: str) -> List[RiskProfile]:
        """Find risk profiles associated with a specific strategy."""
        pass

    @abstractmethod
    def delete(self, risk_profile_id: RiskProfileId) -> None:
        """Delete a risk profile from the repository."""
        pass

    @abstractmethod
    def exists(self, risk_profile_id: RiskProfileId) -> bool:
        """Check if a risk profile exists in the repository."""
        pass

    @abstractmethod
    def count_profiles_by_tolerance(self, risk_tolerance: RiskTolerance) -> int:
        """Count risk profiles by risk tolerance level."""
        pass

    @abstractmethod
    def count_profiles_by_status(self, status: RiskProfileStatus) -> int:
        """Count risk profiles by status."""
        pass

    @abstractmethod
    def get_risk_distribution_summary(self) -> dict:
        """
        Get summary of risk profile distribution.

        Returns:
            dict: Summary with counts by risk tolerance and status
        """
        pass

    @abstractmethod
    def get_most_strict_profiles(self, limit: int = 5) -> List[RiskProfile]:
        """
        Get most strict risk profiles (lowest risk tolerance).

        Returns:
            List of risk profiles ordered by strictness
        """
        pass

    @abstractmethod
    def get_least_strict_profiles(self, limit: int = 5) -> List[RiskProfile]:
        """
        Get least strict risk profiles (highest risk tolerance).

        Returns:
            List of risk profiles ordered by leniency
        """
        pass

    @abstractmethod
    def activate_profile(self, risk_profile_id: RiskProfileId) -> None:
        """Activate a risk profile."""
        pass

    @abstractmethod
    def deactivate_profile(self, risk_profile_id: RiskProfileId) -> None:
        """Deactivate a risk profile."""
        pass

    @abstractmethod
    def update_profile_associations(self, risk_profile_id: RiskProfileId, strategy_ids: List[str]) -> None:
        """
        Update strategy associations for a risk profile.

        Args:
            risk_profile_id: The risk profile to update
            strategy_ids: List of strategy IDs to associate
        """
        pass

