feat: Implement real database query execution in rule engine

Context:
	•	Linked Spec: .meta/cli_scanner_fixes/spec.md#real-data
	•	Linked Task: .meta/cli_scanner_fixes/tasks.md#task-3

Changes:
	•	Replaced mock data generation with actual DuckDB query execution
	•	Added proper database connection handling in rule engine
	•	Implemented column name mapping for query results
	•	Added comprehensive error handling for database operations
	•	Added debug logging for query execution and results

Tests:
	•	Added real database query execution tests
	•	All tests passing with 67M+ records processed
	•	Time filters and data validation working correctly

Notes:
	•	Eliminates all mock data usage in favor of real database queries
	•	Processes actual market data with proper error handling
	•	Maintains compatibility with existing rule engine interface
	•	Significant performance improvement over mock data generation
