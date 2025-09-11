"""
Rule Repository Interface

This module defines the repository interface for Rule entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.rule import Rule, RuleId, RuleType, RuleStatus


class RuleRepository(ABC):
    """
    Repository interface for Rule entities.

    Defines the contract for rule data persistence and retrieval.
    """

    @abstractmethod
    def save(self, rule: Rule) -> None:
        """Save a rule to the repository."""
        pass

    @abstractmethod
    def find_by_id(self, rule_id: RuleId) -> Optional[Rule]:
        """Find a rule by its ID."""
        pass

    @abstractmethod
    def find_by_type(self, rule_type: RuleType) -> List[Rule]:
        """Find all rules of a specific type."""
        pass

    @abstractmethod
    def find_by_status(self, status: RuleStatus) -> List[Rule]:
        """Find all rules with a specific status."""
        pass

    @abstractmethod
    def find_active_rules(self) -> List[Rule]:
        """Find all active rules."""
        pass

    @abstractmethod
    def find_rules_by_tag(self, tag: str) -> List[Rule]:
        """Find all rules with a specific tag."""
        pass

    @abstractmethod
    def find_top_performing_rules(self, limit: int = 10) -> List[Rule]:
        """Find top performing rules by performance metrics."""
        pass

    @abstractmethod
    def delete(self, rule_id: RuleId) -> None:
        """Delete a rule from the repository."""
        pass

    @abstractmethod
    def exists(self, rule_id: RuleId) -> bool:
        """Check if a rule exists in the repository."""
        pass

    @abstractmethod
    def count_rules_by_type(self, rule_type: RuleType) -> int:
        """Count rules by type."""
        pass

    @abstractmethod
    def count_rules_by_status(self, status: RuleStatus) -> int:
        """Count rules by status."""
        pass

    @abstractmethod
    def get_rule_performance_summary(self) -> dict:
        """
        Get rule performance summary statistics.

        Returns:
            dict: Summary with win rates, returns, etc.
        """
        pass

    @abstractmethod
    def get_most_used_rule_types(self, limit: int = 5) -> List[dict]:
        """
        Get most used rule types by execution count.

        Returns:
            List of dicts with rule type and usage metrics
        """
        pass

    @abstractmethod
    def get_rule_success_rates(self) -> dict:
        """
        Get success rates for different rule types.

        Returns:
            dict: Success rates by rule type
        """
        pass

    @abstractmethod
    def activate_rule(self, rule_id: RuleId) -> None:
        """Activate a rule."""
        pass

    @abstractmethod
    def deactivate_rule(self, rule_id: RuleId) -> None:
        """Deactivate a rule."""
        pass

    @abstractmethod
    def update_rule_performance(self, rule_id: RuleId, signals: List[dict]) -> None:
        """
        Update rule performance metrics.

        Args:
            rule_id: The rule to update
            signals: List of signal results to analyze
        """
        pass

