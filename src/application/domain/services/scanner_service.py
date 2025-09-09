"""
Scanner Service - Domain Service for Scanner Business Logic

This service encapsulates the business logic for scanner operations,
following Domain-Driven Design principles.

SOLID Principles:
- Single Responsibility: Handles scanner execution logic
- Open/Closed: Can be extended for new scanner types
- Liskov Substitution: Works with any scanner implementation
- Interface Segregation: Clean domain service interface
- Dependency Inversion: Depends on abstractions
"""

from typing import List, Dict, Any, Optional
from datetime import date, time

from ...interfaces.scanner_service_interface import IScannerService
from ...interfaces.base_scanner_interface import IBaseScanner


class ScannerService(IScannerService):
    """
    Domain service that orchestrates scanner operations.

    This service contains the business logic for running scanners
    and follows DDD principles by being in the domain layer.
    """

    def run_scanner_date_range(
        self,
        scanner: IBaseScanner,
        start_date: date,
        end_date: date,
        cutoff_time: Optional[time] = None,
        end_of_day_time: Optional[time] = None
    ) -> List[Dict[str, Any]]:
        """
        Run scanner for date range with business logic.

        Args:
            scanner: Scanner instance to run
            start_date: Start date for scanning
            end_date: End date for scanning
            cutoff_time: Optional cutoff time
            end_of_day_time: Optional end-of-day time

        Returns:
            List of scanner results with business logic applied
        """
        # Apply business rules for date range validation
        self._validate_date_range(start_date, end_date)

        # Execute scanner based on its capabilities
        if hasattr(scanner, 'scan_date_range') and start_date == end_date:
            # Enhanced scanner with single date support - use scan_date_range for consistency
            results = scanner.scan_date_range(
                start_date=start_date,
                end_date=end_date,
                cutoff_time=cutoff_time,
                end_of_day_time=end_of_day_time
            )
        else:
            # Basic scanner or multi-day scan - run single days
            results = self._run_single_day_scanner(
                scanner, start_date, end_date, cutoff_time
            )

        # Apply business rules to results
        return self._apply_business_rules(results)

    def _validate_date_range(self, start_date: date, end_date: date) -> None:
        """Validate date range according to business rules."""
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date")

        if (end_date - start_date).days > 30:
            raise ValueError("Date range cannot exceed 30 days")

        # Business rule: Only trading days
        if start_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            raise ValueError("Start date must be a weekday")

    def _run_single_day_scanner(
        self,
        scanner: IBaseScanner,
        start_date: date,
        end_date: date,
        cutoff_time: Optional[time]
    ) -> List[Dict[str, Any]]:
        """Run scanner day by day for basic scanners."""
        results = []
        current_date = start_date

        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday-Friday
                try:
                    day_result = scanner.scan(current_date, cutoff_time)
                    if not day_result.empty:
                        # Convert DataFrame to dict and add date
                        day_dict = day_result.to_dict('records')
                        for record in day_dict:
                            record['scan_date'] = current_date
                        results.extend(day_dict)
                except Exception as e:
                    # Log error but continue with other days
                    print(f"Warning: Failed to scan {current_date}: {e}")

            current_date += timedelta(days=1)

        return results

    def _apply_business_rules(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply business rules to scanner results."""
        if not results:
            return results

        # Business rule: Filter out invalid results
        valid_results = []
        for result in results:
            if self._is_valid_result(result):
                # Apply business transformations
                transformed_result = self._transform_result(result)
                valid_results.append(transformed_result)

        # Business rule: Sort by relevance score
        return sorted(valid_results, key=lambda x: x.get('probability_score', 0), reverse=True)

    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        """Validate result according to business rules."""
        # Must have symbol
        if not result.get('symbol'):
            return False

        # Must have valid price - check multiple possible price fields
        price = (result.get('current_price') or
                result.get('close') or
                result.get('breakout_price') or
                result.get('price') or 0)

        if price <= 0 or price > 100000:  # Reasonable price bounds
            return False

        # Must have probability score for ranking
        if 'probability_score' not in result:
            return False

        return True

    def _transform_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Transform result according to business rules."""
        transformed = result.copy()

        # Ensure consistent field names
        if 'close' in transformed and 'current_price' not in transformed:
            transformed['current_price'] = transformed['close']

        # Add business metadata
        transformed['processed_by'] = 'ScannerService'
        transformed['business_rules_applied'] = True

        return transformed
