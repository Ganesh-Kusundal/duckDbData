# Technical Design — DuckDB Integration & Scanner Verification

## Architecture Context
The system uses a Domain-Driven Design (DDD) architecture with clear separation between domain, application, and infrastructure layers. The database integration needs to ensure all components use the unified `data/financial_data.duckdb` database while maintaining clean interfaces and proper dependency injection.

## Data Flow
1. **Input**: Database path `data/financial_data.duckdb`, scanner configurations
2. **Processing**:
   - Configuration validation and unification
   - Scanner factory initialization with unified database path
   - Scanner execution with proper port injection
   - Result persistence and error handling
3. **Output**: Verified scanner results, unified database connections, comprehensive test reports

## Interfaces
- **DuckDBAnalytics**: `execute_analytics_query(query: str, **params) -> pd.DataFrame`
- **ScannerFactory**: `create_scanner(name: str, config: Dict) -> IBaseScanner`
- **ScannerService**: `run_scanner_date_range(scanner, start_date, end_date) -> List[Dict]`
- **UnifiedDuckDBManager**: `persistence_query(query: str) -> pd.DataFrame`

## Database Schema
Current schema includes:
- **market_data**: symbol, timestamp, open, high, low, close, volume, timeframe
- **symbols**: symbol, name, sector, industry, exchange
- **scanner_results**: scanner_name, symbol, timestamp, signals, execution_time_ms

## Error Handling
- **DatabaseConnectionError**: Raised when database connection fails
- **ScannerExecutionError**: Raised when scanner fails to execute
- **ConfigurationError**: Raised when configuration is invalid
- **Fallback mechanisms**: Retry logic with exponential backoff

## Observability
- **Logs**: Database connection status, scanner execution times, error details
- **Metrics**: Query execution time, scanner success rate, database connection pool stats
- **Health checks**: Database connectivity, scanner availability, configuration validation

## Performance Notes
- Expected complexity: O(1) for database connections, O(n) for scanner execution
- Connection pooling: Maintain up to 10 concurrent connections
- Caching: Enable DuckDB object cache for repeated queries
- Memory limits: 2GB per connection to handle 8.4GB dataset efficiently