# Steering Notes (DuckDB Performance Optimization)

## Coding Conventions
- Naming: Use `fast_` prefix for performance-optimized classes/functions
- Performance: All database operations must have timeout parameters
- Logging: Use structured logging with `performance_mode` field
- Testing: Performance tests must include baseline comparisons

## Tech Choices
- DB: DuckDB with connection pooling for development mode
- Caching: In-memory LRU cache for prepared statements
- Monitoring: Lightweight metrics collection without external dependencies
- Configuration: Environment-based mode switching (FAST_MODE=1)

## Do / Don't Rules
- ✅ Always measure performance impact before/after changes
- ✅ Use connection pooling for repeated database operations
- ✅ Skip complex validations in development mode
- ✅ Cache query results for read-heavy operations
- ❌ Don't remove production safety checks
- ❌ Don't cache write operations
- ❌ Don't use global state for connection management
- ❌ Don't add external performance monitoring dependencies

## Glossary
- "Fast Mode": Development mode with minimal validations for speed
- "Standard Mode": Production mode with full validations
- "Connection Pool": Reusable database connections to avoid overhead
- "Essential Checks": Minimal validations required for basic functionality

## Open Decisions
- [ ] Should we implement query result caching with TTL?
- [ ] Should connection pool size be configurable per environment?
- [ ] Should we add performance profiling for all database operations?

