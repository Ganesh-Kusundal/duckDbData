# Steering Notes (Data Verification and Integration)

## Coding Conventions
- Naming: snake_case for functions/variables, PascalCase for classes
- Testing: pytest with descriptive test names, integration tests preferred over unit tests
- Documentation: Google-style docstrings, comprehensive error messages
- Error Handling: Custom exceptions with context, graceful degradation

## Tech Choices
- Database: DuckDB for analytical workloads and real-time data access
- Testing: pytest with real data integration (no mocking)
- Architecture: Clean Architecture with domain/infrastructure separation
- Data Processing: pandas for data manipulation, DuckDB for queries

## Do / Don't Rules
- ✅ DO: Use real database connections and data for all verification
- ✅ DO: Implement comprehensive error handling and logging
- ✅ DO: Follow existing architectural patterns in src/ and analytics/
- ✅ DO: Write integration tests that verify end-to-end functionality
- ❌ DON'T: Use mocking or fake data for verification purposes
- ❌ DON'T: Bypass existing domain services or repositories
- ❌ DON'T: Create tight coupling between analytics and domain layers
- ❌ DON'T: Expose sensitive data in logs or test outputs

## Glossary
- **Data Verification**: Process of ensuring data integrity and consistency across modules
- **Cross-Module Consistency**: Ensuring analytics and domain layers work with same data
- **Unified Data Access**: Consistent patterns for accessing data across different modules
- **Real-Time Verification**: Continuous validation of streaming data operations
- **Health Checks**: Automated monitoring of system data integrity

## Open Decisions
- [ ] Should we implement caching for frequently accessed verification results?
- [ ] How to handle verification failures in production vs development environments?
- [ ] Whether to implement alerting system for data quality issues?
- [ ] Performance thresholds for different types of verification checks

## Current Architecture Decisions
- Data verification service acts as bridge between analytics and domain layers
- All verification uses real database connections and actual data
- Integration tests validate cross-module functionality
- Error handling provides detailed context without exposing sensitive information

## Risk Mitigation Strategies
- Database connection failures: Implement retry logic with exponential backoff
- Large dataset performance: Use streaming and pagination for data processing
- Schema changes: Validate compatibility before deployment
- Memory usage: Monitor and limit resource consumption during verification

## Performance Benchmarks
- Basic connectivity check: < 5 seconds
- Schema validation: < 30 seconds for typical datasets
- Cross-module consistency: < 2 minutes for comprehensive checks
- Parquet integration: < 10 seconds for file discovery and access

## Testing Strategy
- Integration tests over unit tests where possible
- Real data usage instead of mocking
- Performance regression tests for critical paths
- Error scenario testing with proper cleanup

