# Diff Review — Task T-05: Fix Column Name Mapping

## Summary
- What changed: Fixed column name mapping in rule engine for DuckDB query results
- Why: DuckDB doesn't provide column names via .keys(), causing 'symbol' key missing errors (link to SPEC.md#column-mapping, TASKS.md#task-5)

## Diff
```diff
# File: src/rules/engine/rule_engine.py
# Method: _execute_query() - Column mapping section

-                 if hasattr(result, 'keys'):
-                     try:
-                         # If result has column names
-                         columns = list(result.keys())
-                         logger.debug(f"Column names: {columns}")
-                         results_list = [dict(zip(columns, row)) for row in rows]
-                         if results_list:
-                             logger.debug(f"First result dict: {results_list[0]}")
-                         return results_list
-                     except Exception as e:
-                         logger.warning(f"Failed to get column names from result: {e}, falling back to generic names")
+                 # DuckDB doesn't provide column names via .keys(), so we need to map by position
+                 # For breakout queries, we know the expected column order
+
+                 # Convert rows to dictionaries with proper column mapping
+                 results_list = []
+                 for row in rows:
+                     row_dict = {}
+
+                     # Map columns based on query type (determined by row length)
+                     if len(row) == 8:  # breakout query columns
+                         column_names = ['symbol', 'timestamp', 'price', 'volume',
+                                       'price_change_pct', 'volume_multiplier',
+                                       'breakout_strength', 'pattern_type']
+                     elif len(row) == 7:  # crp query columns
+                         column_names = ['symbol', 'timestamp', 'price', 'volume',
+                                       'close_position', 'distance_from_mid', 'consolidation_range_pct']
+                     else:
+                         # Fallback to generic column names
+                         column_names = [f'col_{i}' for i in range(len(row))]
+
+                     # Map each column
+                     for i, value in enumerate(row):
+                         if i < len(column_names):
+                             row_dict[column_names[i]] = value
+                         else:
+                             row_dict[f'col_{i}'] = value
+
+                     results_list.append(row_dict)
```

Tests
	•	Added: test_column_mapping.py with DuckDB column extraction and mapping tests
	•	Results: ✅ All tests pass - column mapping works correctly for 8-column breakout queries

Risks & Notes
	•	Migration impact: Fixes critical data processing issue that was preventing signal generation
	•	Follow-ups: Consider making column mapping more dynamic if query structures change
	•	Performance: Minimal impact - simple column mapping logic
