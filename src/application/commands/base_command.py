"""
Base Command Classes for CQRS Pattern
Provides foundation for command-based write operations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

try:
    from infrastructure.messaging.event_types import DomainEvent
except ImportError:
    # Fallback for when infrastructure dependencies are not available
    DomainEvent = None


@dataclass
class CommandResult:
    """
    Result of command execution
    Provides standardized response format for all commands
    """

    success: bool
    command_id: str
    data: Optional[Any] = None
    events: Optional[list[DomainEvent]] = None
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.events is None:
            self.events = []

    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the result"""
        if self.events is None:
            self.events = []
        self.events.append(event)

    def add_events(self, events: list[DomainEvent]) -> None:
        """Add multiple domain events to the result"""
        if self.events is None:
            self.events = []
        self.events.extend(events)


class Command(ABC):
    """
    Base Command class following CQRS pattern
    Commands represent write operations that change application state
    """

    def __init__(self, correlation_id: Optional[str] = None):
        self.command_id = str(uuid4())
        self.timestamp = datetime.now()
        self.correlation_id = correlation_id or str(uuid4())

    @property
    @abstractmethod
    def command_type(self) -> str:
        """Return the command type name"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary for serialization"""
        return {
            'command_id': self.command_id,
            'command_type': self.command_type,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'data': self._get_command_data()
        }

    @abstractmethod
    def _get_command_data(self) -> Dict[str, Any]:
        """Return command-specific data for serialization"""
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create command from dictionary (for deserialization)"""
        instance = cls.__new__(cls)
        instance.command_id = data['command_id']
        instance.timestamp = datetime.fromisoformat(data['timestamp'])
        instance.correlation_id = data['correlation_id']

        # Set command-specific attributes
        command_data = data.get('data', {})
        for key, value in command_data.items():
            setattr(instance, key, value)

        return instance


class CommandHandler(ABC):
    """
    Base Command Handler
    Handles execution of commands and orchestrates domain operations
    """

    @abstractmethod
    async def handle(self, command: Command) -> CommandResult:
        """
        Handle command execution

        Args:
            command: The command to execute

        Returns:
            CommandResult with execution outcome
        """
        pass

    @property
    @abstractmethod
    def handled_command_type(self) -> str:
        """Return the command type this handler processes"""
        pass


class CommandBus:
    """
    Command Bus for routing commands to appropriate handlers
    Implements mediator pattern for command routing
    """

    def __init__(self):
        self._handlers: Dict[str, CommandHandler] = {}

    def register_handler(self, command_type: str, handler: CommandHandler) -> None:
        """
        Register a command handler

        Args:
            command_type: Type of command the handler processes
            handler: Command handler instance
        """
        self._handlers[command_type] = handler

    async def send(self, command: Command) -> CommandResult:
        """
        Send command to appropriate handler

        Args:
            command: Command to execute

        Returns:
            CommandResult from handler execution

        Raises:
            ValueError: If no handler is registered for the command type
        """
        command_type = command.command_type

        if command_type not in self._handlers:
            raise ValueError(f"No handler registered for command type: {command_type}")

        handler = self._handlers[command_type]
        return await handler.handle(command)

    def get_registered_commands(self) -> list[str]:
        """Get list of registered command types"""
        return list(self._handlers.keys())

    def has_handler(self, command_type: str) -> bool:
        """Check if handler is registered for command type"""
        return command_type in self._handlers


# Global command bus instance
_command_bus: Optional[CommandBus] = None


def get_command_bus() -> CommandBus:
    """Get global command bus instance"""
    global _command_bus
    if _command_bus is None:
        _command_bus = CommandBus()
    return _command_bus


def reset_command_bus():
    """Reset global command bus (mainly for testing)"""
    global _command_bus
    _command_bus = None
