"""
Risk Management Risk Assessment Entity

This module defines the RiskAssessment entity for tracking risk evaluations,
violations, and risk monitoring in the Risk Management domain.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from domain.shared.exceptions import DomainException
from .risk_profile import RiskProfileId


class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AssessmentType(Enum):
    """Types of risk assessments."""
    PRE_TRADE = "pre_trade"
    POST_TRADE = "post_trade"
    PORTFOLIO = "portfolio"
    POSITION = "position"
    MARKET = "market"
    STRATEGY = "strategy"


class AssessmentStatus(Enum):
    """Risk assessment status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDE = "override"
    EXPIRED = "expired"


@dataclass(frozen=True)
class RiskAssessmentId:
    """Value object for Risk Assessment ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("RiskAssessmentId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'RiskAssessmentId':
        """Generate a new unique RiskAssessmentId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class RiskViolation:
    """Value object for risk violations."""
    violation_type: str
    description: str
    severity: RiskLevel
    breached_limit: Decimal
    actual_value: Decimal
    threshold_value: Decimal

    def __post_init__(self):
        """Validate risk violation."""
        if not self.violation_type:
            raise DomainException("Violation type is required")
        if not self.description:
            raise DomainException("Violation description is required")

    def get_violation_percentage(self) -> Decimal:
        """Calculate violation percentage above threshold."""
        if self.threshold_value == 0:
            return Decimal('0')
        return ((self.actual_value - self.threshold_value) / self.threshold_value) * 100

    def is_critical(self) -> bool:
        """Check if violation is critical."""
        return self.severity == RiskLevel.CRITICAL

    def requires_immediate_action(self) -> bool:
        """Check if violation requires immediate action."""
        return self.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL]


@dataclass(frozen=True)
class RiskMetricsSnapshot:
    """Value object for risk metrics at a point in time."""
    portfolio_value: Decimal
    volatility: Decimal
    value_at_risk: Decimal
    expected_shortfall: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Optional[Decimal]
    sortino_ratio: Optional[Decimal]
    beta: Optional[Decimal]
    alpha: Optional[Decimal]

    def __post_init__(self):
        """Validate risk metrics snapshot."""
        if self.portfolio_value < 0:
            raise DomainException("Portfolio value cannot be negative")
        if self.volatility < 0:
            raise DomainException("Volatility cannot be negative")
        if self.value_at_risk < 0:
            raise DomainException("Value at Risk cannot be negative")
        if self.expected_shortfall < 0:
            raise DomainException("Expected Shortfall cannot be negative")
        if self.max_drawdown > 0:
            raise DomainException("Max drawdown should be negative or zero")

    def get_risk_score(self) -> RiskLevel:
        """Calculate overall risk score from metrics."""
        score = 0

        # High volatility increases risk
        if self.volatility > 0.3:
            score += 2
        elif self.volatility > 0.2:
            score += 1

        # High VaR increases risk
        if self.value_at_risk > 0.05:
            score += 2
        elif self.value_at_risk > 0.02:
            score += 1

        # High drawdown increases risk
        if self.max_drawdown < -0.2:
            score += 2
        elif self.max_drawdown < -0.1:
            score += 1

        # Low Sharpe ratio increases risk
        if self.sharpe_ratio is not None and self.sharpe_ratio < 0.5:
            score += 1

        # Determine risk level
        if score >= 4:
            return RiskLevel.CRITICAL
        elif score >= 3:
            return RiskLevel.HIGH
        elif score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


@dataclass
class RiskAssessment:
    """
    Risk Assessment aggregate root.

    Represents a risk assessment for a trade, position, or portfolio,
    including violations, metrics, and approval status.
    """
    id: RiskAssessmentId
    risk_profile_id: RiskProfileId
    assessment_type: AssessmentType
    entity_id: str  # Trade ID, Position ID, or Portfolio ID
    risk_level: RiskLevel
    status: AssessmentStatus = AssessmentStatus.PENDING
    violations: List[RiskViolation] = field(default_factory=list)
    risk_metrics: Optional[RiskMetricsSnapshot] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate risk assessment after initialization."""
        if not self.entity_id:
            raise DomainException("Entity ID is required")
        if self.notes and len(self.notes) > 1000:
            raise DomainException("Notes cannot exceed 1000 characters")

    def approve(self, approved_by: str) -> None:
        """Approve the risk assessment."""
        if self.status not in [AssessmentStatus.PENDING, AssessmentStatus.OVERRIDE]:
            raise DomainException(f"Cannot approve assessment with status: {self.status.value}")

        self.status = AssessmentStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def reject(self, reason: str) -> None:
        """Reject the risk assessment."""
        if self.status != AssessmentStatus.PENDING:
            raise DomainException(f"Cannot reject assessment with status: {self.status.value}")

        self.status = AssessmentStatus.REJECTED
        self.notes = reason
        self.updated_at = datetime.utcnow()

    def override(self, approved_by: str, reason: str) -> None:
        """Override risk assessment (force approval despite violations)."""
        if self.status != AssessmentStatus.REJECTED:
            raise DomainException(f"Cannot override assessment with status: {self.status.value}")

        self.status = AssessmentStatus.OVERRIDE
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()
        self.notes = f"Override: {reason}"
        self.updated_at = datetime.utcnow()

    def add_violation(self, violation: RiskViolation) -> None:
        """Add a risk violation."""
        self.violations.append(violation)

        # Update risk level if violation is more severe
        if violation.severity.value > self.risk_level.value:
            self.risk_level = violation.severity

        self.updated_at = datetime.utcnow()

    def has_violations(self) -> bool:
        """Check if assessment has any violations."""
        return len(self.violations) > 0

    def has_critical_violations(self) -> bool:
        """Check if assessment has critical violations."""
        return any(v.is_critical() for v in self.violations)

    def requires_approval(self) -> bool:
        """Check if assessment requires manual approval."""
        return (
            self.has_violations() or
            self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )

    def is_expired(self) -> bool:
        """Check if assessment is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_approved(self) -> bool:
        """Check if assessment is approved."""
        return self.status in [AssessmentStatus.APPROVED, AssessmentStatus.OVERRIDE]

    def can_proceed(self) -> bool:
        """Check if the assessed entity can proceed."""
        return (
            self.is_approved() and
            not self.is_expired() and
            not self.has_critical_violations()
        )

    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of violations."""
        if not self.violations:
            return {'count': 0, 'critical': 0, 'types': []}

        critical_count = sum(1 for v in self.violations if v.is_critical())
        violation_types = list(set(v.violation_type for v in self.violations))

        return {
            'count': len(self.violations),
            'critical': critical_count,
            'types': violation_types
        }

    def get_assessment_summary(self) -> Dict[str, Any]:
        """Get complete assessment summary."""
        return {
            'id': self.id.value,
            'type': self.assessment_type.value,
            'risk_level': self.risk_level.value,
            'status': self.status.value,
            'violations': self.get_violation_summary(),
            'approved': self.is_approved(),
            'can_proceed': self.can_proceed(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
