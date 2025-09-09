# Technical Design — Fix Minor Issues

## Architecture Context
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  YAML Configs   │────│ Settings System │────│  Domain Models  │
│                 │    │  (Pydantic)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Database Schema │
                    │   (DuckDB)      │
                    └─────────────────┘
```

The fixes address configuration validation and schema alignment to ensure consistent data flow from YAML configs through Pydantic models to database operations.

## Data Flow
1. Input: YAML configuration files and database schema
2. Processing:
   - Parse YAML files with proper validation
   - Load settings into Pydantic models
   - Validate domain entities against database schema
   - Update import paths and dependencies
3. Output: Clean, validated configuration and aligned schemas

## Interfaces
- Function: `validate_yaml_configs() -> ValidationResult`
- Function: `align_domain_schema() -> AlignmentResult`
- Function: `fix_import_paths() -> ImportResult`
- CLI: `python scripts/fix_issues.py --config --schema`

## Database Schema
Current schema analysis:
- **market_data**: symbol, timestamp, open, high, low, close, volume, date_partition, industry
- **symbols**: symbol, name, sector, industry, exchange, first_date, last_date, total_records, created_at, updated_at
- **scanner_results**: id, scanner_name, symbol, timestamp, signals, execution_time_ms, success, error_message, created_at

Domain entities to align:
- MarketData: Remove timeframe field or add to database
- Symbol: Ensure all fields match database columns
- ScannerResult: Verify JSON handling compatibility

## Error Handling
- Case: YAML validation error → Log specific validation issues, suggest fixes
- Case: Schema mismatch → Identify field differences, provide migration options
- Case: Import resolution failure → Check PYTHONPATH, suggest dependency fixes

## Observability
- Logs: Configuration loading attempts, schema alignment results, import resolutions
- Metrics: Validation success rate, schema alignment coverage, import resolution time
- Debug flags: VERBOSE_CONFIG_LOADING, DETAILED_SCHEMA_DIFF

## Performance Notes
- Expected complexity: O(n) where n is number of config files/entities
- Memory usage: Minimal additional overhead for validation
- Import time: Should not significantly impact application startup
