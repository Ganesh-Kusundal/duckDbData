# 🏛️ Domain Layer Architecture

The Domain Layer is the heart of the trading system, containing all business logic, rules, and entities that represent the core business concepts.

## 📋 Overview

The Domain Layer implements **Domain-Driven Design (DDD)** principles with the following key components:

- **Entities**: Objects with identity that represent core business concepts
- **Value Objects**: Immutable objects representing descriptive aspects
- **Domain Services**: Stateless operations spanning multiple entities
- **Repositories**: Abstractions for data persistence and retrieval
- **Domain Events**: Events representing significant business occurrences

## 🏗️ Architecture Structure

```
domain/
├── __init__.py                 # Domain layer initialization
├── shared/                     # Shared domain concepts
│   ├── exceptions.py          # Domain exceptions
│   ├── events.py              # Base domain events
│   └── value_objects/         # Shared value objects
│
├── trading/                   # Trading domain
│   ├── __init__.py
│   ├── entities/             # Trading entities
│   │   ├── order.py         # Order aggregate
│   │   ├── position.py      # Position aggregate
│   │   └── portfolio.py     # Portfolio aggregate
│   ├── value_objects/        # Trading value objects
│   │   ├── symbol.py        # Trading symbol
│   │   ├── quantity.py      # Order quantity
│   │   ├── price.py         # Price values
│   │   └── order_status.py  # Order status enum
│   ├── services/             # Domain services
│   │   └── order_execution_service.py
│   └── repositories/         # Repository interfaces
│       ├── order_repository.py
│       └── position_repository.py
│
├── analytics/                 # Analytics domain
│   ├── entities/
│   │   ├── indicator.py      # Technical indicator
│   │   └── analysis.py       # Analysis results
│   ├── value_objects/
│   │   ├── statistics.py     # Statistical measures
│   │   └── signal_strength.py
│   └── services/
│       └── indicator_calculation_service.py
│
├── scanning/                  # Scanning domain
│   ├── entities/
│   │   ├── scan.py          # Market scan
│   │   └── rule.py          # Scanning rule
│   ├── value_objects/
│   │   ├── scan_criteria.py
│   │   └── rule_condition.py
│   └── services/
│       └── scan_execution_service.py
│
├── risk_management/          # Risk management domain
│   ├── entities/
│   │   ├── risk_profile.py   # Risk profile
│   │   └── risk_assessment.py
│   ├── value_objects/
│   │   ├── risk_limits.py    # Risk limits
│   │   └── risk_score.py     # Risk scoring
│   └── services/
│       └── risk_assessment_service.py
│
└── broker_integration/       # Broker integration domain
    ├── entities/
    │   ├── broker_connection.py
    │   └── broker_account.py
    ├── value_objects/
    │   ├── broker_credentials.py
    │   └── order_execution_params.py
    └── services/
        └── broker_connection_service.py
```

## 🎯 Core Domain Concepts

### Entities

Entities are objects with **identity** that represent core business concepts. They:

- Have a unique identity that persists through time
- Encapsulate business logic and rules
- Maintain consistency boundaries
- Can reference other entities and value objects

#### Example: Order Entity

```python
@dataclass
class Order:
    """Trading order aggregate root."""

    id: OrderId
    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    quantity: Quantity
    price: Optional[Price] = None
    status: OrderStatus = OrderStatus.PENDING

    # Business logic methods
    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled."""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]

    def add_fill(self, fill_quantity: Quantity, fill_price: Price) -> None:
        """Add a partial fill to the order."""
        if fill_quantity > self.remaining_quantity:
            raise DomainException("Fill quantity exceeds remaining quantity")

        self.filled_quantity += fill_quantity
        self.status = OrderStatus.PARTIALLY_FILLED

        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
```

### Value Objects

Value objects are **immutable** objects that represent descriptive aspects of the domain. They:

- Have no identity of their own
- Are compared by value, not identity
- Are immutable (cannot be changed after creation)
- Can contain validation logic

#### Example: Price Value Object

```python
@dataclass(frozen=True)
class Price:
    """Price value object with validation."""

    value: Decimal

    def __post_init__(self):
        """Validate price value."""
        if self.value <= 0:
            raise DomainException("Price must be positive")
        if self.value >= 1000000:  # Reasonable upper bound
            raise DomainException("Price exceeds maximum allowed value")

    def __add__(self, other: 'Price') -> 'Price':
        """Add two prices."""
        return Price(self.value + other.value)

    def __mul__(self, factor: Decimal) -> 'Price':
        """Multiply price by factor."""
        return Price(self.value * factor)
```

### Domain Services

Domain services contain business logic that doesn't naturally belong to an entity or value object. They:

- Are stateless
- Operate on multiple domain objects
- Contain complex business logic
- Are named with verbs (e.g., `OrderExecutionService`)

#### Example: Order Execution Service

```python
class OrderExecutionService:
    """Domain service for order execution logic."""

    def validate_order(self, order: Order, account_balance: Money) -> List[str]:
        """Validate order before execution."""
        violations = []

        # Check sufficient funds
        if order.side == OrderSide.BUY:
            required_amount = order.quantity.value * order.price.value
            if account_balance.amount < required_amount:
                violations.append("Insufficient funds")

        # Check position limits
        if order.symbol in restricted_symbols:
            violations.append(f"Symbol {order.symbol} is restricted")

        return violations

    def calculate_execution_price(self, order: Order, market_conditions: Dict) -> Price:
        """Calculate expected execution price based on market conditions."""
        base_price = order.price or self.get_market_price(order.symbol)

        # Apply slippage based on market volatility
        volatility = market_conditions.get('volatility', 0.0)
        slippage = base_price.value * volatility * 0.01

        if order.side == OrderSide.BUY:
            return Price(base_price.value + slippage)
        else:
            return Price(base_price.value - slippage)
```

### Repositories

Repositories provide an abstraction over data persistence, allowing the domain to remain persistence-ignorant. They:

- Define interfaces in the domain layer
- Are implemented in the infrastructure layer
- Provide methods for finding, saving, and deleting aggregates
- Return domain objects, not data transfer objects

#### Example: Order Repository Interface

```python
class OrderRepository(ABC):
    """Abstract repository for Order aggregates."""

    @abstractmethod
    async def save(self, order: Order) -> None:
        """Save an order."""
        pass

    @abstractmethod
    async def find_by_id(self, order_id: OrderId) -> Optional[Order]:
        """Find order by ID."""
        pass

    @abstractmethod
    async def find_by_symbol(self, symbol: Symbol) -> List[Order]:
        """Find orders by symbol."""
        pass

    @abstractmethod
    async def find_by_status(self, status: OrderStatus) -> List[Order]:
        """Find orders by status."""
        pass

    @abstractmethod
    async def update(self, order: Order) -> None:
        """Update an existing order."""
        pass

    @abstractmethod
    async def delete(self, order_id: OrderId) -> None:
        """Delete an order."""
        pass
```

### Domain Events

Domain events represent significant business occurrences that other parts of the system might be interested in. They:

- Are immutable
- Contain all relevant information about what happened
- Are named in past tense (e.g., `OrderPlaced`, `TradeExecuted`)
- Can trigger side effects in other bounded contexts

#### Example: Domain Events

```python
@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Event raised when an order is placed."""
    order_id: OrderId
    symbol: Symbol
    quantity: Quantity
    price: Optional[Price]
    timestamp: datetime

@dataclass(frozen=True)
class OrderFilled(DomainEvent):
    """Event raised when an order is filled."""
    order_id: OrderId
    fill_quantity: Quantity
    fill_price: Price
    commission: Money
    timestamp: datetime

@dataclass(frozen=True)
class PositionUpdated(DomainEvent):
    """Event raised when a position is updated."""
    symbol: Symbol
    quantity_change: Quantity
    price: Price
    pnl_realized: Money
    timestamp: datetime
```

## 🔄 Domain Layer Patterns

### Aggregate Pattern

Aggregates are clusters of domain objects that are treated as a single unit. They:

- Have a root entity (aggregate root)
- Enforce consistency boundaries
- Control access to internal objects
- Maintain invariants across multiple objects

```python
class Order(AggregateRoot):
    """Order aggregate with fills."""

    def __init__(self, id: OrderId, symbol: Symbol, quantity: Quantity):
        super().__init__()
        self.id = id
        self.symbol = symbol
        self.quantity = quantity
        self.fills: List[OrderFill] = []

    def add_fill(self, fill: OrderFill) -> None:
        """Add a fill to the order."""
        # Validate business rules
        if fill.quantity > self.remaining_quantity:
            raise DomainException("Fill exceeds remaining quantity")

        self.fills.append(fill)

        # Update aggregate state
        if self.is_fully_filled:
            self.status = OrderStatus.FILLED
            self.add_domain_event(OrderFilled(self.id, fill.quantity, fill.price))
```

### Factory Pattern

Factories encapsulate complex object creation logic:

```python
class OrderFactory:
    """Factory for creating Order aggregates."""

    @staticmethod
    def create_market_order(symbol: Symbol, quantity: Quantity, side: OrderSide) -> Order:
        """Create a market order."""
        order_id = OrderId.generate()
        return Order(order_id, symbol, quantity, OrderType.MARKET, side)

    @staticmethod
    def create_limit_order(symbol: Symbol, quantity: Quantity,
                          side: OrderSide, limit_price: Price) -> Order:
        """Create a limit order."""
        order_id = OrderId.generate()
        return Order(order_id, symbol, quantity, OrderType.LIMIT, side, limit_price)
```

### Specification Pattern

Specifications define business rules that can be combined and reused:

```python
class OrderSpecification:
    """Specifications for order validation."""

    @staticmethod
    def has_sufficient_funds(order: Order, balance: Money) -> bool:
        """Check if account has sufficient funds."""
        if order.side == OrderSide.BUY:
            return balance.amount >= (order.quantity.value * order.price.value)
        return True

    @staticmethod
    def is_within_position_limits(order: Order, positions: List[Position]) -> bool:
        """Check if order is within position limits."""
        symbol_positions = [p for p in positions if p.symbol == order.symbol]
        total_exposure = sum(p.quantity.value for p in symbol_positions)
        return total_exposure + order.quantity.value <= MAX_POSITION_SIZE
```

## 🧪 Domain Layer Testing

### Unit Testing Entities

```python
def test_order_fill_validation():
    """Test order fill validation logic."""
    order = OrderFactory.create_market_order(Symbol("AAPL"), Quantity(100), OrderSide.BUY)

    # Valid fill
    fill = OrderFill(Quantity(50), Price(150.00))
    order.add_fill(fill)
    assert order.filled_quantity == Quantity(50)
    assert order.status == OrderStatus.PARTIALLY_FILLED

    # Invalid fill (exceeds remaining)
    with pytest.raises(DomainException):
        invalid_fill = OrderFill(Quantity(60), Price(150.00))
        order.add_fill(invalid_fill)
```

### Testing Value Objects

```python
def test_price_validation():
    """Test price value object validation."""
    # Valid price
    price = Price(150.50)
    assert price.value == Decimal('150.50')

    # Invalid prices
    with pytest.raises(DomainException):
        Price(0)  # Zero price

    with pytest.raises(DomainException):
        Price(-10)  # Negative price
```

### Testing Domain Services

```python
def test_order_validation_service():
    """Test order validation domain service."""
    service = OrderValidationService()
    order = OrderFactory.create_market_order(Symbol("AAPL"), Quantity(100), OrderSide.BUY)
    balance = Money(15000, Currency.USD)

    violations = service.validate_order(order, balance)
    assert len(violations) == 0  # Valid order

    # Test insufficient funds
    large_order = OrderFactory.create_market_order(Symbol("AAPL"), Quantity(1000), OrderSide.BUY)
    violations = service.validate_order(large_order, balance)
    assert "insufficient funds" in str(violations).lower()
```

## 🔒 Domain Layer Principles

### 1. Business Logic Encapsulation
All business rules and logic should be encapsulated within the domain layer:

```python
# ✅ Good: Business logic in domain
class Order:
    def can_be_modified(self) -> bool:
        return self.status not in [OrderStatus.FILLED, OrderStatus.CANCELLED]

# ❌ Bad: Business logic in application layer
def can_modify_order(order: Order) -> bool:
    return order.status not in ["filled", "cancelled"]
```

### 2. Persistence Ignorance
The domain layer should not depend on persistence mechanisms:

```python
# ✅ Good: Domain defines repository interface
class OrderRepository(ABC):
    @abstractmethod
    async def save(self, order: Order) -> None: pass

# ❌ Bad: Domain depends on database
class Order:
    def save_to_database(self, connection):
        connection.execute("INSERT INTO orders...")
```

### 3. Rich Domain Model
Entities should contain behavior, not just data:

```python
# ✅ Good: Rich domain model
class Order:
    def cancel(self) -> None:
        if not self.can_be_cancelled:
            raise DomainException("Order cannot be cancelled")
        self.status = OrderStatus.CANCELLED
        self.add_domain_event(OrderCancelled(self.id))

# ❌ Bad: Anemic domain model
class Order:
    def set_status(self, status: OrderStatus) -> None:
        self.status = status
```

### 4. Explicit Domain Concepts
Use domain-specific language and concepts:

```python
# ✅ Good: Domain concepts
@dataclass
class StopLossOrder(Order):
    stop_price: Price
    trailing: bool = False

# ❌ Bad: Generic concepts
@dataclass
class SpecialOrder(Order):
    special_price: float
    is_special: bool = False
```

## 📊 Domain Layer Metrics

### Code Quality Metrics
- **Cyclomatic Complexity**: Keep entity methods under 10
- **Class Size**: Entities should be < 300 lines
- **Method Length**: Business methods should be < 20 lines
- **Test Coverage**: Domain layer should have 90%+ coverage

### Performance Considerations
- **Entity Creation**: Keep entity constructors lightweight
- **Validation**: Cache expensive validation results
- **Event Publishing**: Publish events asynchronously when possible
- **Repository Queries**: Use efficient query patterns

## 🎯 Best Practices

### 1. **Ubiquitous Language**
Use consistent terminology across the domain:

```python
# Consistent naming
class OrderBook:
    def add_order(self, order: Order) -> None: pass
    def cancel_order(self, order_id: OrderId) -> None: pass
    def get_best_bid(self) -> Price: pass
    def get_best_ask(self) -> Price: pass
```

### 2. **Bounded Contexts**
Keep domain boundaries clear:

```python
# Trading context
class TradingOrder:
    def execute(self) -> None: pass

# Risk context
class RiskOrder:
    def assess_risk(self) -> RiskScore: pass

# Analytics context
class AnalyticsOrder:
    def calculate_metrics(self) -> OrderMetrics: pass
```

### 3. **Domain Event Storming**
Identify and model domain events:

```python
# Domain events for order lifecycle
OrderPlaced -> OrderSubmitted -> OrderPartiallyFilled -> OrderFilled
                -> OrderCancelled -> OrderExpired
```

### 4. **Context Mapping**
Document relationships between bounded contexts:

```python
# Context relationships
TRADING_CONTEXT (upstream)
    ↓ publishes events to
RISK_CONTEXT (downstream)
    ↓ shares data with
ANALYTICS_CONTEXT (downstream)
```

## 📚 Related Documentation

- [Application Layer](../application-layer.md) - How domain objects are orchestrated
- [Infrastructure Layer](../infrastructure-layer.md) - How domain objects are persisted
- [Testing Guide](../../testing/domain-testing.md) - Domain layer testing strategies
- [DDD Patterns](../../patterns/ddd-patterns.md) - Domain-Driven Design patterns

---

**The Domain Layer is the most critical part of the system - it contains the business logic that gives the application its value and competitive advantage.**