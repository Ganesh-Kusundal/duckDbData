"""
Analytics Domain Query Handlers

Query handlers for analytics operations that retrieve and process
analytics data efficiently.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from application.queries.base_query import QueryHandler, QueryResult
from application.queries.analytics_queries import (
    GetIndicatorByIdQuery, GetIndicatorsBySymbolQuery, GetAnalysisByIdQuery,
    GetAnalysisHistoryQuery, GetSignalHistoryQuery
)
from domain.analytics.repositories.indicator_repository import IndicatorRepository
from domain.analytics.repositories.analysis_repository import AnalysisRepository
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class GetIndicatorByIdQueryHandler(QueryHandler):
    """
    Handler for GetIndicatorByIdQuery.

    Retrieves a specific indicator by its ID.
    """

    def __init__(self, indicator_repository: Optional[IndicatorRepository] = None):
        self.indicator_repository = indicator_repository

    @property
    def handled_query_type(self) -> str:
        return "GetIndicatorById"

    async def handle(self, query: GetIndicatorByIdQuery) -> QueryResult:
        """Handle get indicator by ID query."""
        try:
            logger.info(f"Retrieving indicator {query.indicator_id}")

            if not self.indicator_repository:
                raise DomainException("Indicator repository not available")

            indicator = await self.indicator_repository.find_by_id(query.indicator_id)
            if not indicator:
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None
                )

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "indicator": {
                        "id": indicator.id,
                        "symbol": indicator.symbol,
                        "indicator_type": indicator.indicator_type,
                        "parameters": indicator.parameters,
                        "timeframe": indicator.timeframe,
                        "values": indicator.values,
                        "metadata": indicator.metadata,
                        "created_at": indicator.created_at,
                        "updated_at": indicator.updated_at
                    }
                }
            )

        except Exception as e:
            logger.error(f"Get indicator by ID failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetIndicatorsBySymbolQueryHandler(QueryHandler):
    """
    Handler for GetIndicatorsBySymbolQuery.

    Retrieves indicators for a specific symbol with optional filtering.
    """

    def __init__(self, indicator_repository: Optional[IndicatorRepository] = None):
        self.indicator_repository = indicator_repository

    @property
    def handled_query_type(self) -> str:
        return "GetIndicatorsBySymbol"

    async def handle(self, query: GetIndicatorsBySymbolQuery) -> QueryResult:
        """Handle get indicators by symbol query."""
        try:
            logger.info(f"Retrieving indicators for {query.symbol}")

            if not self.indicator_repository:
                raise DomainException("Indicator repository not available")

            # Build filters
            filters = {"symbol": query.symbol}

            if query.indicator_type:
                filters["indicator_type"] = query.indicator_type

            if query.timeframe:
                filters["timeframe"] = query.timeframe

            # Add date range filter
            if query.start_date or query.end_date:
                if query.start_date:
                    filters["start_date"] = query.start_date
                if query.end_date:
                    filters["end_date"] = query.end_date

            result = await self.indicator_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            indicators = result.data if result.success and result.data else []

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "indicators": [
                        {
                            "id": ind.id,
                            "symbol": ind.symbol,
                            "indicator_type": ind.indicator_type,
                            "parameters": ind.parameters,
                            "timeframe": ind.timeframe,
                            "values_count": len(ind.values) if ind.values else 0,
                            "last_value": ind.values[-1] if ind.values else None,
                            "created_at": ind.created_at
                        }
                        for ind in indicators
                    ],
                    "total_count": len(indicators),
                    "filters_applied": filters
                }
            )

        except Exception as e:
            logger.error(f"Get indicators by symbol failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetAnalysisByIdQueryHandler(QueryHandler):
    """
    Handler for GetAnalysisByIdQuery.

    Retrieves a specific analysis by its ID.
    """

    def __init__(self, analysis_repository: Optional[AnalysisRepository] = None):
        self.analysis_repository = analysis_repository

    @property
    def handled_query_type(self) -> str:
        return "GetAnalysisById"

    async def handle(self, query: GetAnalysisByIdQuery) -> QueryResult:
        """Handle get analysis by ID query."""
        try:
            logger.info(f"Retrieving analysis {query.analysis_id}")

            if not self.analysis_repository:
                raise DomainException("Analysis repository not available")

            analysis = await self.analysis_repository.find_by_id(query.analysis_id)
            if not analysis:
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None
                )

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "analysis": {
                        "id": analysis.id,
                        "name": analysis.name,
                        "symbol": analysis.symbol,
                        "analysis_type": analysis.analysis_type,
                        "parameters": analysis.parameters,
                        "indicators": analysis.indicators,
                        "result": analysis.result,
                        "status": analysis.status,
                        "created_at": analysis.created_at,
                        "completed_at": analysis.completed_at
                    }
                }
            )

        except Exception as e:
            logger.error(f"Get analysis by ID failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetAnalysisHistoryQueryHandler(QueryHandler):
    """
    Handler for GetAnalysisHistoryQuery.

    Retrieves analysis history with filtering and pagination.
    """

    def __init__(self, analysis_repository: Optional[AnalysisRepository] = None):
        self.analysis_repository = analysis_repository

    @property
    def handled_query_type(self) -> str:
        return "GetAnalysisHistory"

    async def handle(self, query: GetAnalysisHistoryQuery) -> QueryResult:
        """Handle get analysis history query."""
        try:
            logger.info(f"Retrieving analysis history for {query.symbol}")

            if not self.analysis_repository:
                raise DomainException("Analysis repository not available")

            # Build filters
            filters = {}
            if query.symbol:
                filters["symbol"] = query.symbol
            if query.analysis_type:
                filters["analysis_type"] = query.analysis_type
            if query.status:
                filters["status"] = query.status

            # Add date range filter
            if query.start_date or query.end_date:
                if query.start_date:
                    filters["start_date"] = query.start_date
                if query.end_date:
                    filters["end_date"] = query.end_date

            result = await self.analysis_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            analyses = result.data if result.success and result.data else []

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "analyses": [
                        {
                            "id": analysis.id,
                            "name": analysis.name,
                            "symbol": analysis.symbol,
                            "analysis_type": analysis.analysis_type,
                            "status": analysis.status,
                            "result_summary": self._summarize_result(analysis.result),
                            "completed_at": analysis.completed_at
                        }
                        for analysis in analyses
                    ],
                    "total_count": len(analyses),
                    "filters_applied": filters
                }
            )

        except Exception as e:
            logger.error(f"Get analysis history failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )

    def _summarize_result(self, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of analysis results."""
        if not result:
            return {"status": "no_results"}

        summary = {"status": "completed"}

        # Add key metrics from result
        if "analysis_score" in result:
            summary["score"] = result["analysis_score"]
        if "signals_generated" in result:
            summary["signals"] = result["signals_generated"]
        if "confidence_level" in result:
            summary["confidence"] = result["confidence_level"]

        return summary


class GetSignalHistoryQueryHandler(QueryHandler):
    """
    Handler for GetSignalHistoryQuery.

    Retrieves signal history for analysis and backtesting purposes.
    """

    def __init__(self, analysis_repository: Optional[AnalysisRepository] = None):
        self.analysis_repository = analysis_repository

    @property
    def handled_query_type(self) -> str:
        return "GetSignalHistory"

    async def handle(self, query: GetSignalHistoryQuery) -> QueryResult:
        """Handle get signal history query."""
        try:
            logger.info(f"Retrieving signal history for {query.symbol}")

            if not self.analysis_repository:
                raise DomainException("Analysis repository not available")

            # Get analyses that contain signals
            filters = {
                "symbol": query.symbol,
                "analysis_type": "signal_generation"
            }

            if query.signal_type:
                filters["signal_type"] = query.signal_type

            if query.start_date:
                filters["start_date"] = query.start_date
            if query.end_date:
                filters["end_date"] = query.end_date

            result = await self.analysis_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            analyses = result.data if result.success and result.data else []

            # Extract signals from analysis results
            signals = []
            for analysis in analyses:
                if analysis.result and "signals" in analysis.result:
                    for signal in analysis.result["signals"]:
                        signals.append({
                            "analysis_id": analysis.id,
                            "symbol": analysis.symbol,
                            "signal_type": signal.get("type"),
                            "strength": signal.get("strength", 0),
                            "indicator": signal.get("indicator"),
                            "reason": signal.get("reason"),
                            "timestamp": signal.get("timestamp", analysis.completed_at),
                            "analysis_timestamp": analysis.completed_at
                        })

            # Sort by timestamp (most recent first)
            signals.sort(key=lambda x: x["timestamp"], reverse=True)

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "signals": signals[:query.limit] if query.limit else signals,
                    "total_count": len(signals),
                    "symbol": query.symbol,
                    "signal_types": list(set(s["signal_type"] for s in signals if s["signal_type"]))
                }
            )

        except Exception as e:
            logger.error(f"Get signal history failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )
