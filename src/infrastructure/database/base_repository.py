"""
Base Repository Pattern Implementation
Provides common database operations following DDD repository pattern
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Entity type
ID = TypeVar('ID')  # Identifier type


@dataclass
class RepositoryResult:
    """Standardized repository operation result"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseRepository(ABC, Generic[T, ID]):
    """
    Abstract base repository following Domain-Driven Design patterns
    Provides common CRUD operations and transaction management
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def save(self, entity: T) -> RepositoryResult:
        """Save or update an entity"""
        pass

    @abstractmethod
    async def find_by_id(self, entity_id: ID) -> RepositoryResult:
        """Find entity by its identifier"""
        pass

    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> RepositoryResult:
        """Find all entities with pagination"""
        pass

    @abstractmethod
    async def delete_by_id(self, entity_id: ID) -> RepositoryResult:
        """Delete entity by its identifier"""
        pass

    @abstractmethod
    async def exists_by_id(self, entity_id: ID) -> bool:
        """Check if entity exists by identifier"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total entities"""
        pass

    @abstractmethod
    async def find_by_criteria(self, criteria: dict, limit: int = 100, offset: int = 0) -> RepositoryResult:
        """Find entities matching criteria"""
        pass

    async def begin_transaction(self) -> Any:
        """Begin database transaction"""
        pass

    async def commit_transaction(self, transaction: Any) -> RepositoryResult:
        """Commit database transaction"""
        pass

    async def rollback_transaction(self, transaction: Any) -> RepositoryResult:
        """Rollback database transaction"""
        pass

    def _log_operation(self, operation: str, entity_id: Optional[ID] = None, details: Optional[dict] = None):
        """Log repository operations for debugging and monitoring"""
        log_data = {
            'operation': operation,
            'entity_type': self.__class__.__name__,
            'timestamp': datetime.now().isoformat()
        }

        if entity_id:
            log_data['entity_id'] = str(entity_id)

        if details:
            log_data.update(details)

        self.logger.info(f"Repository operation: {operation}", extra=log_data)

    def _handle_error(self, operation: str, error: Exception, entity_id: Optional[ID] = None) -> RepositoryResult:
        """Standardized error handling for repository operations"""
        error_msg = f"Repository {operation} failed: {str(error)}"

        self.logger.error(error_msg, exc_info=True, extra={
            'operation': operation,
            'entity_id': str(entity_id) if entity_id else None,
            'error_type': type(error).__name__
        })

        return RepositoryResult(
            success=False,
            error=error_msg
        )


class QueryBuilder:
    """
    Fluent query builder for complex database queries
    Following builder pattern for readability and maintainability
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.select_fields = ["*"]
        self.where_conditions = []
        self.join_clauses = []
        self.order_by = []
        self.limit_value = None
        self.offset_value = 0
        self.parameters = {}

    def select(self, *fields: str) -> 'QueryBuilder':
        """Specify fields to select"""
        self.select_fields = list(fields)
        return self

    def where(self, condition: str, **params) -> 'QueryBuilder':
        """Add WHERE condition"""
        self.where_conditions.append(condition)
        self.parameters.update(params)
        return self

    def join(self, table: str, on_condition: str) -> 'QueryBuilder':
        """Add JOIN clause"""
        self.join_clauses.append(f"JOIN {table} ON {on_condition}")
        return self

    def order_by(self, *fields: str, desc: bool = False) -> 'QueryBuilder':
        """Add ORDER BY clause"""
        direction = "DESC" if desc else "ASC"
        self.order_by.extend([f"{field} {direction}" for field in fields])
        return self

    def limit(self, limit: int) -> 'QueryBuilder':
        """Set LIMIT"""
        self.limit_value = limit
        return self

    def offset(self, offset: int) -> 'QueryBuilder':
        """Set OFFSET"""
        self.offset_value = offset
        return self

    def build_select(self) -> tuple[str, dict]:
        """Build SELECT query"""
        query_parts = [
            f"SELECT {', '.join(self.select_fields)}",
            f"FROM {self.table_name}"
        ]

        # Add JOINs
        query_parts.extend(self.join_clauses)

        # Add WHERE
        if self.where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")

        # Add ORDER BY
        if self.order_by:
            query_parts.append(f"ORDER BY {', '.join(self.order_by)}")

        # Add LIMIT/OFFSET
        if self.limit_value:
            query_parts.append(f"LIMIT {self.limit_value}")
        if self.offset_value:
            query_parts.append(f"OFFSET {self.offset_value}")

        return " ".join(query_parts), self.parameters

    def build_count(self) -> tuple[str, dict]:
        """Build COUNT query"""
        query = f"SELECT COUNT(*) FROM {self.table_name}"

        if self.where_conditions:
            query += f" WHERE {' AND '.join(self.where_conditions)}"

        return query, self.parameters

    def build_insert(self, data: dict) -> tuple[str, dict]:
        """Build INSERT query"""
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]
        values = {col: data[col] for col in columns}

        query = f"""
        INSERT INTO {self.table_name} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        """

        return query.strip(), values

    def build_update(self, data: dict, where_condition: str, **where_params) -> tuple[str, dict]:
        """Build UPDATE query"""
        set_parts = [f"{col} = :{col}" for col in data.keys()]
        params = dict(data)  # Copy data values
        params.update(where_params)  # Add WHERE parameters

        query = f"""
        UPDATE {self.table_name}
        SET {', '.join(set_parts)}
        WHERE {where_condition}
        """

        return query.strip(), params
