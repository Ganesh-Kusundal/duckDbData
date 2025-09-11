"""
Broker Integration Domain Commands for CQRS Pattern

Commands for broker integration operations including connection management,
order execution, and account operations.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from .base_command import Command


@dataclass
class EstablishBrokerConnectionCommand(Command):
    """
    Command to establish broker connection

    Initiates connection to a broker API.
    """

    connection_id: str
    broker_name: str
    connection_type: str
    credentials: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "EstablishBrokerConnection"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'broker_name': self.broker_name,
            'connection_type': self.connection_type,
            'credentials': self.credentials
        }


@dataclass
class CloseBrokerConnectionCommand(Command):
    """
    Command to close broker connection

    Terminates connection to a broker API.
    """

    connection_id: str
    reason: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "CloseBrokerConnection"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'reason': self.reason
        }


@dataclass
class SubmitBrokerOrderCommand(Command):
    """
    Command to submit order to broker

    Submits trading order through broker integration.
    """

    connection_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "DAY"
    execution_params: Optional[Dict[str, Any]] = None

    @property
    def command_type(self) -> str:
        return "SubmitBrokerOrder"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'price': str(self.price) if self.price else None,
            'stop_price': str(self.stop_price) if self.stop_price else None,
            'time_in_force': self.time_in_force,
            'execution_params': self.execution_params or {}
        }


@dataclass
class CancelBrokerOrderCommand(Command):
    """
    Command to cancel broker order

    Cancels an existing order through broker integration.
    """

    connection_id: str
    broker_order_id: str
    reason: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "CancelBrokerOrder"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'broker_order_id': self.broker_order_id,
            'reason': self.reason
        }


@dataclass
class ModifyBrokerOrderCommand(Command):
    """
    Command to modify broker order

    Modifies an existing order through broker integration.
    """

    connection_id: str
    broker_order_id: str
    modifications: Dict[str, Any]
    reason: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "ModifyBrokerOrder"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'broker_order_id': self.broker_order_id,
            'modifications': self.modifications,
            'reason': self.reason
        }


@dataclass
class SyncAccountDataCommand(Command):
    """
    Command to sync account data

    Synchronizes account information from broker.
    """

    connection_id: str
    account_id: str
    sync_types: List[str]  # e.g., ["positions", "orders", "balances"]

    @property
    def command_type(self) -> str:
        return "SyncAccountData"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'account_id': self.account_id,
            'sync_types': self.sync_types
        }


@dataclass
class ProcessBrokerExecutionCommand(Command):
    """
    Command to process broker execution

    Processes and records trade execution from broker.
    """

    connection_id: str
    execution_data: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "ProcessBrokerExecution"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'execution_data': self.execution_data
        }


@dataclass
class RequestMarketDataCommand(Command):
    """
    Command to request market data

    Requests real-time or historical market data from broker.
    """

    connection_id: str
    symbol: str
    data_type: str  # "realtime", "historical"
    timeframe: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @property
    def command_type(self) -> str:
        return "RequestMarketData"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'symbol': self.symbol,
            'data_type': self.data_type,
            'timeframe': self.timeframe,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }


@dataclass
class CreateBrokerAccountCommand(Command):
    """
    Command to create broker account

    Creates a new trading account through broker integration.
    """

    connection_id: str
    account_type: str
    account_name: str
    initial_balance: Optional[Decimal] = None

    @property
    def command_type(self) -> str:
        return "CreateBrokerAccount"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'account_type': self.account_type,
            'account_name': self.account_name,
            'initial_balance': str(self.initial_balance) if self.initial_balance else None
        }


@dataclass
class UpdateBrokerCredentialsCommand(Command):
    """
    Command to update broker credentials

    Updates authentication credentials for broker connection.
    """

    connection_id: str
    new_credentials: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "UpdateBrokerCredentials"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'new_credentials': self.new_credentials
        }


@dataclass
class TestBrokerConnectionCommand(Command):
    """
    Command to test broker connection

    Performs connectivity and authentication tests.
    """

    connection_id: str
    test_types: List[str]  # e.g., ["connectivity", "authentication", "market_data"]

    @property
    def command_type(self) -> str:
        return "TestBrokerConnection"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'test_types': self.test_types
        }


@dataclass
class ConfigureBrokerWebhooksCommand(Command):
    """
    Command to configure broker webhooks

    Sets up webhook endpoints for real-time broker notifications.
    """

    connection_id: str
    webhook_config: Dict[str, Any]

    @property
    def command_type(self) -> str:
        return "ConfigureBrokerWebhooks"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'webhook_config': self.webhook_config
        }


@dataclass
class GetBrokerCapabilitiesCommand(Command):
    """
    Command to get broker capabilities

    Retrieves supported features and limitations from broker.
    """

    connection_id: str

    @property
    def command_type(self) -> str:
        return "GetBrokerCapabilities"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id
        }


@dataclass
class ExecuteBrokerMaintenanceCommand(Command):
    """
    Command to execute broker maintenance

    Performs maintenance operations on broker connections.
    """

    connection_id: str
    maintenance_type: str
    parameters: Optional[Dict[str, Any]] = None

    @property
    def command_type(self) -> str:
        return "ExecuteBrokerMaintenance"

    def _get_command_data(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'maintenance_type': self.maintenance_type,
            'parameters': self.parameters or {}
        }
