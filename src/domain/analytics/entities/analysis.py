"""
Analytics Analysis Entity

This module defines the Analysis entity for storing analysis results,
patterns, and statistical calculations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from domain.shared.exceptions import DomainException
from .indicator import Symbol, IndicatorId


class AnalysisType(Enum):
    """Types of analysis."""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    STATISTICAL = "statistical"
    PATTERN_RECOGNITION = "pattern_recognition"
    CORRELATION = "correlation"


class AnalysisStatus(Enum):
    """Analysis execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class AnalysisId:
    """Value object for Analysis ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("AnalysisId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'AnalysisId':
        """Generate a new unique AnalysisId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class AnalysisName:
    """Value object for Analysis Name."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("AnalysisName must be a non-empty string")
        if len(self.value) > 100:
            raise DomainException("AnalysisName cannot exceed 100 characters")


@dataclass(frozen=True)
class ConfidenceLevel:
    """Value object for analysis confidence."""
    value: Decimal

    def __post_init__(self):
        if not (0 <= self.value <= 1):
            raise DomainException("Confidence must be between 0 and 1")

    @property
    def percentage(self) -> Decimal:
        """Get confidence as percentage."""
        return self.value * 100

    def is_high_confidence(self, threshold: Decimal = Decimal('0.8')) -> bool:
        """Check if confidence is above threshold."""
        return self.value >= threshold

    def is_low_confidence(self, threshold: Decimal = Decimal('0.3')) -> bool:
        """Check if confidence is below threshold."""
        return self.value <= threshold


@dataclass
class Analysis:
    """
    Analysis aggregate root.

    Represents an analysis execution with its results,
    parameters, and metadata.
    """
    id: AnalysisId
    name: AnalysisName
    analysis_type: AnalysisType
    symbol: Symbol
    parameters: Dict[str, Any]
    status: AnalysisStatus = AnalysisStatus.PENDING
    confidence: Optional[ConfidenceLevel] = None
    results: Dict[str, Any] = field(default_factory=dict)
    indicators_used: List[IndicatorId] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate analysis after initialization."""
        self._validate_parameters()

    def _validate_parameters(self):
        """Validate analysis parameters."""
        if self.analysis_type == AnalysisType.TECHNICAL:
            if 'indicators' not in self.parameters:
                raise DomainException("Technical analysis requires indicators parameter")

        elif self.analysis_type == AnalysisType.STATISTICAL:
            if 'method' not in self.parameters:
                raise DomainException("Statistical analysis requires method parameter")

        elif self.analysis_type == AnalysisType.PATTERN_RECOGNITION:
            if 'patterns' not in self.parameters:
                raise DomainException("Pattern recognition requires patterns parameter")

    def start_execution(self) -> None:
        """Mark analysis as started."""
        if self.status != AnalysisStatus.PENDING:
            raise DomainException(f"Cannot start analysis with status: {self.status.value}")

        self.status = AnalysisStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete_execution(self, results: Dict[str, Any], confidence: ConfidenceLevel) -> None:
        """Mark analysis as completed with results."""
        if self.status != AnalysisStatus.RUNNING:
            raise DomainException(f"Cannot complete analysis with status: {self.status.value}")

        self.status = AnalysisStatus.COMPLETED
        self.results = results
        self.confidence = confidence
        self.completed_at = datetime.utcnow()

    def fail_execution(self, error_message: str) -> None:
        """Mark analysis as failed."""
        if self.status not in [AnalysisStatus.PENDING, AnalysisStatus.RUNNING]:
            raise DomainException(f"Cannot fail analysis with status: {self.status.value}")

        self.status = AnalysisStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()

    def cancel_execution(self) -> None:
        """Cancel analysis execution."""
        if self.status not in [AnalysisStatus.PENDING, AnalysisStatus.RUNNING]:
            raise DomainException(f"Cannot cancel analysis with status: {self.status.value}")

        self.status = AnalysisStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def is_completed(self) -> bool:
        """Check if analysis is completed."""
        return self.status == AnalysisStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if analysis failed."""
        return self.status == AnalysisStatus.FAILED

    def is_running(self) -> bool:
        """Check if analysis is currently running."""
        return self.status == AnalysisStatus.RUNNING

    def get_execution_time(self) -> Optional[float]:
        """Get execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def get_result(self, key: str, default: Any = None) -> Any:
        """Get a specific result value."""
        return self.results.get(key, default)

    def add_indicator(self, indicator_id: IndicatorId) -> None:
        """Add an indicator used in this analysis."""
        if indicator_id not in self.indicators_used:
            self.indicators_used.append(indicator_id)

    def get_signal_strength(self) -> Optional[str]:
        """Get signal strength based on confidence."""
        if not self.confidence:
            return None

        if self.confidence.is_high_confidence():
            return "STRONG"
        elif self.confidence.is_low_confidence():
            return "WEAK"
        else:
            return "MODERATE"


@dataclass
class Pattern:
    """
    Pattern entity for storing recognized patterns.
    """
    symbol: Symbol
    pattern_type: str
    confidence: ConfidenceLevel
    detected_at: datetime
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None

    def __post_init__(self):
        """Validate pattern after initialization."""
        if not self.pattern_type:
            raise DomainException("Pattern type is required")

        if self.description and len(self.description) > 500:
            raise DomainException("Pattern description cannot exceed 500 characters")

    def is_bullish(self) -> bool:
        """Check if pattern is bullish."""
        bullish_patterns = ['ascending_triangle', 'bullish_flag', 'double_bottom', 'head_shoulders_bottom']
        return self.pattern_type.lower() in bullish_patterns

    def is_bearish(self) -> bool:
        """Check if pattern is bearish."""
        bearish_patterns = ['descending_triangle', 'bearish_flag', 'double_top', 'head_shoulders_top']
        return self.pattern_type.lower() in bearish_patterns

