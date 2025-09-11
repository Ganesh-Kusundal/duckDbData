#!/usr/bin/env python3
"""
Sync Verification Service for Broker Integration

This service provides verification mechanisms to ensure that broker data synchronization
is working correctly and that data integrity is maintained across sync operations.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from domain.broker_integration.entities.broker_connection import BrokerConnectionId
from domain.shared.exceptions import DomainException
from infrastructure.adapters.dhan_broker_adapter import DhanBrokerAdapter
from infrastructure.external.broker_integration_adapter import get_broker_integration_manager

logger = logging.getLogger(__name__)


class SyncVerificationStatus(Enum):
    """Status of sync verification."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"


class SyncVerificationType(Enum):
    """Types of sync verification."""
    ACCOUNT_DATA = "account_data"
    POSITIONS = "positions"
    ORDERS = "orders"
    MARKET_DATA = "market_data"
    FULL_SYNC = "full_sync"


@dataclass
class SyncVerificationResult:
    """Result of sync verification operation."""
    verification_id: str
    connection_id: str
    verification_type: SyncVerificationType
    status: SyncVerificationStatus
    timestamp: datetime
    checks_performed: List[str]
    issues_found: List[str]
    data_consistency_score: float  # 0.0 to 1.0
    recommendations: List[str]
    details: Dict[str, Any]

    def is_successful(self) -> bool:
        """Check if verification was successful."""
        return self.status == SyncVerificationStatus.SUCCESS

    def has_issues(self) -> bool:
        """Check if verification found issues."""
        return len(self.issues_found) > 0

    def get_summary(self) -> Dict[str, Any]:
        """Get verification summary."""
        return {
            'verification_id': self.verification_id,
            'connection_id': self.connection_id,
            'type': self.verification_type.value,
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'checks_count': len(self.checks_performed),
            'issues_count': len(self.issues_found),
            'data_consistency': f"{self.data_consistency_score:.2%}",
            'recommendations_count': len(self.recommendations)
        }


class SyncVerificationService:
    """
    Service for verifying broker data synchronization integrity.

    This service performs comprehensive checks to ensure that:
    - Broker connections are working
    - Account data is syncing correctly
    - Position data is accurate
    - Order status is up to date
    - Market data is current
    """

    def __init__(self):
        self.broker_manager = get_broker_integration_manager()
        self.verification_history: List[SyncVerificationResult] = []
        self._active_verifications: Dict[str, asyncio.Task] = {}

    async def verify_connection_sync(self, connection_id: str) -> SyncVerificationResult:
        """
        Verify that broker connection sync is working.

        Args:
            connection_id: Broker connection ID to verify

        Returns:
            SyncVerificationResult with verification details
        """
        verification_id = f"conn_verify_{connection_id}_{int(datetime.now().timestamp())}"
        checks_performed = []
        issues_found = []
        recommendations = []

        try:
            # Check 1: Connection exists and is active
            checks_performed.append("connection_existence")
            if connection_id not in self.broker_manager.active_connections:
                issues_found.append(f"Connection {connection_id} not found in active connections")
                recommendations.append("Ensure broker connection is established before verification")

            # Check 2: Adapter is available
            checks_performed.append("adapter_availability")
            adapter = self.broker_manager.adapters.get(connection_id)
            if not adapter:
                issues_found.append(f"No adapter found for connection {connection_id}")
                recommendations.append("Initialize broker adapter before verification")

            # Check 3: Basic connectivity test
            if adapter:
                checks_performed.append("basic_connectivity")
                try:
                    health = await adapter.health_check()
                    if health.get('status') != 'healthy':
                        issues_found.append(f"Broker health check failed: {health.get('error', 'Unknown error')}")
                        recommendations.append("Check broker credentials and network connectivity")
                    else:
                        logger.info(f"✅ Broker {connection_id} health check passed")
                except Exception as e:
                    issues_found.append(f"Health check error: {str(e)}")
                    recommendations.append("Investigate broker connectivity issues")

            # Check 4: Authentication status
            if adapter and hasattr(adapter, 'is_authenticated'):
                checks_performed.append("authentication_status")
                if not adapter.is_authenticated():
                    issues_found.append("Broker authentication failed")
                    recommendations.append("Verify broker credentials and re-authenticate")

            # Calculate consistency score
            total_checks = len(checks_performed)
            successful_checks = total_checks - len(issues_found)
            consistency_score = successful_checks / total_checks if total_checks > 0 else 0.0

            status = SyncVerificationStatus.SUCCESS if consistency_score == 1.0 else \
                    SyncVerificationStatus.PARTIAL if consistency_score > 0.5 else \
                    SyncVerificationStatus.FAILURE

            result = SyncVerificationResult(
                verification_id=verification_id,
                connection_id=connection_id,
                verification_type=SyncVerificationType.ACCOUNT_DATA,
                status=status,
                timestamp=datetime.now(),
                checks_performed=checks_performed,
                issues_found=issues_found,
                data_consistency_score=consistency_score,
                recommendations=recommendations,
                details={
                    'connection_status': 'active' if connection_id in self.broker_manager.active_connections else 'inactive',
                    'adapter_type': type(adapter).__name__ if adapter else 'None',
                    'health_status': health.get('status') if 'health' in locals() else 'unknown'
                }
            )

            self.verification_history.append(result)
            logger.info(f"Connection sync verification completed: {result.get_summary()}")

            return result

        except Exception as e:
            logger.error(f"Connection sync verification failed: {e}")
            return SyncVerificationResult(
                verification_id=verification_id,
                connection_id=connection_id,
                verification_type=SyncVerificationType.ACCOUNT_DATA,
                status=SyncVerificationStatus.FAILURE,
                timestamp=datetime.now(),
                checks_performed=checks_performed,
                issues_found=[f"Verification error: {str(e)}"],
                data_consistency_score=0.0,
                recommendations=["Investigate system errors"],
                details={'error': str(e)}
            )

    async def verify_account_data_sync(self, connection_id: str) -> SyncVerificationResult:
        """
        Verify that account data synchronization is working correctly.

        Args:
            connection_id: Broker connection ID to verify

        Returns:
            SyncVerificationResult with account data verification details
        """
        verification_id = f"account_verify_{connection_id}_{int(datetime.now().timestamp())}"
        checks_performed = []
        issues_found = []
        recommendations = []

        try:
            # Check 1: Account info retrieval
            checks_performed.append("account_info_retrieval")
            account_summary = await self.broker_manager.get_account_summary(connection_id)

            if not account_summary.get('success', False):
                issues_found.append(f"Failed to retrieve account summary: {account_summary.get('error', 'Unknown error')}")
                recommendations.append("Check broker API permissions for account data")

            # Check 2: Account data completeness
            if account_summary.get('success'):
                checks_performed.append("account_data_completeness")
                account_data = account_summary.get('account', {})

                required_fields = ['cash_balance', 'buying_power', 'total_value']
                missing_fields = [field for field in required_fields if field not in account_data]

                if missing_fields:
                    issues_found.append(f"Missing account fields: {missing_fields}")
                    recommendations.append("Ensure broker API provides complete account information")

                # Check 3: Data reasonableness
                checks_performed.append("account_data_reasonableness")
                cash_balance = account_data.get('cash_balance', 0)
                if cash_balance < 0:
                    issues_found.append("Negative cash balance detected")
                    recommendations.append("Review account status and margin requirements")

            # Check 4: Positions data
            checks_performed.append("positions_data_sync")
            if account_summary.get('success'):
                positions = account_summary.get('positions', [])
                # Basic validation - ensure positions is a list
                if not isinstance(positions, list):
                    issues_found.append("Positions data is not in expected format")
                    recommendations.append("Verify broker API response format for positions")

            # Calculate consistency score
            total_checks = len(checks_performed)
            successful_checks = total_checks - len(issues_found)
            consistency_score = successful_checks / total_checks if total_checks > 0 else 0.0

            status = SyncVerificationStatus.SUCCESS if consistency_score == 1.0 else \
                    SyncVerificationStatus.PARTIAL if consistency_score > 0.5 else \
                    SyncVerificationStatus.FAILURE

            result = SyncVerificationResult(
                verification_id=verification_id,
                connection_id=connection_id,
                verification_type=SyncVerificationType.ACCOUNT_DATA,
                status=status,
                timestamp=datetime.now(),
                checks_performed=checks_performed,
                issues_found=issues_found,
                data_consistency_score=consistency_score,
                recommendations=recommendations,
                details={
                    'account_data_available': account_summary.get('success', False),
                    'positions_count': len(account_summary.get('positions', [])) if account_summary.get('success') else 0,
                    'account_fields_present': list(account_data.keys()) if 'account_data' in locals() else []
                }
            )

            self.verification_history.append(result)
            logger.info(f"Account data sync verification completed: {result.get_summary()}")

            return result

        except Exception as e:
            logger.error(f"Account data sync verification failed: {e}")
            return SyncVerificationResult(
                verification_id=verification_id,
                connection_id=connection_id,
                verification_type=SyncVerificationType.ACCOUNT_DATA,
                status=SyncVerificationStatus.FAILURE,
                timestamp=datetime.now(),
                checks_performed=checks_performed,
                issues_found=[f"Verification error: {str(e)}"],
                data_consistency_score=0.0,
                recommendations=["Investigate system errors"],
                details={'error': str(e)}
            )

    async def verify_full_sync_integrity(self, connection_id: str) -> SyncVerificationResult:
        """
        Perform comprehensive sync integrity verification.

        Args:
            connection_id: Broker connection ID to verify

        Returns:
            SyncVerificationResult with full sync verification details
        """
        verification_id = f"full_sync_verify_{connection_id}_{int(datetime.now().timestamp())}"

        try:
            # Run all verification types
            connection_result = await self.verify_connection_sync(connection_id)
            account_result = await self.verify_account_data_sync(connection_id)

            # Combine results
            all_checks = connection_result.checks_performed + account_result.checks_performed
            all_issues = connection_result.issues_found + account_result.issues_found
            all_recommendations = list(set(connection_result.recommendations + account_result.recommendations))

            # Calculate weighted consistency score
            connection_weight = 0.4
            account_weight = 0.6

            consistency_score = (
                connection_result.data_consistency_score * connection_weight +
                account_result.data_consistency_score * account_weight
            )

            status = SyncVerificationStatus.SUCCESS if consistency_score >= 0.8 else \
                    SyncVerificationStatus.PARTIAL if consistency_score >= 0.5 else \
                    SyncVerificationStatus.FAILURE

            result = SyncVerificationResult(
                verification_id=verification_id,
                connection_id=connection_id,
                verification_type=SyncVerificationType.FULL_SYNC,
                status=status,
                timestamp=datetime.now(),
                checks_performed=all_checks,
                issues_found=all_issues,
                data_consistency_score=consistency_score,
                recommendations=all_recommendations,
                details={
                    'connection_verification': connection_result.get_summary(),
                    'account_verification': account_result.get_summary(),
                    'overall_score': consistency_score
                }
            )

            self.verification_history.append(result)
            logger.info(f"Full sync integrity verification completed: {result.get_summary()}")

            return result

        except Exception as e:
            logger.error(f"Full sync integrity verification failed: {e}")
            return SyncVerificationResult(
                verification_id=verification_id,
                connection_id=connection_id,
                verification_type=SyncVerificationType.FULL_SYNC,
                status=SyncVerificationStatus.FAILURE,
                timestamp=datetime.now(),
                checks_performed=[],
                issues_found=[f"Full verification error: {str(e)}"],
                data_consistency_score=0.0,
                recommendations=["Investigate system errors"],
                details={'error': str(e)}
            )

    async def get_verification_history(self, connection_id: Optional[str] = None,
                                     limit: int = 10) -> List[SyncVerificationResult]:
        """
        Get verification history for a connection or all connections.

        Args:
            connection_id: Optional connection ID filter
            limit: Maximum number of results to return

        Returns:
            List of recent verification results
        """
        if connection_id:
            history = [r for r in self.verification_history if r.connection_id == connection_id]
        else:
            history = self.verification_history

        # Sort by timestamp descending and limit results
        history.sort(key=lambda x: x.timestamp, reverse=True)
        return history[:limit]

    def get_verification_stats(self, connection_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get verification statistics.

        Args:
            connection_id: Optional connection ID filter

        Returns:
            Dictionary with verification statistics
        """
        if connection_id:
            history = [r for r in self.verification_history if r.connection_id == connection_id]
        else:
            history = self.verification_history

        if not history:
            return {
                'total_verifications': 0,
                'success_rate': 0.0,
                'average_consistency_score': 0.0,
                'issues_found': 0,
                'last_verification': None
            }

        total_verifications = len(history)
        successful_verifications = len([r for r in history if r.is_successful()])
        success_rate = successful_verifications / total_verifications if total_verifications > 0 else 0.0

        average_consistency = sum(r.data_consistency_score for r in history) / total_verifications
        total_issues = sum(len(r.issues_found) for r in history)
        last_verification = max(history, key=lambda x: x.timestamp)

        return {
            'total_verifications': total_verifications,
            'success_rate': success_rate,
            'average_consistency_score': average_consistency,
            'issues_found': total_issues,
            'last_verification': last_verification.timestamp.isoformat() if last_verification else None,
            'last_status': last_verification.status.value if last_verification else 'unknown'
        }

    async def start_periodic_verification(self, connection_id: str, interval_minutes: int = 60) -> str:
        """
        Start periodic verification for a connection.

        Args:
            connection_id: Broker connection ID
            interval_minutes: Verification interval in minutes

        Returns:
            Verification task ID
        """
        task_id = f"periodic_verify_{connection_id}_{int(datetime.now().timestamp())}"

        async def periodic_verify():
            while True:
                try:
                    logger.info(f"Running periodic verification for {connection_id}")
                    result = await self.verify_full_sync_integrity(connection_id)

                    if not result.is_successful():
                        logger.warning(f"Periodic verification found issues for {connection_id}: {result.issues_found}")

                    # Wait for next interval
                    await asyncio.sleep(interval_minutes * 60)

                except asyncio.CancelledError:
                    logger.info(f"Periodic verification cancelled for {connection_id}")
                    break
                except Exception as e:
                    logger.error(f"Periodic verification error for {connection_id}: {e}")
                    await asyncio.sleep(interval_minutes * 60)

        task = asyncio.create_task(periodic_verify())
        self._active_verifications[task_id] = task

        logger.info(f"Started periodic verification for {connection_id} (every {interval_minutes} minutes)")
        return task_id

    async def stop_periodic_verification(self, task_id: str) -> bool:
        """
        Stop periodic verification.

        Args:
            task_id: Verification task ID

        Returns:
            True if stopped successfully, False otherwise
        """
        if task_id in self._active_verifications:
            task = self._active_verifications[task_id]
            task.cancel()
            del self._active_verifications[task_id]
            logger.info(f"Stopped periodic verification: {task_id}")
            return True

        return False

    def get_active_verifications(self) -> List[str]:
        """Get list of active verification task IDs."""
        return list(self._active_verifications.keys())


# Global sync verification service instance
_sync_verification_service: Optional[SyncVerificationService] = None


def get_sync_verification_service() -> SyncVerificationService:
    """Get global sync verification service instance."""
    global _sync_verification_service
    if _sync_verification_service is None:
        _sync_verification_service = SyncVerificationService()
    return _sync_verification_service


def reset_sync_verification_service():
    """Reset global sync verification service (mainly for testing)."""
    global _sync_verification_service
    _sync_verification_service = None
