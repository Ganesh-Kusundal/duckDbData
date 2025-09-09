# Technical Design — Scanner Integration with Unified DuckDB Layer

## Architecture Context
The scanner integration will leverage the existing unified DuckDB infrastructure while maintaining scanner-specific optimizations and configurations. The design follows these principles:

- **Unified Resource Management**: All scanner database operations use the shared connection pool
- **Scanner-Specific Query Optimization**: Maintain scanner query patterns optimized for time-series analysis
- **Configuration Inheritance**: Scanner configs extend unified layer configs with scanner-specific settings
- **Error Handling Consistency**: Scanner errors follow unified layer error handling patterns
- **Monitoring Integration**: Scanner operations are tracked through unified layer monitoring

## Data Flow
1. **Scanner Request**: Scanner API receives scan request with parameters
2. **Configuration Resolution**: Scanner config merged with unified layer config
3. **Connection Acquisition**: Connection obtained from unified pool
4. **Query Execution**: Scanner-specific queries executed through unified QueryExecutor
5. **Result Processing**: Results processed and formatted by scanner logic
6. **Resource Cleanup**: Connection automatically returned to unified pool

## Interfaces

### Enhanced ScannerReadPort
```python
class UnifiedScannerReadPort(ScannerReadPort):
    """Scanner read operations using unified DuckDB layer."""

    def __init__(self, unified_manager: UnifiedDuckDBManager):
        self.unified_manager = unified_manager

    def get_crp_candidates(self, scan_date, cutoff_time, config, max_results):
        # Uses unified_manager.analytics_query() with scanner-optimized query
        pass

    def get_end_of_day_prices(self, symbols, scan_date, end_time):
        # Uses unified_manager.persistence_query() for EOD data
        pass

    def get_breakout_candidates(self, scan_date, cutoff_time, config, max_results):
        # Uses unified_manager.analytics_query() with breakout logic
        pass
```

### Scanner Configuration Integration
```python
@dataclass
class ScannerConfig:
    """Scanner-specific configuration extending unified config."""
    unified_config: DuckDBConfig
    scanner_cache_enabled: bool = True
    scanner_query_timeout: float = 30.0
    scanner_result_cache_ttl: int = 300
    scanner_parallel_queries: int = 3
```

## Database Schema
Scanner operations utilize the unified schema with scanner-specific optimizations:

- **market_data_unified** view: Primary data source for scanner queries
- **scanner_results** table: Stores scan results with performance metrics
- **scanner_cache** table: Optional result caching for repeated queries
- **scanner_metrics** table: Performance and usage tracking

## Error Handling
Scanner-specific errors extend unified layer errors:

- **ScannerQueryError**: Query execution failures with scanner context
- **ScannerConfigError**: Configuration validation failures
- **ScannerTimeoutError**: Query timeout specific to scanner operations
- **ScannerResourceError**: Resource exhaustion during scanner operations

## Observability
Scanner operations are monitored through:

- **Query Performance**: Execution time, row count, memory usage
- **Connection Pool Stats**: Pool utilization during scanner operations
- **Error Metrics**: Scanner-specific error rates and patterns
- **Cache Hit Rates**: Result cache effectiveness (if enabled)

## Performance Notes
- **Connection Pool Optimization**: Scanner queries use dedicated pool segment
- **Query Result Caching**: Frequently accessed scanner results cached in memory
- **Parallel Query Execution**: Multiple scanner types can run concurrently
- **Memory Management**: Scanner result sets managed through unified memory limits
- **Expected Complexity**: O(n) for scanner queries with n being time-series data points
