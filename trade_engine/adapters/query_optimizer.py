"""
Query Optimization Adapter
==========================

Optimizes DuckDB queries for backtesting performance and memory efficiency.
Provides intelligent query optimization, caching, and performance monitoring.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
import hashlib

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QueryAnalysis:
    """Analysis results for a query."""
    query_complexity: str  # 'simple', 'medium', 'complex'
    estimated_rows: int
    recommended_optimizations: List[str]
    performance_score: float  # 0-1, higher is better
    execution_time_estimate: float  # seconds


@dataclass
class OptimizedQuery:
    """Optimized query with metadata."""
    original_query: str
    optimized_query: str
    optimization_applied: List[str]
    expected_improvement: float  # percentage
    cache_key: Optional[str] = None


@dataclass
class CacheConfiguration:
    """Query caching configuration."""
    cache_key: str
    ttl_seconds: int
    compression_enabled: bool
    priority: str  # 'low', 'medium', 'high'


class QueryOptimizer:
    """
    Intelligent query optimizer for DuckDB backtesting operations.

    Provides automatic query optimization, result caching, and performance
    monitoring to ensure efficient data access for trading algorithms.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize query optimizer.

        Args:
            config: Configuration dictionary with optimization settings
        """
        self.config = config
        self.query_cache: Dict[str, Any] = {}
        self.performance_stats: Dict[str, List[float]] = {}
        self.optimization_rules = self._load_optimization_rules()

        # Cache settings
        self.cache_enabled = config.get('query_cache', {}).get('enabled', True)
        self.cache_ttl = config.get('query_cache', {}).get('ttl_seconds', 3600)  # 1 hour
        self.max_cache_size = config.get('query_cache', {}).get('max_size', 100)

        logger.info("QueryOptimizer initialized with cache settings", cache_enabled=self.cache_enabled)

    def _load_optimization_rules(self) -> Dict[str, Any]:
        """
        Load query optimization rules.

        Returns:
            Dictionary of optimization rules
        """
        return {
            'add_limit_clause': {
                'pattern': r'SELECT.*FROM.*ORDER BY.*$',
                'replacement': r'\g<0> LIMIT 1000',
                'condition': lambda q: 'LIMIT' not in q.upper(),
                'improvement': 0.3,
                'description': 'Add LIMIT clause to prevent excessive data retrieval'
            },
            'optimize_date_filters': {
                'pattern': r"date_partition\s*=\s*'([^']+)'",
                'replacement': r"date_partition = '\1'::DATE",
                'improvement': 0.2,
                'description': 'Cast date strings to DATE type for better performance'
            },
            'use_partition_pruning': {
                'pattern': r'WHERE.*date_partition.*BETWEEN.*AND.*',
                'improvement': 0.4,
                'description': 'Ensure date range filters use partition pruning'
            },
            'optimize_symbol_filters': {
                'pattern': r"symbol\s*=\s*'([^']+)'",
                'improvement': 0.15,
                'description': 'Use indexed symbol filtering'
            },
            'add_time_filters': {
                'pattern': r'WHERE.*timestamp.*BETWEEN.*AND.*',
                'improvement': 0.25,
                'description': 'Add time-based filters to reduce data volume'
            }
        }

    async def analyze_query_performance(self, query: str) -> QueryAnalysis:
        """
        Analyze query performance characteristics.

        Args:
            query: SQL query to analyze

        Returns:
            QueryAnalysis with performance insights
        """
        try:
            # Analyze query complexity
            complexity = self._assess_query_complexity(query)

            # Estimate result size
            estimated_rows = self._estimate_result_size(query)

            # Generate optimization recommendations
            recommendations = self._generate_recommendations(query)

            # Calculate performance score
            performance_score = self._calculate_performance_score(query, complexity, estimated_rows)

            # Estimate execution time
            execution_estimate = self._estimate_execution_time(query, complexity, estimated_rows)

            analysis = QueryAnalysis(
                query_complexity=complexity,
                estimated_rows=estimated_rows,
                recommended_optimizations=recommendations,
                performance_score=performance_score,
                execution_time_estimate=execution_estimate
            )

            logger.debug(f"Query analysis complete: complexity={complexity}, estimated_rows={estimated_rows}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing query performance: {e}")
            return QueryAnalysis(
                query_complexity='unknown',
                estimated_rows=0,
                recommended_optimizations=['Error during analysis'],
                performance_score=0.0,
                execution_time_estimate=0.0
            )

    def _assess_query_complexity(self, query: str) -> str:
        """
        Assess query complexity based on various factors.

        Args:
            query: SQL query

        Returns:
            Complexity level: 'simple', 'medium', 'complex'
        """
        query_upper = query.upper()

        complexity_score = 0

        # Check for complex operations
        if 'JOIN' in query_upper:
            complexity_score += 3
        if 'GROUP BY' in query_upper:
            complexity_score += 2
        if 'ORDER BY' in query_upper:
            complexity_score += 1
        if 'HAVING' in query_upper:
            complexity_score += 2
        if 'UNION' in query_upper:
            complexity_score += 2
        if 'SUBQUERY' in query_upper or 'WITH' in query_upper:
            complexity_score += 3
        if 'WINDOW' in query_upper or 'OVER' in query_upper:
            complexity_score += 2

        # Check for multiple tables
        table_count = query_upper.count('FROM') + query_upper.count('JOIN')
        complexity_score += max(0, table_count - 1) * 2

        # Determine complexity level
        if complexity_score <= 2:
            return 'simple'
        elif complexity_score <= 5:
            return 'medium'
        else:
            return 'complex'

    def _estimate_result_size(self, query: str) -> int:
        """
        Estimate the number of rows the query will return.

        Args:
            query: SQL query

        Returns:
            Estimated row count
        """
        query_upper = query.upper()

        # Simple heuristics for estimation
        if 'LIMIT' in query_upper:
            # Extract LIMIT value
            limit_match = re.search(r'LIMIT\s+(\d+)', query_upper)
            if limit_match:
                return min(int(limit_match.group(1)), 10000)  # Cap at 10k for safety

        # Check for date filters
        if 'date_partition' in query_upper:
            # Estimate based on date range
            if 'BETWEEN' in query_upper:
                # Assume daily data volume
                return 5000  # Conservative estimate
            else:
                # Single date
                return 1000

        # Check for symbol filters
        if 'symbol =' in query_upper:
            # Single symbol query
            return 500

        # Default estimate
        return 10000

    def _generate_recommendations(self, query: str) -> List[str]:
        """
        Generate optimization recommendations for the query.

        Args:
            query: SQL query

        Returns:
            List of optimization recommendations
        """
        recommendations = []
        query_upper = query.upper()

        # Check optimization rules
        for rule_name, rule_config in self.optimization_rules.items():
            pattern = rule_config['pattern']
            condition = rule_config.get('condition', lambda q: True)

            if re.search(pattern, query, re.IGNORECASE) and condition(query):
                recommendations.append(rule_config['description'])

        # General recommendations
        if 'SELECT *' in query_upper and 'LIMIT' not in query_upper:
            recommendations.append('Consider selecting specific columns instead of SELECT *')

        if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper:
            recommendations.append('Consider adding LIMIT clause when using ORDER BY')

        if 'LIKE' in query_upper:
            recommendations.append('Consider using more specific filters instead of LIKE for better performance')

        return recommendations[:5]  # Limit to top 5 recommendations

    def _calculate_performance_score(self, query: str, complexity: str, estimated_rows: int) -> float:
        """
        Calculate performance score for the query.

        Args:
            query: SQL query
            complexity: Query complexity level
            estimated_rows: Estimated result size

        Returns:
            Performance score (0-1)
        """
        score = 1.0

        # Complexity penalty
        if complexity == 'medium':
            score *= 0.8
        elif complexity == 'complex':
            score *= 0.6

        # Row count penalty
        if estimated_rows > 10000:
            score *= 0.7
        elif estimated_rows > 1000:
            score *= 0.9

        # Query structure bonuses/penalties
        query_upper = query.upper()

        if 'LIMIT' in query_upper:
            score *= 1.1
        if 'SELECT *' in query_upper:
            score *= 0.95
        if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper:
            score *= 0.9

        return max(0.0, min(1.0, score))

    def _estimate_execution_time(self, query: str, complexity: str, estimated_rows: int) -> float:
        """
        Estimate query execution time.

        Args:
            query: SQL query
            complexity: Query complexity level
            estimated_rows: Estimated result size

        Returns:
            Estimated execution time in seconds
        """
        base_time = 0.1  # Base execution time

        # Complexity multiplier
        if complexity == 'medium':
            base_time *= 2
        elif complexity == 'complex':
            base_time *= 5

        # Row count multiplier
        if estimated_rows > 10000:
            base_time *= 3
        elif estimated_rows > 1000:
            base_time *= 1.5

        return base_time

    async def generate_optimized_query(self, original_query: str,
                                     constraints: Optional[Dict[str, Any]] = None) -> OptimizedQuery:
        """
        Generate an optimized version of the query.

        Args:
            original_query: Original SQL query
            constraints: Optional constraints for optimization

        Returns:
            OptimizedQuery with improvements
        """
        try:
            optimized_query = original_query
            optimizations_applied = []
            total_improvement = 0.0

            # Apply optimization rules
            for rule_name, rule_config in self.optimization_rules.items():
                pattern = rule_config['pattern']
                replacement = rule_config.get('replacement', '')
                condition = rule_config.get('condition', lambda q: True)
                improvement = rule_config.get('improvement', 0.0)

                if re.search(pattern, optimized_query, re.IGNORECASE) and condition(optimized_query):
                    if replacement:
                        optimized_query = re.sub(pattern, replacement, optimized_query, flags=re.IGNORECASE)
                        optimizations_applied.append(rule_name)
                        total_improvement += improvement

            # Apply additional optimizations based on constraints
            if constraints:
                if constraints.get('add_explain', False):
                    optimized_query = f"EXPLAIN ANALYZE {optimized_query}"

                if constraints.get('force_parallel', False):
                    # Add hints for parallel execution (DuckDB specific)
                    optimized_query = f"SET threads=4; {optimized_query}"

            # Generate cache key if caching is enabled
            cache_key = None
            if self.cache_enabled and len(optimizations_applied) > 0:
                cache_key = hashlib.md5(optimized_query.encode()).hexdigest()[:16]

            result = OptimizedQuery(
                original_query=original_query,
                optimized_query=optimized_query,
                optimization_applied=optimizations_applied,
                expected_improvement=total_improvement,
                cache_key=cache_key
            )

            logger.info(f"Query optimization complete: applied {len(optimizations_applied)} optimizations")
            return result

        except Exception as e:
            logger.error(f"Error generating optimized query: {e}")
            return OptimizedQuery(
                original_query=original_query,
                optimized_query=original_query,
                optimization_applied=[],
                expected_improvement=0.0
            )

    async def validate_query_results(self, query: str, expected_schema: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate query results against expected schema.

        Args:
            query: SQL query to validate
            expected_schema: Expected column schema as {column_name: data_type}

        Returns:
            Validation results dictionary
        """
        try:
            # This would typically execute the query and validate results
            # For now, return mock validation
            validation_results = {
                'query_valid': True,
                'schema_match': True,
                'performance_acceptable': True,
                'warnings': [],
                'errors': []
            }

            # Basic validation checks
            query_upper = query.upper()

            if 'SELECT' not in query_upper:
                validation_results['errors'].append('Query must contain SELECT statement')

            if len(expected_schema) == 0:
                validation_results['warnings'].append('No expected schema provided for validation')

            # Check for common issues
            if 'DROP' in query_upper or 'DELETE' in query_upper:
                validation_results['warnings'].append('Query contains data modification statements')

            return validation_results

        except Exception as e:
            logger.error(f"Error validating query results: {e}")
            return {
                'query_valid': False,
                'errors': [str(e)]
            }

    async def cache_frequent_queries(self, query_patterns: List[str]) -> CacheConfiguration:
        """
        Set up caching for frequent query patterns.

        Args:
            query_patterns: List of query patterns to cache

        Returns:
            CacheConfiguration for the query patterns
        """
        try:
            # Generate cache key from patterns
            pattern_hash = hashlib.md5(str(sorted(query_patterns)).encode()).hexdigest()[:16]
            cache_key = f"pattern_cache_{pattern_hash}"

            config = CacheConfiguration(
                cache_key=cache_key,
                ttl_seconds=self.cache_ttl,
                compression_enabled=True,
                priority='medium'
            )

            # Store in cache configuration
            self.query_cache[cache_key] = {
                'patterns': query_patterns,
                'config': config,
                'created_at': time.time()
            }

            logger.info(f"Set up caching for {len(query_patterns)} query patterns")
            return config

        except Exception as e:
            logger.error(f"Error setting up query caching: {e}")
            return CacheConfiguration(
                cache_key="error_cache",
                ttl_seconds=300,
                compression_enabled=False,
                priority='low'
            )

    def get_performance_stats(self, query_pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics for queries.

        Args:
            query_pattern: Optional pattern to filter stats

        Returns:
            Performance statistics dictionary
        """
        if query_pattern and query_pattern in self.performance_stats:
            stats = self.performance_stats[query_pattern]
            return {
                'pattern': query_pattern,
                'execution_count': len(stats),
                'avg_execution_time': sum(stats) / len(stats) if stats else 0,
                'min_execution_time': min(stats) if stats else 0,
                'max_execution_time': max(stats) if stats else 0,
                'total_execution_time': sum(stats)
            }

        # Return overall stats
        all_times = []
        for pattern_stats in self.performance_stats.values():
            all_times.extend(pattern_stats)

        return {
            'total_queries': len(all_times),
            'avg_execution_time': sum(all_times) / len(all_times) if all_times else 0,
            'total_execution_time': sum(all_times),
            'patterns_tracked': len(self.performance_stats)
        }

    def clear_cache(self, pattern: Optional[str] = None) -> int:
        """
        Clear query cache.

        Args:
            pattern: Optional pattern to clear (clears all if None)

        Returns:
            Number of cache entries cleared
        """
        if pattern:
            if pattern in self.query_cache:
                del self.query_cache[pattern]
                return 1
            return 0
        else:
            cleared_count = len(self.query_cache)
            self.query_cache.clear()
            logger.info(f"Cleared {cleared_count} cache entries")
            return cleared_count

    def optimize_backtesting_queries(self, queries: List[str]) -> List[OptimizedQuery]:
        """
        Optimize a batch of backtesting queries.

        Args:
            queries: List of SQL queries to optimize

        Returns:
            List of optimized queries
        """
        optimized_queries = []

        for query in queries:
            # Analyze and optimize each query
            analysis = asyncio.run(self.analyze_query_performance(query))
            optimized = asyncio.run(self.generate_optimized_query(query))
            optimized_queries.append(optimized)

        logger.info(f"Optimized {len(queries)} backtesting queries")
        return optimized_queries
