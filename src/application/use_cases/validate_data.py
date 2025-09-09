"""
Validate Data Use Case
======================

Orchestrates data validation processes by coordinating between
domain services, repositories, and validation frameworks.

This use case handles:
- Data quality validation using Great Expectations
- Schema validation and integrity checks
- Business rule validation
- Anomaly detection and outlier identification
- Validation result aggregation and reporting
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime
from dataclasses import dataclass
from enum import Enum

from ...domain.repositories.market_data_repo import MarketDataRepository
from ...application.ports.event_bus_port import EventBusPort
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


class ValidationType(Enum):
    """Types of data validation."""
    SCHEMA = "schema"
    QUALITY = "quality"
    BUSINESS_RULES = "business_rules"
    ANOMALY = "anomaly"
    COMPREHENSIVE = "comprehensive"


@dataclass
class ValidationRequest:
    """Request data for data validation."""
    validation_type: ValidationType
    symbols: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    fail_fast: bool = False
    generate_report: bool = True


@dataclass
class ValidationResult:
    """Result data from data validation."""
    validation_type: ValidationType
    total_checks: int
    passed_checks: int
    failed_checks: int
    symbols_validated: int
    validation_timestamp: datetime
    execution_time_seconds: float
    results: Dict[str, Any]
    errors: List[str]


class ValidateDataUseCase:
    """
    Use case for orchestrating data validation operations.

    This class coordinates the validation workflow by:
    1. Validating validation parameters
    2. Executing appropriate validation checks
    3. Aggregating validation results
    4. Publishing validation events
    5. Generating validation reports
    """

    def __init__(
        self,
        market_data_repo: MarketDataRepository,
        event_bus: EventBus
    ):
        """
        Initialize the validate data use case.

        Args:
            market_data_repo: Repository for market data access
            event_bus: Event bus for publishing validation events
        """
        self.market_data_repo = market_data_repo
        self.event_bus = event_bus

        logger.info("ValidateDataUseCase initialized")

    def execute(self, request: ValidationRequest) -> ValidationResult:
        """
        Execute data validation for the given request.

        Args:
            request: Validation request with parameters

        Returns:
            ValidationResult containing validation statistics

        Raises:
            ValueError: If validation parameters are invalid
            RuntimeError: If validation fails
        """
        start_time = datetime.now()
        logger.info(f"Starting {request.validation_type.value} data validation")

        # Validate request
        self._validate_request(request)

        # Execute validation based on type
        if request.validation_type == ValidationType.SCHEMA:
            result = self._execute_schema_validation(request)
        elif request.validation_type == ValidationType.QUALITY:
            result = self._execute_quality_validation(request)
        elif request.validation_type == ValidationType.BUSINESS_RULES:
            result = self._execute_business_rules_validation(request)
        elif request.validation_type == ValidationType.ANOMALY:
            result = self._execute_anomaly_validation(request)
        elif request.validation_type == ValidationType.COMPREHENSIVE:
            result = self._execute_comprehensive_validation(request)
        else:
            raise ValueError(f"Unsupported validation type: {request.validation_type}")

        execution_time = (datetime.now() - start_time).total_seconds()

        final_result = ValidationResult(
            validation_type=request.validation_type,
            total_checks=result['total_checks'],
            passed_checks=result['passed_checks'],
            failed_checks=result['failed_checks'],
            symbols_validated=result['symbols_validated'],
            validation_timestamp=start_time,
            execution_time_seconds=execution_time,
            results=result['results'],
            errors=result['errors']
        )

        # Publish completion event
        self._publish_validation_completed_event(final_result)

        # Generate report if requested
        if request.generate_report:
            self._generate_validation_report(final_result)

        logger.info(f"Data validation completed: {final_result.total_checks} checks, "
                   f"{final_result.passed_checks} passed, "
                   f"{final_result.failed_checks} failed in {execution_time:.2f}s")

        return final_result

    def _execute_schema_validation(self, request: ValidationRequest) -> Dict[str, Any]:
        """
        Execute schema validation.

        Args:
            request: Validation request parameters

        Returns:
            Dictionary with validation statistics
        """
        logger.info("Executing schema validation")

        symbols = request.symbols or self.market_data_repo.get_all_symbols()
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        results = {}
        errors = []

        for symbol in symbols:
            try:
                logger.debug(f"Validating schema for {symbol}")

                # Get sample data for schema validation
                sample_data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    limit=100  # Sample for schema validation
                )

                if sample_data.empty:
                    logger.warning(f"No data found for {symbol}")
                    continue

                # Validate required columns
                required_columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in sample_data.columns]

                total_checks += len(required_columns)

                if missing_columns:
                    failed_checks += len(missing_columns)
                    results[symbol] = {
                        'status': 'failed',
                        'missing_columns': missing_columns
                    }
                else:
                    passed_checks += len(required_columns)
                    results[symbol] = {'status': 'passed'}

                # Validate data types
                if 'timestamp' in sample_data.columns:
                    total_checks += 1
                    try:
                        pd.to_datetime(sample_data['timestamp'])
                        passed_checks += 1
                    except Exception:
                        failed_checks += 1
                        results[symbol]['timestamp_type_error'] = True

                # Validate numeric columns
                numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_columns:
                    if col in sample_data.columns:
                        total_checks += 1
                        if pd.api.types.is_numeric_dtype(sample_data[col]):
                            passed_checks += 1
                        else:
                            failed_checks += 1
                            results[symbol][f'{col}_type_error'] = True

            except Exception as e:
                error_msg = f"Schema validation failed for {symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_checks += 1

        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'symbols_validated': len(symbols),
            'results': results,
            'errors': errors
        }

    def _execute_quality_validation(self, request: ValidationRequest) -> Dict[str, Any]:
        """
        Execute data quality validation.

        Args:
            request: Validation request parameters

        Returns:
            Dictionary with validation statistics
        """
        logger.info("Executing quality validation")

        symbols = request.symbols or self.market_data_repo.get_all_symbols()
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        results = {}
        errors = []

        for symbol in symbols:
            try:
                logger.debug(f"Validating data quality for {symbol}")

                # Get data for quality validation
                data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    start_date=request.start_date,
                    end_date=request.end_date
                )

                if data.empty:
                    logger.warning(f"No data found for {symbol}")
                    continue

                results[symbol] = {}

                # Check for null values
                null_counts = data.isnull().sum()
                total_checks += len(data.columns)

                for col in data.columns:
                    if null_counts[col] > 0:
                        failed_checks += 1
                        results[symbol][f'{col}_null_count'] = int(null_counts[col])
                    else:
                        passed_checks += 1

                # Check for negative prices
                price_columns = ['open', 'high', 'low', 'close']
                for col in price_columns:
                    if col in data.columns:
                        total_checks += 1
                        negative_count = (data[col] < 0).sum()
                        if negative_count > 0:
                            failed_checks += 1
                            results[symbol][f'{col}_negative_count'] = int(negative_count)
                        else:
                            passed_checks += 1

                # Check for zero volumes
                if 'volume' in data.columns:
                    total_checks += 1
                    zero_volume_count = (data['volume'] == 0).sum()
                    if zero_volume_count > len(data) * 0.1:  # More than 10% zeros
                        failed_checks += 1
                        results[symbol]['zero_volume_percentage'] = zero_volume_count / len(data)
                    else:
                        passed_checks += 1

                # Check OHLC relationships
                total_checks += 1
                invalid_ohlc = (
                    (data['high'] < data['low']) |
                    (data['high'] < data['open']) |
                    (data['high'] < data['close']) |
                    (data['low'] > data['open']) |
                    (data['low'] > data['close'])
                ).sum()

                if invalid_ohlc > 0:
                    failed_checks += 1
                    results[symbol]['invalid_ohlc_count'] = int(invalid_ohlc)
                else:
                    passed_checks += 1

            except Exception as e:
                error_msg = f"Quality validation failed for {symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_checks += 1

        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'symbols_validated': len(symbols),
            'results': results,
            'errors': errors
        }

    def _execute_business_rules_validation(self, request: ValidationRequest) -> Dict[str, Any]:
        """
        Execute business rules validation.

        Args:
            request: Validation request parameters

        Returns:
            Dictionary with validation statistics
        """
        logger.info("Executing business rules validation")

        symbols = request.symbols or self.market_data_repo.get_all_symbols()
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        results = {}
        errors = []

        for symbol in symbols:
            try:
                logger.debug(f"Validating business rules for {symbol}")

                # Get data for business rules validation
                data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    start_date=request.start_date,
                    end_date=request.end_date
                )

                if data.empty:
                    logger.warning(f"No data found for {symbol}")
                    continue

                results[symbol] = {}

                # Business rule: Trading hours (9:15 AM to 3:30 PM IST)
                if 'timestamp' in data.columns:
                    total_checks += 1
                    data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
                    data['minute'] = pd.to_datetime(data['timestamp']).dt.minute

                    invalid_hours = ~(
                        ((data['hour'] == 9) & (data['minute'] >= 15)) |
                        ((data['hour'] > 9) & (data['hour'] < 15)) |
                        ((data['hour'] == 15) & (data['minute'] <= 30))
                    )

                    invalid_count = invalid_hours.sum()
                    if invalid_count > 0:
                        failed_checks += 1
                        results[symbol]['invalid_trading_hours'] = int(invalid_count)
                    else:
                        passed_checks += 1

                # Business rule: Reasonable price ranges
                if 'close' in data.columns:
                    total_checks += 1
                    # Assuming reasonable range for Indian stocks
                    unreasonable_prices = (
                        (data['close'] < 1) | (data['close'] > 100000)
                    ).sum()

                    if unreasonable_prices > 0:
                        failed_checks += 1
                        results[symbol]['unreasonable_prices'] = int(unreasonable_prices)
                    else:
                        passed_checks += 1

                # Business rule: Volume thresholds
                if 'volume' in data.columns:
                    total_checks += 1
                    # Check for abnormally high volumes
                    volume_mean = data['volume'].mean()
                    volume_std = data['volume'].std()
                    outlier_volumes = (data['volume'] > volume_mean + 5 * volume_std).sum()

                    if outlier_volumes > len(data) * 0.01:  # More than 1% outliers
                        failed_checks += 1
                        results[symbol]['volume_outliers'] = int(outlier_volumes)
                    else:
                        passed_checks += 1

            except Exception as e:
                error_msg = f"Business rules validation failed for {symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_checks += 1

        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'symbols_validated': len(symbols),
            'results': results,
            'errors': errors
        }

    def _execute_anomaly_validation(self, request: ValidationRequest) -> Dict[str, Any]:
        """
        Execute anomaly detection validation.

        Args:
            request: Validation request parameters

        Returns:
            Dictionary with validation statistics
        """
        logger.info("Executing anomaly validation")

        symbols = request.symbols or self.market_data_repo.get_all_symbols()
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        results = {}
        errors = []

        for symbol in symbols:
            try:
                logger.debug(f"Detecting anomalies for {symbol}")

                # Get data for anomaly detection
                data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    start_date=request.start_date,
                    end_date=request.end_date
                )

                if len(data) < 30:  # Need minimum data for anomaly detection
                    logger.warning(f"Insufficient data for anomaly detection: {symbol}")
                    continue

                results[symbol] = {}

                # Simple statistical anomaly detection for price changes
                if 'close' in data.columns:
                    total_checks += 1
                    data['price_change_pct'] = data['close'].pct_change()

                    # Detect extreme price changes (>20% in a day)
                    extreme_changes = (abs(data['price_change_pct']) > 0.20).sum()

                    if extreme_changes > 0:
                        failed_checks += 1
                        results[symbol]['extreme_price_changes'] = int(extreme_changes)
                    else:
                        passed_checks += 1

                # Volume anomaly detection
                if 'volume' in data.columns:
                    total_checks += 1
                    volume_mean = data['volume'].mean()
                    volume_std = data['volume'].std()

                    # Detect volume spikes (>3 standard deviations)
                    volume_spikes = (data['volume'] > volume_mean + 3 * volume_std).sum()

                    if volume_spikes > len(data) * 0.05:  # More than 5% spikes
                        failed_checks += 1
                        results[symbol]['volume_spikes'] = int(volume_spikes)
                    else:
                        passed_checks += 1

            except Exception as e:
                error_msg = f"Anomaly validation failed for {symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_checks += 1

        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'symbols_validated': len(symbols),
            'results': results,
            'errors': errors
        }

    def _execute_comprehensive_validation(self, request: ValidationRequest) -> Dict[str, Any]:
        """
        Execute comprehensive validation (all types).

        Args:
            request: Validation request parameters

        Returns:
            Dictionary with validation statistics
        """
        logger.info("Executing comprehensive validation")

        # Run all validation types
        validation_types = [
            ValidationType.SCHEMA,
            ValidationType.QUALITY,
            ValidationType.BUSINESS_RULES,
            ValidationType.ANOMALY
        ]

        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        all_results = {}
        all_errors = []

        for validation_type in validation_types:
            temp_request = ValidationRequest(
                validation_type=validation_type,
                symbols=request.symbols,
                start_date=request.start_date,
                end_date=request.end_date,
                fail_fast=False,
                generate_report=False
            )

            try:
                result = self.execute(temp_request)
                total_checks += result.total_checks
                passed_checks += result.passed_checks
                failed_checks += result.failed_checks
                all_results[validation_type.value] = result.results
                all_errors.extend(result.errors)
            except Exception as e:
                logger.error(f"Comprehensive validation failed for {validation_type.value}: {e}")
                all_errors.append(f"{validation_type.value}: {str(e)}")

        return {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'symbols_validated': len(request.symbols or self.market_data_repo.get_all_symbols()),
            'results': all_results,
            'errors': all_errors
        }

    def _validate_request(self, request: ValidationRequest):
        """
        Validate validation request parameters.

        Args:
            request: Validation request to validate

        Raises:
            ValueError: If validation fails
        """
        if request.start_date and request.end_date and request.start_date > request.end_date:
            raise ValueError("Start date cannot be after end date")

    def _publish_validation_completed_event(self, result: ValidationResult):
        """
        Publish validation completion event to the event bus.

        Args:
            result: Validation results to publish
        """
        event_data = {
            'validation_type': result.validation_type.value,
            'validation_timestamp': result.validation_timestamp.isoformat(),
            'total_checks': result.total_checks,
            'passed_checks': result.passed_checks,
            'failed_checks': result.failed_checks,
            'symbols_validated': result.symbols_validated,
            'execution_time_seconds': result.execution_time_seconds,
            'errors': result.errors
        }

        try:
            self.event_bus.publish({
                'event_type': 'data_validation_completed',
                'data': event_data,
                'timestamp': datetime.now().isoformat()
            })
            logger.info("Published data validation completion event")
        except Exception as e:
            logger.error(f"Failed to publish validation completion event: {e}")

    def _generate_validation_report(self, result: ValidationResult):
        """
        Generate validation report.

        Args:
            result: Validation results to report
        """
        try:
            report_path = f"reports/validation_report_{result.validation_timestamp.strftime('%Y%m%d_%H%M%S')}.json"

            report_data = {
                'validation_type': result.validation_type.value,
                'timestamp': result.validation_timestamp.isoformat(),
                'summary': {
                    'total_checks': result.total_checks,
                    'passed_checks': result.passed_checks,
                    'failed_checks': result.failed_checks,
                    'symbols_validated': result.symbols_validated,
                    'success_rate': result.passed_checks / result.total_checks if result.total_checks > 0 else 0
                },
                'results': result.results,
                'errors': result.errors
            }

            import json
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

            logger.info(f"Validation report generated: {report_path}")

        except Exception as e:
            logger.error(f"Failed to generate validation report: {e}")
