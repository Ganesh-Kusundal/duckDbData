"""
Broker Integration Broker Connection Repository

This module defines the repository interface and implementation for
managing broker connections in the Broker Integration domain.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from domain.broker_integration.entities.broker_connection import BrokerConnection, ConnectionStatus
from domain.shared.exceptions import DomainException


class BrokerConnectionRepository(ABC):
    """Abstract repository for broker connection management."""

    @abstractmethod
    def save(self, connection: BrokerConnection) -> None:
        """Save a broker connection."""
        pass

    @abstractmethod
    def find_by_id(self, connection_id: str) -> Optional[BrokerConnection]:
        """Find broker connection by ID."""
        pass

    @abstractmethod
    def find_by_broker_name(self, broker_name: str) -> List[BrokerConnection]:
        """Find broker connections by broker name."""
        pass

    @abstractmethod
    def find_by_status(self, status: ConnectionStatus) -> List[BrokerConnection]:
        """Find broker connections by status."""
        pass

    @abstractmethod
    def find_active_connections(self) -> List[BrokerConnection]:
        """Find all active broker connections."""
        pass

    @abstractmethod
    def find_connections_by_user(self, user_id: str) -> List[BrokerConnection]:
        """Find broker connections by user ID."""
        pass

    @abstractmethod
    def delete(self, connection_id: str) -> None:
        """Delete a broker connection."""
        pass

    @abstractmethod
    def update_connection_status(self, connection_id: str, status: ConnectionStatus) -> None:
        """Update broker connection status."""
        pass

    @abstractmethod
    def update_last_activity(self, connection_id: str, activity_time: datetime) -> None:
        """Update last activity timestamp for a connection."""
        pass

    @abstractmethod
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        pass


class InMemoryBrokerConnectionRepository(BrokerConnectionRepository):
    """In-memory implementation of broker connection repository."""

    def __init__(self):
        self._connections: Dict[str, BrokerConnection] = {}

    def save(self, connection: BrokerConnection) -> None:
        """Save a broker connection."""
        self._connections[connection.connection_id] = connection

    def find_by_id(self, connection_id: str) -> Optional[BrokerConnection]:
        """Find broker connection by ID."""
        return self._connections.get(connection_id)

    def find_by_broker_name(self, broker_name: str) -> List[BrokerConnection]:
        """Find broker connections by broker name."""
        return [
            conn for conn in self._connections.values()
            if conn.broker_name == broker_name
        ]

    def find_by_status(self, status: ConnectionStatus) -> List[BrokerConnection]:
        """Find broker connections by status."""
        return [
            conn for conn in self._connections.values()
            if conn.status == status
        ]

    def find_active_connections(self) -> List[BrokerConnection]:
        """Find all active broker connections."""
        return [
            conn for conn in self._connections.values()
            if conn.is_active()
        ]

    def find_connections_by_user(self, user_id: str) -> List[BrokerConnection]:
        """Find broker connections by user ID."""
        return [
            conn for conn in self._connections.values()
            if conn.user_id == user_id
        ]

    def delete(self, connection_id: str) -> None:
        """Delete a broker connection."""
        if connection_id in self._connections:
            del self._connections[connection_id]

    def update_connection_status(self, connection_id: str, status: ConnectionStatus) -> None:
        """Update broker connection status."""
        if connection_id in self._connections:
            connection = self._connections[connection_id]
            updated_connection = connection.update_status(status)
            self._connections[connection_id] = updated_connection

    def update_last_activity(self, connection_id: str, activity_time: datetime) -> None:
        """Update last activity timestamp for a connection."""
        if connection_id in self._connections:
            connection = self._connections[connection_id]
            updated_connection = connection.update_last_activity(activity_time)
            self._connections[connection_id] = updated_connection

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        total_connections = len(self._connections)
        active_connections = len(self.find_active_connections())
        connections_by_status = {}

        for status in ConnectionStatus:
            connections_by_status[status.value] = len(self.find_by_status(status))

        connections_by_broker = {}
        for conn in self._connections.values():
            broker_name = conn.broker_name
            connections_by_broker[broker_name] = connections_by_broker.get(broker_name, 0) + 1

        return {
            'total_connections': total_connections,
            'active_connections': active_connections,
            'connections_by_status': connections_by_status,
            'connections_by_broker': connections_by_broker,
            'inactive_connections': total_connections - active_connections
        }


class BrokerAccountRepository(ABC):
    """Abstract repository for broker account management."""

    @abstractmethod
    def save(self, account: 'BrokerAccount') -> None:
        """Save a broker account."""
        pass

    @abstractmethod
    def find_by_id(self, account_id: str) -> Optional['BrokerAccount']:
        """Find broker account by ID."""
        pass

    @abstractmethod
    def find_by_broker_connection(self, connection_id: str) -> List['BrokerAccount']:
        """Find broker accounts by broker connection ID."""
        pass

    @abstractmethod
    def find_by_account_number(self, account_number: str) -> Optional['BrokerAccount']:
        """Find broker account by account number."""
        pass

    @abstractmethod
    def find_accounts_by_user(self, user_id: str) -> List['BrokerAccount']:
        """Find broker accounts by user ID."""
        pass

    @abstractmethod
    def delete(self, account_id: str) -> None:
        """Delete a broker account."""
        pass

    @abstractmethod
    def update_account_balance(self, account_id: str, new_balance: float) -> None:
        """Update account balance."""
        pass

    @abstractmethod
    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        """Get account summary information."""
        pass


class InMemoryBrokerAccountRepository(BrokerAccountRepository):
    """In-memory implementation of broker account repository."""

    def __init__(self):
        self._accounts: Dict[str, 'BrokerAccount'] = {}

    def save(self, account: 'BrokerAccount') -> None:
        """Save a broker account."""
        self._accounts[account.account_id] = account

    def find_by_id(self, account_id: str) -> Optional['BrokerAccount']:
        """Find broker account by ID."""
        return self._accounts.get(account_id)

    def find_by_broker_connection(self, connection_id: str) -> List['BrokerAccount']:
        """Find broker accounts by broker connection ID."""
        return [
            account for account in self._accounts.values()
            if account.connection_id == connection_id
        ]

    def find_by_account_number(self, account_number: str) -> Optional['BrokerAccount']:
        """Find broker account by account number."""
        return next(
            (account for account in self._accounts.values()
             if account.account_number == account_number),
            None
        )

    def find_accounts_by_user(self, user_id: str) -> List['BrokerAccount']:
        """Find broker accounts by user ID."""
        return [
            account for account in self._accounts.values()
            if account.user_id == user_id
        ]

    def delete(self, account_id: str) -> None:
        """Delete a broker account."""
        if account_id in self._accounts:
            del self._accounts[account_id]

    def update_account_balance(self, account_id: str, new_balance: float) -> None:
        """Update account balance."""
        if account_id in self._accounts:
            account = self._accounts[account_id]
            updated_account = account.update_balance(new_balance)
            self._accounts[account_id] = updated_account

    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        """Get account summary information."""
        account = self.find_by_id(account_id)
        if not account:
            raise DomainException(f"Account not found: {account_id}")

        return {
            'account_id': account.account_id,
            'account_number': account.account_number,
            'account_type': account.account_type,
            'balance': account.balance,
            'currency': account.currency,
            'margin_available': account.margin_available,
            'buying_power': account.buying_power,
            'is_margin_account': account.is_margin_account,
            'is_active': account.is_active,
            'created_at': account.created_at,
            'updated_at': account.updated_at
        }
