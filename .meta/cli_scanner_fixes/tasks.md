# Task Plan — CLI Scanner Fixes & Integration

## Task 1: Fix Time Parameter Conversion
- **Goal:** Ensure CLI time strings are properly converted to datetime.time objects
- **Changes:** Modify `src/interfaces/cli/commands/scanners.py` time parameter handling
- **Tests:** Add unit tests for time conversion functions
- **Commands:** `python -c "from datetime import time; print(time.fromisoformat('09:50'))"`
- **Exit Criteria:** Time strings convert to datetime.time objects without errors
- **Risks:** Potential format validation issues with edge cases

## Task 2: Fix Result Processing Data Types
- **Goal:** Ensure scanner results are properly handled as lists, not DataFrames
- **Changes:** Update `src/interfaces/cli/commands/scanners.py` result processing logic
- **Tests:** Add tests for list vs DataFrame result handling
- **Commands:** Test with various result formats
- **Exit Criteria:** No 'list' object has no attribute 'empty' errors
- **Risks:** Breaking changes to result display formatting

## Task 3: Implement Real Database Query Execution
- **Goal:** Replace mock data with actual DuckDB query execution
- **Changes:** Update `src/rules/engine/rule_engine.py` _execute_query method
- **Tests:** Integration tests with real database queries
- **Commands:** `python cli.py scanners run --scanner-type breakout --date 2024-11-14`
- **Exit Criteria:** Queries execute against real database and return actual market data
- **Risks:** Performance impact with large datasets

## Task 4: Fix Database Connection Integration
- **Goal:** Ensure rule engine has proper database connection
- **Changes:** Update `src/app/startup.py` connection injection logic
- **Tests:** Test database connection establishment and reuse
- **Commands:** Verify connection pool initialization
- **Exit Criteria:** Rule engine successfully connects to database without errors
- **Risks:** Connection pool exhaustion with concurrent usage

## Task 5: Fix Column Name Mapping
- **Goal:** Ensure query results have proper column names for signal generation
- **Changes:** Update column mapping logic in rule engine
- **Tests:** Test result processing with various column structures
- **Commands:** Execute queries and verify column mapping
- **Exit Criteria:** No 'symbol' key missing errors in signal generation
- **Risks:** Inconsistent column naming across different query types

## Task 6: Fix Import Path Issues
- **Goal:** Resolve all module import errors in CLI components
- **Changes:** Update import statements in CLI and rule engine files
- **Tests:** Test module loading in various environments
- **Commands:** `python -c "import src.interfaces.cli.commands.scanners"`
- **Exit Criteria:** All CLI modules import successfully without errors
- **Risks:** Path resolution issues in different deployment environments

## Task 7: Add Comprehensive Error Handling
- **Goal:** Implement robust error handling throughout the CLI pipeline
- **Changes:** Add try-catch blocks and error logging in critical paths
- **Tests:** Test error scenarios and recovery mechanisms
- **Commands:** Test with invalid inputs and network issues
- **Exit Criteria:** All error conditions handled gracefully with clear messages
- **Risks:** Over-logging potentially impacting performance

## Task 8: Validate End-to-End Functionality
- **Goal:** Ensure complete CLI scanner workflow works with real data
- **Changes:** Integration testing of full scanner execution pipeline
- **Tests:** End-to-end tests with real market data
- **Commands:** `python cli.py scanners run --scanner-type breakout --date 2024-11-14 --limit 5`
- **Exit Criteria:** Full scanner execution completes successfully with real trading signals
- **Risks:** Database lock conflicts in multi-user environments
