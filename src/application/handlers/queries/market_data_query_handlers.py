"""
Market Data Query Handlers
CQRS query handlers for market data read operations
"""

import logging
from typing import List, Optional
from datetime import datetime
import time

from ...queries.base_query import QueryHandler, QueryResult
from ...queries.market_data_queries import (
    GetMarketDataQuery,
    GetMarketDataHistoryQuery,
    GetMarketDataSummaryQuery
)
from domain.market_data.repositories.market_data_repository import MarketDataRepository
from domain.market_data.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class GetMarketDataQueryHandler(QueryHandler):
    """
    Handler for GetMarketDataQuery
    Retrieves current market data for a symbol
    """

    def __init__(self, repository: MarketDataRepository):
        self.repository = repository

    @property
    def handled_query_type(self) -> str:
        return "GetMarketData"

    async def handle(self, query: GetMarketDataQuery) -> QueryResult:
        """
        Handle get market data query

        Args:
            query: GetMarketDataQuery with symbol and timeframe

        Returns:
            QueryResult with current market data
        """
        start_time = time.time()

        try:
            logger.info(f"Retrieving market data for {query.symbol}")

            # Get latest market data
            market_data = await self.repository.find_latest_by_symbol(
                query.symbol,
                query.timeframe
            )

            execution_time = time.time() - start_time

            if market_data:
                logger.info(f"Found market data for {query.symbol}")
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=market_data,
                    execution_time=execution_time,
                    metadata={
                        'symbol': query.symbol,
                        'timeframe': query.timeframe,
                        'data_found': True
                    }
                )
            else:
                logger.info(f"No market data found for {query.symbol}")
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None,
                    execution_time=execution_time,
                    metadata={
                        'symbol': query.symbol,
                        'timeframe': query.timeframe,
                        'data_found': False
                    }
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error retrieving market data for {query.symbol}: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e),
                execution_time=execution_time
            )


class GetMarketDataHistoryQueryHandler(QueryHandler):
    """
    Handler for GetMarketDataHistoryQuery
    Retrieves historical market data for analysis
    """

    def __init__(self, repository: MarketDataRepository, market_data_service: MarketDataService):
        self.repository = repository
        self.market_data_service = market_data_service

    @property
    def handled_query_type(self) -> str:
        return "GetMarketDataHistory"

    async def handle(self, query: GetMarketDataHistoryQuery) -> QueryResult:
        """
        Handle get market data history query

        Args:
            query: GetMarketDataHistoryQuery with parameters

        Returns:
            QueryResult with historical market data
        """
        start_time = time.time()

        try:
            logger.info(f"Retrieving market data history for {query.symbol}")

            # Use service for business logic (includes filtering)
            historical_data = await self.market_data_service.get_price_history(
                symbol=query.symbol,
                timeframe=query.timeframe,
                days=(query.end_date - query.start_date).days if query.start_date and query.end_date else 30
            )

            # Apply limit if specified
            if len(historical_data) > query.limit:
                historical_data = historical_data[:query.limit]

            execution_time = time.time() - start_time

            logger.info(f"Retrieved {len(historical_data)} historical records for {query.symbol}")

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data=historical_data,
                execution_time=execution_time,
                metadata={
                    'symbol': query.symbol,
                    'timeframe': query.timeframe,
                    'record_count': len(historical_data),
                    'date_range': {
                        'start': query.start_date.isoformat() if query.start_date else None,
                        'end': query.end_date.isoformat() if query.end_date else None
                    }
                }
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error retrieving market data history for {query.symbol}: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e),
                execution_time=execution_time
            )


class GetMarketDataSummaryQueryHandler(QueryHandler):
    """
    Handler for GetMarketDataSummaryQuery
    Provides market data analysis and summary statistics
    """

    def __init__(self, market_data_service: MarketDataService):
        self.market_data_service = market_data_service

    @property
    def handled_query_type(self) -> str:
        return "GetMarketDataSummary"

    async def handle(self, query: GetMarketDataSummaryQuery) -> QueryResult:
        """
        Handle get market data summary query

        Args:
            query: GetMarketDataSummaryQuery with analysis parameters

        Returns:
            QueryResult with market data summary
        """
        start_time = time.time()

        try:
            logger.info(f"Generating market data summary for {query.symbol}")

            # Use service for comprehensive analysis
            summary = await self.market_data_service.get_market_summary(
                symbol=query.symbol
            )

            execution_time = time.time() - start_time

            if summary and 'error' not in summary:
                logger.info(f"Generated market data summary for {query.symbol}")
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=summary,
                    execution_time=execution_time,
                    metadata={
                        'symbol': query.symbol,
                        'analysis_period_days': query.analysis_period_days,
                        'analysis_type': 'comprehensive_summary'
                    }
                )
            else:
                error_msg = summary.get('error', 'Failed to generate summary') if summary else 'No data available'
                logger.warning(f"Failed to generate summary for {query.symbol}: {error_msg}")
                return QueryResult(
                    success=False,
                    query_id=query.query_id,
                    error_message=error_msg,
                    execution_time=execution_time
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error generating market data summary for {query.symbol}: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e),
                execution_time=execution_time
            )
