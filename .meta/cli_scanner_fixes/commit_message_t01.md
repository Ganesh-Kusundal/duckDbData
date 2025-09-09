feat: Fix CLI time parameter conversion for scanner commands

Context:
	•	Linked Spec: .meta/cli_scanner_fixes/spec.md#time-conversion
	•	Linked Task: .meta/cli_scanner_fixes/tasks.md#task-1

Changes:
	•	Enhanced time parameter validation in CLI scanner commands
	•	Added proper HH:MM format validation with range checking
	•	Improved error messages for invalid time formats
	•	Added debug logging for time conversion process

Tests:
	•	Added comprehensive time conversion tests
	•	All tests passing with proper validation

Notes:
	•	Fixes 'str' object has no attribute 'strftime' errors
	•	Maintains backward compatibility with existing CLI usage
	•	No breaking changes to existing scanner interfaces
