feat: Fix column name mapping for DuckDB query results

Context:
	•	Linked Spec: .meta/cli_scanner_fixes/spec.md#column-mapping
	•	Linked Task: .meta/cli_scanner_fixes/tasks.md#task-5

Changes:
	•	Fixed column name mapping in rule engine for DuckDB query results
	•	Replaced .keys() method calls with position-based column mapping
	•	Added proper column name assignment for breakout and CRP queries
	•	Improved error handling for column extraction failures
	•	Added debug logging for column mapping process

Tests:
	•	Added comprehensive column mapping tests
	•	All tests passing with proper 8-column breakout query mapping

Notes:
	•	Fixes 'symbol' key missing errors in signal generation
	•	Enables proper processing of real database query results
	•	DuckDB-specific fix for column name extraction
	•	Maintains compatibility with existing query structures
