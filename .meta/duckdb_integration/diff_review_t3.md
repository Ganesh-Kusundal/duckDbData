# Diff Review — Task 3 (Update Scanner Factory)

## Summary
- **What changed:** Updated scanner factory and related files to use unified database path
- **Why:** Link to SPEC.md (US-02) and DESIGN.md (Unified database path usage)

## Diff
```diff
src/infrastructure/config/settings.py
- path: str = Field(default="financial_data.duckdb")
+ path: str = Field(default="data/financial_data.duckdb")

src/infrastructure/core/singleton_database.py
- def __init__(self, db_path: str = "/Users/apple/Downloads/duckDbData/data/financial_data.duckdb",
- def create_db_manager(db_path: str = "/Users/apple/Downloads/duckDbData/data/financial_data.duckdb",
- def get_db_manager(db_path: str = "/Users/apple/Downloads/duckDbData/data/financial_data.duckdb",

+ def __init__(self, db_path: str = "data/financial_data.duckdb",
+ def create_db_manager(db_path: str = "data/financial_data.duckdb",
+ def get_db_manager(db_path: str = "data/financial_data.duckdb",

src/application/infrastructure/di_container.py
- db_path="/Users/apple/Downloads/duckDbData/data/financial_data.duckdb",
+ db_path="data/financial_data.duckdb",

src/application/scanners/backtests/optimization_engine.py
- def __init__(self, db_path: str = "../data/financial_data.duckdb",
- parser.add_argument('--db-path', default='../data/financial_data.duckdb',
+ def __init__(self, db_path: str = "data/financial_data.duckdb",
+ parser.add_argument('--db-path', default='data/financial_data.duckdb',

src/application/scanners/backtests/simple_optimizer.py
- def __init__(self, db_path: str = "../data/financial_data.duckdb",
- parser.add_argument('--db-path', default='../data/financial_data.duckdb',
+ def __init__(self, db_path: str = "data/financial_data.duckdb",
+ parser.add_argument('--db-path', default='data/financial_data.duckdb',
```

Tests
	•	Added: tests/test_scanner_factory_unified_db.py with 6 test cases
	•	Results: ✅ All tests passing

Risks & Notes
	•	Migration impact: Low - only path changes
	•	Follow-ups: Verify all scanner implementations work with unified path
