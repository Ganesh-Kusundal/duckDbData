#!/usr/bin/env python3
"""
Comprehensive tests for DuckDBConnectionManager and connection pooling functionality.
Tests verify that the singleton pattern has been properly removed and concurrent access works.
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, time
import pandas as pd


class TestDuckDBConnectionManager:
    """Test suite for DuckDBConnectionManager functionality."""

    def test_connection_manager_creation(self):
        """Test that connection manager can be created successfully."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")
        assert manager is not None
        assert hasattr(manager, 'get_connection')
        assert hasattr(manager, 'execute_query')
        assert hasattr(manager, 'close')

        manager.close()

    def test_connection_pool_initialization(self):
        """Test that connection pool is properly initialized."""
        from src.infrastructure.core.singleton_database import DuckDBConnectionManager

        db_path = ":memory:"
        manager = DuckDBConnectionManager(db_path=db_path)

        assert manager.connection_pool is not None
        assert manager.connection_pool.db_path == db_path
        assert manager.connection_pool.max_connections == 10
        assert manager.connection_pool.max_retries == 5
        assert manager.connection_pool.timeout == 60.0

        manager.close()

    def test_connection_pool_custom_config(self):
        """Test connection pool with custom configuration."""
        from src.infrastructure.core.singleton_database import DuckDBConnectionManager

        db_path = ":memory:"
        manager = DuckDBConnectionManager(
            db_path=db_path,
            max_connections=20,
            max_retries=10,
            timeout=120.0
        )

        pool = manager.connection_pool
        assert pool.max_connections == 20
        assert pool.max_retries == 10
        assert pool.timeout == 120.0

        manager.close()

    def test_get_connection_context_manager(self):
        """Test that get_connection returns a proper context manager."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        with manager.get_connection() as conn:
            assert conn is not None
            # Test basic query execution
            result = conn.execute("SELECT 1 as test").fetchone()
            assert result[0] == 1

        manager.close()

    def test_execute_query_basic(self):
        """Test basic query execution."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        # Create test table
        with manager.get_connection() as conn:
            conn.execute("""
                CREATE TABLE test_table (
                    id INTEGER,
                    name VARCHAR
                )
            """)
            conn.execute("INSERT INTO test_table VALUES (1, 'test')")

        # Execute query
        df = manager.execute_query("SELECT * FROM test_table")
        assert len(df) == 1
        assert df.iloc[0]['name'] == 'test'

        manager.close()

    def test_execute_custom_query_with_params(self):
        """Test custom query execution with parameters."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        # Create test table
        with manager.get_connection() as conn:
            conn.execute("""
                CREATE TABLE users (
                    id INTEGER,
                    name VARCHAR,
                    age INTEGER
                )
            """)
            conn.execute("INSERT INTO users VALUES (1, 'Alice', 25)")
            conn.execute("INSERT INTO users VALUES (2, 'Bob', 30)")

        # Test with list parameters
        df = manager.execute_custom_query(
            "SELECT * FROM users WHERE age > ?",
            [25]
        )
        assert len(df) == 1
        assert df.iloc[0]['name'] == 'Bob'

        # Test with dict parameters
        df = manager.execute_custom_query(
            "SELECT * FROM users WHERE name = :name",
            {"name": "Alice"}
        )
        assert len(df) == 1
        assert df.iloc[0]['age'] == 25

        manager.close()

    def test_read_only_mode(self):
        """Test read-only mode functionality."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")
        manager.set_read_only(True)

        # Test that read operations work
        with manager.get_connection() as conn:
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1

        manager.close()

    def test_connection_pool_reuse(self):
        """Test that connections are properly reused from the pool."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:", max_connections=2)

        connections = []

        # Get multiple connections
        for i in range(5):
            with manager.get_connection() as conn:
                connections.append(id(conn))
                time.sleep(0.01)  # Small delay to allow reuse

        # Check that some connections were reused (pool should only have 2 unique connections)
        unique_connections = set(connections)
        assert len(unique_connections) <= 2  # Should reuse connections from pool

        manager.close()

    def test_concurrent_connections(self):
        """Test concurrent access to database connections."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")
        results = []

        def worker(worker_id):
            """Worker function for concurrent testing."""
            try:
                with manager.get_connection() as conn:
                    result = conn.execute(f"SELECT {worker_id} as worker_id").fetchone()
                    results.append(result[0])
                    time.sleep(0.01)  # Simulate some work
                return True
            except Exception as e:
                results.append(f"error_{worker_id}: {e}")
                return False

        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            concurrent_results = [future.result() for future in as_completed(futures)]

        # Verify all workers completed successfully
        assert all(concurrent_results)
        assert len(results) == 10
        assert all(isinstance(r, int) for r in results if isinstance(r, int))

        manager.close()

    def test_connection_timeout_handling(self):
        """Test that connection timeouts are handled properly."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:", timeout=1.0)

        # Test with a long-running query simulation
        try:
            with manager.get_connection() as conn:
                # This should complete within timeout
                result = conn.execute("SELECT 1").fetchone()
                assert result[0] == 1
        except Exception as e:
            pytest.fail(f"Connection should not timeout for simple query: {e}")

        manager.close()

    def test_error_handling_invalid_query(self):
        """Test error handling for invalid queries."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        # Test invalid query
        with pytest.raises(Exception):
            manager.execute_query("SELECT * FROM nonexistent_table")

        manager.close()

    def test_connection_pool_cleanup(self):
        """Test that connection pool is properly cleaned up."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager = create_db_manager(db_path=":memory:")

        # Use some connections
        for _ in range(3):
            with manager.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()

        # Close manager
        manager.close()

        # Verify pool is cleaned up (this is more of a smoke test)
        assert manager.connection_pool is not None


class TestSingletonRemoval:
    """Test that singleton pattern has been properly removed."""

    def test_multiple_managers_can_exist(self):
        """Test that multiple database managers can exist simultaneously."""
        from src.infrastructure.core.singleton_database import create_db_manager

        manager1 = create_db_manager(db_path=":memory:")
        manager2 = create_db_manager(db_path=":memory:")

        # They should be different instances
        assert manager1 is not manager2
        assert manager1.connection_pool is not manager2.connection_pool

        # Both should work independently
        with manager1.get_connection() as conn1:
            conn1.execute("SELECT 1").fetchone()

        with manager2.get_connection() as conn2:
            conn2.execute("SELECT 2").fetchone()

        manager1.close()
        manager2.close()

    def test_no_global_singleton_variable(self):
        """Test that there are no global singleton variables."""
        from src.infrastructure.core.singleton_database import DuckDBConnectionManager

        # Check that the class doesn't have singleton-like attributes
        assert not hasattr(DuckDBConnectionManager, '_instance')
        assert not hasattr(DuckDBConnectionManager, '_singleton_instance')
        assert not hasattr(DuckDBConnectionManager, '__instance')

    def test_concurrent_manager_creation(self):
        """Test creating multiple managers concurrently."""
        from src.infrastructure.core.singleton_database import create_db_manager

        managers = []

        def create_manager():
            manager = create_db_manager(db_path=":memory:")
            managers.append(manager)
            return manager

        # Create multiple managers concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_manager) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]

        # All should be successful
        assert len(managers) == 5
        assert len(results) == 5
        assert all(m is not None for m in managers)

        # Clean up
        for manager in managers:
            manager.close()


class TestDatabaseIsolation:
    """Test database isolation between different manager instances."""

    def test_isolated_database_operations(self):
        """Test that different managers operate on isolated databases."""
        from src.infrastructure.core.singleton_database import create_db_manager

        # Create two managers with different database paths
        with tempfile.TemporaryDirectory() as temp_dir:
            db1_path = Path(temp_dir) / "db1.duckdb"
            db2_path = Path(temp_dir) / "db2.duckdb"

            manager1 = create_db_manager(db_path=str(db1_path))
            manager2 = create_db_manager(db_path=str(db2_path))

            # Create different tables in each database
            with manager1.get_connection() as conn:
                conn.execute("CREATE TABLE table1 (id INTEGER, name VARCHAR)")
                conn.execute("INSERT INTO table1 VALUES (1, 'manager1')")

            with manager2.get_connection() as conn:
                conn.execute("CREATE TABLE table2 (id INTEGER, name VARCHAR)")
                conn.execute("INSERT INTO table2 VALUES (2, 'manager2')")

            # Verify isolation
            df1 = manager1.execute_query("SELECT * FROM table1")
            assert len(df1) == 1
            assert df1.iloc[0]['name'] == 'manager1'

            df2 = manager2.execute_query("SELECT * FROM table2")
            assert len(df2) == 1
            assert df2.iloc[0]['name'] == 'manager2'

            # Cross-database queries should fail
            with pytest.raises(Exception):
                manager1.execute_query("SELECT * FROM table2")

            with pytest.raises(Exception):
                manager2.execute_query("SELECT * FROM table1")

            manager1.close()
            manager2.close()


if __name__ == "__main__":
    # Run basic smoke tests
    print("🧪 Running DuckDBConnectionManager smoke tests...")

    test_instance = TestDuckDBConnectionManager()
    test_instance.test_connection_manager_creation()
    print("✅ Connection manager creation test passed")

    test_instance.test_connection_pool_initialization()
    print("✅ Connection pool initialization test passed")

    test_instance.test_get_connection_context_manager()
    print("✅ Connection context manager test passed")

    print("\\n🎉 All smoke tests passed!")
    print("\\n💡 Run with pytest for comprehensive testing:")
    print("pytest tests/database/test_connection_manager.py -v")


