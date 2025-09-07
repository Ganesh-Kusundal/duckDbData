"""Unit tests for QueryBuilder and AdvancedQueryBuilder."""
import pytest
from database.framework.query_builder import (
    QueryBuilder,
    AdvancedQueryBuilder,
    JoinType,
    AggregateFunction,
    WindowFunction,
    WhereClause,
    JoinClause,
    OrderByClause,
    GroupByClause,
    WindowClause
)


class TestQueryBuilder:
    """Unit tests for basic QueryBuilder."""

    def test_select_columns(self):
        """Test selecting columns."""
        builder = QueryBuilder("market_data").select("symbol", "close")
        query, params = builder.build()
        assert "SELECT symbol, close" in query
        assert params == {}

    def test_select_distinct(self):
        """Test selecting distinct columns."""
        builder = QueryBuilder("market_data").select_distinct("symbol")
        query, params = builder.build()
        assert "SELECT DISTINCT symbol" in query

    def test_join(self):
        """Test adding a join."""
        builder = QueryBuilder("market_data").join(
            "symbols", "market_data.symbol = symbols.symbol", JoinType.LEFT, "s"
        )
        query, params = builder.build()
        assert "LEFT JOIN symbols AS s ON market_data.symbol = symbols.symbol" in query

    def test_where_condition(self):
        """Test adding a where condition."""
        builder = QueryBuilder("market_data").where("symbol", "=", "AAPL")
        query, params = builder.build()
        assert "WHERE symbol = $1" in query
        assert params == {'param_1': 'AAPL'}

    def test_multiple_where(self):
        """Test multiple where conditions."""
        builder = QueryBuilder("market_data").where("symbol", "=", "AAPL").where(
            "close", ">", 100, "OR"
        )
        query, params = builder.build()
        assert "WHERE symbol = $1 OR close > $2" in query
        assert params == {'param_1': 'AAPL', 'param_2': 100}

    def test_where_in(self):
        """Test where in condition."""
        builder = QueryBuilder("market_data").where_in("symbol", ["AAPL", "GOOGL"])
        query, params = builder.build()
        assert "symbol IN ($1, $2)" in query
        assert len(params) == 2

    def test_where_between(self):
        """Test where between condition."""
        builder = QueryBuilder("market_data").where_between("timestamp", "2025-01-01", "2025-12-31")
        query, params = builder.build()
        assert "timestamp BETWEEN $1 AND $2" in query
        assert len(params) == 2

    def test_group_by(self):
        """Test group by."""
        builder = QueryBuilder("market_data").group_by("symbol", "date_partition")
        query, params = builder.build()
        assert "GROUP BY symbol, date_partition" in query

    def test_having(self):
        """Test having condition."""
        builder = QueryBuilder("market_data").group_by("symbol").having("AVG(close)", ">", 100)
        query, params = builder.build()
        assert "HAVING AVG(close) > $1" in query

    def test_order_by(self):
        """Test order by."""
        builder = QueryBuilder("market_data").order_by("timestamp", "DESC")
        query, params = builder.build()
        assert "ORDER BY timestamp DESC" in query

    def test_limit_offset(self):
        """Test limit and offset."""
        builder = QueryBuilder("market_data").limit(10).offset(5)
        query, params = builder.build()
        assert "LIMIT 10" in query
        assert "OFFSET 5" in query

    def test_with_cte(self):
        """Test CTE."""
        builder = QueryBuilder("market_data").with_cte("recent_data", "SELECT * FROM market_data WHERE timestamp > CURRENT_DATE - INTERVAL 30 DAY")
        query, params = builder.build()
        assert "WITH recent_data AS (SELECT * FROM market_data WHERE timestamp > CURRENT_DATE - INTERVAL 30 DAY)" in query

    def test_full_build(self):
        """Test full query build."""
        builder = (
            QueryBuilder("market_data")
            .select("symbol", "close")
            .join("symbols", "market_data.symbol = symbols.symbol")
            .where("symbol", "=", "AAPL")
            .group_by("symbol")
            .order_by("close", "DESC")
            .limit(5)
        )
        query, params = builder.build()
        expected_parts = [
            "SELECT symbol, close",
            "FROM market_data",
            "INNER JOIN symbols ON market_data.symbol = symbols.symbol",
            "WHERE symbol = $1",
            "GROUP BY symbol",
            "ORDER BY close DESC",
            "LIMIT 5"
        ]
        for part in expected_parts:
            assert part in query
        assert params == {'param_1': 'AAPL'}


class TestAdvancedQueryBuilder:
    """Unit tests for AdvancedQueryBuilder."""

    def test_time_series_filter(self):
        """Test time series filter."""
        builder = AdvancedQueryBuilder("market_data").time_series_filter("2025-01-01", "2025-12-31")
        query, params = builder.build()
        assert "timestamp BETWEEN $1 AND $2" in query

    def test_symbol_filter(self):
        """Test symbol filter."""
        builder = AdvancedQueryBuilder("market_data").symbol_filter(["AAPL", "GOOGL"])
        query, params = builder.build()
        assert "symbol IN ($1, $2)" in query

    def test_price_filter(self):
        """Test price filter."""
        builder = AdvancedQueryBuilder("market_data").price_filter(100, 200)
        query, params = builder.build()
        assert "close >= $1" in query
        assert "close <= $2" in query

    def test_volume_filter(self):
        """Test volume filter."""
        builder = AdvancedQueryBuilder("market_data").volume_filter(1000)
        query, params = builder.build()
        assert "volume >= $1" in query

    def test_technical_indicator(self):
        """Test technical indicator."""
        builder = AdvancedQueryBuilder("market_data").technical_indicator("sma", 14)
        query, params = builder.build()
        assert "sma_14" in query
        assert "WITH sma_calc AS (SELECT *, AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS 13 PRECEDING) as sma_14 FROM market_data)" in query

    def test_pivot_by_timeframe(self):
        """Test pivot by timeframe."""
        builder = AdvancedQueryBuilder("market_data").pivot_by_timeframe("1H")
        query, params = builder.build()
        assert "date_trunc('1H', timestamp) as period" in query

    def test_correlation_analysis(self):
        """Test correlation analysis."""
        builder = AdvancedQueryBuilder("market_data").correlation_analysis(["AAPL", "GOOGL"])
        query, params = builder.build()
        assert "CORR(s1.close, s2.close) as correlation" in query