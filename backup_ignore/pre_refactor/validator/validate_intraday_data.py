#!/usr/bin/env python3
"""
Comprehensive Data Validation Script for Intraday Data
Validates the correctness and integrity of data inserted into DuckDB.

This script performs multiple validation checks:
- Data integrity (no duplicates, proper timestamps)
- Data completeness (all expected records)
- Data quality (proper OHLCV values)
- Symbol coverage validation
- Time range validation
"""

import os
import sys
import datetime
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.duckdb_infra.database import DuckDBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataValidator:
    """Comprehensive validator for intraday data integrity."""

    def __init__(self, db_path: str = "data/financial_data.duckdb"):
        """
        Initialize the validator.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_manager = DuckDBManager(db_path=db_path)
        self.today = datetime.date.today()
        self.validation_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'errors': []
        }

        logger.info(f"🧪 Initialized DataValidator for {self.today}")

    def run_all_validations(self) -> Dict:
        """
        Run all validation checks.

        Returns:
            Dictionary with validation results
        """
        logger.info("🎯 STARTING COMPREHENSIVE DATA VALIDATION")
        logger.info("=" * 60)

        # Run all validation checks
        self.validate_data_integrity()
        self.validate_data_completeness()
        self.validate_data_quality()
        self.validate_symbol_coverage()
        self.validate_time_ranges()

        # Generate summary
        self.generate_validation_summary()

        return self.validation_results

    def validate_data_integrity(self):
        """Validate data integrity - no duplicates, proper structure."""
        logger.info("🔍 VALIDATING DATA INTEGRITY")
        logger.info("-" * 40)

        try:
            # Check for duplicates
            duplicates_query = '''
            SELECT symbol, timestamp, COUNT(*) as count
            FROM market_data
            WHERE date_partition = ?
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
            '''

            duplicates = self.db_manager.execute_custom_query(duplicates_query, [self.today])

            if not duplicates.empty:
                self.validation_results['failed'] += 1
                self.validation_results['errors'].append(
                    f"❌ Found {len(duplicates)} duplicate records"
                )
                logger.error(f"❌ Found {len(duplicates)} duplicate records")
                for _, row in duplicates.iterrows():
                    logger.error(f"   - {row['symbol']} at {row['timestamp']}: {row['count']} duplicates")
            else:
                self.validation_results['passed'] += 1
                logger.info("✅ No duplicate records found")

            # Check table structure
            structure_query = '''
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'market_data'
            ORDER BY ordinal_position
            '''

            structure = self.db_manager.execute_custom_query(structure_query)

            expected_columns = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'date_partition']
            actual_columns = structure['column_name'].tolist() if not structure.empty else []

            missing_columns = set(expected_columns) - set(actual_columns)
            if missing_columns:
                self.validation_results['failed'] += 1
                self.validation_results['errors'].append(
                    f"❌ Missing columns: {missing_columns}"
                )
                logger.error(f"❌ Missing columns: {missing_columns}")
            else:
                self.validation_results['passed'] += 1
                logger.info("✅ Table structure is correct")

        except Exception as e:
            self.validation_results['failed'] += 1
            self.validation_results['errors'].append(f"❌ Data integrity validation failed: {e}")
            logger.error(f"❌ Data integrity validation failed: {e}")

    def validate_data_completeness(self):
        """Validate data completeness - expected number of records."""
        logger.info("📊 VALIDATING DATA COMPLETENESS")
        logger.info("-" * 40)

        try:
            # Get total records for today
            total_query = '''
            SELECT COUNT(*) as total_records
            FROM market_data
            WHERE date_partition = ?
            '''

            total_result = self.db_manager.execute_custom_query(total_query, [self.today])
            total_records = total_result.iloc[0]['total_records'] if not total_result.empty else 0

            # Get records per symbol
            per_symbol_query = '''
            SELECT symbol, COUNT(*) as record_count
            FROM market_data
            WHERE date_partition = ?
            GROUP BY symbol
            ORDER BY record_count DESC
            '''

            per_symbol = self.db_manager.execute_custom_query(per_symbol_query, [self.today])

            if per_symbol.empty:
                self.validation_results['failed'] += 1
                self.validation_results['errors'].append("❌ No data found for today")
                logger.error("❌ No data found for today")
                return

            # Check for symbols with insufficient data
            expected_records = 375  # Typical trading minutes (9:15 AM - 3:30 PM)
            insufficient_data = per_symbol[per_symbol['record_count'] < expected_records * 0.8]  # 80% threshold

            if not insufficient_data.empty:
                self.validation_results['warnings'] += 1
                logger.warning(f"⚠️ Found {len(insufficient_data)} symbols with insufficient data:")
                for _, row in insufficient_data.head(5).iterrows():
                    logger.warning(f"   - {row['symbol']}: {row['record_count']} records (expected ~{expected_records})")

            # Check for symbols with too much data
            excessive_data = per_symbol[per_symbol['record_count'] > expected_records * 1.5]  # 150% threshold

            if not excessive_data.empty:
                self.validation_results['warnings'] += 1
                logger.warning(f"⚠️ Found {len(excessive_data)} symbols with excessive data:")
                for _, row in excessive_data.head(3).iterrows():
                    logger.warning(f"   - {row['symbol']}: {row['record_count']} records (expected ~{expected_records})")

            # Overall statistics
            avg_records = per_symbol['record_count'].mean()
            min_records = per_symbol['record_count'].min()
            max_records = per_symbol['record_count'].max()

            logger.info("✅ Data completeness statistics:")
            logger.info(f"   📊 Total records: {total_records:,}")
            logger.info(f"   📊 Unique symbols: {len(per_symbol)}")
            logger.info(".0f")
            logger.info(f"   📊 Records range: {min_records} - {max_records}")

            if avg_records >= expected_records * 0.9:  # 90% of expected
                self.validation_results['passed'] += 1
                logger.info("✅ Data completeness is satisfactory")
            else:
                self.validation_results['warnings'] += 1
                logger.warning("⚠️ Data completeness is below expected levels")

        except Exception as e:
            self.validation_results['failed'] += 1
            self.validation_results['errors'].append(f"❌ Data completeness validation failed: {e}")
            logger.error(f"❌ Data completeness validation failed: {e}")

    def validate_data_quality(self):
        """Validate data quality - proper OHLCV values."""
        logger.info("🔬 VALIDATING DATA QUALITY")
        logger.info("-" * 40)

        try:
            # Check for invalid OHLC values
            quality_query = '''
            SELECT
                COUNT(*) as total_records,
                SUM(CASE WHEN open <= 0 THEN 1 ELSE 0 END) as invalid_open,
                SUM(CASE WHEN high <= 0 THEN 1 ELSE 0 END) as invalid_high,
                SUM(CASE WHEN low <= 0 THEN 1 ELSE 0 END) as invalid_low,
                SUM(CASE WHEN close <= 0 THEN 1 ELSE 0 END) as invalid_close,
                SUM(CASE WHEN volume < 0 THEN 1 ELSE 0 END) as invalid_volume,
                SUM(CASE WHEN high < open THEN 1 ELSE 0 END) as high_below_open,
                SUM(CASE WHEN low > open THEN 1 ELSE 0 END) as low_above_open,
                SUM(CASE WHEN high < close THEN 1 ELSE 0 END) as high_below_close,
                SUM(CASE WHEN low > close THEN 1 ELSE 0 END) as low_above_close
            FROM market_data
            WHERE date_partition = ?
            '''

            quality = self.db_manager.execute_custom_query(quality_query, [self.today])

            if quality.empty:
                self.validation_results['failed'] += 1
                self.validation_results['errors'].append("❌ No data available for quality validation")
                logger.error("❌ No data available for quality validation")
                return

            row = quality.iloc[0]
            total_records = row['total_records']

            # Check for invalid values
            invalid_count = (
                row['invalid_open'] + row['invalid_high'] + row['invalid_low'] +
                row['invalid_close'] + row['invalid_volume']
            )

            # Check for logical inconsistencies
            logic_errors = (
                row['high_below_open'] + row['low_above_open'] +
                row['high_below_close'] + row['low_above_close']
            )

            if invalid_count > 0:
                self.validation_results['failed'] += 1
                self.validation_results['errors'].append(
                    f"❌ Found {invalid_count} records with invalid OHLCV values"
                )
                logger.error(f"❌ Found {invalid_count} records with invalid OHLCV values")
            else:
                self.validation_results['passed'] += 1
                logger.info("✅ No invalid OHLCV values found")

            if logic_errors > 0:
                self.validation_results['failed'] += 1
                self.validation_results['errors'].append(
                    f"❌ Found {logic_errors} records with logical OHLC inconsistencies"
                )
                logger.error(f"❌ Found {logic_errors} records with logical OHLC inconsistencies")
            else:
                self.validation_results['passed'] += 1
                logger.info("✅ No logical OHLC inconsistencies found")

            # Check for reasonable price ranges
            price_range_query = '''
            SELECT
                MIN(low) as min_price,
                MAX(high) as max_price,
                AVG(close) as avg_price
            FROM market_data
            WHERE date_partition = ?
            '''

            price_range = self.db_manager.execute_custom_query(price_range_query, [self.today])

            if not price_range.empty:
                min_price = price_range.iloc[0]['min_price']
                max_price = price_range.iloc[0]['max_price']
                avg_price = price_range.iloc[0]['avg_price']

                logger.info("✅ Price range validation:")
                logger.info(".2f")
                logger.info(".2f")
                logger.info(".2f")

                # Flag extreme values
                if min_price < 1 or max_price > 100000:
                    self.validation_results['warnings'] += 1
                    logger.warning("⚠️ Extreme price values detected - please verify")

        except Exception as e:
            self.validation_results['failed'] += 1
            self.validation_results['errors'].append(f"❌ Data quality validation failed: {e}")
            logger.error(f"❌ Data quality validation failed: {e}")

    def validate_symbol_coverage(self):
        """Validate symbol coverage against available symbols."""
        logger.info("📈 VALIDATING SYMBOL COVERAGE")
        logger.info("-" * 40)

        try:
            # Get available symbols from database
            available_symbols = self.db_manager.get_available_symbols()
            logger.info(f"📊 Available symbols in database: {len(available_symbols)}")

            # Get symbols with today's data
            today_symbols_query = '''
            SELECT DISTINCT symbol
            FROM market_data
            WHERE date_partition = ?
            '''

            today_symbols_result = self.db_manager.execute_custom_query(today_symbols_query, [self.today])
            today_symbols = today_symbols_result['symbol'].tolist() if not today_symbols_result.empty else []

            logger.info(f"📊 Symbols with today's data: {len(today_symbols)}")

            # Find missing symbols
            missing_symbols = set(available_symbols) - set(today_symbols)
            extra_symbols = set(today_symbols) - set(available_symbols)

            if missing_symbols:
                self.validation_results['warnings'] += 1
                logger.warning(f"⚠️ Found {len(missing_symbols)} symbols without today's data:")
                for symbol in sorted(list(missing_symbols))[:10]:  # Show first 10
                    logger.warning(f"   - {symbol}")
                if len(missing_symbols) > 10:
                    logger.warning(f"   ... and {len(missing_symbols) - 10} more")

            if extra_symbols:
                self.validation_results['warnings'] += 1
                logger.warning(f"⚠️ Found {len(extra_symbols)} symbols with data but not in available list:")
                for symbol in sorted(list(extra_symbols)):
                    logger.warning(f"   - {symbol}")

            coverage_percentage = (len(today_symbols) / len(available_symbols)) * 100 if available_symbols else 0

            logger.info(".1f")

            if coverage_percentage >= 95:  # 95% coverage threshold
                self.validation_results['passed'] += 1
                logger.info("✅ Symbol coverage is excellent")
            elif coverage_percentage >= 80:  # 80% coverage threshold
                self.validation_results['passed'] += 1
                logger.info("✅ Symbol coverage is good")
            else:
                self.validation_results['warnings'] += 1
                logger.warning("⚠️ Symbol coverage is below expected levels")

        except Exception as e:
            self.validation_results['failed'] += 1
            self.validation_results['errors'].append(f"❌ Symbol coverage validation failed: {e}")
            logger.error(f"❌ Symbol coverage validation failed: {e}")

    def validate_time_ranges(self):
        """Validate time ranges and trading hours."""
        logger.info("⏰ VALIDATING TIME RANGES")
        logger.info("-" * 40)

        try:
            # Check timestamp format and range
            time_query = '''
            SELECT
                MIN(timestamp) as earliest_time,
                MAX(timestamp) as latest_time,
                COUNT(*) as total_records
            FROM market_data
            WHERE date_partition = ?
            '''

            time_result = self.db_manager.execute_custom_query(time_query, [self.today])

            if time_result.empty or time_result.iloc[0]['total_records'] == 0:
                self.validation_results['failed'] += 1
                self.validation_results['errors'].append("❌ No timestamp data available")
                logger.error("❌ No timestamp data available")
                return

            earliest = time_result.iloc[0]['earliest_time']
            latest = time_result.iloc[0]['latest_time']

            logger.info("✅ Time range validation:")
            logger.info(f"   🕐 Earliest timestamp: {earliest}")
            logger.info(f"   🕐 Latest timestamp: {latest}")

            # Check if timestamps are for today
            if earliest.date() != self.today or latest.date() != self.today:
                self.validation_results['failed'] += 1
                self.validation_results['errors'].append("❌ Timestamps are not for the expected date")
                logger.error("❌ Timestamps are not for the expected date")
            else:
                self.validation_results['passed'] += 1
                logger.info("✅ All timestamps are for the correct date")

            # Check trading hours (typical Indian market: 9:15 AM - 3:30 PM)
            expected_start = pd.Timestamp(f"{self.today} 09:15:00")
            expected_end = pd.Timestamp(f"{self.today} 15:30:00")

            if earliest < expected_start or latest > expected_end:
                self.validation_results['warnings'] += 1
                logger.warning("⚠️ Timestamps outside typical trading hours")
                logger.warning(f"   Expected: {expected_start.time()} - {expected_end.time()}")
            else:
                self.validation_results['passed'] += 1
                logger.info("✅ Timestamps are within expected trading hours")

            # Check for gaps in time series (for a sample symbol)
            sample_symbol_query = '''
            SELECT symbol, COUNT(*) as record_count
            FROM market_data
            WHERE date_partition = ?
            GROUP BY symbol
            ORDER BY record_count DESC
            LIMIT 1
            '''

            sample_result = self.db_manager.execute_custom_query(sample_symbol_query, [self.today])

            if not sample_result.empty:
                sample_symbol = sample_result.iloc[0]['symbol']

                # Check time gaps for sample symbol
                gaps_query = f'''
                SELECT
                    timestamp,
                    LEAD(timestamp) OVER (ORDER BY timestamp) as next_timestamp,
                    EXTRACT(EPOCH FROM (LEAD(timestamp) OVER (ORDER BY timestamp) - timestamp)) / 60 as gap_minutes
                FROM market_data
                WHERE date_partition = ? AND symbol = ?
                ORDER BY timestamp
                '''

                gaps = self.db_manager.execute_custom_query(gaps_query, [self.today, sample_symbol])

                if not gaps.empty:
                    large_gaps = gaps[gaps['gap_minutes'] > 10]  # Gaps larger than 10 minutes

                    if not large_gaps.empty:
                        self.validation_results['warnings'] += 1
                        logger.warning(f"⚠️ Found {len(large_gaps)} large time gaps in sample symbol {sample_symbol}")
                        logger.warning("   Large gaps may indicate missing data points")

        except Exception as e:
            self.validation_results['failed'] += 1
            self.validation_results['errors'].append(f"❌ Time range validation failed: {e}")
            logger.error(f"❌ Time range validation failed: {e}")

    def generate_validation_summary(self):
        """Generate comprehensive validation summary."""
        logger.info("📋 VALIDATION SUMMARY")
        logger.info("=" * 60)

        total_checks = self.validation_results['passed'] + self.validation_results['failed'] + self.validation_results['warnings']

        logger.info("🎯 OVERALL RESULTS:")
        logger.info(f"   ✅ Passed: {self.validation_results['passed']}")
        logger.info(f"   ⚠️  Warnings: {self.validation_results['warnings']}")
        logger.info(f"   ❌ Failed: {self.validation_results['failed']}")
        logger.info(f"   📊 Total checks: {total_checks}")

        success_rate = (self.validation_results['passed'] / total_checks * 100) if total_checks > 0 else 0
        logger.info(".1f")

        if self.validation_results['errors']:
            logger.info("🚨 ERRORS ENCOUNTERED:")
            for error in self.validation_results['errors'][:5]:  # Show first 5 errors
                logger.error(f"   {error}")
            if len(self.validation_results['errors']) > 5:
                logger.error(f"   ... and {len(self.validation_results['errors']) - 5} more errors")

        # Overall assessment
        if self.validation_results['failed'] == 0 and self.validation_results['warnings'] <= 2:
            logger.info("🎉 VALIDATION STATUS: EXCELLENT")
            logger.info("   Data integrity and quality are outstanding!")
        elif self.validation_results['failed'] == 0:
            logger.info("✅ VALIDATION STATUS: GOOD")
            logger.info("   Data is acceptable with minor warnings")
        else:
            logger.info("⚠️ VALIDATION STATUS: NEEDS ATTENTION")
            logger.info("   Some validation checks failed - please review errors above")

        logger.info("=" * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate intraday data integrity")
    parser.add_argument('--db-path', default='data/financial_data.duckdb',
                       help='Path to DuckDB database')
    parser.add_argument('--date', help='Date to validate (YYYY-MM-DD format)',
                       default=datetime.date.today().isoformat())
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Parse date
    if args.date:
        try:
            target_date = datetime.datetime.fromisoformat(args.date).date()
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD format.")
            sys.exit(1)
    else:
        target_date = datetime.date.today()

    # Create validator
    validator = DataValidator(db_path=args.db_path)
    validator.today = target_date

    # Run validations
    results = validator.run_all_validations()

    # Exit with appropriate code
    if results['failed'] > 0:
        sys.exit(1)  # Fail if any critical validations failed
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()
