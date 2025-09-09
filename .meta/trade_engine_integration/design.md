# Technical Design — Trade Engine DuckDB Integration & Scanner Implementation

## Architecture Context
The trade engine follows a clean architecture pattern with DDD principles. The current implementation provides a solid foundation with ports/adapters separation. This design extends the existing architecture to support efficient DuckDB data access and scanner integration for algorithm implementation and backtesting.

```
┌─────────────────────────────────────────────────────────────┐
│                    Strategy Runner                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            Ports & Adapters Layer                      │ │
│  │  ┌─────────────┬─────────────┬─────────────┬──────────┐ │ │
│  │  │ DataFeedPort│ScannerPort  │ DBManager   │Repository│ │ │
│  │  │             │             │ Port        │          │ │ │
│  │  └─────────────┴─────────────┴─────────────┴──────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Adapters Implementation                    │ │
│  │  ┌─────────────┬─────────────┬─────────────┬──────────┐ │ │
│  │  │ DuckDBData  │ Scanner     │ UnifiedDB   │ DuckDB   │ │ │
│  │  │ Feed        │ Adapter     │ Manager     │ Repository│ │ │
│  │  │ Enhanced    │ Integration │ Adapter     │          │ │ │
│  │  └─────────────┴─────────────┴─────────────┴──────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Systems                         │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐ │
│  │ DuckDB      │ Scanner     │ Backtest    │ Telemetry  │ │
│  │ Database    │ System      │ Engine      │ Dashboard  │ │
│  │ Unified     │ Integration │             │            │ │
│  └─────────────┴─────────────┴─────────────┴─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Enhanced Backtest Mode (DuckDB-Optimized)
```
1. Market Data Request → UnifiedDuckDBManager → Connection Pooling
2. Optimized Query → Parquet Data Access → Data Retrieval
3. Data Validation → Quality Checks → Clean Data
4. Scanner Integration → Algorithm Processing → Signal Generation
5. Strategy Runner → Backtest Execution → Results Generation
6. Performance Metrics → Telemetry Storage → Analytics Dashboard
```

### DuckDB Integration Flow
```
Trading Application → UnifiedDuckDBManager → Database Connection
                              ↓
                    Query Optimization → Efficient Retrieval
                              ↓
                Data Processing → Format Conversion
                              ↓
            Scanner System → Algorithm Execution
                              ↓
                Signal Processing → Strategy Implementation
                              ↓
                Backtest Results → Performance Analysis
```

## Interfaces

### DuckDBDataAccessPort (New)
```python
class DuckDBDataAccessPort:
    async def connect_to_database(self, config: Dict[str, Any]) -> bool
    async def execute_market_data_query(self, query: str, params: Dict[str, Any]) -> pd.DataFrame
    async def get_available_symbols(self, date_range: Optional[Tuple[str, str]] = None) -> List[str]
    async def validate_data_integrity(self, symbol: str, date: str) -> DataValidationResult
    async def optimize_query_performance(self, query: str) -> OptimizedQuery
```

### ScannerIntegrationPort (New)
```python
class ScannerIntegrationPort:
    async def load_scanner_algorithm(self, scanner_name: str) -> ScannerAlgorithm
    async def execute_scanner_on_data(self, algorithm: ScannerAlgorithm, data: pd.DataFrame) -> List[TradingSignal]
    async def validate_scanner_output(self, signals: List[TradingSignal]) -> ValidationResult
    async def get_scanner_performance_metrics(self, scanner_name: str) -> ScannerMetrics
    async def update_scanner_parameters(self, scanner_name: str, params: Dict[str, Any]) -> bool
```

### QueryOptimizationPort (New)
```python
class QueryOptimizationPort:
    async def analyze_query_performance(self, query: str) -> QueryAnalysis
    async def generate_optimized_query(self, original_query: str, constraints: Dict[str, Any]) -> str
    async def validate_query_results(self, query: str, expected_schema: Dict[str, str]) -> ValidationResult
    async def cache_frequent_queries(self, query_patterns: List[str]) -> CacheConfiguration
```

### LiveDataFeedPort Extension
```python
class LiveDataFeedPort(DataFeedPort):
    async def connect_websocket(self, url: str) -> None
    async def subscribe_symbols(self, symbols: List[str]) -> None
    async def handle_reconnection(self) -> None
    async def get_realtime_bar(self, symbol: str) -> Bar
```

### Integration Interfaces
```python
class ScannerIntegrationPort:
    async def poll_scanner_signals(self) -> List[Signal]
    async def acknowledge_signal(self, signal_id: str) -> None
    async def get_scanner_status(self) -> ScannerStatus
```

## Database Schema

### Enhanced market_data table
```sql
CREATE TABLE market_data (
    symbol VARCHAR,
    timestamp TIMESTAMP,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    trading_date DATE,
    sector VARCHAR,
    -- Live trading extensions
    bid_price DECIMAL(10,2),
    ask_price DECIMAL(10,2),
    bid_qty INTEGER,
    ask_qty INTEGER,
    last_traded_price DECIMAL(10,2),
    last_traded_qty INTEGER
);
```

### Backtesting telemetry and scanner data
```sql
CREATE TABLE backtest_runs (
    run_id VARCHAR PRIMARY KEY,
    algorithm_name VARCHAR,
    scanner_used VARCHAR,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    symbols_tested INTEGER,
    total_signals INTEGER,
    profitable_signals INTEGER,
    total_return DECIMAL(8,4),
    max_drawdown DECIMAL(6,4),
    sharpe_ratio DECIMAL(6,4),
    execution_time_seconds INTEGER,
    config_snapshot JSON
);

CREATE TABLE scanner_signals (
    signal_id VARCHAR PRIMARY KEY,
    scanner_name VARCHAR,
    symbol VARCHAR,
    signal_type VARCHAR,  -- 'BUY', 'SELL', 'HOLD'
    entry_price DECIMAL(10,2),
    target_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    confidence_score DECIMAL(3,2),
    timestamp TIMESTAMP,
    backtest_run_id VARCHAR,
    executed BOOLEAN DEFAULT FALSE,
    execution_price DECIMAL(10,2),
    exit_price DECIMAL(10,2),
    pnl DECIMAL(8,2)
);

CREATE TABLE data_quality_metrics (
    symbol VARCHAR,
    date DATE,
    total_records INTEGER,
    valid_records INTEGER,
    missing_data_pct DECIMAL(5,2),
    outlier_count INTEGER,
    data_quality_score DECIMAL(3,2),
    last_updated TIMESTAMP,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE query_performance (
    query_id VARCHAR PRIMARY KEY,
    query_type VARCHAR,  -- 'market_data', 'scanner_data', 'backtest_data'
    execution_time_ms INTEGER,
    records_returned INTEGER,
    query_complexity VARCHAR,
    optimization_applied BOOLEAN,
    timestamp TIMESTAMP,
    user_id VARCHAR
);

CREATE TABLE scanner_performance (
    scanner_name VARCHAR,
    backtest_run_id VARCHAR,
    total_signals INTEGER,
    profitable_signals INTEGER,
    win_rate DECIMAL(5,2),
    avg_profit DECIMAL(8,2),
    avg_loss DECIMAL(8,2),
    profit_factor DECIMAL(6,2),
    max_consecutive_losses INTEGER,
    timestamp TIMESTAMP,
    PRIMARY KEY (scanner_name, backtest_run_id)
);
```

## Error Handling

### Circuit Breaker Pattern
```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenException()

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
```

### Error Categories
- **Network Errors**: WebSocket disconnections, API timeouts
- **Authentication Errors**: Token expiry, invalid credentials
- **Order Errors**: Insufficient funds, invalid quantities, market closed
- **Data Errors**: Missing symbols, invalid price data
- **System Errors**: Database connection issues, memory constraints

## Observability

### Metrics Collection
```python
@dataclass
class TradingMetrics:
    order_latency_ms: Histogram
    signal_processing_time: Histogram
    execution_success_rate: Counter
    position_pnl: Gauge
    system_uptime: Gauge
    websocket_reconnections: Counter
```

### Logging Structure
```json
{
  "timestamp": "2025-01-20T10:30:45Z",
  "level": "INFO",
  "component": "DhanBroker",
  "operation": "place_order",
  "symbol": "RELIANCE",
  "order_id": "DHAN_12345",
  "latency_ms": 245,
  "status": "SUCCESS"
}
```

## Performance Notes

### Latency Optimization
- **WebSocket Connection Pooling**: Maintain persistent connections
- **Async Processing**: Non-blocking order execution and data processing
- **Caching Layer**: Redis for frequently accessed market data
- **Batch Processing**: Group small orders for efficiency

### Memory Management
- **Data Windowing**: Keep only recent market data in memory
- **Object Pooling**: Reuse order and signal objects
- **Garbage Collection**: Explicit cleanup of historical data

### Expected Performance Targets
- **Order Execution**: < 500ms from signal to API
- **Data Processing**: < 100ms per bar processing
- **Memory Usage**: < 512MB during normal operation
- **CPU Usage**: < 20% during market hours
