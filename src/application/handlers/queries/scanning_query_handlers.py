"""
Scanning Domain Query Handlers

Query handlers for scanning operations that retrieve scan results
and rule configurations efficiently.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from application.queries.base_query import QueryHandler, QueryResult
from application.queries.scanning_queries import (
    GetScanByIdQuery, GetScanResultsQuery, GetRuleByIdQuery,
    GetRulesByTypeQuery, GetScanHistoryQuery
)
from domain.scanning.repositories.scan_repository import ScanRepository
from domain.scanning.repositories.rule_repository import RuleRepository
from domain.shared.exceptions import DomainException

logger = logging.getLogger(__name__)


class GetScanByIdQueryHandler(QueryHandler):
    """
    Handler for GetScanByIdQuery.

    Retrieves a specific scan by its ID.
    """

    def __init__(self, scan_repository: Optional[ScanRepository] = None):
        self.scan_repository = scan_repository

    @property
    def handled_query_type(self) -> str:
        return "GetScanById"

    async def handle(self, query: GetScanByIdQuery) -> QueryResult:
        """Handle get scan by ID query."""
        try:
            logger.info(f"Retrieving scan {query.scan_id}")

            if not self.scan_repository:
                raise DomainException("Scan repository not available")

            scan = await self.scan_repository.find_by_id(query.scan_id)
            if not scan:
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None
                )

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "scan": {
                        "id": scan.id,
                        "name": scan.name,
                        "symbol": scan.symbol,
                        "scan_type": scan.scan_type,
                        "criteria": scan.criteria,
                        "timeframe": scan.timeframe,
                        "results": scan.results,
                        "status": scan.status,
                        "execution_time": scan.execution_time,
                        "metadata": scan.metadata,
                        "created_at": scan.created_at,
                        "completed_at": scan.completed_at
                    }
                }
            )

        except Exception as e:
            logger.error(f"Get scan by ID failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetScanResultsQueryHandler(QueryHandler):
    """
    Handler for GetScanResultsQuery.

    Retrieves scan results with filtering and pagination.
    """

    def __init__(self, scan_repository: Optional[ScanRepository] = None):
        self.scan_repository = scan_repository

    @property
    def handled_query_type(self) -> str:
        return "GetScanResults"

    async def handle(self, query: GetScanResultsQuery) -> QueryResult:
        """Handle get scan results query."""
        try:
            logger.info(f"Retrieving scan results for {query.symbol or 'all symbols'}")

            if not self.scan_repository:
                raise DomainException("Scan repository not available")

            # Build filters
            filters = {}
            if query.symbol:
                filters["symbol"] = query.symbol
            if query.scan_type:
                filters["scan_type"] = query.scan_type
            if query.status:
                filters["status"] = query.status

            # Add date range filter
            if query.start_date or query.end_date:
                if query.start_date:
                    filters["start_date"] = query.start_date
                if query.end_date:
                    filters["end_date"] = query.end_date

            result = await self.scan_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            scans = result.data if result.success and result.data else []

            # Extract and aggregate results
            all_results = []
            for scan in scans:
                if scan.results:
                    for result_item in scan.results:
                        result_item["scan_id"] = scan.id
                        result_item["scan_type"] = scan.scan_type
                        result_item["executed_at"] = scan.completed_at
                        all_results.append(result_item)

            # Sort by timestamp (most recent first)
            all_results.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "results": all_results[:query.limit] if query.limit else all_results,
                    "total_count": len(all_results),
                    "scans_processed": len(scans),
                    "filters_applied": filters,
                    "result_types": list(set(r.get("signal_type") for r in all_results if r.get("signal_type")))
                }
            )

        except Exception as e:
            logger.error(f"Get scan results failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetRuleByIdQueryHandler(QueryHandler):
    """
    Handler for GetRuleByIdQuery.

    Retrieves a specific scanning rule by its ID.
    """

    def __init__(self, rule_repository: Optional[RuleRepository] = None):
        self.rule_repository = rule_repository

    @property
    def handled_query_type(self) -> str:
        return "GetRuleById"

    async def handle(self, query: GetRuleByIdQuery) -> QueryResult:
        """Handle get rule by ID query."""
        try:
            logger.info(f"Retrieving rule {query.rule_id}")

            if not self.rule_repository:
                raise DomainException("Rule repository not available")

            rule = await self.rule_repository.find_by_id(query.rule_id)
            if not rule:
                return QueryResult(
                    success=True,
                    query_id=query.query_id,
                    data=None
                )

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "rule": {
                        "id": rule.id,
                        "name": rule.name,
                        "rule_type": rule.rule_type,
                        "conditions": rule.conditions,
                        "actions": rule.actions,
                        "parameters": rule.parameters,
                        "is_active": rule.is_active,
                        "priority": rule.priority,
                        "metadata": rule.metadata,
                        "created_at": rule.created_at,
                        "updated_at": rule.updated_at
                    }
                }
            )

        except Exception as e:
            logger.error(f"Get rule by ID failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetRulesByTypeQueryHandler(QueryHandler):
    """
    Handler for GetRulesByTypeQuery.

    Retrieves rules filtered by type with pagination.
    """

    def __init__(self, rule_repository: Optional[RuleRepository] = None):
        self.rule_repository = rule_repository

    @property
    def handled_query_type(self) -> str:
        return "GetRulesByType"

    async def handle(self, query: GetRulesByTypeQuery) -> QueryResult:
        """Handle get rules by type query."""
        try:
            logger.info(f"Retrieving rules of type {query.rule_type}")

            if not self.rule_repository:
                raise DomainException("Rule repository not available")

            # Build filters
            filters = {"rule_type": query.rule_type}
            if query.is_active is not None:
                filters["is_active"] = query.is_active

            result = await self.rule_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            rules = result.data if result.success and result.data else []

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "rules": [
                        {
                            "id": rule.id,
                            "name": rule.name,
                            "rule_type": rule.rule_type,
                            "conditions": rule.conditions,
                            "actions": rule.actions,
                            "is_active": rule.is_active,
                            "priority": rule.priority,
                            "created_at": rule.created_at
                        }
                        for rule in rules
                    ],
                    "total_count": len(rules),
                    "rule_type": query.rule_type,
                    "active_only": query.is_active
                }
            )

        except Exception as e:
            logger.error(f"Get rules by type failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )


class GetScanHistoryQueryHandler(QueryHandler):
    """
    Handler for GetScanHistoryQuery.

    Retrieves scan execution history for monitoring and analysis.
    """

    def __init__(self, scan_repository: Optional[ScanRepository] = None):
        self.scan_repository = scan_repository

    @property
    def handled_query_type(self) -> str:
        return "GetScanHistory"

    async def handle(self, query: GetScanHistoryQuery) -> QueryResult:
        """Handle get scan history query."""
        try:
            logger.info(f"Retrieving scan history for {query.symbol or 'all symbols'}")

            if not self.scan_repository:
                raise DomainException("Scan repository not available")

            # Build filters
            filters = {}
            if query.symbol:
                filters["symbol"] = query.symbol
            if query.scan_type:
                filters["scan_type"] = query.scan_type
            if query.status:
                filters["status"] = query.status

            # Add date range filter
            if query.start_date or query.end_date:
                if query.start_date:
                    filters["start_date"] = query.start_date
                if query.end_date:
                    filters["end_date"] = query.end_date

            result = await self.scan_repository.find_by_criteria(
                filters, limit=query.limit, offset=query.offset
            )

            scans = result.data if result.success and result.data else []

            # Calculate summary statistics
            total_scans = len(scans)
            completed_scans = sum(1 for s in scans if s.status == "COMPLETED")
            failed_scans = sum(1 for s in scans if s.status == "FAILED")
            avg_execution_time = sum(s.execution_time for s in scans if s.execution_time) / max(1, sum(1 for s in scans if s.execution_time))

            return QueryResult(
                success=True,
                query_id=query.query_id,
                data={
                    "scans": [
                        {
                            "id": scan.id,
                            "name": scan.name,
                            "symbol": scan.symbol,
                            "scan_type": scan.scan_type,
                            "status": scan.status,
                            "results_count": len(scan.results) if scan.results else 0,
                            "execution_time": scan.execution_time,
                            "completed_at": scan.completed_at
                        }
                        for scan in scans
                    ],
                    "summary": {
                        "total_scans": total_scans,
                        "completed_scans": completed_scans,
                        "failed_scans": failed_scans,
                        "success_rate": (completed_scans / max(1, total_scans)) * 100,
                        "average_execution_time": avg_execution_time
                    },
                    "filters_applied": filters
                }
            )

        except Exception as e:
            logger.error(f"Get scan history failed: {e}")
            return QueryResult(
                success=False,
                query_id=query.query_id,
                error_message=str(e)
            )
