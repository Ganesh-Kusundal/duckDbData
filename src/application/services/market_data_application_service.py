"""
Market Data Application Service
Orchestrates market data operations using CQRS pattern
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..commands.base_command import get_command_bus, CommandResult
from ..queries.base_query import get_query_bus, QueryResult
from ..commands.market_data_commands import (
    UpdateMarketDataCommand,
    ValidateMarketDataCommand,
    ProcessMarketDataBatchCommand
)
from ..queries.market_data_queries import (
    GetMarketDataQuery,
    GetMarketDataHistoryQuery,
    GetMarketDataSummaryQuery
)
from domain.market_data.entities.market_data import MarketData, MarketDataBatch
from domain.market_data.value_objects.ohlcv import OHLCV
try:
    from infrastructure.messaging.event_types import DomainEvent
except ImportError:
    # Fallback for when infrastructure dependencies are not available
    DomainEvent = None

logger = logging.getLogger(__name__)


class MarketDataApplicationService:
    """
    Market Data Application Service

    Orchestrates market data operations using CQRS pattern.
    Handles use cases that span multiple domain objects and coordinates
    between command and query operations.

    This service acts as the application layer orchestrator, coordinating
    between the presentation layer and domain layer.
    """

    def __init__(self):
        self.command_bus = get_command_bus()
        self.query_bus = get_query_bus()

    async def update_market_data(self, symbol: str, market_data: MarketData) -> CommandResult:
        """
        Update market data for a symbol

        Args:
            symbol: Trading symbol
            market_data: MarketData entity to update

        Returns:
            CommandResult with operation outcome
        """
        logger.info(f"Application service: Updating market data for {symbol}")

        command = UpdateMarketDataCommand(
            symbol=symbol,
            market_data=market_data
        )

        return await self.command_bus.send(command)

    async def validate_and_update_market_data(self, symbol: str, market_data: MarketData) -> CommandResult:
        """
        Validate and then update market data

        Args:
            symbol: Trading symbol
            market_data: MarketData entity to validate and update

        Returns:
            CommandResult with validation and update outcome
        """
        logger.info(f"Application service: Validating and updating market data for {symbol}")

        # First validate
        validate_command = ValidateMarketDataCommand(market_data=market_data)
        validate_result = await self.command_bus.send(validate_command)

        if not validate_result.success:
            logger.warning(f"Market data validation failed for {symbol}")
            return validate_result

        # If validation passes, update
        update_command = UpdateMarketDataCommand(
            symbol=symbol,
            market_data=market_data
        )

        update_result = await self.command_bus.send(update_command)

        # Combine results
        combined_result = CommandResult(
            success=update_result.success,
            command_id=update_result.command_id,
            data={
                'validation_passed': validate_result.success,
                'update_successful': update_result.success,
                'symbol': symbol
            }
        )

        # Add events from both operations
        if validate_result.events:
            for event in validate_result.events:
                combined_result.add_event(event)
        if update_result.events:
            for event in update_result.events:
                combined_result.add_event(event)

        if not update_result.success:
            combined_result.error_message = update_result.error_message

        return combined_result

    async def process_market_data_batch(self, batch: MarketDataBatch) -> CommandResult:
        """
        Process a batch of market data

        Args:
            batch: MarketDataBatch to process

        Returns:
            CommandResult with batch processing outcome
        """
        logger.info(f"Application service: Processing market data batch for {batch.symbol}")

        command = ProcessMarketDataBatchCommand(batch=batch)
        return await self.command_bus.send(command)

    async def get_current_market_data(self, symbol: str, timeframe: str = "1D") -> QueryResult:
        """
        Get current market data for a symbol

        Args:
            symbol: Trading symbol
            timeframe: Data timeframe

        Returns:
            QueryResult with current market data
        """
        logger.info(f"Application service: Getting current market data for {symbol}")

        query = GetMarketDataQuery(symbol=symbol, timeframe=timeframe)
        return await self.query_bus.send(query)

    async def get_market_data_history(
        self,
        symbol: str,
        timeframe: str = "1D",
        days: int = 30,
        limit: int = 1000
    ) -> QueryResult:
        """
        Get historical market data for a symbol

        Args:
            symbol: Trading symbol
            timeframe: Data timeframe
            days: Number of days of history
            limit: Maximum number of records

        Returns:
            QueryResult with historical market data
        """
        logger.info(f"Application service: Getting {days} days of history for {symbol}")

        end_date = datetime.now()
        start_date = end_date.replace(day=end_date.day - days)

        query = GetMarketDataHistoryQuery(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return await self.query_bus.send(query)

    async def get_market_data_summary(self, symbol: str, analysis_period_days: int = 30) -> QueryResult:
        """
        Get comprehensive market data summary

        Args:
            symbol: Trading symbol
            analysis_period_days: Period for analysis

        Returns:
            QueryResult with market data summary
        """
        logger.info(f"Application service: Getting summary for {symbol}")

        query = GetMarketDataSummaryQuery(
            symbol=symbol,
            analysis_period_days=analysis_period_days
        )

        return await self.query_bus.send(query)

    async def create_market_data_from_raw(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int,
        exchange: str = "NSE"
    ) -> MarketData:
        """
        Create MarketData entity from raw price data

        Args:
            symbol: Trading symbol
            timestamp: Data timestamp
            open_price: Opening price
            high_price: High price
            low_price: Low price
            close_price: Closing price
            volume: Trading volume
            exchange: Exchange name

        Returns:
            MarketData entity
        """
        # Create OHLCV value object
        ohlcv = OHLCV(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume
        )

        # Create MarketData entity
        market_data = MarketData(
            symbol=symbol,
            timestamp=timestamp.isoformat(),
            timeframe="1D",  # Default timeframe
            ohlcv=ohlcv,
            date_partition=timestamp.strftime("%Y-%m-%d")
        )

        return market_data

    async def bulk_update_market_data(self, updates: List[Dict[str, Any]]) -> List[CommandResult]:
        """
        Bulk update multiple market data records

        Args:
            updates: List of update dictionaries with symbol and market_data

        Returns:
            List of CommandResult objects
        """
        logger.info(f"Application service: Bulk updating {len(updates)} market data records")

        results = []

        for update in updates:
            symbol = update['symbol']
            market_data = update['market_data']

            result = await self.update_market_data(symbol, market_data)
            results.append(result)

        successful = sum(1 for r in results if r.success)
        logger.info(f"Bulk update completed: {successful}/{len(results)} successful")

        return results

    async def get_market_health_status(self) -> Dict[str, Any]:
        """
        Get overall market data system health status

        Returns:
            Dictionary with health metrics
        """
        logger.info("Application service: Getting market health status")

        # This would typically aggregate health from multiple sources
        # For now, return basic status
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'command_bus': 'operational',
                'query_bus': 'operational',
                'domain_services': 'operational'
            },
            'metrics': {
                'active_symbols': 0,  # Would be populated from repository
                'data_points_today': 0,
                'last_update': datetime.now().isoformat()
            }
        }

    async def validate_market_data_quality(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Validate market data quality over a date range

        Args:
            symbol: Trading symbol
            start_date: Start of validation period
            end_date: End of validation period

        Returns:
            Dictionary with quality metrics
        """
        logger.info(f"Application service: Validating data quality for {symbol}")

        # Get historical data
        history_result = await self.get_market_data_history(
            symbol=symbol,
            days=(end_date - start_date).days
        )

        if not history_result.success or not history_result.data:
            return {
                'symbol': symbol,
                'quality_score': 0.0,
                'issues': ['No data available for validation']
            }

        data = history_result.data
        total_records = len(data)
        issues = []

        # Check for data gaps
        expected_records = (end_date - start_date).days
        if total_records < expected_records * 0.8:  # Less than 80% of expected data
            issues.append(f"Data gaps detected: {total_records}/{expected_records} records")

        # Check for price anomalies
        prices = [record.ohlcv.close for record in data]
        if prices:
            avg_price = sum(prices) / len(prices)
            anomalies = sum(1 for price in prices if abs(price - avg_price) / avg_price > 0.5)
            if anomalies > len(prices) * 0.1:  # More than 10% anomalies
                issues.append(f"Price anomalies detected: {anomalies}/{len(prices)} records")

        # Calculate quality score
        quality_score = 1.0
        if issues:
            quality_score -= len(issues) * 0.2  # Reduce score for each issue
        quality_score = max(0.0, min(1.0, quality_score))

        return {
            'symbol': symbol,
            'quality_score': quality_score,
            'total_records': total_records,
            'issues': issues,
            'validation_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
