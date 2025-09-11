# 🚀 Application Layer (CQRS) Architecture

The Application Layer orchestrates domain objects and implements the **CQRS (Command Query Responsibility Segregation)** pattern to optimize read and write operations.

## 📋 Overview

The Application Layer acts as a **thin orchestration layer** between the Presentation Layer and the Domain Layer. It implements CQRS to separate:

- **Commands**: Write operations that change application state
- **Queries**: Read operations that retrieve data
- **Events**: Notifications of state changes
- **Handlers**: Process commands and queries

## 🏗️ CQRS Architecture

```
┌─────────────────────────────────────┐
│         APPLICATION LAYER           │
│  ┌─────────────────────────────────┐ │
│  │         CQRS BUS              │ │
│  │  ┌─────────────────────────────┐ │ │
│  │  │  Command Bus              │ │ │
│  │  │  Query Bus                │ │ │
│  │  └─────────────────────────────┘ │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
                    │
          ┌─────────┼─────────┐
          │         │         │
          ▼         ▼         ▼
┌─────────────────┐ ┌───────┐ ┌─────────────────┐
│  COMMAND       │ │EVENTS │ │  QUERY          │
│  HANDLERS      │ │       │ │  HANDLERS       │
│                 │ │       │ │                 │
│ • SubmitOrder   │ │ • Order│ │ • GetOrderById │
│ • CancelOrder   │ │   Placed│ │ • GetOrders   │
│ • ExecuteScan   │ │ • Trade│ │ • GetPortfolio │
│                 │ │   Executed│                 │
└─────────────────┘ └───────┘ └─────────────────┘
          │         │         │
          └─────────┼─────────┘
                    ▼
           ┌─────────────────┐
           │   DOMAIN LAYER  │
           │                 │
           │ • Entities      │
           │ • Services      │
           │ • Repositories  │
           │ • Domain Events │
           └─────────────────┘
```

## 🎯 CQRS Principles

### Command Query Separation

**Commands** (Write Operations):
- Change application state
- Are imperative ("Do this")
- May have side effects
- Are validated before execution
- Return success/failure status

```python
@dataclass
class SubmitOrderCommand(Command):
    """Command to submit a trading order."""
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Optional[Decimal] = None

    @property
    def command_type(self) -> str:
        return "SubmitOrder"
```

**Queries** (Read Operations):
- Return data without side effects
- Are declarative ("Give me this data")
- Are optimized for reading
- Can be cached
- Return DTOs or domain objects

```python
@dataclass
class GetOrderByIdQuery(Query):
    """Query to get an order by ID."""
    order_id: str

    @property
    def query_type(self) -> str:
        return "GetOrderById"
```

### Command Processing Flow

```
1. Command Created
       ↓
2. Command Validation
       ↓
3. Command Handler Selection
       ↓
4. Domain Logic Execution
       ↓
5. Repository Persistence
       ↓
6. Domain Events Published
       ↓
7. Command Result Returned
```

## 📁 Application Layer Structure

```
application/
├── __init__.py                    # Application layer exports
├── cqrs_registry.py              # CQRS registry and buses
│
├── commands/                     # Command definitions and handlers
│   ├── __init__.py
│   ├── base_command.py           # Base command classes
│   ├── trading_commands.py       # Trading domain commands
│   ├── analytics_commands.py     # Analytics domain commands
│   ├── scanning_commands.py      # Scanning domain commands
│   ├── risk_management_commands.py
│   ├── broker_integration_commands.py
│   └── handlers/
│       ├── commands/
│       │   ├── trading_command_handlers.py
│       │   ├── analytics_command_handlers.py
│       │   ├── scanning_command_handlers.py
│       │   ├── risk_management_command_handlers.py
│       │   └── broker_integration_command_handlers.py
│       └── queries/
│           ├── trading_query_handlers.py
│           ├── analytics_query_handlers.py
│           ├── scanning_query_handlers.py
│           ├── risk_management_query_handlers.py
│           └── broker_integration_query_handlers.py
│
├── queries/                      # Query definitions and handlers
│   ├── __init__.py
│   ├── base_query.py             # Base query classes
│   ├── trading_queries.py        # Trading domain queries
│   ├── analytics_queries.py      # Analytics domain queries
│   ├── scanning_queries.py       # Scanning domain queries
│   ├── risk_management_queries.py
│   └── broker_integration_queries.py
│
└── services/                     # Application services
    ├── __init__.py
    ├── market_data_application_service.py
    └── trading_application_service.py
```

## 🔧 Core Components

### Command Bus

The Command Bus routes commands to appropriate handlers:

```python
class CommandBus:
    """Routes commands to handlers using mediator pattern."""

    def __init__(self):
        self._handlers: Dict[str, CommandHandler] = {}

    def register_handler(self, command_type: str, handler: CommandHandler):
        """Register a command handler."""
        self._handlers[command_type] = handler

    async def send(self, command: Command) -> CommandResult:
        """Send command to appropriate handler."""
        if command.command_type not in self._handlers:
            raise ValueError(f"No handler for command: {command.command_type}")

        handler = self._handlers[command.command_type]
        return await handler.handle(command)
```

### Query Bus

The Query Bus routes queries to appropriate handlers:

```python
class QueryBus:
    """Routes queries to handlers using mediator pattern."""

    def __init__(self):
        self._handlers: Dict[str, QueryHandler] = {}

    def register_handler(self, query_type: str, handler: QueryHandler):
        """Register a query handler."""
        self._handlers[query_type] = handler

    async def send(self, query: Query) -> QueryResult:
        """Send query to appropriate handler."""
        if query.query_type not in self._handlers:
            raise ValueError(f"No handler for query: {query.query_type}")

        handler = self._handlers[query.query_type]
        return await handler.handle(query)
```

### CQRS Registry

The CQRS Registry manages all commands, queries, and their handlers:

```python
class CQRSRegistry:
    """Central registry for CQRS components."""

    def __init__(self):
        self.command_bus = CommandBus()
        self.query_bus = QueryBus()
        self._handlers_registered = False

    def initialize(self):
        """Initialize and register all handlers."""
        if not self._handlers_registered:
            self._register_all_handlers()
            self._handlers_registered = True

    def _register_all_handlers(self):
        """Register handlers for all domains."""
        # Trading domain
        self._register_trading_handlers()
        # Analytics domain
        self._register_analytics_handlers()
        # Scanning domain
        self._register_scanning_handlers()
        # Risk management domain
        self._register_risk_management_handlers()
        # Broker integration domain
        self._register_broker_integration_handlers()

    async def execute_command(self, command: Command) -> CommandResult:
        """Execute a command through the bus."""
        return await self.command_bus.send(command)

    async def execute_query(self, query: Query) -> QueryResult:
        """Execute a query through the bus."""
        return await self.query_bus.send(query)
```

## 🎯 Command Handlers

Command handlers orchestrate domain operations:

```python
class SubmitOrderCommandHandler(CommandHandler):
    """Handler for SubmitOrderCommand."""

    def __init__(self, order_repository: OrderRepository,
                 order_execution_service: OrderExecutionService):
        self.order_repository = order_repository
        self.order_execution_service = order_execution_service

    @property
    def handled_command_type(self) -> str:
        return "SubmitOrder"

    async def handle(self, command: SubmitOrderCommand) -> CommandResult:
        """Handle order submission."""
        try:
            # 1. Validate command
            self._validate_command(command)

            # 2. Create domain object
            order = Order(
                id=OrderId.generate(),
                symbol=Symbol(command.symbol),
                side=OrderSide(command.side),
                quantity=Quantity(command.quantity),
                order_type=OrderType(command.order_type),
                price=Price(command.price) if command.price else None
            )

            # 3. Execute domain logic
            violations = await self.order_execution_service.validate_order(order)
            if violations:
                return CommandResult(
                    success=False,
                    command_id=command.command_id,
                    error_message=f"Validation failed: {', '.join(violations)}"
                )

            # 4. Persist to repository
            await self.order_repository.save(order)

            # 5. Publish domain events
            # Events are automatically published by the aggregate

            return CommandResult(
                success=True,
                command_id=command.command_id,
                data={
                    "order_id": str(order.id),
                    "status": order.status.value
                }
            )

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return CommandResult(
                success=False,
                command_id=command.command_id,
                error_message=str(e)
            )
```

## 🔍 Query Handlers

Query handlers retrieve and format data:

```python
class GetOrderByIdQueryHandler(QueryHandler):
    """Handler for GetOrderByIdQuery."""

    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository

    @property
    def handled_query_type(self) -> str:
        return "GetOrderById"

    async def handle(self, query: GetOrderByIdQuery) -> QueryResult:
        """Handle order retrieval query."""
        try:
            order_id = OrderId(query.order_id)
            order = await self.order_repository.find_by_id(order_id)

            if not order:
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None
                )

            # Convert to DTO for presentation
            order_dto = {
                "id": str(order.id),
                "symbol": order.symbol.value,
                "side": order.side.value,
                "quantity": order.quantity.value,
                "filled_quantity": order.filled_quantity.value,
                "remaining_quantity": order.remaining_quantity.value,
                "status": order.status.value,
                "created_at": order.created_at.isoformat()
            }

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={"order": order_dto}
            )

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )
```

## 📊 Application Services

Application services provide high-level orchestration:

```python
class TradingApplicationService:
    """Application service for trading operations."""

    def __init__(self, cqrs_registry: CQRSRegistry):
        self.cqrs = cqrs_registry

    async def submit_order(self, symbol: str, side: str, quantity: int,
                          order_type: str, price: Optional[Decimal] = None) -> Dict[str, Any]:
        """Submit a trading order."""
        command = SubmitOrderCommand(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price
        )

        result = await self.cqrs.execute_command(command)

        if not result.success:
            raise ApplicationException(f"Order submission failed: {result.error_message}")

        return result.data

    async def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """Get portfolio summary."""
        query = GetPortfolioSummaryQuery(portfolio_id=portfolio_id)

        result = await self.cqrs.execute_query(query)

        if not result.success:
            raise ApplicationException(f"Portfolio query failed: {result.error_message}")

        return result.data
```

## 🔄 CQRS Patterns

### Command Sourcing

Commands can be stored for audit and replay:

```python
class CommandStore:
    """Store commands for audit and replay."""

    async def save_command(self, command: Command) -> None:
        """Save command to store."""
        command_data = {
            "id": command.command_id,
            "type": command.command_type,
            "data": command.to_dict(),
            "timestamp": command.timestamp,
            "correlation_id": command.correlation_id
        }
        await self.store.save(command_data)

    async def get_commands_for_aggregate(self, aggregate_id: str) -> List[Command]:
        """Get all commands for an aggregate."""
        return await self.store.find_by_aggregate_id(aggregate_id)
```

### Event Sourcing

Domain events can be stored for state reconstruction:

```python
class EventStore:
    """Store domain events for state reconstruction."""

    async def save_events(self, events: List[DomainEvent]) -> None:
        """Save domain events."""
        for event in events:
            event_data = {
                "id": str(uuid4()),
                "aggregate_id": event.aggregate_id,
                "event_type": event.event_type,
                "data": asdict(event),
                "timestamp": event.timestamp
            }
            await self.store.save(event_data)

    async def get_events_for_aggregate(self, aggregate_id: str) -> List[DomainEvent]:
        """Get all events for an aggregate."""
        events_data = await self.store.find_by_aggregate_id(aggregate_id)
        return [self._deserialize_event(event_data) for event_data in events_data]
```

### CQRS with Event Sourcing

Combining CQRS with Event Sourcing:

```python
class OrderAggregate:
    """Order aggregate with event sourcing."""

    def __init__(self, id: OrderId):
        self.id = id
        self.events: List[DomainEvent] = []
        self.version = 0

        # State
        self.symbol: Optional[Symbol] = None
        self.quantity: Optional[Quantity] = None
        self.status = OrderStatus.PENDING

    def submit(self, symbol: Symbol, quantity: Quantity) -> None:
        """Submit the order."""
        if self.status != OrderStatus.PENDING:
            raise DomainException("Order already submitted")

        event = OrderSubmitted(self.id, symbol, quantity, self.version + 1)
        self.apply_event(event)
        self.events.append(event)

    def apply_event(self, event: DomainEvent) -> None:
        """Apply event to update state."""
        if isinstance(event, OrderSubmitted):
            self.symbol = event.symbol
            self.quantity = event.quantity
            self.status = OrderStatus.SUBMITTED
        elif isinstance(event, OrderFilled):
            self.status = OrderStatus.FILLED

        self.version = event.version
```

## 🧪 Application Layer Testing

### Testing Command Handlers

```python
@pytest.mark.asyncio
async def test_submit_order_command_handler():
    """Test order submission command handler."""
    # Arrange
    order_repo = Mock(spec=OrderRepository)
    execution_service = Mock(spec=OrderExecutionService)

    handler = SubmitOrderCommandHandler(order_repo, execution_service)

    command = SubmitOrderCommand(
        symbol="AAPL",
        side="BUY",
        quantity=100,
        order_type="MARKET"
    )

    # Mock domain service
    execution_service.validate_order.return_value = []

    # Act
    result = await handler.handle(command)

    # Assert
    assert result.success is True
    assert "order_id" in result.data
    order_repo.save.assert_called_once()
```

### Testing Query Handlers

```python
@pytest.mark.asyncio
async def test_get_order_query_handler():
    """Test order retrieval query handler."""
    # Arrange
    order_repo = Mock(spec=OrderRepository)
    mock_order = Order(
        id=OrderId("test-id"),
        symbol=Symbol("AAPL"),
        quantity=Quantity(100)
    )
    order_repo.find_by_id.return_value = mock_order

    handler = GetOrderByIdQueryHandler(order_repo)

    query = GetOrderByIdQuery(order_id="test-id")

    # Act
    result = await handler.handle(query)

    # Assert
    assert result.success is True
    assert result.data["order"]["symbol"] == "AAPL"
    order_repo.find_by_id.assert_called_once_with(OrderId("test-id"))
```

## 📈 Performance Optimization

### Command Processing Optimization

```python
class OptimizedCommandBus(CommandBus):
    """Command bus with performance optimizations."""

    def __init__(self):
        super().__init__()
        self._handler_cache = {}  # Cache handler instances
        self._metrics = {}  # Track performance metrics

    async def send(self, command: Command) -> CommandResult:
        """Send command with performance tracking."""
        start_time = time.time()

        try:
            result = await super().send(command)

            # Track metrics
            processing_time = time.time() - start_time
            self._record_metric(command.command_type, processing_time, result.success)

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self._record_metric(command.command_type, processing_time, False)
            raise
```

### Query Result Caching

```python
class CachedQueryBus(QueryBus):
    """Query bus with result caching."""

    def __init__(self, cache_ttl: int = 300):
        super().__init__()
        self.cache = {}
        self.cache_ttl = cache_ttl

    async def send(self, query: Query) -> QueryResult:
        """Send query with caching."""
        cache_key = self._generate_cache_key(query)

        # Check cache
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_result

        # Execute query
        result = await super().send(query)

        # Cache result
        if result.success:
            self.cache[cache_key] = (result, time.time())

        return result

    def _generate_cache_key(self, query: Query) -> str:
        """Generate cache key for query."""
        return f"{query.query_type}:{hash(str(query.__dict__))}"
```

## 🔒 Security Considerations

### Command Authorization

```python
class AuthorizedCommandBus(CommandBus):
    """Command bus with authorization checks."""

    def __init__(self, auth_service: AuthorizationService):
        super().__init__()
        self.auth_service = auth_service

    async def send(self, command: Command) -> CommandResult:
        """Send command with authorization check."""
        # Check if user can execute this command
        if not await self.auth_service.can_execute_command(command, get_current_user()):
            raise AuthorizationException(f"Unauthorized to execute {command.command_type}")

        return await super().send(command)
```

### Query Access Control

```python
class AccessControlledQueryBus(QueryBus):
    """Query bus with access control."""

    def __init__(self, access_control: AccessControlService):
        super().__init__()
        self.access_control = access_control

    async def send(self, query: Query) -> QueryResult:
        """Send query with access control."""
        # Filter results based on user permissions
        result = await super().send(query)

        if result.success and result.data:
            result.data = await self.access_control.filter_data(result.data, get_current_user())

        return result
```

## 📊 Monitoring and Observability

### CQRS Metrics

```python
class MonitoredCQRSRegistry(CQRSRegistry):
    """CQRS registry with monitoring capabilities."""

    def __init__(self, metrics_collector: MetricsCollector):
        super().__init__()
        self.metrics = metrics_collector

    async def execute_command(self, command: Command) -> CommandResult:
        """Execute command with metrics collection."""
        start_time = time.time()

        try:
            result = await super().execute_command(command)

            # Record metrics
            self.metrics.record_command_execution(
                command_type=command.command_type,
                duration=time.time() - start_time,
                success=result.success
            )

            if not result.success:
                self.metrics.record_command_failure(
                    command_type=command.command_type,
                    error=result.error_message
                )

            return result

        except Exception as e:
            self.metrics.record_command_error(
                command_type=command.command_type,
                error=str(e)
            )
            raise
```

### CQRS Tracing

```python
class TracedCQRSRegistry(CQRSRegistry):
    """CQRS registry with distributed tracing."""

    def __init__(self, tracer: Tracer):
        super().__init__()
        self.tracer = tracer

    async def execute_command(self, command: Command) -> CommandResult:
        """Execute command with tracing."""
        with self.tracer.start_span(f"command:{command.command_type}") as span:
            span.set_attribute("command.id", command.command_id)
            span.set_attribute("command.correlation_id", command.correlation_id)

            result = await super().execute_command(command)

            span.set_attribute("result.success", result.success)
            if not result.success:
                span.set_attribute("result.error", result.error_message)

            return result
```

## 🎯 Best Practices

### 1. **Thin Application Layer**
Keep the application layer thin - delegate business logic to the domain:

```python
# ✅ Good: Thin application layer
async def submit_order(self, command_data: dict) -> dict:
    command = SubmitOrderCommand(**command_data)
    result = await self.cqrs.execute_command(command)
    return result.data

# ❌ Bad: Business logic in application layer
async def submit_order(self, command_data: dict) -> dict:
    # Don't put validation logic here
    if command_data['quantity'] <= 0:
        raise ValueError("Invalid quantity")
    # Don't put domain logic here
    order_id = str(uuid4())
    # ...
```

### 2. **Command Immutability**
Commands should be immutable:

```python
# ✅ Good: Immutable commands
@dataclass(frozen=True)
class SubmitOrderCommand(Command):
    symbol: str
    quantity: int

# ❌ Bad: Mutable commands
class SubmitOrderCommand(Command):
    def __init__(self):
        self.symbol = None
        self.quantity = None

    def set_symbol(self, symbol):  # Avoid setters
        self.symbol = symbol
```

### 3. **Query Optimization**
Optimize queries for read performance:

```python
# ✅ Good: Optimized queries
class GetOrdersSummaryQuery(Query):
    """Query for order summaries (not full objects)."""
    status: Optional[str] = None
    limit: int = 100

# ❌ Bad: Inefficient queries
class GetAllOrdersQuery(Query):
    """Returns all order data - inefficient."""
    pass
```

### 4. **Handler Isolation**
Keep handlers focused and isolated:

```python
# ✅ Good: Single responsibility
class SubmitOrderHandler(CommandHandler):
    @property
    def handled_command_type(self):
        return "SubmitOrder"

# ❌ Bad: Multiple responsibilities
class OrderHandler(CommandHandler):
    @property
    def handled_command_type(self):
        return "Order"  # Handles all order operations
```

## 🔧 Configuration

### CQRS Configuration

```python
@dataclass
class CQRSConfig:
    """Configuration for CQRS components."""
    enable_command_logging: bool = True
    enable_query_logging: bool = True
    enable_performance_monitoring: bool = True
    command_timeout_seconds: int = 30
    query_timeout_seconds: int = 30
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
```

### Handler Registration

```python
def configure_cqrs_registry(registry: CQRSRegistry) -> None:
    """Configure CQRS registry with all handlers."""

    # Trading handlers
    registry.command_bus.register_handler(
        "SubmitOrder",
        SubmitOrderCommandHandler(order_repo, execution_service)
    )
    registry.query_bus.register_handler(
        "GetOrderById",
        GetOrderByIdQueryHandler(order_repo)
    )

    # Analytics handlers
    registry.command_bus.register_handler(
        "CalculateIndicator",
        CalculateIndicatorCommandHandler(indicator_repo, calc_service)
    )
    registry.query_bus.register_handler(
        "GetIndicatorById",
        GetIndicatorByIdQueryHandler(indicator_repo)
    )

    # Add more handlers...
```

## 📚 Related Documentation

- [Domain Layer](../domain-layer.md) - Business logic and entities
- [Infrastructure Layer](../infrastructure-layer.md) - Data persistence and external services
- [CQRS Patterns](../../patterns/cqrs-patterns.md) - CQRS implementation patterns
- [Testing Guide](../../testing/application-testing.md) - Application layer testing

---

**The Application Layer serves as the orchestration hub, coordinating between the presentation layer's requests and the domain layer's business logic through the CQRS pattern.**