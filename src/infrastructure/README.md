# Infrastructure Layer

The Infrastructure Layer provides technical capabilities and external integrations for the application, following the hexagonal architecture pattern and dependency inversion principle.

## Overview

This layer contains:
- **Database Adapters**: Repository implementations for data persistence
- **External Service Adapters**: Integration with external APIs and services
- **Messaging**: Event-driven communication between bounded contexts
- **Dependency Injection**: Container for managing dependencies

## Architecture Principles

### 1. Dependency Inversion
- High-level modules don't depend on low-level modules
- Both depend on abstractions (interfaces)
- External dependencies are injected, not imported

### 2. Repository Pattern
- Abstract data access operations
- Domain objects don't know about persistence details
- Easy to switch between different data sources

### 3. Adapter Pattern
- Clean interface for external service integrations
- Isolate external API changes from domain logic
- Consistent error handling and retry logic

### 4. Event-Driven Architecture
- Loose coupling between bounded contexts
- Asynchronous communication
- Domain events for cross-context integration

## Components

### Database Layer (`database/`)
- `BaseRepository`: Abstract base for all repositories
- `DuckDBAdapter`: Database connection and query execution
- `MarketDataRepositoryImpl`: Market data persistence operations

### External Services Layer (`external/`)
- `BaseExternalAdapter`: Common external service functionality
- `BrokerAdapter`: Abstract broker integration interface
- `DhanBrokerAdapter`: Concrete Dhan broker implementation

### Messaging Layer (`messaging/`)
- `DomainEvent`: Base class for domain events
- `IntegrationEvent`: Cross-context integration events
- Event publishers and subscribers for async communication

### Dependency Injection (`dependency_container.py`)
- `DependencyContainer`: IoC container for dependency management
- `ServiceLocator`: Simple service location pattern
- `@inject` decorator for automatic dependency injection

## Usage Examples

### Repository Usage
```python
from src.infrastructure import MarketDataRepositoryImpl, get_container

# Register repository
container = get_container()
container.register_factory(
    'MarketDataRepository',
    lambda: MarketDataRepositoryImpl('path/to/database.db')
)

# Use repository
repo = container.resolve('MarketDataRepository')
result = await repo.find_by_symbol_and_date_range('AAPL', start_date, end_date)
```

### External Service Usage
```python
from src.infrastructure import DhanBrokerAdapter, BrokerCredentials

# Create broker adapter
credentials = BrokerCredentials(
    client_id="your_client_id",
    access_token="your_access_token"
)

async with DhanBrokerAdapter("client_id", "access_token") as broker:
    # Authenticate
    authenticated = await broker.authenticate(credentials)

    # Place order
    order = OrderRequest(
        symbol="AAPL",
        side="BUY",
        quantity=10,
        order_type="MARKET"
    )
    response = await broker.place_order(order)
```

### Event Publishing
```python
from src.infrastructure import MarketDataReceived, get_container

# Publish domain event
event = MarketDataReceived(
    aggregate_id="market_data_feed_1",
    symbol="AAPL",
    price=150.25,
    volume=1000000
)

publisher = container.resolve('EventPublisher')
await publisher.publish(event)
```

### Dependency Injection
```python
from src.infrastructure import inject, ServiceLocator

@inject(ServiceLocator)
def process_market_data(service_locator):
    repo = service_locator.get_market_data_repository()
    # Use repository...
```

## Configuration

### Database Configuration
```python
# Environment variables
DATABASE_PATH="/path/to/financial_data.db"
DATABASE_MAX_CONNECTIONS=10
```

### External Service Configuration
```python
# Broker configuration
BROKER_CLIENT_ID="your_client_id"
BROKER_ACCESS_TOKEN="your_access_token"
BROKER_BASE_URL="https://api.dhan.co"
```

### Messaging Configuration
```python
# Redis configuration (for production)
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_DB=0
```

## Error Handling

### Repository Errors
- `RepositoryResult.success`: Operation success status
- `RepositoryResult.error`: Error message if failed
- `RepositoryResult.data`: Operation result data

### External Service Errors
- `ExternalServiceResult.success`: API call success
- `ExternalServiceResult.status_code`: HTTP status code
- `ExternalServiceResult.response_time`: API response time
- Automatic retry logic with exponential backoff

### Messaging Errors
- Dead letter queues for failed event processing
- Event replay capabilities for transient failures
- Circuit breaker pattern for unhealthy services

## Testing

### Unit Testing Infrastructure
```python
import pytest
from src.infrastructure import DependencyContainer

@pytest.fixture
def container():
    container = DependencyContainer()
    # Register test dependencies
    yield container
    container.clear()
```

### Integration Testing
```python
@pytest.mark.asyncio
async def test_market_data_repository():
    repo = MarketDataRepositoryImpl(":memory:")
    # Test repository operations
```

### Mocking External Services
```python
from unittest.mock import AsyncMock

@pytest.fixture
def mock_broker():
    broker = AsyncMock()
    broker.authenticate.return_value = True
    return broker
```

## Performance Considerations

### Database Optimization
- Connection pooling with configurable limits
- Query result caching for frequently accessed data
- Batch operations for bulk data processing
- Index optimization for common query patterns

### External Service Optimization
- Rate limiting to respect API quotas
- Connection pooling for HTTP requests
- Response caching for idempotent operations
- Asynchronous processing for non-blocking calls

### Messaging Optimization
- Event batching for high-throughput scenarios
- Message deduplication to prevent duplicate processing
- Partitioning for parallel event processing
- Dead letter queue monitoring and cleanup

## Monitoring

### Health Checks
- Database connectivity verification
- External service availability monitoring
- Message queue health and throughput
- Dependency injection container status

### Metrics
- Repository operation latency and success rates
- External API call statistics
- Event publishing and processing metrics
- Dependency resolution performance

### Logging
- Structured logging for all operations
- Error tracking with correlation IDs
- Performance monitoring logs
- Audit trails for sensitive operations

## Security

### Data Protection
- Sensitive configuration encryption
- Secure credential management
- Input validation and sanitization
- SQL injection prevention

### Network Security
- HTTPS for all external communications
- API key rotation and management
- Request/response encryption
- Rate limiting for abuse prevention

### Access Control
- Authentication for external services
- Authorization for sensitive operations
- Audit logging for compliance
- Secure session management

## Migration Guide

### From Direct Dependencies
1. Identify direct infrastructure imports in domain code
2. Create abstraction interfaces in domain layer
3. Implement adapters in infrastructure layer
4. Register dependencies in container
5. Update domain code to use abstractions

### From Monolithic Database Access
1. Extract query logic into repository classes
2. Create repository interfaces
3. Implement repository pattern
4. Update service classes to use repositories
5. Add database transaction management

### From Synchronous External Calls
1. Identify blocking external service calls
2. Implement async adapter interfaces
3. Add retry and circuit breaker logic
4. Update calling code for async patterns
5. Add proper error handling and fallback logic

## Troubleshooting

### Common Issues
- **Circular Dependencies**: Review import structure and use dependency injection
- **Connection Pool Exhaustion**: Adjust connection pool size and monitor usage
- **Rate Limiting**: Implement proper backoff strategies and monitor API quotas
- **Event Processing Delays**: Check message queue configuration and processing capacity

### Debug Tools
- Dependency container registration inspection
- Database connection pool monitoring
- External service call tracing
- Event processing pipeline monitoring
