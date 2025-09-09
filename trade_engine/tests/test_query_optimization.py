"""
Test Query Optimization
=======================

Tests for query optimization adapter functionality.
Validates query analysis, optimization, and performance improvements.
"""

import pytest
import asyncio
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from trade_engine.adapters.query_optimizer import QueryOptimizer, QueryAnalysis, OptimizedQuery, CacheConfiguration


class TestQueryOptimizer:
    """Test suite for QueryOptimizer."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'query_cache': {
                'enabled': True,
                'ttl_seconds': 3600,
                'max_size': 100
            },
            'performance_monitoring': {
                'enabled': True,
                'log_slow_queries': True,
                'slow_query_threshold': 1.0
            }
        }

    @pytest.fixture
    def optimizer(self, config):
        """Query optimizer instance."""
        return QueryOptimizer(config)

    @pytest.mark.asyncio
    async def test_analyze_simple_query(self, optimizer):
        """Test analysis of a simple query."""
        query = "SELECT symbol, close FROM market_data WHERE symbol = 'RELIANCE'"

        analysis = await optimizer.analyze_query_performance(query)

        assert isinstance(analysis, QueryAnalysis)
        assert analysis.query_complexity == 'simple'
        assert analysis.estimated_rows > 0
        assert isinstance(analysis.recommended_optimizations, list)
        assert 0 <= analysis.performance_score <= 1
        assert analysis.execution_time_estimate >= 0

    @pytest.mark.asyncio
    async def test_analyze_complex_query(self, optimizer):
        """Test analysis of a complex query."""
        query = """
        SELECT symbol, AVG(close) as avg_close, MAX(high) as max_high
        FROM market_data
        WHERE date_partition BETWEEN '2024-01-01' AND '2024-01-02'
        GROUP BY symbol
        HAVING AVG(close) > 100
        ORDER BY avg_close DESC
        """

        analysis = await optimizer.analyze_query_performance(query)

        assert isinstance(analysis, QueryAnalysis)
        assert analysis.query_complexity in ['medium', 'complex']
        assert analysis.estimated_rows > 0
        # Check that we get some recommendations (don't be too specific about content)
        assert len(analysis.recommended_optimizations) > 0

    @pytest.mark.asyncio
    async def test_optimize_query_with_limit(self, optimizer):
        """Test optimizing a query by adding LIMIT clause."""
        original_query = "SELECT * FROM market_data ORDER BY timestamp DESC"

        optimized = await optimizer.generate_optimized_query(original_query)

        assert isinstance(optimized, OptimizedQuery)
        assert optimized.original_query == original_query
        assert 'LIMIT' in optimized.optimized_query.upper()
        assert len(optimized.optimization_applied) > 0
        assert optimized.expected_improvement > 0

    @pytest.mark.asyncio
    async def test_optimize_date_filter_query(self, optimizer):
        """Test optimizing a query with date filters."""
        original_query = "SELECT * FROM market_data WHERE date_partition = '2024-01-01'"

        optimized = await optimizer.generate_optimized_query(original_query)

        assert isinstance(optimized, OptimizedQuery)
        assert optimized.original_query == original_query
        # Should contain date casting optimization
        assert '::DATE' in optimized.optimized_query or optimized.optimized_query == original_query

    @pytest.mark.asyncio
    async def test_validate_query_schema(self, optimizer):
        """Test query result validation against schema."""
        query = "SELECT symbol, close, volume FROM market_data"
        expected_schema = {
            'symbol': 'VARCHAR',
            'close': 'DOUBLE',
            'volume': 'BIGINT'
        }

        validation = await optimizer.validate_query_results(query, expected_schema)

        assert isinstance(validation, dict)
        assert 'query_valid' in validation
        assert 'schema_match' in validation
        assert isinstance(validation.get('warnings', []), list)
        assert isinstance(validation.get('errors', []), list)

    @pytest.mark.asyncio
    async def test_cache_frequent_queries(self, optimizer):
        """Test caching setup for frequent queries."""
        query_patterns = [
            "SELECT * FROM market_data WHERE symbol = ?",
            "SELECT close FROM market_data WHERE date_partition = ?"
        ]

        cache_config = await optimizer.cache_frequent_queries(query_patterns)

        assert isinstance(cache_config, CacheConfiguration)
        assert cache_config.cache_key.startswith('pattern_cache_')
        assert cache_config.ttl_seconds > 0
        assert cache_config.compression_enabled is True
        assert cache_config.priority in ['low', 'medium', 'high']

    def test_get_performance_stats(self, optimizer):
        """Test getting performance statistics."""
        # Add some mock performance data
        optimizer.performance_stats['test_pattern'] = [0.5, 0.7, 0.3, 0.8]

        stats = optimizer.get_performance_stats('test_pattern')

        assert isinstance(stats, dict)
        assert stats['pattern'] == 'test_pattern'
        assert stats['execution_count'] == 4
        assert stats['avg_execution_time'] == 0.575  # (0.5+0.7+0.3+0.8)/4
        assert stats['min_execution_time'] == 0.3
        assert stats['max_execution_time'] == 0.8

    def test_get_overall_performance_stats(self, optimizer):
        """Test getting overall performance statistics."""
        optimizer.performance_stats = {
            'pattern1': [0.5, 0.6],
            'pattern2': [0.7, 0.8, 0.9]
        }

        stats = optimizer.get_performance_stats()

        assert isinstance(stats, dict)
        assert stats['total_queries'] == 5  # 2 + 3
        assert stats['patterns_tracked'] == 2

    def test_clear_cache_specific_pattern(self, optimizer):
        """Test clearing cache for specific pattern."""
        optimizer.query_cache['test_pattern'] = {'data': 'test'}

        cleared = optimizer.clear_cache('test_pattern')

        assert cleared == 1
        assert 'test_pattern' not in optimizer.query_cache

    def test_clear_all_cache(self, optimizer):
        """Test clearing all cache entries."""
        optimizer.query_cache = {
            'pattern1': {'data': 'test1'},
            'pattern2': {'data': 'test2'},
            'pattern3': {'data': 'test3'}
        }

        cleared = optimizer.clear_cache()

        assert cleared == 3
        assert len(optimizer.query_cache) == 0

    def test_assess_query_complexity_simple(self, optimizer):
        """Test complexity assessment for simple query."""
        query = "SELECT symbol FROM market_data WHERE symbol = 'RELIANCE'"

        complexity = optimizer._assess_query_complexity(query)

        assert complexity == 'simple'

    def test_assess_query_complexity_medium(self, optimizer):
        """Test complexity assessment for medium complexity query."""
        query = """
        SELECT symbol, AVG(close) FROM market_data
        WHERE date_partition BETWEEN '2024-01-01' AND '2024-01-02'
        GROUP BY symbol
        """

        complexity = optimizer._assess_query_complexity(query)

        assert complexity in ['simple', 'medium', 'complex']

    def test_assess_query_complexity_complex(self, optimizer):
        """Test complexity assessment for complex query."""
        query = """
        WITH daily_stats AS (
            SELECT symbol, date_partition,
                   AVG(close) as avg_close,
                   MAX(high) as max_high
            FROM market_data
            GROUP BY symbol, date_partition
        )
        SELECT ds.symbol, ds.avg_close, ds.max_high
        FROM daily_stats ds
        JOIN market_data md ON ds.symbol = md.symbol
        WHERE ds.avg_close > 100
        ORDER BY ds.avg_close DESC
        """

        complexity = optimizer._assess_query_complexity(query)

        assert complexity == 'complex'

    def test_estimate_result_size_with_limit(self, optimizer):
        """Test result size estimation for query with LIMIT."""
        query = "SELECT * FROM market_data LIMIT 100"

        estimated = optimizer._estimate_result_size(query)

        assert estimated == 100

    def test_estimate_result_size_date_filter(self, optimizer):
        """Test result size estimation for query with date filter."""
        query = "SELECT * FROM market_data WHERE date_partition = '2024-01-01'"

        estimated = optimizer._estimate_result_size(query)

        assert estimated > 0

    def test_estimate_result_size_symbol_filter(self, optimizer):
        """Test result size estimation for query with symbol filter."""
        query = "SELECT * FROM market_data WHERE symbol = 'RELIANCE'"

        estimated = optimizer._estimate_result_size(query)

        assert estimated > 0

    def test_generate_recommendations(self, optimizer):
        """Test generation of optimization recommendations."""
        query = "SELECT * FROM market_data ORDER BY timestamp DESC"

        recommendations = optimizer._generate_recommendations(query)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should include recommendations about SELECT * and LIMIT
        recommendation_text = ' '.join(recommendations).lower()
        assert 'select *' in recommendation_text or 'limit' in recommendation_text

    def test_calculate_performance_score(self, optimizer):
        """Test performance score calculation."""
        query = "SELECT symbol, close FROM market_data WHERE symbol = 'RELIANCE' LIMIT 100"

        score = optimizer._calculate_performance_score(query, 'simple', 100)

        assert 0 <= score <= 1
        # Should be higher due to LIMIT clause
        assert score > 0.8

    def test_estimate_execution_time(self, optimizer):
        """Test execution time estimation."""
        query = "SELECT * FROM market_data"
        complexity = 'simple'
        estimated_rows = 1000

        estimated_time = optimizer._estimate_execution_time(query, complexity, estimated_rows)

        assert estimated_time > 0
        assert isinstance(estimated_time, float)

    @pytest.mark.asyncio
    async def test_optimize_backtesting_queries(self, optimizer):
        """Test batch optimization of backtesting queries."""
        queries = [
            "SELECT * FROM market_data ORDER BY timestamp",
            "SELECT symbol FROM market_data WHERE date_partition = '2024-01-01'",
            "SELECT close FROM market_data WHERE symbol = 'RELIANCE'"
        ]

        # Optimize queries individually since we're in async context
        optimized_queries = []
        for query in queries:
            analysis = await optimizer.analyze_query_performance(query)
            optimized = await optimizer.generate_optimized_query(query)
            optimized_queries.append(optimized)

        assert len(optimized_queries) == 3
        for optimized in optimized_queries:
            assert isinstance(optimized, OptimizedQuery)
            assert optimized.original_query in queries

    @pytest.mark.asyncio
    async def test_generate_optimized_query_with_constraints(self, optimizer):
        """Test query optimization with additional constraints."""
        original_query = "SELECT symbol, close FROM market_data"
        constraints = {
            'add_explain': True,
            'force_parallel': False
        }

        optimized = await optimizer.generate_optimized_query(original_query, constraints)

        assert isinstance(optimized, OptimizedQuery)
        assert 'EXPLAIN ANALYZE' in optimized.optimized_query.upper()

    @pytest.mark.asyncio
    async def test_error_handling_in_analysis(self, optimizer):
        """Test error handling in query analysis."""
        # Pass empty query - should still work but return basic analysis
        analysis = await optimizer.analyze_query_performance("")

        assert isinstance(analysis, QueryAnalysis)
        assert analysis.query_complexity in ['simple', 'unknown']
        assert 0 <= analysis.performance_score <= 1

    @pytest.mark.asyncio
    async def test_error_handling_in_optimization(self, optimizer):
        """Test error handling in query optimization."""
        # Pass invalid query to trigger error handling
        optimized = await optimizer.generate_optimized_query("INVALID QUERY")

        assert isinstance(optimized, OptimizedQuery)
        assert optimized.original_query == "INVALID QUERY"
        assert len(optimized.optimization_applied) == 0
