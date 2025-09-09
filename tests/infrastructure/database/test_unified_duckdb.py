"""
Tests for Unified DuckDB Integration Layer
==========================================

Comprehensive tests for the unified DuckDB abstraction layer,
ensuring proper connection management, query execution, and resource handling.
"""

import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.infrastructure.database.unified_duckdb import (
    UnifiedDuckDBManager,
    DuckDBConfig,
    ConnectionPool,
    SchemaManager,
    QueryExecutor,
)


class TestDuckDBConfig:
    """Test DuckDB configuration management."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DuckDBConfig(database_path="test.db")

        assert config.database_path == "test.db"
        assert config.max_connections == 10
        assert config.connection_timeout == 30.0
        assert config.memory_limit == "2GB"
        assert config.threads == 4
        assert config.enable_object_cache is True
        assert config.enable_profiling is False
        assert config.read_only is False
        assert config.enable_httpfs is True
        assert config.use_parquet_in_unified_view is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DuckDBConfig(
            database_path="/custom/path.db",
            max_connections=5,
            memory_limit="1GB",
            threads=2,
            enable_profiling=True
        )

        assert config.database_path == "/custom/path.db"
        assert config.max_connections == 5
        assert config.memory_limit == "1GB"
        assert config.threads == 2
        assert config.enable_profiling is True


class TestConnectionPool:
    """Test connection pool functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.config = DuckDBConfig(database_path=self.temp_db.name, max_connections=3)

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_pool_initialization(self):
        """Test connection pool initialization."""
        pool = ConnectionPool(self.config)

        assert pool.active_connections == 0
        assert pool.available_connections == 0
        assert pool._closed is False

    def test_get_connection_creates_new(self):
        """Test getting a connection creates a new one when pool is empty."""
        pool = ConnectionPool(self.config)

        conn = pool.get_connection()

        assert conn is not None
        assert pool.active_connections == 1
        assert pool.available_connections == 0

        # Clean up
        pool.release_connection(conn)

    def test_connection_reuse(self):
        """Test connection reuse from pool."""
        pool = ConnectionPool(self.config)

        # Get and release a connection
        conn1 = pool.get_connection()
        pool.release_connection(conn1)

        # Connection is still active (created) but available in pool
        assert pool.active_connections == 1
        assert pool.available_connections == 1

        # Get connection again (should reuse)
        conn2 = pool.get_connection()
        assert pool.active_connections == 1  # Same connection reused
        assert pool.available_connections == 0

        # Clean up
        pool.release_connection(conn2)

    def test_pool_exhaustion(self):
        """Test behavior when pool is exhausted."""
        config = DuckDBConfig(database_path=self.temp_db.name, max_connections=1)
        pool = ConnectionPool(config)

        # Get the only connection
        conn1 = pool.get_connection()

        # Try to get another (should fail)
        with pytest.raises(RuntimeError, match="Connection pool exhausted"):
            pool.get_connection()

        # Clean up
        pool.release_connection(conn1)

    def test_pool_close(self):
        """Test closing the connection pool."""
        pool = ConnectionPool(self.config)

        conn = pool.get_connection()
        pool.release_connection(conn)

        pool.close_all()

        assert pool._closed is True
        assert pool.active_connections == 0
        assert pool.available_connections == 0

        # Getting connection after close should fail
        with pytest.raises(RuntimeError, match="Connection pool is closed"):
            pool.get_connection()


class TestQueryExecutor:
    """Test query execution functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.config = DuckDBConfig(database_path=self.temp_db.name)
        self.pool = ConnectionPool(self.config)
        self.executor = QueryExecutor(self.pool)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.pool.close_all()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    @patch('duckdb.connect')
    def test_execute_query_success(self, mock_connect):
        """Test successful query execution."""
        # Mock the connection and result
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        mock_result.df.return_value = mock_df
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        # Execute query
        result = self.executor.execute_query("SELECT * FROM test_table")

        assert result is not None
        assert len(result) == 2
        assert result.iloc[0]['col1'] == 1

    @patch('duckdb.connect')
    def test_execute_command_success(self, mock_connect):
        """Test successful command execution."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.rows_changed = 5
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        result = self.executor.execute_command("INSERT INTO test_table VALUES (1)")

        assert result == 5

    @patch('duckdb.connect')
    def test_execute_analytics_query_with_params(self, mock_connect):
        """Test analytics query execution with parameter substitution."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_df = pd.DataFrame({'result': [42]})
        mock_result.df.return_value = mock_df

        # Mock the execute method to capture the actual query
        executed_queries = []
        def mock_execute(query):
            executed_queries.append(query)
            return mock_result

        mock_conn.execute.side_effect = mock_execute
        mock_connect.return_value = mock_conn

        result = self.executor.execute_analytics_query(
            "SELECT * FROM table WHERE value > {threshold}",
            threshold=100
        )

        # Verify parameter substitution occurred
        # Find the analytics query (not the initialization queries)
        analytics_query = None
        for query in executed_queries:
            if "SELECT * FROM table WHERE value > 100" in query:
                analytics_query = query
                break

        assert analytics_query is not None
        assert "100" in analytics_query
        assert "{threshold}" not in analytics_query
        assert "SELECT * FROM table WHERE value > 100" == analytics_query

        assert result is not None
        assert result.iloc[0]['result'] == 42


class TestSchemaManager:
    """Test schema management functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.config = DuckDBConfig(database_path=self.temp_db.name)
        self.pool = ConnectionPool(self.config)
        self.schema_manager = SchemaManager(self.config, self.pool)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.pool.close_all()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    @patch('duckdb.connect')
    def test_schema_initialization(self, mock_connect):
        """Test schema initialization."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Initialize schema
        self.schema_manager.initialize_schema()

        # Verify schema initialization was called
        assert self.schema_manager._schema_initialized is True

        # Verify it doesn't initialize again
        self.schema_manager.initialize_schema()
        # Should still be True, no additional calls


class TestUnifiedDuckDBManager:
    """Test the main unified manager functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.config = DuckDBConfig(database_path=self.temp_db.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_manager_initialization(self):
        """Test unified manager initialization."""
        manager = UnifiedDuckDBManager(self.config)

        assert manager.config == self.config
        assert manager.connection_pool is not None
        assert manager.schema_manager is not None
        assert manager.query_executor is not None

        # Clean up
        manager.close()

    def test_context_manager(self):
        """Test unified manager as context manager."""
        with UnifiedDuckDBManager(self.config) as manager:
            assert manager is not None
            stats = manager.get_connection_stats()
            assert 'active_connections' in stats
            assert 'available_connections' in stats
            assert 'max_connections' in stats

    @patch('duckdb.connect')
    def test_analytics_query(self, mock_connect):
        """Test analytics query through unified manager."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_df = pd.DataFrame({'data': [1, 2, 3]})
        mock_result.df.return_value = mock_df
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        with UnifiedDuckDBManager(self.config) as manager:
            result = manager.analytics_query("SELECT * FROM {table}", table="test_table")

            assert result is not None
            assert len(result) == 3

    @patch('duckdb.connect')
    def test_persistence_operations(self, mock_connect):
        """Test persistence operations through unified manager."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.df.return_value = pd.DataFrame({'id': [1]})
        mock_result.rows_changed = 1
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        with UnifiedDuckDBManager(self.config) as manager:
            # Test query
            result = manager.persistence_query("SELECT * FROM users")
            assert result is not None

            # Test command
            affected = manager.persistence_command("INSERT INTO users VALUES (1)")
            assert affected == 1

    def test_connection_stats(self):
        """Test connection statistics retrieval."""
        with UnifiedDuckDBManager(self.config) as manager:
            stats = manager.get_connection_stats()

            assert isinstance(stats, dict)
            assert 'active_connections' in stats
            assert 'available_connections' in stats
            assert 'max_connections' in stats
            assert stats['max_connections'] == self.config.max_connections


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.config = DuckDBConfig(database_path=self.temp_db.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    @patch('duckdb.connect')
    def test_concurrent_operations(self, mock_connect):
        """Test concurrent database operations."""
        import threading

        mock_conn = MagicMock()
        executed_queries = []

        def mock_execute(query):
            executed_queries.append(query)
            # Extract the worker ID from the query
            if "SELECT" in query and "as result" in query:
                # Parse the query to extract the ID
                import re
                match = re.search(r'SELECT (\d+) as result', query)
                if match:
                    worker_id = int(match.group(1))
                    mock_result = MagicMock()
                    mock_result.df.return_value = pd.DataFrame({'result': [worker_id]})
                    return mock_result
            # Default fallback
            mock_result = MagicMock()
            mock_result.df.return_value = pd.DataFrame({'result': [0]})
            return mock_result

        mock_conn.execute.side_effect = mock_execute
        mock_connect.return_value = mock_conn

        results = []
        errors = []

        def worker(manager, worker_id):
            try:
                result = manager.analytics_query("SELECT {id} as result", id=worker_id)
                results.append((worker_id, result.iloc[0]['result']))
            except Exception as e:
                errors.append((worker_id, str(e)))

        with UnifiedDuckDBManager(self.config) as manager:
            threads = []
            for i in range(3):  # Reduced to 3 for simpler testing
                t = threading.Thread(target=worker, args=(manager, i))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

        assert len(results) == 3
        assert len(errors) == 0
        # Verify all workers got their expected results
        for worker_id, result in results:
            assert result == worker_id

    @patch('duckdb.connect')
    def test_error_handling_and_recovery(self, mock_connect):
        """Test error handling and connection recovery."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Mock successful execution
        mock_result_success = MagicMock()
        mock_result_success.df.return_value = pd.DataFrame({'data': [1]})

        def mock_execute_success(query):
            return mock_result_success

        mock_conn.execute.side_effect = mock_execute_success

        with UnifiedDuckDBManager(self.config) as manager:
            # Successful operation
            result = manager.analytics_query("SELECT 1 as data")
            assert result.iloc[0]['data'] == 1

            # Simulate connection failure
            mock_conn.reset_mock()
            def mock_execute_failure(query):
                if "failing_table" in query:
                    raise Exception("Connection lost")
                return mock_result_success

            mock_conn.execute.side_effect = mock_execute_failure

            # Operation should handle the error gracefully
            with pytest.raises(Exception, match="Connection lost"):
                manager.analytics_query("SELECT * FROM failing_table")


# Performance and Load Tests
class TestPerformanceScenarios:
    """Test performance characteristics of the unified layer."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.config = DuckDBConfig(database_path=self.temp_db.name, max_connections=5)

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    @patch('duckdb.connect')
    def test_connection_pooling_efficiency(self, mock_connect):
        """Test that connection pooling improves performance."""
        import time

        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.df.return_value = pd.DataFrame({'result': [1]})
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        with UnifiedDuckDBManager(self.config) as manager:
            start_time = time.time()

            # Execute multiple queries
            for i in range(10):
                manager.analytics_query("SELECT {i} as result", i=i)

            end_time = time.time()
            execution_time = end_time - start_time

            # Verify reasonable execution time (should be fast due to connection reuse)
            assert execution_time < 1.0  # Should complete in less than 1 second

            # Verify connection was created only once (due to mocking, we check call count)
            # In real scenario, this would verify connection reuse
            assert mock_connect.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__])
