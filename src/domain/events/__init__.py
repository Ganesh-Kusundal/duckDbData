"""Domain events for the financial data infrastructure."""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from decimal import Decimal


class DomainEvent(ABC):
    """Base class for all domain events."""

    def __init__(self, event_type: str, timestamp: Optional[datetime] = None):
        """Initialize domain event."""
        self.event_type = event_type
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class DataIngestedEvent(DomainEvent):
    """Event fired when new market data is ingested."""

    symbol: str
    timeframe: str
    records_count: int
    start_date: datetime
    end_date: datetime

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        records_count: int,
        start_date: datetime,
        end_date: datetime
    ):
        """Initialize data ingested event."""
        super().__init__('data_ingested')
        self.symbol = symbol
        self.timeframe = timeframe
        self.records_count = records_count
        self.start_date = start_date
        self.end_date = end_date

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        base = super().to_dict()
        base.update({
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'records_count': self.records_count,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
        })
        return base


@dataclass
class DataValidatedEvent(DomainEvent):
    """Event fired when data validation is completed."""

    symbol: str
    timeframe: str
    validation_results: Dict[str, Any]
    is_valid: bool

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        validation_results: Dict[str, Any],
        is_valid: bool
    ):
        """Initialize data validated event."""
        super().__init__('data_validated')
        self.symbol = symbol
        self.timeframe = timeframe
        self.validation_results = validation_results
        self.is_valid = is_valid

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        base = super().to_dict()
        base.update({
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'validation_results': self.validation_results,
            'is_valid': self.is_valid,
        })
        return base


@dataclass
class ScanTriggeredEvent(DomainEvent):
    """Event fired when a scanner execution is triggered."""

    scanner_name: str
    symbol: str
    parameters: Dict[str, Any]

    def __init__(self, scanner_name: str, symbol: str, parameters: Dict[str, Any]):
        """Initialize scan triggered event."""
        super().__init__('scan_triggered')
        self.scanner_name = scanner_name
        self.symbol = symbol
        self.parameters = parameters

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        base = super().to_dict()
        base.update({
            'scanner_name': self.scanner_name,
            'symbol': self.symbol,
            'parameters': self.parameters,
        })
        return base


@dataclass
class ScanCompletedEvent(DomainEvent):
    """Event fired when a scanner execution is completed."""

    scanner_name: str
    symbol: str
    signals_count: int
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None

    def __init__(
        self,
        scanner_name: str,
        symbol: str,
        signals_count: int,
        execution_time_ms: float,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Initialize scan completed event."""
        super().__init__('scan_completed')
        self.scanner_name = scanner_name
        self.symbol = symbol
        self.signals_count = signals_count
        self.execution_time_ms = execution_time_ms
        self.success = success
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        base = super().to_dict()
        base.update({
            'scanner_name': self.scanner_name,
            'symbol': self.symbol,
            'signals_count': self.signals_count,
            'execution_time_ms': self.execution_time_ms,
            'success': self.success,
            'error_message': self.error_message,
        })
        return base


@dataclass
class SignalGeneratedEvent(DomainEvent):
    """Event fired when a trading signal is generated."""

    symbol: str
    signal_type: str
    strength: str
    price: Decimal
    confidence: float
    scanner_name: str
    metadata: Dict[str, Any]

    def __init__(
        self,
        symbol: str,
        signal_type: str,
        strength: str,
        price: Decimal,
        confidence: float,
        scanner_name: str,
        metadata: Dict[str, Any]
    ):
        """Initialize signal generated event."""
        super().__init__('signal_generated')
        self.symbol = symbol
        self.signal_type = signal_type
        self.strength = strength
        self.price = price
        self.confidence = confidence
        self.scanner_name = scanner_name
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        base = super().to_dict()
        base.update({
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'strength': self.strength,
            'price': str(self.price),
            'confidence': self.confidence,
            'scanner_name': self.scanner_name,
            'metadata': self.metadata,
        })
        return base


@dataclass
class OrderPlacedEvent(DomainEvent):
    """Event fired when a broker order is placed."""

    symbol: str
    order_type: str
    quantity: int
    price: Decimal
    order_id: str
    broker_name: str

    def __init__(
        self,
        symbol: str,
        order_type: str,
        quantity: int,
        price: Decimal,
        order_id: str,
        broker_name: str
    ):
        """Initialize order placed event."""
        super().__init__('order_placed')
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.order_id = order_id
        self.broker_name = broker_name

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        base = super().to_dict()
        base.update({
            'symbol': self.symbol,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': str(self.price),
            'order_id': self.order_id,
            'broker_name': self.broker_name,
        })
        return base


@dataclass
class SystemHealthEvent(DomainEvent):
    """Event fired for system health monitoring."""

    component: str
    status: str
    metrics: Dict[str, Any]
    message: Optional[str] = None

    def __init__(
        self,
        component: str,
        status: str,
        metrics: Dict[str, Any],
        message: Optional[str] = None
    ):
        """Initialize system health event."""
        super().__init__('system_health')
        self.component = component
        self.status = status
        self.metrics = metrics
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        base = super().to_dict()
        base.update({
            'component': self.component,
            'status': self.status,
            'metrics': self.metrics,
            'message': self.message,
        })
        return base
