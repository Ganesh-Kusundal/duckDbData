"""
Risk Assessment Service

This module defines the RiskAssessmentService domain service
for risk evaluation, monitoring, and control in the Risk Management domain.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from domain.shared.exceptions import DomainException
from ..entities.risk_profile import RiskProfile
from ..entities.risk_assessment import RiskAssessment, RiskAssessmentId, RiskViolation, RiskLevel
from ..value_objects.risk_limits import PortfolioLimits, TradingLimits, RiskThresholds
from ..repositories.risk_profile_repository import RiskProfileRepository
from ..repositories.risk_assessment_repository import RiskAssessmentRepository


class RiskAssessmentService:
    """
    Domain service for risk assessment and evaluation.

    Handles risk evaluation for trades, positions, and portfolios,
    monitors risk limits, and manages risk control workflows.
    """

    def __init__(
        self,
        risk_profile_repository: RiskProfileRepository,
        risk_assessment_repository: RiskAssessmentRepository
    ):
        self.risk_profile_repository = risk_profile_repository
        self.risk_assessment_repository = risk_assessment_repository

    def assess_trade_risk(
        self,
        trade_details: Dict[str, Any],
        risk_profile: RiskProfile
    ) -> RiskAssessment:
        """
        Assess risk for a proposed trade.

        Args:
            trade_details: Trade information (symbol, quantity, price, etc.)
            risk_profile: Risk profile to evaluate against

        Returns:
            RiskAssessment: Complete risk assessment
        """
        # Validate trade details
        self._validate_trade_details(trade_details)

        # Get current market conditions
        market_conditions = self._get_market_conditions(trade_details.get('symbol'))

        # Create risk assessment
        assessment = RiskAssessment(
            id=RiskAssessmentId.generate(),
            risk_profile_id=risk_profile.id,
            assessment_type=AssessmentType.PRE_TRADE,
            entity_id=trade_details.get('trade_id', 'unknown'),
            risk_level=RiskLevel.LOW  # Default, will be updated
        )

        # Evaluate position limits
        position_violations = self._evaluate_position_limits(
            trade_details, risk_profile, market_conditions
        )
        assessment.violations.extend(position_violations)

        # Evaluate loss limits
        loss_violations = self._evaluate_loss_limits(
            trade_details, risk_profile, market_conditions
        )
        assessment.violations.extend(loss_violations)

        # Evaluate risk metrics
        metrics_violations = self._evaluate_risk_metrics(
            trade_details, risk_profile, market_conditions
        )
        assessment.violations.extend(metrics_violations)

        # Determine overall risk level
        assessment.risk_level = self._calculate_overall_risk_level(assessment.violations)

        # Set assessment status based on violations
        if assessment.has_critical_violations():
            assessment.reject("Critical risk violations detected")
        elif assessment.has_violations():
            assessment.status = AssessmentStatus.PENDING  # Requires approval
        else:
            assessment.approve("auto_approved")  # Auto-approve if no violations

        # Save assessment
        self.risk_assessment_repository.save(assessment)

        return assessment

    def assess_portfolio_risk(
        self,
        portfolio_data: Dict[str, Any],
        risk_profile: RiskProfile
    ) -> RiskAssessment:
        """
        Assess risk for an entire portfolio.

        Args:
            portfolio_data: Portfolio information
            risk_profile: Risk profile to evaluate against

        Returns:
            RiskAssessment: Complete risk assessment
        """
        # Create risk assessment
        assessment = RiskAssessment(
            id=RiskAssessmentId.generate(),
            risk_profile_id=risk_profile.id,
            assessment_type=AssessmentType.PORTFOLIO,
            entity_id=portfolio_data.get('portfolio_id', 'unknown'),
            risk_level=RiskLevel.LOW
        )

        # Evaluate portfolio limits
        portfolio_violations = self._evaluate_portfolio_limits(portfolio_data, risk_profile)
        assessment.violations.extend(portfolio_violations)

        # Evaluate diversification
        diversification_violations = self._evaluate_diversification(portfolio_data, risk_profile)
        assessment.violations.extend(diversification_violations)

        # Determine overall risk level
        assessment.risk_level = self._calculate_overall_risk_level(assessment.violations)

        # Set assessment status
        if assessment.has_violations():
            assessment.reject("Portfolio risk violations detected")
        else:
            assessment.approve("auto_approved")

        # Save assessment
        self.risk_assessment_repository.save(assessment)

        return assessment

    def monitor_portfolio_risk(
        self,
        portfolio_id: str,
        risk_thresholds: RiskThresholds
    ) -> Dict[str, Any]:
        """
        Monitor portfolio risk in real-time.

        Args:
            portfolio_id: Portfolio to monitor
            risk_thresholds: Risk thresholds for alerts

        Returns:
            Dict with monitoring results and alerts
        """
        # Get current portfolio data
        portfolio_data = self._get_portfolio_data(portfolio_id)

        # Calculate current risk metrics
        risk_metrics = self._calculate_portfolio_risk_metrics(portfolio_data)

        # Check thresholds
        threshold_breaches = risk_thresholds.check_thresholds(
            volatility=risk_metrics.get('volatility', Decimal('0')),
            drawdown=risk_metrics.get('max_drawdown', Decimal('0')),
            var=risk_metrics.get('value_at_risk', Decimal('0')),
            max_correlation=risk_metrics.get('max_correlation', Decimal('0')),
            liquidity_ratio=risk_metrics.get('liquidity_ratio', Decimal('1')),
            max_concentration=risk_metrics.get('max_concentration', Decimal('0'))
        )

        # Generate alerts for breaches
        alerts = self._generate_risk_alerts(threshold_breaches, risk_metrics)

        return {
            'portfolio_id': portfolio_id,
            'risk_metrics': risk_metrics,
            'threshold_breaches': threshold_breaches,
            'alerts': alerts,
            'breach_summary': risk_thresholds.get_breach_summary(threshold_breaches)
        }

    def get_risk_exposure_summary(self, risk_profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive risk exposure summary."""
        if risk_profile_id:
            # Get assessments for specific risk profile
            assessments = self.risk_assessment_repository.find_by_risk_profile(
                RiskProfileId(risk_profile_id)
            )
        else:
            # Get all assessments
            assessments = []
            for status in [AssessmentStatus.APPROVED, AssessmentStatus.REJECTED, AssessmentStatus.PENDING]:
                assessments.extend(self.risk_assessment_repository.find_by_status(status))

        # Analyze assessments
        total_assessments = len(assessments)
        approved_count = sum(1 for a in assessments if a.is_approved())
        rejected_count = sum(1 for a in assessments if a.status == AssessmentStatus.REJECTED)
        pending_count = sum(1 for a in assessments if a.status == AssessmentStatus.PENDING)

        # Risk level distribution
        risk_distribution = {}
        for assessment in assessments:
            level = assessment.risk_level.value
            risk_distribution[level] = risk_distribution.get(level, 0) + 1

        # Violation analysis
        total_violations = sum(len(a.violations) for a in assessments)
        critical_violations = sum(
            1 for a in assessments
            for v in a.violations
            if v.is_critical()
        )

        return {
            'total_assessments': total_assessments,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'pending_count': pending_count,
            'approval_rate': approved_count / total_assessments if total_assessments > 0 else 0,
            'risk_distribution': risk_distribution,
            'total_violations': total_violations,
            'critical_violations': critical_violations,
            'average_violations_per_assessment': total_violations / total_assessments if total_assessments > 0 else 0
        }

    def _validate_trade_details(self, trade_details: Dict[str, Any]) -> None:
        """Validate trade details."""
        required_fields = ['symbol', 'quantity', 'price']
        for field in required_fields:
            if field not in trade_details:
                raise DomainException(f"Missing required trade field: {field}")

        if trade_details['quantity'] <= 0:
            raise DomainException("Trade quantity must be positive")
        if trade_details['price'] <= 0:
            raise DomainException("Trade price must be positive")

    def _get_market_conditions(self, symbol: str) -> Dict[str, Any]:
        """Get current market conditions for a symbol."""
        # In a real implementation, this would fetch from market data service
        return {
            'volatility': Decimal('0.15'),
            'liquidity': Decimal('0.8'),
            'trend': 'SIDEWAYS',
            'volume_ratio': Decimal('1.2')
        }

    def _evaluate_position_limits(
        self,
        trade_details: Dict[str, Any],
        risk_profile: RiskProfile,
        market_conditions: Dict[str, Any]
    ) -> List[RiskViolation]:
        """Evaluate position size limits."""
        violations = []
        trade_value = trade_details['quantity'] * trade_details['price']

        # Check position limits
        if not risk_profile.can_accept_trade(
            trade_value=trade_value,
            portfolio_value=Decimal('100000'),  # Would be fetched from portfolio service
            current_volatility=market_conditions['volatility'],
            current_var=Decimal('0.02'),
            current_drawdown=Decimal('0'),
            asset_concentration=Decimal('0.05')
        ):
            violations.append(RiskViolation(
                violation_type="POSITION_LIMIT",
                description=f"Trade value {trade_value} exceeds position limits",
                severity=RiskLevel.HIGH,
                breached_limit=risk_profile.position_limits.max_position_size,
                actual_value=trade_value,
                threshold_value=risk_profile.position_limits.max_position_size
            ))

        return violations

    def _evaluate_loss_limits(
        self,
        trade_details: Dict[str, Any],
        risk_profile: RiskProfile,
        market_conditions: Dict[str, Any]
    ) -> List[RiskViolation]:
        """Evaluate loss limits."""
        violations = []

        # Check stop loss distance
        entry_price = trade_details['price']
        stop_loss_price = risk_profile.loss_limits.calculate_stop_loss_price(
            entry_price, trade_details.get('side', 'BUY') == 'BUY'
        )
        stop_distance = abs(entry_price - stop_loss_price) / entry_price

        if stop_distance > risk_profile.loss_limits.stop_loss_percentage:
            violations.append(RiskViolation(
                violation_type="STOP_LOSS_LIMIT",
                description=f"Stop loss distance {stop_distance:.2%} exceeds limit",
                severity=RiskLevel.MEDIUM,
                breached_limit=risk_profile.loss_limits.stop_loss_percentage,
                actual_value=stop_distance,
                threshold_value=risk_profile.loss_limits.stop_loss_percentage
            ))

        return violations

    def _evaluate_risk_metrics(
        self,
        trade_details: Dict[str, Any],
        risk_profile: RiskProfile,
        market_conditions: Dict[str, Any]
    ) -> List[RiskViolation]:
        """Evaluate risk metrics."""
        violations = []

        # Check volatility
        if market_conditions['volatility'] > risk_profile.risk_metrics.volatility_limit:
            violations.append(RiskViolation(
                violation_type="VOLATILITY_LIMIT",
                description=f"Market volatility {market_conditions['volatility']:.2%} exceeds limit",
                severity=RiskLevel.MEDIUM,
                breached_limit=risk_profile.risk_metrics.volatility_limit,
                actual_value=market_conditions['volatility'],
                threshold_value=risk_profile.risk_metrics.volatility_limit
            ))

        return violations

    def _calculate_overall_risk_level(self, violations: List[RiskViolation]) -> RiskLevel:
        """Calculate overall risk level from violations."""
        if not violations:
            return RiskLevel.LOW

        # Check for critical violations
        if any(v.severity == RiskLevel.CRITICAL for v in violations):
            return RiskLevel.CRITICAL

        # Check for high violations
        if any(v.severity == RiskLevel.HIGH for v in violations):
            return RiskLevel.HIGH

        # Check for medium violations
        if any(v.severity == RiskLevel.MEDIUM for v in violations):
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _evaluate_portfolio_limits(
        self,
        portfolio_data: Dict[str, Any],
        risk_profile: RiskProfile
    ) -> List[RiskViolation]:
        """Evaluate portfolio-level limits."""
        violations = []

        # This would implement comprehensive portfolio limit checking
        # For now, return empty list
        return violations

    def _evaluate_diversification(
        self,
        portfolio_data: Dict[str, Any],
        risk_profile: RiskProfile
    ) -> List[RiskViolation]:
        """Evaluate portfolio diversification."""
        violations = []

        # This would implement diversification analysis
        # For now, return empty list
        return violations

    def _get_portfolio_data(self, portfolio_id: str) -> Dict[str, Any]:
        """Get current portfolio data."""
        # In a real implementation, this would fetch from portfolio service
        return {
            'portfolio_value': Decimal('100000'),
            'positions': [],
            'cash': Decimal('50000')
        }

    def _calculate_portfolio_risk_metrics(self, portfolio_data: Dict[str, Any]) -> Dict[str, Decimal]:
        """Calculate portfolio risk metrics."""
        # In a real implementation, this would perform complex risk calculations
        return {
            'volatility': Decimal('0.15'),
            'max_drawdown': Decimal('0.05'),
            'value_at_risk': Decimal('0.02'),
            'max_correlation': Decimal('0.3'),
            'liquidity_ratio': Decimal('0.8'),
            'max_concentration': Decimal('0.1')
        }

    def _generate_risk_alerts(
        self,
        breaches: Dict[str, bool],
        risk_metrics: Dict[str, Decimal]
    ) -> List[Dict[str, Any]]:
        """Generate risk alerts for threshold breaches."""
        alerts = []

        for risk_type, is_breached in breaches.items():
            if is_breached:
                alerts.append({
                    'type': risk_type,
                    'severity': 'HIGH' if risk_type in ['volatility', 'drawdown'] else 'MEDIUM',
                    'message': f"{risk_type.replace('_', ' ').title()} threshold breached",
                    'current_value': risk_metrics.get(risk_type, Decimal('0')),
                    'timestamp': datetime.utcnow()
                })

        return alerts

