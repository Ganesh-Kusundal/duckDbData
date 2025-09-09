feat: Fix CLI result processing for list-based scanner results

Context:
	•	Linked Spec: .meta/cli_scanner_fixes/spec.md#result-processing
	•	Linked Task: .meta/cli_scanner_fixes/tasks.md#task-2

Changes:
	•	Updated CLI to handle scanner results as lists instead of DataFrames
	•	Removed DataFrame.empty calls that caused 'list' object has no attribute 'empty' errors
	•	Added proper list validation and DataFrame conversion for display
	•	Improved result processing robustness

Tests:
	•	Added comprehensive result processing tests
	•	All tests passing with proper list handling

Notes:
	•	Fixes result processing errors in CLI scanner commands
	•	Maintains backward compatibility with existing result display
	•	No breaking changes to scanner interfaces
