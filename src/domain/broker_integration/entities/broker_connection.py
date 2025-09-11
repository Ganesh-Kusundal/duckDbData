"""
Broker Integration Broker Connection Entity

This module defines the BrokerConnection entity and related value objects for the Broker Integration domain.
Broker connections manage connectivity and authentication to external broker APIs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from domain.shared.exceptions import DomainException


class BrokerType(Enum):
    """Types of brokers supported."""
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"
    ETRADE = "etrade"
    FIDELITY = "fidelity"
    SCHWAB = "schwab"
    WEBULL = "webull"
    ROBINHOOD = "robinhood"
    ALPACA = "alpaca"
    TRADIER = "tradier"
    DHAN_HQ = "dhan_hq"


class ConnectionStatus(Enum):
    """Broker connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ERROR = "error"
    SUSPENDED = "suspended"


@dataclass(frozen=True)
class BrokerConnectionId:
    """Value object for Broker Connection ID."""
    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise DomainException("BrokerConnectionId must be a non-empty string")

    @classmethod
    def generate(cls) -> 'BrokerConnectionId':
        """Generate a new unique BrokerConnectionId."""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class BrokerCredentials:
    """Value object for broker authentication credentials."""
    api_key: str
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    account_id: Optional[str] = None
    client_id: Optional[str] = None

    def __post_init__(self):
        """Validate credentials."""
        if not self.api_key:
            raise DomainException("API key is required")

        # Additional validation based on broker type
        if self.api_secret and len(self.api_secret) < 10:
            raise DomainException("API secret must be at least 10 characters")

    def is_authenticated(self) -> bool:
        """Check if credentials include authentication tokens."""
        return self.access_token is not None

    def needs_refresh(self) -> bool:
        """Check if access token needs refresh."""
        return (self.access_token is not None and
                self.refresh_token is not None and
                not self.is_token_valid())

    def is_token_valid(self) -> bool:
        """Check if current access token is valid."""
        # This would integrate with token validation logic
        # For now, assume tokens are valid if present
        return self.access_token is not None


@dataclass(frozen=True)
class BrokerEndpoint:
    """Value object for broker API endpoints."""
    base_url: str
    websocket_url: Optional[str] = None
    auth_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None

    def __post_init__(self):
        """Validate endpoints."""
        if not self.base_url:
            raise DomainException("Base URL is required")

        # Validate URL format
        if not self.base_url.startswith(('http://', 'https://', 'wss://')):
            raise DomainException("Invalid URL format")

    def get_auth_url(self) -> Optional[str]:
        """Get authentication URL."""
        if self.auth_endpoint:
            return f"{self.base_url.rstrip('/')}/{self.auth_endpoint.lstrip('/')}"
        return None

    def get_token_url(self) -> Optional[str]:
        """Get token endpoint URL."""
        if self.token_endpoint:
            return f"{self.base_url.rstrip('/')}/{self.token_endpoint.lstrip('/')}"
        return None


@dataclass
class BrokerConnection:
    """
    Broker Connection aggregate root.

    Represents a connection to an external broker API with authentication,
    session management, and connection health monitoring.
    """
    id: BrokerConnectionId
    broker_type: BrokerType
    credentials: BrokerCredentials
    endpoints: BrokerEndpoint
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    name: Optional[str] = None
    description: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int = 0
    max_retry_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate broker connection after initialization."""
        if self.description and len(self.description) > 500:
            raise DomainException("Description cannot exceed 500 characters")

        if self.name and len(self.name) > 100:
            raise DomainException("Name cannot exceed 100 characters")

    def connect(self) -> None:
        """Initiate connection to broker."""
        if self.status in [ConnectionStatus.CONNECTED, ConnectionStatus.AUTHENTICATED]:
            raise DomainException(f"Already connected with status: {self.status.value}")

        if self.error_count >= self.max_retry_attempts:
            raise DomainException("Maximum retry attempts exceeded")

        self.status = ConnectionStatus.CONNECTING
        self.updated_at = datetime.utcnow()

    def authenticate(self) -> None:
        """Authenticate with broker."""
        if self.status != ConnectionStatus.CONNECTED:
            raise DomainException(f"Cannot authenticate with status: {self.status.value}")

        if not self.credentials.is_authenticated():
            raise DomainException("Credentials not available for authentication")

        self.status = ConnectionStatus.AUTHENTICATING
        self.updated_at = datetime.utcnow()

    def mark_authenticated(self) -> None:
        """Mark connection as authenticated."""
        if self.status != ConnectionStatus.AUTHENTICATING:
            raise DomainException(f"Cannot mark as authenticated with status: {self.status.value}")

        self.status = ConnectionStatus.AUTHENTICATED
        self.last_connected_at = datetime.utcnow()
        self.error_count = 0  # Reset error count on successful auth
        self.updated_at = datetime.utcnow()

    def mark_connected(self) -> None:
        """Mark connection as connected."""
        if self.status != ConnectionStatus.CONNECTING:
            raise DomainException(f"Cannot mark as connected with status: {self.status.value}")

        self.status = ConnectionStatus.CONNECTED
        self.updated_at = datetime.utcnow()

    def disconnect(self) -> None:
        """Disconnect from broker."""
        if self.status == ConnectionStatus.DISCONNECTED:
            return  # Already disconnected

        self.status = ConnectionStatus.DISCONNECTED
        self.updated_at = datetime.utcnow()

    def mark_error(self, error_message: str) -> None:
        """Mark connection as having an error."""
        self.status = ConnectionStatus.ERROR
        self.last_error = error_message
        self.error_count += 1
        self.updated_at = datetime.utcnow()

    def suspend(self) -> None:
        """Suspend the connection."""
        self.status = ConnectionStatus.SUSPENDED
        self.updated_at = datetime.utcnow()

    def resume(self) -> None:
        """Resume a suspended connection."""
        if self.status != ConnectionStatus.SUSPENDED:
            raise DomainException(f"Cannot resume connection with status: {self.status.value}")

        self.status = ConnectionStatus.DISCONNECTED
        self.updated_at = datetime.utcnow()

    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.status in [ConnectionStatus.CONNECTED, ConnectionStatus.AUTHENTICATED]

    def is_authenticated(self) -> bool:
        """Check if connection is authenticated."""
        return self.status == ConnectionStatus.AUTHENTICATED

    def can_retry(self) -> bool:
        """Check if connection can be retried."""
        return self.error_count < self.max_retry_attempts

    def should_reconnect(self) -> bool:
        """Check if connection should be re-established."""
        return (self.status == ConnectionStatus.ERROR and
                self.can_retry() and
                self.last_error is not None)

    def get_connection_summary(self) -> Dict[str, Any]:
        """Get connection summary."""
        return {
            'id': self.id.value,
            'broker_type': self.broker_type.value,
            'status': self.status.value,
            'name': self.name,
            'last_connected': self.last_connected_at.isoformat() if self.last_connected_at else None,
            'error_count': self.error_count,
            'can_retry': self.can_retry()
        }

    def update_credentials(self, new_credentials: BrokerCredentials) -> None:
        """Update connection credentials."""
        self.credentials = new_credentials
        # Reset authentication status when credentials change
        if self.status == ConnectionStatus.AUTHENTICATED:
            self.status = ConnectionStatus.CONNECTED
        self.updated_at = datetime.utcnow()
