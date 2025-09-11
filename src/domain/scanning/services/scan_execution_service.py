"""
Scan Execution Service

This module defines the ScanExecutionService domain service
for managing scan execution and signal generation.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from domain.shared.exceptions import DomainException
from ..entities.scan import Scan, ScanId, ScanStatus, Signal, SignalStrength
from ..entities.rule import Rule
from ..value_objects.scan_parameters import ScanConfiguration, SignalThresholds
from ..repositories.scan_repository import ScanRepository
from ..repositories.rule_repository import RuleRepository


class ScanExecutionService:
    """
    Domain service for scan execution and orchestration.

    Handles the business logic for executing market scans,
    applying rules, and generating trading signals.
    """

    def __init__(
        self,
        scan_repository: ScanRepository,
        rule_repository: RuleRepository
    ):
        self.scan_repository = scan_repository
        self.rule_repository = rule_repository

    def execute_scan(self, scan: Scan) -> Scan:
        """
        Execute a market scan and generate signals.

        This is the main entry point for scan execution.
        """
        # Validate scan before execution
        self._validate_scan_for_execution(scan)

        # Start execution
        scan.start_execution()
        self.scan_repository.save(scan)

        try:
            # Get active rules for this scan type
            rules = self._get_active_rules_for_scan(scan)

            if not rules:
                raise DomainException(f"No active rules found for scan type: {scan.criteria.scan_type.value}")

            # Execute scan logic
            signals = self._execute_scan_logic(scan, rules)

            # Filter and rank signals
            filtered_signals = self._filter_and_rank_signals(signals, scan.criteria.parameters)

            # Complete scan execution
            scan.complete_execution(filtered_signals)
            self.scan_repository.save(scan)

            # Update rule performance metrics
            self._update_rule_performance(rules, filtered_signals)

            return scan

        except Exception as e:
            # Handle execution failure
            scan.fail_execution(str(e))
            self.scan_repository.save(scan)
            raise

    def _validate_scan_for_execution(self, scan: Scan) -> None:
        """Validate scan parameters before execution."""
        if scan.status != ScanStatus.PENDING:
            raise DomainException(f"Scan {scan.id.value} is not in pending status")

        # Validate scan criteria
        if not scan.criteria.parameters:
            raise DomainException("Scan criteria parameters are required")

        # Additional business validations can be added here
        self._apply_business_validations(scan)

    def _apply_business_validations(self, scan: Scan) -> None:
        """Apply business-specific validations."""
        # Check if scan type is supported
        supported_types = ['breakout', 'consolidation', 'trend', 'volume', 'momentum', 'reversal']
        if scan.criteria.scan_type.value not in supported_types:
            raise DomainException(f"Unsupported scan type: {scan.criteria.scan_type.value}")

        # Validate required parameters for scan type
        required_params = self._get_required_parameters(scan.criteria.scan_type.value)
        for param in required_params:
            if param not in scan.criteria.parameters:
                raise DomainException(f"Missing required parameter: {param}")

    def _get_required_parameters(self, scan_type: str) -> List[str]:
        """Get required parameters for a scan type."""
        requirements = {
            'breakout': ['timeframe', 'min_volume'],
            'consolidation': ['consolidation_period'],
            'trend': ['trend_period'],
            'volume': ['volume_threshold'],
            'momentum': ['momentum_period'],
            'reversal': ['reversal_sensitivity']
        }
        return requirements.get(scan_type, [])

    def _get_active_rules_for_scan(self, scan: Scan) -> List[Rule]:
        """Get active rules that match the scan criteria."""
        # Get all active rules
        active_rules = self.rule_repository.find_active_rules()

        # Filter rules by scan type
        matching_rules = []
        for rule in active_rules:
            if rule.rule_type.value == scan.criteria.scan_type.value:
                matching_rules.append(rule)

        return matching_rules

    def _execute_scan_logic(self, scan: Scan, rules: List[Rule]) -> List[Signal]:
        """
        Execute the core scan logic using rules and market data.

        This is a simplified implementation. In a real system,
        this would integrate with market data providers and
        execute rules against real-time or historical data.
        """
        signals = []

        # Simulate market data for scanning
        # In a real implementation, this would fetch actual market data
        market_data_points = self._get_market_data_for_scan(scan)

        for data_point in market_data_points:
            for rule in rules:
                # Execute rule against market data
                signal_data = rule.execute(data_point)

                if signal_data:
                    # Convert rule output to Signal entity
                    signal = self._create_signal_from_rule_output(signal_data, data_point)
                    signals.append(signal)

        return signals

    def _get_market_data_for_scan(self, scan: Scan) -> List[Dict[str, Any]]:
        """
        Get market data for scanning.

        This is a placeholder for actual market data retrieval.
        In a real system, this would query market data repositories
        or integrate with market data feeds.
        """
        # Simulate market data points
        # In production, this would be replaced with actual data queries
        return [
            {
                'symbol': 'AAPL',
                'price': Decimal('150.25'),
                'volume': 1000000,
                'timestamp': datetime.utcnow(),
                'high': Decimal('151.00'),
                'low': Decimal('149.50'),
                'open': Decimal('150.00'),
                'close': Decimal('150.25'),
                'price_change_pct': Decimal('0.5'),
                'volume_multiplier': Decimal('1.2')
            },
            {
                'symbol': 'MSFT',
                'price': Decimal('280.75'),
                'volume': 800000,
                'timestamp': datetime.utcnow(),
                'high': Decimal('282.00'),
                'low': Decimal('279.00'),
                'open': Decimal('280.00'),
                'close': Decimal('280.75'),
                'price_change_pct': Decimal('0.3'),
                'volume_multiplier': Decimal('0.9')
            },
            {
                'symbol': 'GOOGL',
                'price': Decimal('2750.50'),
                'volume': 500000,
                'timestamp': datetime.utcnow(),
                'high': Decimal('2760.00'),
                'low': Decimal('2740.00'),
                'open': Decimal('2750.00'),
                'close': Decimal('2750.50'),
                'price_change_pct': Decimal('0.1'),
                'volume_multiplier': Decimal('1.5')
            }
        ]

    def _create_signal_from_rule_output(
        self,
        signal_data: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Signal:
        """Create a Signal entity from rule execution output."""
        # Extract signal parameters
        signal_type = signal_data.get('signal_type', 'BUY')
        confidence = Decimal(str(signal_data.get('confidence', 0.5)))

        # Determine signal strength based on confidence
        if confidence >= Decimal('0.8'):
            strength = SignalStrength.VERY_STRONG
        elif confidence >= Decimal('0.6'):
            strength = SignalStrength.STRONG
        elif confidence >= Decimal('0.4'):
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        # Create signal
        return Signal(
            symbol=market_data['symbol'],
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            price=market_data['price'],
            volume=market_data.get('volume'),
            metadata={
                'rule_id': signal_data.get('rule_id'),
                'rule_name': signal_data.get('rule_name'),
                'market_data': market_data
            }
        )

    def _filter_and_rank_signals(
        self,
        signals: List[Signal],
        criteria_params: Dict[str, Any]
    ) -> List[Signal]:
        """Filter and rank signals based on criteria."""
        # Apply signal thresholds
        thresholds = self._get_signal_thresholds(criteria_params)

        filtered_signals = []
        for signal in signals:
            if (signal.confidence >= thresholds.min_confidence and
                signal.get_signal_score() >= thresholds.min_strength_score):
                filtered_signals.append(signal)

        # Sort by signal score (descending)
        filtered_signals.sort(key=lambda s: s.get_signal_score(), reverse=True)

        # Apply maximum signals limit
        max_signals = criteria_params.get('max_signals', thresholds.max_signals_per_scan)
        return filtered_signals[:max_signals]

    def _get_signal_thresholds(self, criteria_params: Dict[str, Any]) -> SignalThresholds:
        """Get signal thresholds from criteria parameters."""
        from ..value_objects.scan_parameters import SignalThresholds

        return SignalThresholds(
            min_confidence=Decimal(str(criteria_params.get('min_confidence', 0.5))),
            min_strength_score=Decimal(str(criteria_params.get('min_strength_score', 0.7))),
            max_signals_per_scan=criteria_params.get('max_signals', 50),
            signal_cooldown_minutes=criteria_params.get('cooldown_minutes', 5)
        )

    def _update_rule_performance(self, rules: List[Rule], signals: List[Signal]) -> None:
        """Update performance metrics for rules based on signal results."""
        # Group signals by rule
        rule_signals = {}
        for signal in signals:
            rule_id = signal.metadata.get('rule_id')
            if rule_id:
                if rule_id not in rule_signals:
                    rule_signals[rule_id] = []
                rule_signals[rule_id].append({
                    'success': signal.confidence >= Decimal('0.6'),  # Simplified success criteria
                    'return': Decimal('0.02') if signal.confidence >= Decimal('0.7') else Decimal('0')
                })

        # Update each rule's performance
        for rule in rules:
            rule_signals_list = rule_signals.get(rule.id.value, [])
            if rule_signals_list:
                self.rule_repository.update_rule_performance(rule.id, rule_signals_list)

    def get_scan_execution_summary(self) -> dict:
        """Get summary of scan execution statistics."""
        return self.scan_repository.get_scan_execution_stats()

    def get_top_performing_rules(self, limit: int = 5) -> List[Rule]:
        """Get top performing rules."""
        return self.rule_repository.find_top_performing_rules(limit)

    def cancel_scan(self, scan_id: ScanId) -> Scan:
        """Cancel a running scan."""
        scan = self.scan_repository.find_by_id(scan_id)
        if not scan:
            raise DomainException(f"Scan {scan_id.value} not found")

        if scan.status not in [ScanStatus.PENDING, ScanStatus.RUNNING]:
            raise DomainException(f"Scan {scan_id.value} cannot be cancelled")

        scan.cancel_execution()
        self.scan_repository.save(scan)

        return scan

