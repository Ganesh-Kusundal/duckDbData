"""
Event Store Implementation for Event Sourcing

Provides persistent storage and retrieval of domain events,
enabling event sourcing patterns and audit trails.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from .event_types import DomainEvent, deserialize_event
from ..database.duckdb_adapter import DuckDBAdapter

logger = logging.getLogger(__name__)


class EventStore(ABC):
    """
    Abstract event store for storing and retrieving domain events.

    Provides the foundation for event sourcing patterns.
    """

    @abstractmethod
    async def save_event(self, event: DomainEvent) -> bool:
        """Save a single event to the store."""
        pass

    @abstractmethod
    async def save_events(self, events: List[DomainEvent]) -> bool:
        """Save multiple events to the store."""
        pass

    @abstractmethod
    async def get_events_for_aggregate(self, aggregate_id: str, aggregate_type: str) -> List[DomainEvent]:
        """Get all events for a specific aggregate."""
        pass

    @abstractmethod
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[DomainEvent]:
        """Get events of a specific type."""
        pass

    @abstractmethod
    async def get_events_by_time_range(self, start_time: datetime, end_time: datetime) -> List[DomainEvent]:
        """Get events within a time range."""
        pass

    @abstractmethod
    async def get_event_count(self, aggregate_id: Optional[str] = None) -> int:
        """Get total event count, optionally filtered by aggregate."""
        pass


class DuckDBEventStore(EventStore):
    """
    DuckDB-based event store implementation.

    Stores events in a DuckDB database for persistence and querying.
    """

    def __init__(self, db_path: str = "data/events.duckdb"):
        self.db_path = db_path
        self.db = DuckDBAdapter(db_path)
        self._initialized = False

    async def initialize(self):
        """Initialize the event store database schema."""
        if self._initialized:
            return

        schema_sql = """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            aggregate_id TEXT NOT NULL,
            aggregate_type TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_version TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            correlation_id TEXT,
            causation_id TEXT,
            source_context TEXT,
            user_id TEXT,
            event_data TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_events_aggregate ON events(aggregate_id, aggregate_type);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_correlation ON events(correlation_id);
        """

        try:
            await self.db.execute_query(schema_sql)
            self._initialized = True
            logger.info("Event store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize event store: {e}")
            raise

    async def save_event(self, event: DomainEvent) -> bool:
        """Save a single event to the store."""
        await self.initialize()

        event_data = event.to_dict()
        metadata = event_data['metadata']
        payload = event_data['data']

        # Remove metadata from payload to avoid duplication
        payload.pop('metadata', None)

        insert_sql = """
        INSERT INTO events (
            event_id, aggregate_id, aggregate_type, event_type, event_version,
            timestamp, correlation_id, causation_id, source_context, user_id, event_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            metadata['event_id'],
            metadata['aggregate_id'],
            metadata['aggregate_type'],
            metadata['event_type'],
            metadata['event_version'],
            metadata['timestamp'],
            metadata.get('correlation_id'),
            metadata.get('causation_id'),
            metadata.get('source_context'),
            metadata.get('user_id'),
            json.dumps(payload)
        )

        try:
            await self.db.execute_query(insert_sql, params)
            logger.debug(f"Event saved: {metadata['event_type']} for aggregate {metadata['aggregate_id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to save event {metadata['event_id']}: {e}")
            return False

    async def save_events(self, events: List[DomainEvent]) -> bool:
        """Save multiple events to the store."""
        await self.initialize()

        if not events:
            return True

        # Use batch insert for better performance
        values_list = []
        for event in events:
            event_data = event.to_dict()
            metadata = event_data['metadata']
            payload = event_data['data']
            payload.pop('metadata', None)

            values_list.append((
                metadata['event_id'],
                metadata['aggregate_id'],
                metadata['aggregate_type'],
                metadata['event_type'],
                metadata['event_version'],
                metadata['timestamp'],
                metadata.get('correlation_id'),
                metadata.get('causation_id'),
                metadata.get('source_context'),
                metadata.get('user_id'),
                json.dumps(payload)
            ))

        placeholders = ', '.join(['?' for _ in values_list[0]])
        insert_sql = f"""
        INSERT INTO events (
            event_id, aggregate_id, aggregate_type, event_type, event_version,
            timestamp, correlation_id, causation_id, source_context, user_id, event_data
        ) VALUES {', '.join([f'({placeholders})' for _ in values_list])}
        """

        # Flatten the parameter list
        params = [param for values in values_list for param in values]

        try:
            await self.db.execute_query(insert_sql, params)
            logger.info(f"Batch saved {len(events)} events")
            return True
        except Exception as e:
            logger.error(f"Failed to batch save events: {e}")
            return False

    async def get_events_for_aggregate(self, aggregate_id: str, aggregate_type: str) -> List[DomainEvent]:
        """Get all events for a specific aggregate."""
        await self.initialize()

        query = """
        SELECT * FROM events
        WHERE aggregate_id = ? AND aggregate_type = ?
        ORDER BY timestamp ASC
        """

        try:
            result = await self.db.execute_query(query, (aggregate_id, aggregate_type))
            return self._deserialize_events(result)
        except Exception as e:
            logger.error(f"Failed to get events for aggregate {aggregate_id}: {e}")
            return []

    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[DomainEvent]:
        """Get events of a specific type."""
        await self.initialize()

        query = """
        SELECT * FROM events
        WHERE event_type = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """

        try:
            result = await self.db.execute_query(query, (event_type, limit))
            return self._deserialize_events(result)
        except Exception as e:
            logger.error(f"Failed to get events by type {event_type}: {e}")
            return []

    async def get_events_by_time_range(self, start_time: datetime, end_time: datetime) -> List[DomainEvent]:
        """Get events within a time range."""
        await self.initialize()

        query = """
        SELECT * FROM events
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
        """

        try:
            result = await self.db.execute_query(query, (
                start_time.isoformat(),
                end_time.isoformat()
            ))
            return self._deserialize_events(result)
        except Exception as e:
            logger.error(f"Failed to get events by time range: {e}")
            return []

    async def get_event_count(self, aggregate_id: Optional[str] = None) -> int:
        """Get total event count, optionally filtered by aggregate."""
        await self.initialize()

        if aggregate_id:
            query = "SELECT COUNT(*) as count FROM events WHERE aggregate_id = ?"
            params = (aggregate_id,)
        else:
            query = "SELECT COUNT(*) as count FROM events"
            params = ()

        try:
            result = await self.db.execute_query(query, params)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to get event count: {e}")
            return 0

    async def get_recent_events(self, limit: int = 50) -> List[DomainEvent]:
        """Get most recent events."""
        await self.initialize()

        query = """
        SELECT * FROM events
        ORDER BY timestamp DESC
        LIMIT ?
        """

        try:
            result = await self.db.execute_query(query, (limit,))
            return self._deserialize_events(result)
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

    async def get_events_by_correlation(self, correlation_id: str) -> List[DomainEvent]:
        """Get events by correlation ID for tracing."""
        await self.initialize()

        query = """
        SELECT * FROM events
        WHERE correlation_id = ?
        ORDER BY timestamp ASC
        """

        try:
            result = await self.db.execute_query(query, (correlation_id,))
            return self._deserialize_events(result)
        except Exception as e:
            logger.error(f"Failed to get events by correlation {correlation_id}: {e}")
            return []

    def _deserialize_events(self, rows: List[Dict[str, Any]]) -> List[DomainEvent]:
        """Deserialize database rows back to domain events."""
        events = []

        for row in rows:
            try:
                event_data = {
                    'metadata': {
                        'event_id': row['event_id'],
                        'aggregate_id': row['aggregate_id'],
                        'aggregate_type': row['aggregate_type'],
                        'event_type': row['event_type'],
                        'event_version': row['event_version'],
                        'timestamp': row['timestamp'],
                        'correlation_id': row['correlation_id'],
                        'causation_id': row['causation_id'],
                        'source_context': row['source_context'],
                        'user_id': row['user_id']
                    },
                    'data': json.loads(row['event_data'])
                }

                event = deserialize_event(event_data)
                if event:
                    events.append(event)

            except Exception as e:
                logger.error(f"Failed to deserialize event {row['event_id']}: {e}")
                continue

        return events

    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event store statistics."""
        await self.initialize()

        stats_query = """
        SELECT
            COUNT(*) as total_events,
            COUNT(DISTINCT aggregate_id) as unique_aggregates,
            COUNT(DISTINCT event_type) as unique_event_types,
            MIN(timestamp) as oldest_event,
            MAX(timestamp) as newest_event
        FROM events
        """

        type_distribution_query = """
        SELECT event_type, COUNT(*) as count
        FROM events
        GROUP BY event_type
        ORDER BY count DESC
        """

        try:
            stats_result = await self.db.execute_query(stats_query)
            type_result = await self.db.execute_query(type_distribution_query)

            stats = stats_result[0] if stats_result else {}

            return {
                'total_events': stats.get('total_events', 0),
                'unique_aggregates': stats.get('unique_aggregates', 0),
                'unique_event_types': stats.get('unique_event_types', 0),
                'oldest_event': stats.get('oldest_event'),
                'newest_event': stats.get('newest_event'),
                'event_type_distribution': {row['event_type']: row['count'] for row in type_result}
            }

        except Exception as e:
            logger.error(f"Failed to get event statistics: {e}")
            return {}


class InMemoryEventStore(EventStore):
    """
    In-memory event store for testing and development.

    Stores events in memory without persistence.
    """

    def __init__(self):
        self.events: List[DomainEvent] = []
        self._initialized = True

    async def save_event(self, event: DomainEvent) -> bool:
        """Save a single event to memory."""
        self.events.append(event)
        logger.debug(f"Event saved to memory: {event.metadata.event_type}")
        return True

    async def save_events(self, events: List[DomainEvent]) -> bool:
        """Save multiple events to memory."""
        self.events.extend(events)
        logger.info(f"Batch saved {len(events)} events to memory")
        return True

    async def get_events_for_aggregate(self, aggregate_id: str, aggregate_type: str) -> List[DomainEvent]:
        """Get all events for a specific aggregate."""
        return [
            event for event in self.events
            if event.metadata.aggregate_id == aggregate_id and
               event.metadata.aggregate_type == aggregate_type
        ]

    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[DomainEvent]:
        """Get events of a specific type."""
        return [
            event for event in self.events
            if event.metadata.event_type == event_type
        ][:limit]

    async def get_events_by_time_range(self, start_time: datetime, end_time: datetime) -> List[DomainEvent]:
        """Get events within a time range."""
        return [
            event for event in self.events
            if start_time <= event.metadata.timestamp <= end_time
        ]

    async def get_event_count(self, aggregate_id: Optional[str] = None) -> int:
        """Get total event count, optionally filtered by aggregate."""
        if aggregate_id:
            return len([
                event for event in self.events
                if event.metadata.aggregate_id == aggregate_id
            ])
        return len(self.events)

    async def clear(self):
        """Clear all events (for testing)."""
        self.events.clear()
        logger.info("Cleared all events from memory store")


# Global event store instance
_event_store: Optional[EventStore] = None


def get_event_store(store_type: str = "duckdb", **kwargs) -> EventStore:
    """Get global event store instance."""
    global _event_store

    if _event_store is None:
        if store_type == "duckdb":
            _event_store = DuckDBEventStore(**kwargs)
        elif store_type == "memory":
            _event_store = InMemoryEventStore()
        else:
            raise ValueError(f"Unsupported event store type: {store_type}")

    return _event_store


def reset_event_store():
    """Reset global event store (mainly for testing)."""
    global _event_store
    _event_store = None
