# Trading Domain

The Trading domain handles order management, position tracking, and trade execution for the financial trading system.

## Overview

This bounded context is responsible for:
- Order lifecycle management (creation, submission, execution, cancellation)
- Position tracking and P&L calculations
- Trading signal processing and order generation
- Risk management integration
- Trade execution coordination

## Domain Model

### Core Entities

#### Order
Represents a trading order with its complete lifecycle:
- Order types: Market, Limit, Stop, Stop-Limit
- Order sides: Buy, Sell
- Status tracking: Pending, Submitted, Partially Filled, Filled, Cancelled, Rejected
- Fill management and average price calculation

#### Position
Tracks portfolio positions with P&L calculations:
- Position quantity and average price
- Real-time P&L (realized and unrealized)
- Trade history tracking
- Market value calculations

### Value Objects

#### TradingStrategy
Defines trading strategy parameters:
- Strategy types (Breakout, Momentum, Mean Reversion, etc.)
- Risk parameters (position size, stop loss, take profit)
- Execution parameters (Market, Limit, Stop orders)

#### TradingSignal
Represents signals from scanning systems:
- Signal types (BUY, SELL, HOLD)
- Confidence levels
- Price targets and metadata

### Domain Services

#### OrderExecutionService
Handles order execution business logic:
- Order validation and submission
- Signal-to-order conversion
- Position updates from fills
- Business rule enforcement

## Repository Interfaces

### OrderRepository
Data access interface for orders:
- CRUD operations for orders
- Query by status, symbol, date range
- Order lifecycle tracking

### PositionRepository
Data access interface for positions:
- CRUD operations for positions
- Portfolio summary and P&L calculations
- Batch price updates

## Business Rules

1. **Order Validation**: Orders must have valid symbols, positive quantities, and appropriate prices
2. **Position Limits**: Cannot sell more than current position
3. **Risk Management**: Orders must comply with strategy risk parameters
4. **Fill Processing**: Fills update positions and calculate P&L correctly

## Integration Points

- **Market Data**: Receives real-time price updates for P&L calculations
- **Scanning**: Processes trading signals to generate orders
- **Risk Management**: Validates orders against risk limits
- **Broker Integration**: Sends orders for execution and receives fills

## Usage Examples

### Creating and Executing an Order

```python
from domain.trading import Order, OrderId, OrderType, OrderSide, Symbol, Quantity, Price
from domain.trading.services import OrderExecutionService

# Create an order
order = Order(
    id=OrderId.generate(),
    symbol=Symbol("AAPL"),
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=Quantity(100)
)

# Execute the order
execution_service = OrderExecutionService(order_repo, position_repo)
executed_order = execution_service.execute_order(order)
```

### Processing a Trading Signal

```python
from domain.trading.value_objects import TradingSignal

signal = TradingSignal(
    symbol="AAPL",
    signal_type="BUY",
    confidence=0.85,
    price=150.00,
    strategy_id=strategy_id
)

order = execution_service.process_signal(signal)
```

## Testing

The domain includes comprehensive unit tests covering:
- Entity validation and business rules
- Domain service orchestration
- Repository interface contracts
- Value object immutability and validation

## Future Enhancements

1. **Advanced Order Types**: Support for options, futures, and complex order types
2. **Portfolio Optimization**: Integration with portfolio management strategies
3. **Multi-Asset Support**: Support for different asset classes beyond equities
4. **Real-time Execution**: Integration with high-frequency trading systems

