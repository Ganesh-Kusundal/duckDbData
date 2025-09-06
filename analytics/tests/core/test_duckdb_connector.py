#!/usr/bin/env python3
"""
Tests for DuckDB Analytics Connector
====================================

Comprehensive tests for the DuckDB connector component.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from analytics.core.duckdb_connector import DuckDBAnalytics


class TestDuckDBAnalytics:
    """Test suite for DuckDBAnalytics class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.connector = DuckDBAnalytics()

    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(self.connector, 'connection') and self.connector.connection:
            self.connector.close()

    def test_initialization(self):
        """Test DuckDBAnalytics initialization."""
        connector = DuckDBAnalytics()
        assert connector is not None
        assert connector.connection is None  # Not connected yet
        assert connector.db_path.endswith('financial_data.duckdb')

    @patch('duckdb.connect')
    def test_connect(self, mock_connect):
        """Test connecting to database."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        result = self.connector.connect()

        mock_connect.assert_called_once_with(self.connector.db_path)
        assert self.connector.connection == mock_conn
        assert result == mock_conn

    def test_close_connection(self):
        """Test closing database connection."""
        mock_conn = MagicMock()
        self.connector.connection = mock_conn
        self.connector.close()

        mock_conn.close.assert_called_once()
        assert self.connector.connection is None


    def test_close_without_connection(self):
        """Test closing when no connection exists."""
        self.connector.connection = None
        self.connector.close()  # Should not raise error
        assert self.connector.connection is None

    @patch('duckdb.connect')
    def test_execute_analytics_query_success(self, mock_connect):
        """Test successful query execution."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_df = pd.DataFrame({
            'symbol': ['AAPL', 'GOOGL'],
            'price': [150.0, 2800.0]
        })
        mock_result.fetchdf.return_value = mock_df
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        self.connector.connect()
        result = self.connector.execute_analytics_query("SELECT symbol, price FROM stocks")

        assert result is not None
        assert len(result) == 2
        assert result.iloc[0]['symbol'] == 'AAPL'

    @patch('duckdb.connect')
    def test_execute_analytics_query_with_params(self, mock_connect):
        """Test query execution with parameters."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_df = pd.DataFrame({'symbol': ['AAPL']})
        mock_result.fetchdf.return_value = mock_df
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        self.connector.connect()
        result = self.connector.execute_analytics_query(
            "SELECT symbol FROM stocks WHERE price > {price}",
            price=100.0
        )

        assert result is not None
        assert len(result) == 1

    @patch('duckdb.connect')
    def test_get_available_symbols(self, mock_connect):
        """Test getting available symbols."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_df = pd.DataFrame({'symbol': ['AAPL', 'GOOGL', 'MSFT']})
        mock_result.fetchdf.return_value = mock_df
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        self.connector.connect()
        symbols = self.connector.get_available_symbols()

        assert symbols == ['AAPL', 'GOOGL', 'MSFT']

    @patch('duckdb.connect')
    def test_get_date_range(self, mock_connect):
        """Test getting date range."""
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_df = pd.DataFrame({
            'min_date': ['2020-01-01'],
            'max_date': ['2024-12-31']
        })
        mock_result.fetchdf.return_value = mock_df
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        self.connector.connect()
        date_range = self.connector.get_date_range()

        assert date_range == ('2015-01-01', '2025-12-31')  # Actual data range

    def test_scan_parquet_files(self):
        """Test scanning parquet files."""
        # Test with default pattern
        files = self.connector.scan_parquet_files()
        assert isinstance(files, list)



class TestDuckDBAnalyticsErrorHandling:
    """Test error handling in DuckDBAnalytics."""

    def setup_method(self):
        """Setup test fixtures."""
        self.connector = DuckDBAnalytics()

    @patch('duckdb.connect')
    def test_connection_error_handling(self, mock_connect):
        """Test handling connection errors."""
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            self.connector.connect()

    def test_invalid_database_path(self):
        """Test handling invalid database path."""
        connector = DuckDBAnalytics(db_path="/invalid/path/database.db")

        with pytest.raises(Exception):
            connector.connect()
