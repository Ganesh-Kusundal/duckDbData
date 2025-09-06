"""
Advanced Query Builder for Complex DuckDB Operations
====================================================

Provides a fluent interface for building complex SQL queries with:
- Dynamic WHERE clauses
- JOIN operations
- Window functions
- Aggregations
- CTEs (Common Table Expressions)
- Subqueries
"""

from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd


class JoinType(Enum):
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL OUTER JOIN"
    CROSS = "CROSS JOIN"


class AggregateFunction(Enum):
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    STDDEV = "STDDEV"
    VARIANCE = "VARIANCE"


class WindowFunction(Enum):
    ROW_NUMBER = "ROW_NUMBER"
    RANK = "RANK"
    DENSE_RANK = "DENSE_RANK"
    PERCENT_RANK = "PERCENT_RANK"
    CUME_DIST = "CUME_DIST"
    LAG = "LAG"
    LEAD = "LEAD"
    FIRST_VALUE = "FIRST_VALUE"
    LAST_VALUE = "LAST_VALUE"


@dataclass
class JoinClause:
    """Represents a JOIN clause in SQL."""
    table: str
    join_type: JoinType
    on_condition: str
    alias: Optional[str] = None


@dataclass
class WhereClause:
    """Represents a WHERE condition."""
    column: str
    operator: str
    value: Any
    logical_operator: str = "AND"


@dataclass
class OrderByClause:
    """Represents an ORDER BY clause."""
    column: str
    direction: str = "ASC"


@dataclass
class GroupByClause:
    """Represents a GROUP BY clause."""
    columns: List[str]


@dataclass
class WindowClause:
    """Represents a window function."""
    function: WindowFunction
    partition_by: Optional[List[str]] = None
    order_by: Optional[List[OrderByClause]] = None
    alias: Optional[str] = None


class QueryBuilder:
    """
    Fluent interface for building SQL queries.
    """

    def __init__(self, base_table: str):
        self.base_table = base_table
        self._select_columns: List[str] = ["*"]
        self._joins: List[JoinClause] = []
        self._where_clauses: List[WhereClause] = []
        self._group_by: Optional[GroupByClause] = None
        self._having_clauses: List[WhereClause] = []
        self._order_by: List[OrderByClause] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._distinct: bool = False
        self._cte: Dict[str, str] = {}
        self._parameters: Dict[str, Any] = {}

    def select(self, *columns: str) -> 'QueryBuilder':
        """Specify columns to select."""
        self._select_columns = list(columns)
        return self

    def select_distinct(self, *columns: str) -> 'QueryBuilder':
        """Specify distinct columns to select."""
        self._distinct = True
        self._select_columns = list(columns)
        return self

    def join(self, table: str, on_condition: str, join_type: JoinType = JoinType.INNER,
             alias: Optional[str] = None) -> 'QueryBuilder':
        """Add a JOIN clause."""
        join_clause = JoinClause(
            table=table,
            join_type=join_type,
            on_condition=on_condition,
            alias=alias
        )
        self._joins.append(join_clause)
        return self

    def where(self, column: str, operator: str, value: Any,
              logical_operator: str = "AND") -> 'QueryBuilder':
        """Add a WHERE condition."""
        where_clause = WhereClause(
            column=column,
            operator=operator,
            value=value,
            logical_operator=logical_operator
        )
        self._where_clauses.append(where_clause)
        return self

    def where_in(self, column: str, values: List[Any],
                 logical_operator: str = "AND") -> 'QueryBuilder':
        """Add a WHERE IN condition."""
        if values:
            placeholders = ', '.join([f'${i+1}' for i in range(len(values))])
            condition = f"{column} IN ({placeholders})"
            self._cte[f"where_in_{column}"] = condition
            for i, value in enumerate(values):
                self._parameters[f"param_{i+1}"] = value
        return self

    def where_between(self, column: str, start_value: Any, end_value: Any,
                      logical_operator: str = "AND") -> 'QueryBuilder':
        """Add a WHERE BETWEEN condition."""
        where_clause = WhereClause(
            column=f"{column} BETWEEN ${len(self._parameters)+1} AND ${len(self._parameters)+2}",
            operator="",
            value=None,
            logical_operator=logical_operator
        )
        self._where_clauses.append(where_clause)
        self._parameters[f"param_{len(self._parameters)+1}"] = start_value
        self._parameters[f"param_{len(self._parameters)+2}"] = end_value
        return self

    def group_by(self, *columns: str) -> 'QueryBuilder':
        """Add GROUP BY clause."""
        self._group_by = GroupByClause(columns=list(columns))
        return self

    def having(self, column: str, operator: str, value: Any,
               logical_operator: str = "AND") -> 'QueryBuilder':
        """Add HAVING condition."""
        having_clause = WhereClause(
            column=column,
            operator=operator,
            value=value,
            logical_operator=logical_operator
        )
        self._having_clauses.append(having_clause)
        return self

    def order_by(self, column: str, direction: str = "ASC") -> 'QueryBuilder':
        """Add ORDER BY clause."""
        order_clause = OrderByClause(column=column, direction=direction.upper())
        self._order_by.append(order_clause)
        return self

    def limit(self, count: int) -> 'QueryBuilder':
        """Add LIMIT clause."""
        self._limit = count
        return self

    def offset(self, count: int) -> 'QueryBuilder':
        """Add OFFSET clause."""
        self._offset = count
        return self

    def with_cte(self, name: str, query: str) -> 'QueryBuilder':
        """Add a Common Table Expression (CTE)."""
        self._cte[name] = query
        return self

    def build(self) -> Tuple[str, Dict[str, Any]]:
        """Build the SQL query and return it with parameters."""
        query_parts = []

        # CTEs
        if self._cte:
            cte_parts = [f"{name} AS ({query})" for name, query in self._cte.items()]
            query_parts.append(f"WITH {', '.join(cte_parts)}")

        # SELECT
        distinct = "DISTINCT " if self._distinct else ""
        select_clause = f"SELECT {distinct}{', '.join(self._select_columns)}"
        query_parts.append(select_clause)

        # FROM
        query_parts.append(f"FROM {self.base_table}")

        # JOINS
        for join in self._joins:
            join_str = f"{join.join_type.value} {join.table}"
            if join.alias:
                join_str += f" AS {join.alias}"
            join_str += f" ON {join.on_condition}"
            query_parts.append(join_str)

        # WHERE
        if self._where_clauses:
            where_conditions = []
            for i, where_clause in enumerate(self._where_clauses):
                if i == 0:
                    condition = f"{where_clause.column} {where_clause.operator} ${len(self._parameters)+1}"
                else:
                    condition = f"{where_clause.logical_operator} {where_clause.column} {where_clause.operator} ${len(self._parameters)+1}"
                where_conditions.append(condition)
                self._parameters[f"param_{len(self._parameters)+1}"] = where_clause.value

            query_parts.append(f"WHERE {' '.join(where_conditions)}")

        # GROUP BY
        if self._group_by:
            query_parts.append(f"GROUP BY {', '.join(self._group_by.columns)}")

        # HAVING
        if self._having_clauses:
            having_conditions = []
            for having_clause in self._having_clauses:
                condition = f"{having_clause.column} {having_clause.operator} ${len(self._parameters)+1}"
                having_conditions.append(condition)
                self._parameters[f"param_{len(self._parameters)+1}"] = having_clause.value

            query_parts.append(f"HAVING {' '.join(having_conditions)}")

        # ORDER BY
        if self._order_by:
            order_parts = [f"{order.column} {order.direction}" for order in self._order_by]
            query_parts.append(f"ORDER BY {', '.join(order_parts)}")

        # LIMIT/OFFSET
        if self._limit:
            query_parts.append(f"LIMIT {self._limit}")
        if self._offset:
            query_parts.append(f"OFFSET {self._offset}")

        return " ".join(query_parts), self._parameters


class AdvancedQueryBuilder(QueryBuilder):
    """
    Advanced query builder with financial-specific features.
    """

    def __init__(self, base_table: str = "market_data"):
        super().__init__(base_table)

    def time_series_filter(self, start_date: str, end_date: str,
                          date_column: str = "timestamp") -> 'AdvancedQueryBuilder':
        """Add time series filtering."""
        return self.where_between(date_column, start_date, end_date)

    def symbol_filter(self, symbols: List[str]) -> 'AdvancedQueryBuilder':
        """Filter by specific symbols."""
        return self.where_in("symbol", symbols)

    def price_filter(self, min_price: Optional[float] = None,
                    max_price: Optional[float] = None) -> 'AdvancedQueryBuilder':
        """Filter by price range."""
        if min_price is not None:
            self.where("close", ">=", min_price)
        if max_price is not None:
            self.where("close", "<=", max_price)
        return self

    def volume_filter(self, min_volume: Optional[int] = None,
                     max_volume: Optional[int] = None) -> 'AdvancedQueryBuilder':
        """Filter by volume range."""
        if min_volume is not None:
            self.where("volume", ">=", min_volume)
        if max_volume is not None:
            self.where("volume", "<=", max_volume)
        return self

    def technical_indicator(self, indicator: str, period: int = 14) -> 'AdvancedQueryBuilder':
        """Add technical indicator calculation."""
        if indicator.lower() == "sma":
            self.with_cte("sma_calc",
                         f"SELECT *, AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS {period-1} PRECEDING) as sma_{period} FROM {self.base_table}")
            self._select_columns.append(f"sma_{period}")
        elif indicator.lower() == "rsi":
            # RSI calculation would be more complex
            pass
        return self

    def pivot_by_timeframe(self, timeframe: str = "1D") -> 'AdvancedQueryBuilder':
        """Create pivoted view by timeframe."""
        pivot_query = f"""
        SELECT
            symbol,
            date_trunc('{timeframe}', timestamp) as period,
            FIRST(open) as open,
            MAX(high) as high,
            MIN(low) as low,
            LAST(close) as close,
            SUM(volume) as volume
        FROM {self.base_table}
        GROUP BY symbol, date_trunc('{timeframe}', timestamp)
        ORDER BY symbol, period
        """
        self.with_cte("pivoted_data", pivot_query)
        self.base_table = "pivoted_data"
        return self

    def correlation_analysis(self, symbols: List[str]) -> 'AdvancedQueryBuilder':
        """Calculate correlation matrix for symbols."""
        if len(symbols) < 2:
            raise ValueError("Need at least 2 symbols for correlation analysis")

        # This would create a complex correlation query
        corr_query = f"""
        SELECT
            s1.symbol as symbol1,
            s2.symbol as symbol2,
            CORR(s1.close, s2.close) as correlation
        FROM {self.base_table} s1
        JOIN {self.base_table} s2 ON s1.timestamp = s2.timestamp
        WHERE s1.symbol IN ({','.join([f"'{s}'" for s in symbols])})
          AND s2.symbol IN ({','.join([f"'{s}'" for s in symbols])})
          AND s1.symbol < s2.symbol
        GROUP BY s1.symbol, s2.symbol
        """
        self.with_cte("correlation_matrix", corr_query)
        self.base_table = "correlation_matrix"
        return self
