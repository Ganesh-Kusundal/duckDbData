"""
Broker Integration Broker Connection Service

This module defines the domain service for managing broker connections,
handling authentication, connection lifecycle, and broker communication.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import logging

from domain.broker_integration.entities.broker_connection import (
    BrokerConnection, ConnectionStatus, BrokerCredentials
)
from domain.broker_integration.repositories.broker_connection_repository import BrokerConnectionRepository
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class BrokerConnectionService(ABC):
    """Abstract domain service for broker connection management."""

    @abstractmethod
    async def establish_connection(self, connection_id: str) -> bool:
        """Establish connection to broker."""
        pass

    @abstractmethod
    async def close_connection(self, connection_id: str) -> None:
        """Close broker connection."""
        pass

    @abstractmethod
    async def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test broker connection and return diagnostics."""
        pass

    @abstractmethod
    async def refresh_connection(self, connection_id: str) -> None:
        """Refresh broker connection (re-authenticate if needed)."""
        pass

    @abstractmethod
    async def get_connection_status(self, connection_id: str) -> Dict[str, Any]:
        """Get detailed connection status."""
        pass

    @abstractmethod
    async def handle_connection_error(self, connection_id: str, error: Exception) -> None:
        """Handle connection errors and attempt recovery."""
        pass


class BrokerAuthenticationService(ABC):
    """Abstract domain service for broker authentication."""

    @abstractmethod
    async def authenticate(self, connection_id: str, credentials: BrokerCredentials) -> Dict[str, Any]:
        """Authenticate with broker using credentials."""
        pass

    @abstractmethod
    async def refresh_token(self, connection_id: str) -> Optional[str]:
        """Refresh authentication token."""
        pass

    @abstractmethod
    async def validate_session(self, connection_id: str) -> bool:
        """Validate current session is still active."""
        pass

    @abstractmethod
    async def logout(self, connection_id: str) -> None:
        """Logout from broker session."""
        pass


class BrokerConnectionManager(BrokerConnectionService, BrokerAuthenticationService):
    """Domain service implementation for broker connection management."""

    def __init__(self, connection_repository: BrokerConnectionRepository):
        self._repository = connection_repository
        self._active_connections: Dict[str, Dict[str, Any]] = {}
        self._connection_tasks: Dict[str, asyncio.Task] = {}

    async def establish_connection(self, connection_id: str) -> bool:
        """Establish connection to broker."""
        connection = self._repository.find_by_id(connection_id)
        if not connection:
            raise DomainException(f"Connection not found: {connection_id}")

        try:
            # Test connection first
            test_result = await self.test_connection(connection_id)
            if not test_result.get('success', False):
                logger.error(f"Connection test failed for {connection_id}: {test_result.get('error')}")
                return False

            # Authenticate if needed
            if connection.requires_authentication():
                auth_result = await self.authenticate(connection_id, connection.credentials)
                if not auth_result.get('success', False):
                    logger.error(f"Authentication failed for {connection_id}: {auth_result.get('error')}")
                    return False

            # Update connection status
            self._repository.update_connection_status(connection_id, ConnectionStatus.CONNECTED)
            self._repository.update_last_activity(connection_id, datetime.utcnow())

            # Store active connection info
            self._active_connections[connection_id] = {
                'connected_at': datetime.utcnow(),
                'last_activity': datetime.utcnow(),
                'session_info': test_result.get('session_info', {})
            }

            # Start connection monitoring task
            await self._start_connection_monitor(connection_id)

            logger.info(f"Successfully established connection for {connection_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to establish connection for {connection_id}: {str(e)}")
            await self.handle_connection_error(connection_id, e)
            return False

    async def close_connection(self, connection_id: str) -> None:
        """Close broker connection."""
        connection = self._repository.find_by_id(connection_id)
        if not connection:
            raise DomainException(f"Connection not found: {connection_id}")

        try:
            # Logout if authenticated
            if connection.is_authenticated():
                await self.logout(connection_id)

            # Stop monitoring task
            await self._stop_connection_monitor(connection_id)

            # Update connection status
            self._repository.update_connection_status(connection_id, ConnectionStatus.DISCONNECTED)

            # Remove from active connections
            if connection_id in self._active_connections:
                del self._active_connections[connection_id]

            logger.info(f"Successfully closed connection for {connection_id}")

        except Exception as e:
            logger.error(f"Error closing connection for {connection_id}: {str(e)}")
            # Still mark as disconnected even if logout fails
            self._repository.update_connection_status(connection_id, ConnectionStatus.DISCONNECTED)

    async def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test broker connection and return diagnostics."""
        connection = self._repository.find_by_id(connection_id)
        if not connection:
            return {
                'success': False,
                'error': f"Connection not found: {connection_id}"
            }

        try:
            # This would typically involve actual network calls to broker APIs
            # For now, we'll simulate connection testing
            await asyncio.sleep(0.1)  # Simulate network latency

            # Mock successful connection test
            return {
                'success': True,
                'latency_ms': 45.2,
                'session_info': {
                    'session_id': f"session_{connection_id}",
                    'api_version': 'v1',
                    'server_time': datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def refresh_connection(self, connection_id: str) -> None:
        """Refresh broker connection (re-authenticate if needed)."""
        connection = self._repository.find_by_id(connection_id)
        if not connection:
            raise DomainException(f"Connection not found: {connection_id}")

        try:
            # Refresh authentication token if needed
            if connection.is_authenticated():
                new_token = await self.refresh_token(connection_id)
                if new_token:
                    logger.info(f"Refreshed authentication token for {connection_id}")

            # Test connection after refresh
            test_result = await self.test_connection(connection_id)
            if test_result.get('success', False):
                self._repository.update_last_activity(connection_id, datetime.utcnow())
                logger.info(f"Successfully refreshed connection for {connection_id}")
            else:
                logger.warning(f"Connection test failed after refresh for {connection_id}")
                await self.handle_connection_error(connection_id, Exception("Connection test failed after refresh"))

        except Exception as e:
            logger.error(f"Failed to refresh connection for {connection_id}: {str(e)}")
            await self.handle_connection_error(connection_id, e)

    async def get_connection_status(self, connection_id: str) -> Dict[str, Any]:
        """Get detailed connection status."""
        connection = self._repository.find_by_id(connection_id)
        if not connection:
            raise DomainException(f"Connection not found: {connection_id}")

        status_info = {
            'connection_id': connection.connection_id,
            'broker_name': connection.broker_name,
            'status': connection.status.value,
            'is_active': connection.is_active(),
            'is_authenticated': connection.is_authenticated(),
            'last_activity': connection.last_activity,
            'created_at': connection.created_at,
            'updated_at': connection.updated_at
        }

        # Add active connection info if available
        if connection_id in self._active_connections:
            active_info = self._active_connections[connection_id]
            status_info.update({
                'connected_at': active_info['connected_at'],
                'session_info': active_info['session_info'],
                'uptime_seconds': (datetime.utcnow() - active_info['connected_at']).total_seconds()
            })

        return status_info

    async def handle_connection_error(self, connection_id: str, error: Exception) -> None:
        """Handle connection errors and attempt recovery."""
        logger.error(f"Connection error for {connection_id}: {str(error)}")

        # Update connection status to error state
        try:
            self._repository.update_connection_status(connection_id, ConnectionStatus.ERROR)
        except Exception as e:
            logger.error(f"Failed to update connection status: {str(e)}")

        # Stop monitoring task if running
        await self._stop_connection_monitor(connection_id)

        # Remove from active connections
        if connection_id in self._active_connections:
            del self._active_connections[connection_id]

        # TODO: Implement retry logic with exponential backoff
        # For now, we'll just log the error

    async def authenticate(self, connection_id: str, credentials: BrokerCredentials) -> Dict[str, Any]:
        """Authenticate with broker using credentials."""
        try:
            # This would typically involve actual authentication calls to broker APIs
            # For now, we'll simulate authentication
            await asyncio.sleep(0.2)  # Simulate authentication delay

            # Mock successful authentication
            return {
                'success': True,
                'token': f"auth_token_{connection_id}",
                'expires_at': (datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat(),
                'permissions': ['read', 'write', 'trade']
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def refresh_token(self, connection_id: str) -> Optional[str]:
        """Refresh authentication token."""
        try:
            # This would typically involve token refresh calls to broker APIs
            # For now, we'll simulate token refresh
            await asyncio.sleep(0.1)  # Simulate token refresh delay

            return f"refreshed_token_{connection_id}"

        except Exception as e:
            logger.error(f"Failed to refresh token for {connection_id}: {str(e)}")
            return None

    async def validate_session(self, connection_id: str) -> bool:
        """Validate current session is still active."""
        try:
            # This would typically involve session validation calls to broker APIs
            # For now, we'll simulate session validation
            await asyncio.sleep(0.05)  # Simulate validation delay

            # Check if connection is in active connections
            return connection_id in self._active_connections

        except Exception as e:
            logger.error(f"Failed to validate session for {connection_id}: {str(e)}")
            return False

    async def logout(self, connection_id: str) -> None:
        """Logout from broker session."""
        try:
            # This would typically involve logout calls to broker APIs
            # For now, we'll simulate logout
            await asyncio.sleep(0.05)  # Simulate logout delay

            logger.info(f"Successfully logged out from {connection_id}")

        except Exception as e:
            logger.error(f"Failed to logout from {connection_id}: {str(e)}")

    async def _start_connection_monitor(self, connection_id: str) -> None:
        """Start connection monitoring task."""
        if connection_id in self._connection_tasks:
            await self._stop_connection_monitor(connection_id)

        task = asyncio.create_task(self._monitor_connection(connection_id))
        self._connection_tasks[connection_id] = task

    async def _stop_connection_monitor(self, connection_id: str) -> None:
        """Stop connection monitoring task."""
        if connection_id in self._connection_tasks:
            task = self._connection_tasks[connection_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._connection_tasks[connection_id]

    async def _monitor_connection(self, connection_id: str) -> None:
        """Monitor connection health."""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute

                # Validate session
                if not await self.validate_session(connection_id):
                    logger.warning(f"Session validation failed for {connection_id}")
                    await self.handle_connection_error(connection_id, Exception("Session validation failed"))
                    break

                # Update last activity
                self._repository.update_last_activity(connection_id, datetime.utcnow())

        except asyncio.CancelledError:
            logger.info(f"Connection monitoring cancelled for {connection_id}")
            raise
        except Exception as e:
            logger.error(f"Error in connection monitoring for {connection_id}: {str(e)}")
            await self.handle_connection_error(connection_id, e)
