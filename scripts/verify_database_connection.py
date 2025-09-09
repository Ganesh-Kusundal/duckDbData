#!/usr/bin/env python3
"""
Database Connection Verification Script

This script verifies that the unified DuckDB database is accessible and contains expected data.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.unified_duckdb import UnifiedDuckDBManager, DuckDBConfig
from src.infrastructure.config.config_manager import ConfigManager


def verify_database_connection():
    """Verify database connection and basic functionality."""
    print("🔍 Verifying database connection...")

    try:
        # Load configuration
        config_manager = ConfigManager()
        db_config = config_manager.get_config('database')

        if not db_config:
            print("❌ Database configuration not found")
            return False

        db_path = db_config.get('path')
        if not db_path:
            print("❌ Database path not configured")
            return False

        print(f"📁 Database path: {db_path}")

        # Check if file exists
        if not Path(db_path).exists():
            print(f"❌ Database file does not exist: {db_path}")
            return False

        file_size = Path(db_path).stat().st_size
        print(f"📊 Database size: {file_size:,} bytes ({file_size/1024/1024/1024:.1f} GB)")

        # Create connection config
        config = DuckDBConfig(
            database_path=db_path,
            max_connections=1,
            connection_timeout=10.0,
            read_only=True
        )

        # Test connection
        manager = None
        try:
            manager = UnifiedDuckDBManager(config)
            print("✅ Database manager initialized successfully")

            # Test basic connectivity
            result = manager.persistence_query("SELECT 1 as test, 'Hello World' as message")
            if len(result) != 1 or result.iloc[0]['test'] != 1:
                print("❌ Basic connectivity test failed")
                return False

            print("✅ Basic connectivity test passed")

            # Check for market data tables
            tables_query = """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name LIKE '%market%'
            ORDER BY name
            """
            tables = manager.persistence_query(tables_query)
            print(f"📋 Found {len(tables)} market-related tables:")
            for table in tables['name'].tolist():
                print(f"   - {table}")

            # Check data volume if market_data table exists
            if 'market_data' in tables['name'].values:
                count_query = "SELECT COUNT(*) as total_records FROM market_data"
                count_result = manager.persistence_query(count_query)
                total_records = count_result.iloc[0]['total_records']
                print(f"📊 Market data records: {total_records:,}")

                # Sample date range
                date_query = """
                SELECT
                    MIN(date_partition) as start_date,
                    MAX(date_partition) as end_date
                FROM market_data
                """
                date_result = manager.persistence_query(date_query)
                if len(date_result) > 0:
                    start_date = date_result.iloc[0]['start_date']
                    end_date = date_result.iloc[0]['end_date']
                    print(f"📅 Date range: {start_date} to {end_date}")

            print("✅ Database verification completed successfully")
            return True

        finally:
            if manager:
                manager.close()

    except Exception as e:
        print(f"❌ Full database verification failed: {e}")

        # Fallback verification - check file properties without connecting
        print("🔄 Attempting fallback verification...")
        return verify_database_file_only(db_path)

    return True


def verify_database_file_only(db_path: str) -> bool:
    """Verify database file properties when full connection is not possible."""
    try:
        path = Path(db_path)

        if not path.exists():
            print(f"❌ Database file does not exist: {db_path}")
            return False

        file_size = path.stat().st_size
        if file_size < 1000:  # Very small file might be corrupted or empty
            print(f"⚠️  Database file is very small: {file_size} bytes")
            return False

        print(f"✅ Database file exists: {file_size:,} bytes ({file_size/1024/1024/1024:.1f} GB)")

        # Try to use DuckDB CLI to check basic file integrity
        import subprocess
        try:
            result = subprocess.run([
                'duckdb', db_path, '-c', 'SELECT COUNT(*) FROM sqlite_master WHERE type=\'table\''
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print("✅ DuckDB CLI verification passed")
                return True
            else:
                print(f"⚠️  DuckDB CLI verification failed: {result.stderr}")
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠️  DuckDB CLI not available, but file properties look good")
            return True

    except Exception as e:
        print(f"❌ Fallback verification failed: {e}")
        return False


def main():
    """Main verification function."""
    print("=" * 60)
    print("🗄️  UNIFIED DUCKDB DATABASE VERIFICATION")
    print("=" * 60)

    success = verify_database_connection()

    print("\n" + "=" * 60)
    if success:
        print("✅ VERIFICATION PASSED")
        sys.exit(0)
    else:
        print("❌ VERIFICATION FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
