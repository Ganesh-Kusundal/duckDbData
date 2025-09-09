# Requirements Document

## Introduction

This feature enhances the existing DuckDB financial infrastructure to efficiently query parquet data files stored in a structured directory format. The system needs to handle thousands of parquet files organized by date and symbol (e.g., `/Users/apple/Downloads/duckDbData/frontend/src/data/2025/09/04/TCS_minute_2025-09-04.parquet`) and provide fast, reliable access to this time-series financial data for trading analysis and backtesting.

## Requirements

### Requirement 1

**User Story:** As a financial analyst, I want to query parquet data files directly from the structured directory without importing them into DuckDB, so that I can access the latest data without data duplication and storage overhead.

#### Acceptance Criteria

1. WHEN a user queries data for a specific symbol and date range THEN the system SHALL automatically locate and read the corresponding parquet files from the directory structure
2. WHEN parquet files are organized in the format `/path/YYYY/MM/DD/SYMBOL_minute_YYYY-MM-DD.parquet` THEN the system SHALL parse the directory structure to identify relevant files
3. WHEN querying multiple symbols or date ranges THEN the system SHALL efficiently read multiple parquet files in parallel
4. IF a requested parquet file does not exist THEN the system SHALL return an empty result set without throwing errors

### Requirement 2

**User Story:** As a trading system developer, I want the parquet querying to integrate seamlessly with the existing DuckDB infrastructure, so that I can use the same connection patterns and query interfaces.

#### Acceptance Criteria

1. WHEN the system queries parquet data THEN it SHALL use the existing DuckDB connection management and lock handling mechanisms (re-using `get_settings().database.*` and read-only flags)
2. WHEN parquet queries are executed THEN they SHALL respect the same timeout and retry logic as regular database queries
3. WHEN both parquet and database queries are needed THEN the system SHALL allow joining data from both sources in a single query
4. IF database locks occur during parquet queries THEN the system SHALL apply the same lock resolution strategies (read-only access + isolated copies when needed)

### Requirement 3

**User Story:** As a system administrator, I want the parquet querying to be performant and memory-efficient, so that it can handle thousands of files without impacting system performance.

#### Acceptance Criteria

1. WHEN querying large date ranges THEN the system SHALL implement lazy loading to avoid loading unnecessary data into memory
2. WHEN multiple concurrent queries access parquet files THEN the system SHALL optimize file access to prevent resource contention
3. WHEN querying specific time ranges THEN the system SHALL use parquet file metadata to skip irrelevant files
4. IF memory usage exceeds thresholds THEN the system SHALL implement streaming or chunked processing

### Requirement 4

**User Story:** As a developer, I want a unified query interface that can handle both database tables and parquet files, so that I can write queries without worrying about the underlying data storage format.

#### Acceptance Criteria

1. WHEN writing queries THEN developers SHALL be able to reference parquet data using table-like syntax via a unified view `market_data_unified`
2. WHEN the unified view is present THEN scanners and analytics SHALL transparently read both on-disk DuckDB tables and parquet files
3. WHEN combining database and parquet data THEN the system SHALL provide transparent joins and unions through `market_data_unified`
4. IF schema mismatches occur between parquet files THEN the system SHALL handle them gracefully with appropriate error messages

### Requirement 5

**User Story:** As a financial data analyst, I want to query historical minute-level data efficiently across multiple symbols and date ranges, so that I can perform comprehensive backtesting and analysis.

#### Acceptance Criteria

1. WHEN querying minute-level data for backtesting THEN the system SHALL support date range filters that span multiple months
2. WHEN analyzing multiple symbols THEN the system SHALL support wildcard or list-based symbol selection
3. WHEN performing time-series analysis THEN the system SHALL maintain proper chronological ordering of data
4. IF data gaps exist in the parquet files THEN the system SHALL provide options to handle missing data (skip, interpolate, or flag)

### Requirement 6

**User Story:** As a system operator, I want comprehensive monitoring and diagnostics for parquet file access, so that I can troubleshoot performance issues and ensure data integrity.

#### Acceptance Criteria

1. WHEN parquet queries are executed THEN the system SHALL log query performance metrics including file count and read times
2. WHEN file access errors occur THEN the system SHALL provide detailed error messages with file paths and error types
3. WHEN the system starts up THEN it SHALL validate the parquet directory structure and report any inconsistencies
4. IF parquet files are corrupted or unreadable THEN the system SHALL log warnings and continue processing other files

## Implementation Notes

- Parquet directory structure: `/Users/apple/Downloads/duckDbData/frontend/src/data/YYYY/MM/DD/SYMBOL_minute_YYYY-MM-DD.parquet`
- Settings additions (env-prefixed `DUCKDB_`):
  - `database.parquet_root` (str | null): root of parquet tree
  - `database.parquet_glob` (str | null): override glob; default `root/*/*/*/*.parquet`
  - `database.use_parquet_in_unified_view` (bool): default true
  - `database.enable_object_cache` (bool): default true
  - `database.enable_profiling` (bool): default false
- Unified view: `market_data_unified = market_data UNION ALL read_parquet(glob, filename=true)` with schema: `symbol, timestamp, open, high, low, close, volume, timeframe('1m' default), date_partition`
- Performance: `SET threads`, `SET enable_object_cache=true`; DuckDB will parallelize parquet scans and prune by filters (pushdown)
- Locking: read-only mode is respected; parquet scans do not write to DB; isolation strategies unchanged

## Adoption Plan (Code Touchpoints)

- `database/adapters/duckdb_adapter.py: get_connection`: set performance flags; create unified view if configured
- `database/adapters/duckdb_adapter.py: execute_parquet_query`: use `read_parquet` and support globs
- `src/infrastructure/adapters/scanner_read_adapter.py`: prefer `market_data_unified` when present; fallback to `market_data`
- `src/infrastructure/config/settings.py`: new settings fields for parquet root/glob and toggles

No changes required to ingestion: direct parquet querying avoids duplication. Existing scanners and analytics continue to work; once the unified view is present, they automatically include parquet data without code changes.
