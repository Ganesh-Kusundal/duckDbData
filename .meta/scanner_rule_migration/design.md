# Technical Design — Scanner Rule-Based Migration

## Architecture Context
The current scanner architecture consists of multiple scanner classes (BreakoutScanner, CRPScanner, TechnicalScanner) with hardcoded SQL queries and business logic. The new rule-based system will centralize all scanner logic into a unified RuleEngine that dynamically interprets JSON rule definitions and executes them against the unified DuckDB database.

The system will follow a layered architecture:
- **Rule Layer**: JSON definitions and validation
- **Engine Layer**: Rule interpretation and execution
- **Database Layer**: Optimized query generation and execution
- **Integration Layer**: Backward compatibility with existing APIs

## Data Flow
1. **Rule Loading**: JSON rules loaded from files or database
2. **Rule Validation**: Syntax and semantic validation of rule definitions
3. **Query Generation**: Dynamic SQL query generation based on rule conditions
4. **Database Execution**: Optimized query execution with connection pooling
5. **Result Processing**: Signal generation with confidence scoring
6. **Performance Tracking**: Execution metrics and success rate monitoring

## Interfaces

### Rule Definition Schema
```json
{
  "rule_id": "breakout_volume_1.5x",
  "name": "Volume Breakout Scanner",
  "description": "Identifies breakouts with 1.5x volume",
  "rule_type": "breakout",
  "enabled": true,
  "priority": 10,
  "conditions": {
    "time_window": {
      "start": "09:35",
      "end": "10:30"
    },
    "volume_conditions": {
      "min_multiplier": 1.5,
      "comparison_period": 10
    },
    "price_conditions": {
      "min_move_pct": 0.02,
      "max_move_pct": 0.10
    },
    "technical_conditions": {
      "rsi_range": [30, 70],
      "macd_signal": "bullish"
    }
  },
  "actions": {
    "signal_type": "BUY",
    "confidence_calculation": "weighted_average",
    "risk_management": {
      "stop_loss_pct": 0.02,
      "take_profit_pct": 0.06,
      "max_position_size": 0.1
    }
  },
  "metadata": {
    "author": "quant_team",
    "created_at": "2025-09-08T10:00:00Z",
    "tags": ["breakout", "volume", "momentum"],
    "version": "1.0.0"
  }
}
```

### Rule Engine Interface
```python
class RuleEngine:
    def load_rules(self, rules: List[Dict]) -> bool
    def validate_rule(self, rule: Dict) -> ValidationResult
    def execute_rule(self, rule_id: str, context: ExecutionContext) -> List[TradingSignal]
    def get_rule_performance(self, rule_id: str) -> PerformanceMetrics
```

### Database Query Generation
```python
class QueryBuilder:
    def build_breakout_query(self, conditions: Dict) -> str
    def build_crp_query(self, conditions: Dict) -> str
    def build_technical_query(self, conditions: Dict) -> str
    def optimize_query(self, query: str, context: Dict) -> str
```

## Database Schema
The rule system will leverage the existing unified database schema:

- **market_data**: Core OHLCV data for all symbols
- **scanner_rules**: JSON rule definitions storage
- **rule_executions**: Execution history and performance tracking
- **trading_signals**: Generated signals with metadata

## Error Handling
- **ValidationError**: Invalid rule syntax or structure
- **ExecutionError**: Database query or processing failures
- **TimeoutError**: Rule execution exceeds time limits
- **ResourceError**: Database connection or memory issues

## Observability
- **Execution Metrics**: Query execution time, result count, success rate
- **Rule Performance**: Win rate, profit/loss ratio, drawdown analysis
- **System Health**: Memory usage, connection pool status, cache hit rates
- **Alerting**: Rule failures, performance degradation, anomalous behavior

## Performance Notes
- **Query Optimization**: Dynamic query generation with proper indexing
- **Connection Pooling**: Maintain persistent connections for frequent queries
- **Caching Strategy**: Cache compiled queries and rule validation results
- **Batch Processing**: Group similar rules for efficient database access
- **Expected Complexity**: O(n) for rule validation, O(m) for query execution where n=rule count, m=result count
