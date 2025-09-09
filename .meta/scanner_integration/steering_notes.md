# Steering Notes — Scanner Integration with Unified DuckDB Layer

## Coding Conventions
- Naming: snake_case for variables, PascalCase for classes
- Error handling: Use custom scanner exceptions extending unified layer errors
- Logging: Structured logging with scanner-specific context information
- Documentation: Comprehensive docstrings with Args/Returns/Raises for all scanner methods

## Tech Choices
- **Database Layer**: Unified DuckDB manager for all scanner operations
- **Connection Management**: Shared connection pool with scanner-specific segment
- **Configuration**: Scanner configs extend unified layer configs
- **Caching**: Optional result caching for performance optimization
- **Monitoring**: Integrated with unified layer observability

## Do / Don't Rules
- ✅ **Do** use the unified manager for all scanner database operations
- ✅ **Do** leverage connection pooling for consistent performance
- ✅ **Do** handle scanner errors through unified error handling
- ✅ **Do** cache frequently accessed scanner results when beneficial
- ❌ **Don't** create direct DuckDB connections in scanner code
- ❌ **Don't** hardcode scanner database paths or configurations
- ❌ **Don't** bypass unified layer for performance reasons
- ❌ **Don't** ignore connection cleanup in scanner operations

## Glossary
- **Scanner Read Adapter**: Interface for scanner data access operations
- **Unified Scanner Adapter**: Implementation using unified DuckDB manager
- **Scanner Strategy**: Algorithm implementation for specific scan types (CRP, Breakout, etc.)
- **Scanner Result Cache**: In-memory cache for frequently accessed scan results
- **Scanner Metrics**: Performance and usage statistics for scanner operations

## Open Decisions
- [ ] Should we implement result caching by default or make it optional?
- [ ] Should we add query result pagination for large scanner result sets?
- [ ] Should we implement scanner query parallelization for multiple symbols?
- [ ] Should we add scanner-specific connection pool isolation?

## Implementation Notes
- **Backward Compatibility**: Existing scanner APIs should continue to work unchanged
- **Performance**: Scanner queries should leverage unified layer optimizations
- **Resource Management**: Scanner operations should not impact other database users
- **Error Handling**: Scanner-specific errors should provide clear context for debugging
- **Configuration**: Scanner settings should be easily configurable without code changes

## Success Metrics
- ✅ All existing scanner tests pass with unified layer
- ✅ Scanner query performance improved by 15%+
- ✅ Connection pool utilization remains optimal during scanner operations
- ✅ Zero scanner-related connection leaks in production
- ✅ Scanner error handling provides clear debugging information
- ✅ Configuration changes apply without service restart

## Risk Mitigation
- **Performance Regression**: Comprehensive benchmarking before and after migration
- **Breaking Changes**: Maintain backward compatibility through facade patterns
- **Resource Contention**: Monitor connection pool usage and implement limits if needed
- **Configuration Complexity**: Provide clear migration guides and examples
