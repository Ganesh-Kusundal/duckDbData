# Steering Notes (Trade Engine Integration)

## Coding Conventions
- **snake_case** for variables and functions
- **PascalCase** for classes and interfaces
- **Async/await** for all I/O operations
- **Type hints** required for all function signatures
- **Docstrings** with Args/Returns/Raises sections

## Tech Choices
- **Database**: DuckDB with UnifiedDuckDBManager for market data and telemetry
- **Query Engine**: Parquet scanning for efficient historical data access
- **Scanner Integration**: Existing scanner infrastructure for algorithm implementation
- **Data Access**: Optimized queries for backtesting performance
- **Async Framework**: asyncio for concurrent data processing
- **Testing**: pytest with real DuckDB data validation (no mocks)

## Do / Don't Rules
- ✅ **DO** use actual DuckDB market data for all testing and validation
- ✅ **DO** integrate with existing scanner infrastructure for algorithm implementation
- ✅ **DO** optimize DuckDB queries for backtesting performance
- ✅ **DO** implement comprehensive error handling and logging
- ✅ **DO** follow ports/adapters pattern for clean architecture
- ✅ **DO** use async/await for database operations
- ✅ **DO** validate all inputs and handle edge cases
- ❌ **DON'T** use mock data or synthetic test data - use real DuckDB data
- ❌ **DON'T** hardcode database credentials or sensitive information
- ❌ **DON'T** implement blocking operations in async functions
- ❌ **DON'T** skip error handling for database connection issues
- ❌ **DON'T** couple business logic with database-specific implementations
- ❌ **DON'T** bypass existing scanner infrastructure
- ❌ **DON'T** ignore query optimization opportunities

## Glossary
- **Signal**: Trading signal from scanner algorithm with entry/exit instructions
- **Scanner**: Algorithm implementation for generating trading signals from market data
- **Backtest**: Historical simulation of trading strategy using past market data
- **Query Optimization**: Process of improving DuckDB query performance for large datasets
- **Data Validation**: Process of ensuring market data quality and integrity
- **Connection Pooling**: Database connection management for efficient resource usage
- **Parquet Scanning**: Efficient data access method for compressed columnar data
- **Algorithm Layer**: Integration layer between scanners and trading strategies

## Open Decisions
- [ ] **Query Caching Strategy**: Should we implement query result caching for frequently accessed data?
- [ ] **Scanner Parallelization**: How to handle multiple scanner algorithms running concurrently?
- [ ] **Data Partitioning**: Should we implement data partitioning strategies for large historical datasets?
- [ ] **Performance Monitoring**: What metrics should we track for database and scanner performance?
- [ ] **Configuration Management**: How to handle environment-specific database and scanner configurations?

## Architecture Principles
- **Clean Architecture**: Strict separation of concerns with ports/adapters
- **DDD**: Domain models at center, external concerns at edges
- **SOLID**: Single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion
- **Event-Driven**: Async processing with proper error handling and recovery
- **Observable**: Comprehensive telemetry for monitoring and debugging

## Performance Targets
- **Query Execution**: < 2 seconds for 500-stock universe queries
- **Data Processing**: < 500ms per scanner execution on typical datasets
- **Memory Usage**: < 1GB during backtesting operations
- **System Uptime**: > 99.5% during backtesting operations
- **Error Recovery**: < 10 seconds for database connection recovery

## Security Considerations
- **Database Credentials**: Environment variables for database connection strings
- **Data Security**: Secure handling of market data and trading signals
- **Access Control**: Role-based access for database and scanner operations
- **Query Validation**: SQL injection prevention and query sanitization
- **Audit Trail**: Complete logging of database operations and scanner executions

## Operational Requirements
- **Monitoring**: Real-time dashboards with database and scanner performance metrics
- **Alerting**: Alerts for database connectivity issues and scanner failures
- **Backup**: Automated DuckDB database backups with point-in-time recovery
- **Maintenance**: Regular query optimization and data integrity checks
- **Scaling**: Support for multiple concurrent backtesting operations
