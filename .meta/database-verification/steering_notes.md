# Steering Notes — Database and Test Verification

## Coding Conventions & Style
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Testing**: pytest framework with descriptive test names
- **Error Handling**: Proper exception handling with context
- **Documentation**: Inline comments and docstrings for complex operations

## Tech Choices & Rationale
- **Database**: DuckDB - Chosen for excellent performance with large datasets
- **Testing Framework**: pytest - Standard Python testing framework
- **Data Validation**: Pydantic models for type safety and validation
- **Query Language**: SQL - Standard for database operations

## Do / Don't Rules
- ✅ **Do**: Verify database connectivity before operations
- ✅ **Do**: Test data integrity constraints
- ✅ **Do**: Validate performance benchmarks
- ✅ **Do**: Handle errors gracefully with proper logging
- ❌ **Don't**: Skip data validation checks
- ❌ **Don't**: Ignore performance degradation
- ❌ **Don't**: Use hardcoded database paths
- ❌ **Don't**: Suppress important error messages

## Domain Glossary
- **OHLCV**: Open, High, Low, Close, Volume - Standard financial data format
- **Market Data**: Time-series financial instrument data
- **Symbol**: Financial instrument identifier (e.g., AAPL, RELIANCE)
- **Timeframe**: Data aggregation period (1m, 1H, 1D)
- **Date Partition**: Database partitioning by date for performance

## Open Decisions / TODOs / Debt
- [ ] **Settings Configuration**: Clean up YAML config files to match Pydantic models
- [ ] **Schema Alignment**: Align domain entities with actual database schema
- [ ] **Enhanced Monitoring**: Add database health monitoring and alerting
- [ ] **Performance Regression Tests**: Implement automated performance regression testing
- [ ] **Documentation**: Update API documentation for new features

## Technical Debt Identified
1. **Import Path Issues**: Relative imports in database module cause confusion
2. **Configuration Complexity**: Settings system has validation strictness issues
3. **Schema Documentation**: Database schema changes not well documented
4. **Test Data Management**: Large test datasets need better management

## Performance Benchmarks Established
- **Count Query**: < 0.015s for 67M records (current: 0.010s)
- **Aggregation Query**: < 0.25s for grouped operations (current: 0.197s)
- **Memory Usage**: < 100MB for 100k record operations (current: 78.9MB)
- **Concurrent Operations**: Support for multiple simultaneous connections

## Lessons Learned
1. **Database Performance**: DuckDB excels with analytical workloads
2. **Data Integrity**: Strict constraints prevent data quality issues
3. **Testing Strategy**: Integration tests are crucial for system validation
4. **Error Handling**: Comprehensive error handling improves reliability
5. **Performance Monitoring**: Regular benchmarking prevents degradation
