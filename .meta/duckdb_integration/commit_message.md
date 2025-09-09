feat: Unify DuckDB integration and verify scanner functionality

## Context
- Linked Spec: .meta/duckdb_integration/spec.md
- Linked Task: .meta/duckdb_integration/tasks.md

## Changes
- Updated database configuration files to use unified `data/financial_data.duckdb` path
- Fixed hardcoded database paths in scanner factory, settings, and DI container
- Created database verification script with fallback options for locked files
- Added comprehensive test suite for configuration, scanner factory, and adapters
- Verified scanner adapter interfaces and dataframe conversion functionality

## Tests
- Added tests/test_config_unified_db.py (3 tests, all passing)
- Added tests/test_scanner_factory_unified_db.py (6 tests, all passing)
- Added tests/test_scanner_adapter_unified_db.py (6 tests, all passing)
- Added scripts/verify_database_connection.py for database verification
- All tests pass with proper mocking to avoid database lock conflicts

## Notes
- Database file verified: 8.4GB at data/financial_data.duckdb
- Configuration unified across all components
- Scanner factory properly injects unified database path
- Scanner adapters maintain proper interface compliance
- No breaking changes to existing functionality