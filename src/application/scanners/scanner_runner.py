"""
Scanner Runner Interface - Unified Interface for Running Different Scanners

This module provides a unified interface for running various scanners following DDD principles.
It acts as a facade that hides the complexity of scanner instantiation and execution.

SOLID Principles:
- Single Responsibility: Each scanner has one job
- Open/Closed: New scanners can be added without modifying existing code
- Liskov Substitution: All scanners implement the same interface
- Interface Segregation: Clean interfaces for different scanner types
- Dependency Inversion: Depends on abstractions, not concretions

DDD Principles:
- Application Layer: Orchestrates domain objects
- Domain Services: Business logic for scanner operations
- Infrastructure: Handles external concerns (database, config)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol
from datetime import date, time
import pandas as pd

from ..interfaces.scanner_runner_interface import IScannerRunner
from ..domain.services.scanner_service import ScannerService
from ..infrastructure.scanner_factory import ScannerFactory
from ..infrastructure.config.scanner_config import ScannerConfig


class ScannerRunner(IScannerRunner):
    """
    Unified Scanner Runner that provides a clean interface for running different scanners.

    This class follows the Facade pattern to provide a simple interface while hiding
    the complexity of scanner instantiation, configuration, and execution.
    """

    def __init__(self, scanner_factory: ScannerFactory, scanner_service: ScannerService):
        """
        Initialize ScannerRunner with dependencies.

        Args:
            scanner_factory: Factory for creating scanner instances
            scanner_service: Domain service for scanner operations
        """
        self._scanner_factory = scanner_factory
        self._scanner_service = scanner_service

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
        Run a scanner for the specified date range.

        Args:
            scanner_name: Name of the scanner to run
            start_date: Start date for scanning
            end_date: End date for scanning
            config: Optional scanner configuration overrides
            cutoff_time: Optional cutoff time for scanning
            end_of_day_time: Optional end-of-day time

        Returns:
            List of scanner results

        Raises:
            ValueError: If scanner is not supported
        """
        # Get scanner instance from factory
        scanner = self._scanner_factory.create_scanner(scanner_name, config)

        if not scanner:
            raise ValueError(f"Scanner '{scanner_name}' is not supported")

        # Provide default times if not specified
        cutoff_time = cutoff_time or time(9, 50)
        end_of_day_time = end_of_day_time or time(15, 15)

        # Run scanner using domain service
        return self._scanner_service.run_scanner_date_range(
            scanner=scanner,
            start_date=start_date,
            end_date=end_date,
            cutoff_time=cutoff_time,
            end_of_day_time=end_of_day_time
        )

    def get_available_scanners(self) -> List[str]:
        """Get list of available scanner names."""
        return self._scanner_factory.get_available_scanners()

    def get_scanner_config(self, scanner_name: str) -> Dict[str, Any]:
        """Get configuration for a specific scanner."""
        return self._scanner_factory.get_scanner_config(scanner_name)

    def validate_scanner_config(self, scanner_name: str, config: Dict[str, Any]) -> bool:
        """Validate configuration for a scanner."""
        return self._scanner_factory.validate_config(scanner_name, config)


class ScannerResult:
    """
    Value Object representing scanner results.

    This follows DDD principles by being immutable and representing
    a complete concept from the domain.
    """

    def __init__(
        self,
        scanner_name: str,
        symbol: str,
        scan_date: date,
        score: float,
        metadata: Dict[str, Any]
    ):
        self._scanner_name = scanner_name
        self._symbol = symbol
        self._scan_date = scan_date
        self._score = score
        self._metadata = metadata.copy()  # Defensive copy

    @property
    def scanner_name(self) -> str:
        return self._scanner_name

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def scan_date(self) -> date:
        return self._scan_date

    @property
    def score(self) -> float:
        return self._score

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata.copy()  # Return copy to maintain immutability

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'scanner_name': self._scanner_name,
            'symbol': self._symbol,
            'scan_date': self._scan_date.isoformat(),
            'score': self._score,
            'metadata': self._metadata
        }

