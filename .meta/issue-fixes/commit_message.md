fix: resolve all minor issues in DuckDB financial system

Context:
• Linked Spec: .meta/issue-fixes/spec.md
• Linked Design: .meta/issue-fixes/design.md
• Linked Tasks: .meta/issue-fixes/tasks.md

Changes:
• Fix settings configuration YAML validation errors by allowing extra fields
• Align domain entities with database schema by making timeframe optional
• Resolve import path resolution issues with absolute imports
• Correct schema configuration access in database adapters
• Maintain backward compatibility for all existing functionality

fix(config): enable flexible YAML configuration loading

• Add extra='allow' to all Pydantic settings models
• Update DatabaseSettings, LoggingSettings, ScannerSettings, BrokerSettings
• Update DataSyncSettings, ValidationSettings, APISettings, MonitoringSettings
• Update CacheSettings, SecuritySettings for configuration flexibility
• Enable loading of additional YAML fields without validation errors

fix(schema): align domain entities with database schema

• Make timeframe field optional in MarketData and MarketDataBatch classes
• Update validation logic to handle optional timeframe values
• Maintain proper field ordering for Python dataclass requirements
• Preserve backward compatibility for existing code using timeframe

fix(imports): resolve module import path issues

• Update database adapters to use absolute imports from src module
• Fix relative import resolution in duckdb_adapter.py
• Correct import paths in duckdb_market_repo.py
• Ensure consistent import patterns across all modules

fix(schema): correct database adapter schema configuration access

• Update database adapter to use correct field name (db_schema)
• Fix schema configuration loading from YAML files
• Enable proper schema initialization and table creation
• Resolve schema-related import and configuration issues

Tests:
• Import validation tests: ✅ PASSED
• Settings configuration tests: ✅ PASSED
• Domain entity compatibility tests: ✅ PASSED
• Database adapter functionality tests: ✅ PASSED
• End-to-end integration tests: ✅ PASSED
• All tests passing ✅

Notes:
• Backward compatibility maintained for all existing code
• No breaking changes introduced
• Performance impact minimal (potential import optimization benefits)
• Configuration flexibility improved for future extensions
• Schema alignment enables better database compatibility
