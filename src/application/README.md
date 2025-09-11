# Application Layer - CQRS Implementation

## Overview

The Application Layer implements the CQRS (Command Query Responsibility Segregation) pattern to provide a clean separation between write operations (Commands) and read operations (Queries). This layer orchestrates domain operations across all bounded contexts while maintaining clear architectural boundaries.

## CQRS Architecture

### Core Components

#### Commands
Commands represent write operations that change the application state. They are:
- **Immutable**: Once created, commands cannot be modified
- **Descriptive**: Contain all necessary information for execution
- **Idempotent**: Multiple executions of the same command should produce the same result

#### Queries
Queries represent read operations that retrieve data without modifying state. They are:
- **Side-effect free**: Do not modify application state
- **Composable**: Can be combined and filtered
- **Optimizable**: Can be cached and optimized for performance

#### Command Handlers
Command handlers execute commands and orchestrate domain operations:
- **Transactional**: Ensure atomicity of operations
- **Domain-focused**: Delegate to appropriate domain services
- **Event-generating**: Produce domain events on successful execution

#### Query Handlers
Query handlers retrieve and format data for presentation:
- **Read-optimized**: Use appropriate data access patterns
- **Projection-based**: Return data in consumer-friendly formats
- **Cacheable**: Support caching for performance

## Domain Coverage

### Trading Domain
**Commands:**
- `SubmitOrderCommand` - Submit new trading orders
- `CancelOrderCommand` - Cancel existing orders
- `ModifyOrderCommand` - Modify order parameters
- `ClosePositionCommand` - Close trading positions
- `CreateTradingStrategyCommand` - Create trading strategies

**Queries:**
- `GetOrderByIdQuery` - Retrieve order details
- `GetOrdersBySymbolQuery` - Get orders by symbol
- `GetPortfolioSummaryQuery` - Portfolio overview
- `GetTradingHistoryQuery` - Historical trading data
- `GetPositionByIdQuery` - Position details

### Analytics Domain
**Commands:**
- `CalculateIndicatorCommand` - Calculate technical indicators
- `ExecuteAnalysisCommand` - Run market analysis
- `CreateAnalysisTemplateCommand` - Create analysis templates

**Queries:**
- `GetIndicatorByIdQuery` - Indicator details
- `GetAnalysisByIdQuery` - Analysis results
- `GetTechnicalSignalsQuery` - Trading signals

### Scanning Domain
**Commands:**
- `ExecuteMarketScanCommand` - Execute market scans
- `ExecuteRuleCommand` - Execute scanning rules
- `CreateScanningRuleCommand` - Create scanning rules

**Queries:**
- `GetScanByIdQuery` - Scan results
- `GetScanResultsQuery` - Detailed scan data
- `GetScanningRuleByIdQuery` - Rule details

### Risk Management Domain
**Commands:**
- `AssessPortfolioRiskCommand` - Risk assessment
- `UpdateRiskLimitsCommand` - Update risk limits
- `CreateRiskProfileCommand` - Create risk profiles

**Queries:**
- `GetRiskAssessmentByIdQuery` - Risk assessment details
- `GetRiskLimitsQuery` - Current risk limits
- `GetRiskBreachesQuery` - Risk limit breaches

### Broker Integration Domain
**Commands:**
- `EstablishBrokerConnectionCommand` - Connect to brokers
- `SubmitBrokerOrderCommand` - Submit orders via broker
- `SyncAccountDataCommand` - Sync account data

**Queries:**
- `GetBrokerConnectionByIdQuery` - Connection details
- `GetBrokerAccountsQuery` - Account information
- `GetBrokerOrdersQuery` - Broker orders

## Usage Examples

### Trading Operations

```python
from application.services.trading_application_service import TradingApplicationService

trading_service = TradingApplicationService()

# Submit a market order
result = await trading_service.submit_market_order(
    symbol="AAPL",
    side="BUY",
    quantity=100
)

# Get portfolio summary
portfolio = await trading_service.get_portfolio_summary()

# Cancel an order
cancel_result = await trading_service.cancel_order("order_123")
```

### Analytics Operations

```python
from application.cqrs_registry import execute_command, execute_query
from application.commands.analytics_commands import CalculateIndicatorCommand
from application.queries.analytics_queries import GetIndicatorByIdQuery

# Calculate RSI indicator
command = CalculateIndicatorCommand(
    symbol="AAPL",
    timeframe="1D",
    indicator_name="rsi",
    parameters={"period": 14}
)

result = await execute_command(command)

# Get indicator values
query = GetIndicatorByIdQuery(indicator_id=result.data["indicator_id"])
indicator_data = await execute_query(query)
```

## CQRS Registry

The `CQRSRegistry` provides centralized management of all commands and queries:

```python
from application.cqrs_registry import get_cqrs_registry

registry = get_cqrs_registry()

# Check available handlers
commands = registry.get_registered_commands()
queries = registry.get_registered_queries()

# Execute operations
result = await registry.execute_command(command)
data = await registry.execute_query(query)
```

## Handler Implementation

### Command Handler Example

```python
from application.commands.base_command import CommandHandler, CommandResult
from application.commands.trading_commands import SubmitOrderCommand

class SubmitOrderCommandHandler(CommandHandler):

    @property
    def handled_command_type(self) -> str:
        return "SubmitOrder"

    async def handle(self, command: SubmitOrderCommand) -> CommandResult:
        # Validate command
        # Execute domain logic
        # Save to repository
        # Return result

        return CommandResult(
            success=True,
            command_id=command.command_id,
            data={"order_id": "order_123"}
        )
```

### Query Handler Example

```python
from application.queries.base_query import QueryHandler, QueryResult
from application.queries.trading_queries import GetOrderByIdQuery

class GetOrderByIdQueryHandler(QueryHandler):

    @property
    def handled_query_type(self) -> str:
        return "GetOrderById"

    async def handle(self, query: GetOrderByIdQuery) -> QueryResult:
        # Retrieve data from repository
        # Format for presentation
        # Return result

        return QueryResult(
            success=True,
            query_id=query.query_id,
            data={"order_details": {...}}
        )
```

## Benefits

### Separation of Concerns
- **Commands**: Handle write operations and business logic
- **Queries**: Handle read operations and data retrieval
- **Handlers**: Orchestrate domain operations

### Performance Optimization
- **Command optimization**: Focus on consistency and reliability
- **Query optimization**: Focus on speed and caching
- **Independent scaling**: Commands and queries can scale separately

### Maintainability
- **Clear interfaces**: Well-defined command and query contracts
- **Testability**: Commands and queries can be tested independently
- **Extensibility**: Easy to add new operations without affecting existing code

### Domain Alignment
- **Ubiquitous Language**: Commands and queries use domain terminology
- **Business Logic**: Handlers implement domain rules and workflows
- **Event Sourcing**: Commands generate events for audit and replay

## Error Handling

The CQRS implementation includes comprehensive error handling:

- **Command Validation**: Commands are validated before execution
- **Domain Exceptions**: Domain rules are enforced with clear error messages
- **Transactional Consistency**: Command handlers ensure atomic operations
- **Query Resilience**: Queries gracefully handle missing data

## Testing

The CQRS layer includes comprehensive testing:

- **Unit Tests**: Test individual handlers and commands
- **Integration Tests**: Test command/query execution end-to-end
- **Mock Repositories**: Enable testing without external dependencies
- **Performance Tests**: Validate query performance and optimization

## Future Enhancements

- **Event Sourcing**: Add event store for audit trail and replay
- **Saga Pattern**: Implement distributed transactions across domains
- **Query Optimization**: Add query result caching and optimization
- **Monitoring**: Add metrics and monitoring for command/query performance
- **API Gateway**: Create unified API layer over CQRS operations