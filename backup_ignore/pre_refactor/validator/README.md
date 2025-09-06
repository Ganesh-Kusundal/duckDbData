# Data Validation Scripts

This directory contains comprehensive validation scripts for ensuring data integrity and quality in the DuckDB database.

## validate_intraday_data.py

**COMPREHENSIVE VALIDATION SCRIPT** - A thorough validator for intraday market data that performs multiple validation checks to ensure data correctness and integrity.

### Features

- ✅ **Data Integrity Validation**: Checks for duplicates, proper table structure
- ✅ **Data Completeness**: Validates expected number of records per symbol
- ✅ **Data Quality**: Ensures proper OHLCV values and logical consistency
- ✅ **Symbol Coverage**: Validates coverage against available symbols
- ✅ **Time Range Validation**: Checks timestamps and trading hours
- ✅ **Comprehensive Reporting**: Detailed validation summary with pass/fail status
- ✅ **Production Ready**: Handles large datasets efficiently

### Validation Checks Performed

#### 1. Data Integrity
- **Duplicate Detection**: Identifies duplicate records by symbol and timestamp
- **Table Structure**: Verifies all required columns are present
- **Data Types**: Ensures proper data types for all fields

#### 2. Data Completeness
- **Record Count**: Validates expected number of records per symbol (375 for full trading day)
- **Symbol Coverage**: Ensures data exists for expected symbols
- **Statistical Analysis**: Provides min/max/average record counts

#### 3. Data Quality
- **OHLCV Validation**: Checks for invalid price/volume values (≤ 0)
- **Logical Consistency**: Ensures high ≥ open, low ≤ open, etc.
- **Price Range Analysis**: Identifies extreme values that may need verification

#### 4. Symbol Coverage
- **Coverage Percentage**: Calculates percentage of available symbols with data
- **Missing Symbols**: Identifies symbols without data
- **Extra Symbols**: Finds symbols with data but not in available list

#### 5. Time Range Validation
- **Date Verification**: Ensures all timestamps are for the correct date
- **Trading Hours**: Validates timestamps are within expected market hours (9:15 AM - 3:30 PM)
- **Time Gaps**: Detects large gaps in time series data

### Usage

#### Basic Usage (Validate Today's Data)
```bash
# Validate today's intraday data
python validator/validate_intraday_data.py

# Or run directly (if executable)
./validator/validate_intraday_data.py
```

#### Advanced Usage
```bash
# Validate specific date
python validator/validate_intraday_data.py --date 2025-09-05

# Custom database path
python validator/validate_intraday_data.py --db-path /path/to/database.duckdb

# Debug logging
python validator/validate_intraday_data.py --log-level DEBUG
```

#### Production Usage
```bash
# Validate with custom database and date
PYTHONPATH=/path/to/project python validator/validate_intraday_data.py \
    --db-path data/financial_data.duckdb \
    --date 2025-09-05 \
    --log-level INFO
```

### Command Line Options

- `--db-path`: Path to DuckDB database file (default: data/financial_data.duckdb)
- `--date`: Date to validate (YYYY-MM-DD format, default: today)
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Validation Results

The script provides detailed validation results with clear pass/fail indicators:

```
🎯 STARTING COMPREHENSIVE DATA VALIDATION
============================================================
🔍 VALIDATING DATA INTEGRITY
----------------------------------------
✅ No duplicate records found
✅ Table structure is correct

📊 VALIDATING DATA COMPLETENESS
----------------------------------------
✅ Data completeness statistics:
   📊 Total records: 180,750
   📊 Unique symbols: 482
   📊 Average records per symbol: 375
   📊 Records range: 375 - 375
✅ Data completeness is satisfactory

🔬 VALIDATING DATA QUALITY
----------------------------------------
✅ No invalid OHLCV values found
✅ No logical OHLC inconsistencies found
✅ Price range validation:
   📊 Min price: ₹1.05
   📊 Max price: ₹8,999.00
   📊 Avg price: ₹1,234.56

📈 VALIDATING SYMBOL COVERAGE
----------------------------------------
📊 Available symbols in database: 487
📊 Symbols with today's data: 482
📊 Coverage: 99.0%
✅ Symbol coverage is excellent

⏰ VALIDATING TIME RANGES
----------------------------------------
✅ Time range validation:
   🕐 Earliest timestamp: 2025-09-05 09:15:00
   🕐 Latest timestamp: 2025-09-05 15:29:00
✅ All timestamps are for the correct date
✅ Timestamps are within expected trading hours

📋 VALIDATION SUMMARY
============================================================
🎯 OVERALL RESULTS:
   ✅ Passed: 8
   ⚠️  Warnings: 2
   ❌ Failed: 0
   📊 Total checks: 10
   📊 Success rate: 80.0%
🎉 VALIDATION STATUS: EXCELLENT
   Data integrity and quality are outstanding!
============================================================
```

### Validation Status Levels

- **🎉 EXCELLENT**: No failures, ≤2 warnings - Data is outstanding
- **✅ GOOD**: No failures, >2 warnings - Data is acceptable
- **⚠️ NEEDS ATTENTION**: Has failures - Review errors and fix issues

### Dependencies

- pandas
- duckdb
- pathlib
- logging
- datetime

### Integration with Existing Codebase

This validator is designed to work seamlessly with:
- DuckDB infrastructure (`DuckDBManager`)
- Existing data sync scripts
- Broker integration modules
- Logging and error handling patterns

### Example Validation Output

**Successful Validation:**
```
🎉 VALIDATION STATUS: EXCELLENT
   Data integrity and quality are outstanding!
```

**Validation with Warnings:**
```
✅ VALIDATION STATUS: GOOD
   Data is acceptable with minor warnings
```

**Validation with Errors:**
```
⚠️ VALIDATION STATUS: NEEDS ATTENTION
   Some validation checks failed - please review errors above
```

### Files in This Directory

- `validate_intraday_data.py` - **MAIN VALIDATION SCRIPT**
- `README.md` - This documentation file

### Best Practices

1. **Run After Data Sync**: Always validate data immediately after syncing
2. **Monitor Warnings**: Even passing validations may have warnings to review
3. **Check Coverage**: Ensure symbol coverage meets your requirements
4. **Review Extreme Values**: Investigate any extreme price values flagged
5. **Verify Time Ranges**: Confirm timestamps are within expected trading hours

### Exit Codes

- `0`: Validation successful (no critical failures)
- `1`: Validation failed (critical issues found)

This allows integration with CI/CD pipelines and automated monitoring systems.
