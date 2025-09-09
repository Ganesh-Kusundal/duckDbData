"""
Data Service
============

Application service for managing data operations and transformations.
This service provides high-level data management functionality by
coordinating between domain services and repositories.

Features:
- Data transformation and enrichment
- Data aggregation and summarization
- Data export and import operations
- Data quality monitoring
- Performance optimization for data operations
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime
from dataclasses import dataclass
import pandas as pd

from ...domain.repositories.market_data_repo import MarketDataRepository
from ...application.ports.event_bus_port import EventBusPort
from ...infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DataQuery:
    """Data query specification."""
    symbols: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    columns: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    aggregation: Optional[str] = None
    limit: Optional[int] = None


@dataclass
class DataTransformation:
    """Data transformation specification."""
    operation: str
    parameters: Dict[str, Any]
    input_columns: List[str]
    output_columns: List[str]


@dataclass
class DataResult:
    """Result from data service operations."""
    data: Any
    metadata: Dict[str, Any]
    execution_time_seconds: float
    timestamp: datetime


class DataService:
    """
    Application service for data operations and transformations.

    This service provides high-level data management by coordinating
    between domain services and repositories.
    """

    def __init__(
        self,
        market_data_repo: MarketDataRepository,
        event_bus: EventBusPort
    ):
        """
        Initialize the data service.

        Args:
            market_data_repo: Repository for market data access
            event_bus: Event bus for publishing data events
        """
        self.market_data_repo = market_data_repo
        self.event_bus = event_bus

        logger.info("DataService initialized")

    def query_market_data(self, query: DataQuery) -> DataResult:
        """
        Query market data with advanced filtering and aggregation.

        Args:
            query: Data query specification

        Returns:
            DataResult with query results
        """
        start_time = datetime.now()
        logger.info("Executing market data query")

        try:
            # Build query parameters
            query_params = {
                'symbols': query.symbols,
                'start_date': query.start_date,
                'end_date': query.end_date,
                'columns': query.columns,
                'limit': query.limit
            }

            # Execute query
            data = self.market_data_repo.get_market_data(**query_params)

            # Apply filters if specified
            if query.filters:
                data = self._apply_filters(data, query.filters)

            # Apply aggregation if specified
            if query.aggregation:
                data = self._apply_aggregation(data, query.aggregation)

            # Calculate metadata
            metadata = {
                'total_records': len(data) if hasattr(data, '__len__') else 0,
                'columns': list(data.columns) if hasattr(data, 'columns') else [],
                'query_parameters': query_params,
                'filters_applied': bool(query.filters),
                'aggregation_applied': bool(query.aggregation)
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            result = DataResult(
                data=data,
                metadata=metadata,
                execution_time_seconds=execution_time,
                timestamp=start_time
            )

            # Publish query event
            self._publish_data_event('query_executed', result)

            logger.info(f"Market data query completed: {metadata['total_records']} records in {execution_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Market data query failed: {e}")
            raise

    def transform_data(self, data: Any, transformations: List[DataTransformation]) -> DataResult:
        """
        Apply transformations to data.

        Args:
            data: Input data to transform
            transformations: List of transformations to apply

        Returns:
            DataResult with transformed data
        """
        start_time = datetime.now()
        logger.info(f"Applying {len(transformations)} data transformations")

        try:
            transformed_data = data.copy() if hasattr(data, 'copy') else data

            applied_transformations = []

            for transformation in transformations:
                logger.debug(f"Applying transformation: {transformation.operation}")

                transformed_data = self._apply_transformation(
                    transformed_data, transformation
                )

                applied_transformations.append(transformation.operation)

            metadata = {
                'original_shape': self._get_data_shape(data),
                'transformed_shape': self._get_data_shape(transformed_data),
                'transformations_applied': applied_transformations,
                'total_transformations': len(transformations)
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            result = DataResult(
                data=transformed_data,
                metadata=metadata,
                execution_time_seconds=execution_time,
                timestamp=start_time
            )

            # Publish transformation event
            self._publish_data_event('data_transformed', result)

            logger.info(f"Data transformation completed in {execution_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Data transformation failed: {e}")
            raise

    def export_data(self, data: Any, format: str, destination: str, **kwargs) -> DataResult:
        """
        Export data to various formats.

        Args:
            data: Data to export
            format: Export format (csv, json, parquet, etc.)
            destination: Export destination path
            **kwargs: Additional export parameters

        Returns:
            DataResult with export metadata
        """
        start_time = datetime.now()
        logger.info(f"Exporting data to {format} format")

        try:
            # Ensure destination directory exists
            import os
            os.makedirs(os.path.dirname(destination), exist_ok=True)

            # Export based on format
            if format.lower() == 'csv':
                data.to_csv(destination, **kwargs)
            elif format.lower() == 'json':
                data.to_json(destination, **kwargs)
            elif format.lower() == 'parquet':
                data.to_parquet(destination, **kwargs)
            elif format.lower() == 'excel':
                data.to_excel(destination, **kwargs)
            else:
                raise ValueError(f"Unsupported export format: {format}")

            metadata = {
                'export_format': format,
                'destination': destination,
                'records_exported': len(data) if hasattr(data, '__len__') else 0,
                'file_size': os.path.getsize(destination) if os.path.exists(destination) else 0
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            result = DataResult(
                data=None,  # No data returned for export
                metadata=metadata,
                execution_time_seconds=execution_time,
                timestamp=start_time
            )

            # Publish export event
            self._publish_data_event('data_exported', result)

            logger.info(f"Data export completed: {destination}")
            return result

        except Exception as e:
            logger.error(f"Data export failed: {e}")
            raise

    def aggregate_market_data(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        aggregation_level: str = 'daily'
    ) -> DataResult:
        """
        Aggregate market data at specified level.

        Args:
            symbols: List of symbols to aggregate
            start_date: Start date for aggregation
            end_date: End date for aggregation
            aggregation_level: Aggregation level (daily, weekly, monthly)

        Returns:
            DataResult with aggregated data
        """
        start_time = datetime.now()
        logger.info(f"Aggregating market data for {len(symbols)} symbols")

        try:
            # Query data for all symbols
            all_data = []
            for symbol in symbols:
                data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                if not data.empty:
                    all_data.append(data)

            if not all_data:
                raise ValueError("No data found for specified symbols and date range")

            # Combine all data
            combined_data = pd.concat(all_data, ignore_index=True)

            # Apply time-based aggregation
            if aggregation_level == 'weekly':
                combined_data['week'] = combined_data['timestamp'].dt.to_period('W')
                aggregated = combined_data.groupby(['symbol', 'week']).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).reset_index()
            elif aggregation_level == 'monthly':
                combined_data['month'] = combined_data['timestamp'].dt.to_period('M')
                aggregated = combined_data.groupby(['symbol', 'month']).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).reset_index()
            else:  # daily
                aggregated = combined_data

            metadata = {
                'symbols_processed': len(symbols),
                'aggregation_level': aggregation_level,
                'date_range': f"{start_date} to {end_date}",
                'total_records': len(aggregated),
                'original_records': sum(len(df) for df in all_data)
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            result = DataResult(
                data=aggregated,
                metadata=metadata,
                execution_time_seconds=execution_time,
                timestamp=start_time
            )

            # Publish aggregation event
            self._publish_data_event('data_aggregated', result)

            logger.info(f"Data aggregation completed: {len(aggregated)} records")
            return result

        except Exception as e:
            logger.error(f"Data aggregation failed: {e}")
            raise

    def get_data_quality_metrics(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get data quality metrics for symbols.

        Args:
            symbols: List of symbols to check (all if None)

        Returns:
            Dictionary with quality metrics
        """
        logger.info("Calculating data quality metrics")

        if not symbols:
            symbols = self.market_data_repo.get_all_symbols()

        quality_metrics = {}

        for symbol in symbols:
            try:
                # Get recent data for quality check
                data = self.market_data_repo.get_market_data(
                    symbol=symbol,
                    limit=1000  # Sample for quality metrics
                )

                if data.empty:
                    quality_metrics[symbol] = {'status': 'no_data'}
                    continue

                # Calculate quality metrics
                metrics = {
                    'total_records': len(data),
                    'null_percentage': (data.isnull().sum().sum() / (len(data) * len(data.columns))) * 100,
                    'duplicate_percentage': (data.duplicated().sum() / len(data)) * 100,
                    'completeness_score': 100 - ((data.isnull().sum().sum() / (len(data) * len(data.columns))) * 100)
                }

                quality_metrics[symbol] = metrics

            except Exception as e:
                logger.error(f"Failed to calculate quality metrics for {symbol}: {e}")
                quality_metrics[symbol] = {'status': 'error', 'error': str(e)}

        return quality_metrics

    def _apply_filters(self, data: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply filters to data.

        Args:
            data: Data to filter
            filters: Filter specifications

        Returns:
            Filtered data
        """
        filtered_data = data.copy()

        for column, condition in filters.items():
            if column not in filtered_data.columns:
                logger.warning(f"Filter column not found: {column}")
                continue

            if isinstance(condition, dict):
                # Complex condition
                if 'min' in condition:
                    filtered_data = filtered_data[filtered_data[column] >= condition['min']]
                if 'max' in condition:
                    filtered_data = filtered_data[filtered_data[column] <= condition['max']]
                if 'equals' in condition:
                    filtered_data = filtered_data[filtered_data[column] == condition['equals']]
            else:
                # Simple equality filter
                filtered_data = filtered_data[filtered_data[column] == condition]

        return filtered_data

    def _apply_aggregation(self, data: pd.DataFrame, aggregation: str) -> pd.DataFrame:
        """
        Apply aggregation to data.

        Args:
            data: Data to aggregate
            aggregation: Aggregation specification

        Returns:
            Aggregated data
        """
        if aggregation == 'daily':
            # Group by date
            data['date'] = pd.to_datetime(data['timestamp']).dt.date
            return data.groupby('date').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).reset_index()
        elif aggregation == 'symbol_summary':
            # Group by symbol
            return data.groupby('symbol').agg({
                'close': ['mean', 'std', 'min', 'max'],
                'volume': 'sum'
            }).reset_index()
        else:
            logger.warning(f"Unknown aggregation: {aggregation}")
            return data

    def _apply_transformation(self, data: Any, transformation: DataTransformation) -> Any:
        """
        Apply a single transformation to data.

        Args:
            data: Data to transform
            transformation: Transformation specification

        Returns:
            Transformed data
        """
        operation = transformation.operation.lower()

        if operation == 'add_column':
            # Add a new calculated column
            formula = transformation.parameters.get('formula', '')
            if formula and hasattr(data, 'eval'):
                data[transformation.output_columns[0]] = data.eval(formula)

        elif operation == 'normalize':
            # Normalize columns
            for col in transformation.input_columns:
                if col in data.columns:
                    mean_val = data[col].mean()
                    std_val = data[col].std()
                    data[f"{col}_normalized"] = (data[col] - mean_val) / std_val

        elif operation == 'percentage_change':
            # Calculate percentage change
            for col in transformation.input_columns:
                if col in data.columns:
                    data[f"{col}_pct_change"] = data[col].pct_change()

        elif operation == 'moving_average':
            # Calculate moving average
            window = transformation.parameters.get('window', 20)
            for col in transformation.input_columns:
                if col in data.columns:
                    data[f"{col}_ma_{window}"] = data[col].rolling(window=window).mean()

        else:
            logger.warning(f"Unknown transformation operation: {operation}")

        return data

    def _get_data_shape(self, data: Any) -> tuple:
        """
        Get data shape information.

        Args:
            data: Data to analyze

        Returns:
            Tuple with shape information
        """
        if hasattr(data, 'shape'):
            return data.shape
        elif hasattr(data, '__len__'):
            return (len(data),)
        else:
            return (0,)

    def _publish_data_event(self, event_type: str, result: DataResult):
        """
        Publish data operation event.

        Args:
            event_type: Type of data event
            result: Operation result
        """
        event_data = {
            'operation_type': event_type,
            'metadata': result.metadata,
            'execution_time_seconds': result.execution_time_seconds,
            'timestamp': result.timestamp.isoformat()
        }

        try:
            self.event_bus.publish({
                'event_type': f'data_{event_type}',
                'data': event_data,
                'timestamp': datetime.now().isoformat()
            })
            logger.debug(f"Published data event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish data event: {e}")

    def optimize_query_performance(self, query: DataQuery) -> Dict[str, Any]:
        """
        Optimize query performance with suggestions.

        Args:
            query: Query to optimize

        Returns:
            Dictionary with optimization suggestions
        """
        suggestions = []

        # Check for potential optimizations
        if not query.limit and not query.symbols:
            suggestions.append("Consider adding a limit to prevent large result sets")

        if query.start_date and query.end_date:
            date_range = (query.end_date - query.start_date).days
            if date_range > 365:
                suggestions.append("Large date range detected - consider partitioning")

        if query.symbols and len(query.symbols) > 50:
            suggestions.append("Many symbols requested - consider batching")

        return {
            'optimizations_available': len(suggestions) > 0,
            'suggestions': suggestions,
            'estimated_complexity': 'high' if len(suggestions) > 2 else 'medium' if len(suggestions) > 0 else 'low'
        }
