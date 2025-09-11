"""
Event Types for Domain-Driven Design
Defines domain events and integration events for cross-context communication
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod


@dataclass
class EventMetadata:
    """Metadata for all events"""
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    event_version: str = "1.0"
    timestamp: datetime = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    source_context: Optional[str] = None
    user_id: Optional[str] = None

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.correlation_id is None:
            self.correlation_id = self.event_id


class DomainEvent(ABC):
    """
    Base class for domain events
    Domain events represent something that happened in the domain
    """

    def __init__(self, aggregate_id: str, correlation_id: Optional[str] = None):
        self.metadata = EventMetadata(
            event_id=str(uuid.uuid4()),
            event_type=self.__class__.__name__,
            aggregate_id=aggregate_id,
            aggregate_type=self._get_aggregate_type(),
            timestamp=datetime.now(),
            correlation_id=correlation_id or str(uuid.uuid4()),
            source_context=self._get_source_context()
        )

    @abstractmethod
    def _get_aggregate_type(self) -> str:
        """Return the aggregate type this event belongs to"""
        pass

    @abstractmethod
    def _get_source_context(self) -> str:
        """Return the bounded context that published this event"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'metadata': asdict(self.metadata),
            'data': asdict(self)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create event from dictionary (for deserialization)"""
        metadata = EventMetadata(**data['metadata'])
        event_data = data['data']

        # Remove metadata fields from event data
        event_data.pop('metadata', None)

        instance = cls.__new__(cls)
        instance.metadata = metadata

        # Set event attributes
        for key, value in event_data.items():
            setattr(instance, key, value)

        return instance


# Market Data Context Events
@dataclass
class MarketDataReceived(DomainEvent):
    """Event fired when new market data is received"""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    exchange: str = "NSE"

    def _get_aggregate_type(self) -> str:
        return "MarketDataFeed"

    def _get_source_context(self) -> str:
        return "market_data"


@dataclass
class MarketDataUpdated(DomainEvent):
    """Event fired when market data is updated"""
    symbol: str
    old_price: float
    new_price: float
    price_change: float
    volume_change: int
    timestamp: datetime

    def _get_aggregate_type(self) -> str:
        return "MarketDataFeed"

    def _get_source_context(self) -> str:
        return "market_data"


# Trading Context Events
@dataclass
class OrderPlaced(DomainEvent):
    """Event fired when an order is placed"""
    order_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: int
    order_type: str
    price: Optional[float] = None
    portfolio_id: str = ""

    def _get_aggregate_type(self) -> str:
        return "Order"

    def _get_source_context(self) -> str:
        return "trading"


@dataclass
class OrderFilled(DomainEvent):
    """Event fired when an order is filled"""
    order_id: str
    symbol: str
    filled_quantity: int
    average_price: float
    total_value: float
    timestamp: datetime

    def _get_aggregate_type(self) -> str:
        return "Order"

    def _get_source_context(self) -> str:
        return "trading"


@dataclass
class PositionUpdated(DomainEvent):
    """Event fired when position is updated"""
    portfolio_id: str
    symbol: str
    quantity_change: int
    price: float
    unrealized_pnl: float
    timestamp: datetime

    def _get_aggregate_type(self) -> str:
        return "Portfolio"

    def _get_source_context(self) -> str:
        return "trading"


# Analytics Context Events
@dataclass
class IndicatorCalculated(DomainEvent):
    """Event fired when technical indicator is calculated"""
    symbol: str
    indicator_name: str
    indicator_value: float
    timestamp: datetime
    parameters: Dict[str, Any] = None

    def _get_aggregate_type(self) -> str:
        return "Indicator"

    def _get_source_context(self) -> str:
        return "analytics"


@dataclass
class SignalGenerated(DomainEvent):
    """Event fired when trading signal is generated"""
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    strength: float  # Signal strength (0-1)
    indicators: Dict[str, Any]  # Supporting indicator values
    timestamp: datetime

    def _get_aggregate_type(self) -> str:
        return "Signal"

    def _get_source_context(self) -> str:
        return "analytics"


# Scanning Context Events
@dataclass
class ScanCompleted(DomainEvent):
    """Event fired when market scan is completed"""
    scan_id: str
    criteria: Dict[str, Any]
    results_count: int
    execution_time: float
    timestamp: datetime

    def _get_aggregate_type(self) -> str:
        return "Scan"

    def _get_source_context(self) -> str:
        return "scanning"


@dataclass
class OpportunityDetected(DomainEvent):
    """Event fired when trading opportunity is detected"""
    symbol: str
    opportunity_type: str
    confidence_score: float
    criteria_matched: Dict[str, Any]
    timestamp: datetime

    def _get_aggregate_type(self) -> str:
        return "Opportunity"

    def _get_source_context(self) -> str:
        return "scanning"


# Risk Management Context Events
@dataclass
class RiskThresholdExceeded(DomainEvent):
    """Event fired when risk threshold is exceeded"""
    portfolio_id: str
    risk_type: str  # POSITION_SIZE, DRAWDOWN, VAR, etc.
    current_value: float
    threshold_value: float
    breach_percentage: float
    timestamp: datetime

    def _get_aggregate_type(self) -> str:
        return "RiskLimit"

    def _get_source_context(self) -> str:
        return "risk_management"


@dataclass
class PositionRiskAssessed(DomainEvent):
    """Event fired when position risk is assessed"""
    portfolio_id: str
    symbol: str
    risk_score: float
    risk_factors: Dict[str, float]
    recommended_action: str
    timestamp: datetime

    def _get_aggregate_type(self) -> str:
        return "Position"

    def _get_source_context(self) -> str:
        return "risk_management"


class IntegrationEvent(DomainEvent):
    """
    Base class for integration events
    Integration events are used for cross-bounded context communication
    """

    def _get_aggregate_type(self) -> str:
        return "Integration"

    def _get_source_context(self) -> str:
        return "integration"


@dataclass
class SystemStatusChanged(IntegrationEvent):
    """Event fired when system status changes"""
    component: str
    status: str  # STARTING, RUNNING, STOPPING, ERROR
    message: Optional[str] = None
    timestamp: datetime = None

    def _get_source_context(self) -> str:
        return "system"


@dataclass
class DataSynchronizationCompleted(IntegrationEvent):
    """Event fired when data synchronization is completed"""
    sync_type: str
    records_processed: int
    duration: float
    success: bool
    timestamp: datetime

    def _get_source_context(self) -> str:
        return "data_sync"


@dataclass
class ConfigurationChanged(IntegrationEvent):
    """Event fired when configuration is changed"""
    component: str
    config_key: str
    old_value: Any
    new_value: Any
    timestamp: datetime

    def _get_source_context(self) -> str:
        return "configuration"


# Event Registry for deserialization
EVENT_REGISTRY = {
    # Domain Events
    'MarketDataReceived': MarketDataReceived,
    'MarketDataUpdated': MarketDataUpdated,
    'OrderPlaced': OrderPlaced,
    'OrderFilled': OrderFilled,
    'PositionUpdated': PositionUpdated,
    'IndicatorCalculated': IndicatorCalculated,
    'SignalGenerated': SignalGenerated,
    'ScanCompleted': ScanCompleted,
    'OpportunityDetected': OpportunityDetected,
    'RiskThresholdExceeded': RiskThresholdExceeded,
    'PositionRiskAssessed': PositionRiskAssessed,

    # Integration Events
    'SystemStatusChanged': SystemStatusChanged,
    'DataSynchronizationCompleted': DataSynchronizationCompleted,
    'ConfigurationChanged': ConfigurationChanged,
}


def deserialize_event(event_data: Dict[str, Any]) -> Optional[DomainEvent]:
    """
    Deserialize event from dictionary

    Args:
        event_data: Dictionary containing event data

    Returns:
        Deserialized event or None if unknown type
    """
    event_type = event_data.get('metadata', {}).get('event_type')
    if not event_type or event_type not in EVENT_REGISTRY:
        return None

    event_class = EVENT_REGISTRY[event_type]
    return event_class.from_dict(event_data)
