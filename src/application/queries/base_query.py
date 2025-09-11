"""
Base Query Classes for CQRS Pattern
Provides foundation for query-based read operations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class QueryResult:
    """
    Result of query execution
    Provides standardized response format for all queries
    """

    success: bool
    query_id: str
    data: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the result"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value


class Query(ABC):
    """
    Base Query class following CQRS pattern
    Queries represent read operations that don't change application state
    """

    def __init__(self, correlation_id: Optional[str] = None):
        self.query_id = str(uuid4())
        self.timestamp = datetime.now()
        self.correlation_id = correlation_id or str(uuid4())

    @property
    @abstractmethod
    def query_type(self) -> str:
        """Return the query type name"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary for serialization"""
        return {
            'query_id': self.query_id,
            'query_type': self.query_type,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'data': self._get_query_data()
        }

    @abstractmethod
    def _get_query_data(self) -> Dict[str, Any]:
        """Return query-specific data for serialization"""
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create query from dictionary (for deserialization)"""
        instance = cls.__new__(cls)
        instance.query_id = data['query_id']
        instance.timestamp = datetime.fromisoformat(data['timestamp'])
        instance.correlation_id = data['correlation_id']

        # Set query-specific attributes
        query_data = data.get('data', {})
        for key, value in query_data.items():
            setattr(instance, key, value)

        return instance


class QueryHandler(ABC):
    """
    Base Query Handler
    Handles execution of queries and returns read-only data
    """

    @abstractmethod
    async def handle(self, query: Query) -> QueryResult:
        """
        Handle query execution

        Args:
            query: The query to execute

        Returns:
            QueryResult with query outcome
        """
        pass

    @property
    @abstractmethod
    def handled_query_type(self) -> str:
        """Return the query type this handler processes"""
        pass


class QueryBus:
    """
    Query Bus for routing queries to appropriate handlers
    Implements mediator pattern for query routing
    """

    def __init__(self):
        self._handlers: Dict[str, QueryHandler] = {}

    def register_handler(self, query_type: str, handler: QueryHandler) -> None:
        """
        Register a query handler

        Args:
            query_type: Type of query the handler processes
            handler: Query handler instance
        """
        self._handlers[query_type] = handler

    async def send(self, query: Query) -> QueryResult:
        """
        Send query to appropriate handler

        Args:
            query: Query to execute

        Returns:
            QueryResult from handler execution

        Raises:
            ValueError: If no handler is registered for the query type
        """
        query_type = query.query_type

        if query_type not in self._handlers:
            raise ValueError(f"No handler registered for query type: {query_type}")

        handler = self._handlers[query_type]
        return await handler.handle(query)

    def get_registered_queries(self) -> list[str]:
        """Get list of registered query types"""
        return list(self._handlers.keys())

    def has_handler(self, query_type: str) -> bool:
        """Check if handler is registered for query type"""
        return query_type in self._handlers


# Global query bus instance
_query_bus: Optional[QueryBus] = None


def get_query_bus() -> QueryBus:
    """Get global query bus instance"""
    global _query_bus
    if _query_bus is None:
        _query_bus = QueryBus()
    return _query_bus


def reset_query_bus():
    """Reset global query bus (mainly for testing)"""
    global _query_bus
    _query_bus = None
